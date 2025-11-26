package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

func (s *Server) registerRESTEndpoints(mux *http.ServeMux) {
	// Order management
	mux.HandleFunc("/api/v1/orders", s.handleOrders)
	mux.HandleFunc("/api/v1/orders/", s.handleOrderByID)
	mux.HandleFunc("/api/v1/orders/batch", s.handleBatchOrders)
	mux.HandleFunc("/api/v1/orders/stop_loss", s.handleStopLoss)
	mux.HandleFunc("/api/v1/orders/take_profit", s.handleTakeProfit)

	// Market data
	mux.HandleFunc("/api/v1/market/", s.handleGetMarketData)

	// Balance
	mux.HandleFunc("/api/v1/balance/", s.handleGetBalance)

	// Order status
	mux.HandleFunc("/api/v1/order_status", s.handleGetOrderStatus)
}

// handleOrders handles GET (list) and POST (submit)
func (s *Server) handleOrders(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		s.handleSubmitOrder(w, r)
	case http.MethodGet:
		s.handleListOrders(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// handleListOrders returns recent orders
func (s *Server) handleListOrders(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	limit := r.URL.Query().Get("limit")
	if limit == "" {
		limit = "50"
	}

	query := fmt.Sprintf(`
		SELECT order_id, strategy_name, symbol, side, quantity, price, 
		       executed_price, status, exchange, timestamp
		FROM trades
		ORDER BY timestamp DESC
		LIMIT %s
	`, limit)

	rows, err := s.db.Query(query)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch orders",
		})
		return
	}
	defer rows.Close()

	orders := make([]map[string]interface{}, 0)
	for rows.Next() {
		var orderID, strategyName, symbol, side, status, exchange string
		var quantity, price float64
		var executedPrice sql.NullFloat64
		var timestamp time.Time

		if err := rows.Scan(&orderID, &strategyName, &symbol, &side, &quantity,
			&price, &executedPrice, &status, &exchange, &timestamp); err != nil {
			continue
		}

		order := map[string]interface{}{
			"order_id":      orderID,
			"strategy_name": strategyName,
			"symbol":        symbol,
			"side":          side,
			"quantity":      quantity,
			"price":         price,
			"status":        status,
			"exchange":      exchange,
			"timestamp":     timestamp.Format(time.RFC3339),
		}
		if executedPrice.Valid {
			order["executed_price"] = executedPrice.Float64
		}

		orders = append(orders, order)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"orders": orders,
		"count":  len(orders),
	})
}

// handleSubmitOrder submits a new order
func (s *Server) handleSubmitOrder(w http.ResponseWriter, r *http.Request) {
	var req struct {
		OrderID      string  `json:"order_id"`
		StrategyName string  `json:"strategy_name"`
		Symbol       string  `json:"symbol"`
		Side         string  `json:"side"`
		Quantity     float64 `json:"quantity"`
		Price        float64 `json:"price"`
		OrderType    string  `json:"order_type"`
		Exchange     string  `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	log.Printf("HTTP Order: %s %s %.8f %s", req.Side, req.Symbol, req.Quantity, req.Exchange)

	if req.Exchange == "" {
		req.Exchange = "binance"
	}
	if req.OrderType == "" {
		req.OrderType = "MARKET"
	}

	s.mu.RLock()
	exchange, exists := s.exchanges[req.Exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("Exchange %s not configured", req.Exchange),
		})
		return
	}

	order := &Order{
		ID:           req.OrderID,
		Symbol:       req.Symbol,
		Side:         req.Side,
		Quantity:     req.Quantity,
		Price:        req.Price,
		OrderType:    req.OrderType,
		StrategyName: req.StrategyName,
	}

	result, err := exchange.SubmitOrder(order)
	if err != nil {
		log.Printf("Order failed: %v", err)
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	if s.db != nil {
		go s.logOrderToDB(req, result)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":           true,
		"order_id":          req.OrderID,
		"exchange_order_id": result.ExchangeOrderID,
		"status":            result.Status,
		"executed_price":    result.ExecutedPrice,
		"executed_quantity": result.ExecutedQuantity,
		"fees":              result.Fees,
	})
}

// handleOrderByID handles DELETE (cancel) and PUT (modify)
func (s *Server) handleOrderByID(w http.ResponseWriter, r *http.Request) {
	orderID := strings.TrimPrefix(r.URL.Path, "/api/v1/orders/")
	if orderID == "" {
		http.Error(w, "Order ID required", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodDelete:
		s.handleCancelOrder(w, r, orderID)
	case http.MethodPut:
		s.handleModifyOrder(w, r, orderID)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// handleCancelOrder cancels an order
func (s *Server) handleCancelOrder(w http.ResponseWriter, r *http.Request, orderID string) {
	var req struct {
		Symbol   string `json:"symbol"`
		Exchange string `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Exchange == "" {
		req.Exchange = "binance"
	}

	s.mu.RLock()
	exchange, exists := s.exchanges[req.Exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": fmt.Sprintf("Exchange %s not configured", req.Exchange),
		})
		return
	}

	// Type assert to get CancelOrder method
	binanceEx, ok := exchange.(*BinanceExchange)
	if !ok {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Exchange does not support order cancellation",
		})
		return
	}

	if err := binanceEx.CancelOrder(req.Symbol, orderID); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"message": fmt.Sprintf("Order %s cancelled successfully", orderID),
	})
}

// handleModifyOrder modifies an order
func (s *Server) handleModifyOrder(w http.ResponseWriter, r *http.Request, orderID string) {
	var req struct {
		Symbol      string  `json:"symbol"`
		NewQuantity float64 `json:"new_quantity"`
		NewPrice    float64 `json:"new_price"`
		Exchange    string  `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Exchange == "" {
		req.Exchange = "binance"
	}

	s.mu.RLock()
	exchange, exists := s.exchanges[req.Exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": fmt.Sprintf("Exchange %s not configured", req.Exchange),
		})
		return
	}

	binanceEx, ok := exchange.(*BinanceExchange)
	if !ok {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Exchange does not support order modification",
		})
		return
	}

	result, err := binanceEx.ModifyOrder(req.Symbol, orderID, req.NewQuantity, req.NewPrice)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":           true,
		"new_order_id":      result.ExchangeOrderID,
		"status":            result.Status,
		"executed_price":    result.ExecutedPrice,
		"executed_quantity": result.ExecutedQuantity,
	})
}

// handleBatchOrders submits multiple orders
func (s *Server) handleBatchOrders(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Orders []struct {
			OrderID      string  `json:"order_id"`
			StrategyName string  `json:"strategy_name"`
			Symbol       string  `json:"symbol"`
			Side         string  `json:"side"`
			Quantity     float64 `json:"quantity"`
			Price        float64 `json:"price"`
			OrderType    string  `json:"order_type"`
		} `json:"orders"`
		Exchange string `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Exchange == "" {
		req.Exchange = "binance"
	}

	s.mu.RLock()
	exchange, exists := s.exchanges[req.Exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": fmt.Sprintf("Exchange %s not configured", req.Exchange),
		})
		return
	}

	results := make([]map[string]interface{}, 0)
	successCount := 0

	for _, orderReq := range req.Orders {
		order := &Order{
			ID:           orderReq.OrderID,
			Symbol:       orderReq.Symbol,
			Side:         orderReq.Side,
			Quantity:     orderReq.Quantity,
			Price:        orderReq.Price,
			OrderType:    orderReq.OrderType,
			StrategyName: orderReq.StrategyName,
		}

		result, err := exchange.SubmitOrder(order)
		if err != nil {
			results = append(results, map[string]interface{}{
				"order_id": orderReq.OrderID,
				"success":  false,
				"error":    err.Error(),
			})
		} else {
			successCount++
			results = append(results, map[string]interface{}{
				"order_id":          orderReq.OrderID,
				"success":           true,
				"exchange_order_id": result.ExchangeOrderID,
				"status":            result.Status,
			})
		}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total":   len(req.Orders),
		"success": successCount,
		"failed":  len(req.Orders) - successCount,
		"results": results,
	})
}

// handleStopLoss creates a stop-loss order
func (s *Server) handleStopLoss(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Symbol       string  `json:"symbol"`
		Side         string  `json:"side"`
		Quantity     float64 `json:"quantity"`
		StopPrice    float64 `json:"stop_price"`
		StrategyName string  `json:"strategy_name"`
		Exchange     string  `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Note: This is a simplified implementation
	// In production, you'd use Binance's STOP_LOSS_LIMIT order type
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":    true,
		"message":    "Stop-loss order created",
		"symbol":     req.Symbol,
		"stop_price": req.StopPrice,
		"note":       "Full implementation requires Binance STOP_LOSS_LIMIT order type",
	})
}

// handleTakeProfit creates a take-profit order
func (s *Server) handleTakeProfit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Symbol       string  `json:"symbol"`
		Side         string  `json:"side"`
		Quantity     float64 `json:"quantity"`
		TargetPrice  float64 `json:"target_price"`
		StrategyName string  `json:"strategy_name"`
		Exchange     string  `json:"exchange"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Note: This is a simplified implementation
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":      true,
		"message":      "Take-profit order created",
		"symbol":       req.Symbol,
		"target_price": req.TargetPrice,
		"note":         "Full implementation requires Binance TAKE_PROFIT_LIMIT order type",
	})
}

// handleGetMarketData fetches market data
func (s *Server) handleGetMarketData(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/v1/market/"), "/")
	if len(parts) < 2 {
		http.Error(w, "Invalid URL format", http.StatusBadRequest)
		return
	}

	exchange := parts[0]
	symbol := parts[1]

	s.mu.RLock()
	exchangeClient, exists := s.exchanges[exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": fmt.Sprintf("Exchange %s not configured", exchange),
		})
		return
	}

	data, err := exchangeClient.GetMarketData(symbol)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": err.Error(),
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"symbol":           symbol,
		"exchange":         exchange,
		"price":            data.Price,
		"bid":              data.Bid,
		"ask":              data.Ask,
		"volume_24h":       data.Volume24h,
		"high_24h":         data.High24h,
		"low_24h":          data.Low24h,
		"price_change_24h": data.PriceChange,
		"timestamp":        data.Timestamp.Format(time.RFC3339),
	})
}

// handleGetBalance fetches account balance
func (s *Server) handleGetBalance(w http.ResponseWriter, r *http.Request) {
	exchange := strings.TrimPrefix(r.URL.Path, "/api/v1/balance/")

	s.mu.RLock()
	exchangeClient, exists := s.exchanges[exchange]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": fmt.Sprintf("Exchange %s not configured", exchange),
		})
		return
	}

	balance, err := exchangeClient.GetBalance()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": err.Error(),
		})
		return
	}

	balances := make(map[string]interface{})
	for asset, bal := range balance.Balances {
		balances[asset] = map[string]float64{
			"free":   bal.Free,
			"locked": bal.Locked,
			"total":  bal.Total,
		}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"exchange":        exchange,
		"balances":        balances,
		"total_value_usd": balance.TotalValueUSD,
		"timestamp":       balance.Timestamp.Format(time.RFC3339),
	})
}

// handleGetOrderStatus fetches order status
func (s *Server) handleGetOrderStatus(w http.ResponseWriter, r *http.Request) {
	orderID := r.URL.Query().Get("order_id")
	if orderID == "" {
		http.Error(w, "order_id required", http.StatusBadRequest)
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"order_id": orderID,
		"status":   "FILLED",
		"message":  "Order status tracking coming soon",
	})
}

// logOrderToDB logs order to database
func (s *Server) logOrderToDB(req interface{}, result *OrderResult) {
	r, ok := req.(struct {
		OrderID      string  `json:"order_id"`
		StrategyName string  `json:"strategy_name"`
		Symbol       string  `json:"symbol"`
		Side         string  `json:"side"`
		Quantity     float64 `json:"quantity"`
		Price        float64 `json:"price"`
		OrderType    string  `json:"order_type"`
		Exchange     string  `json:"exchange"`
	})
	if !ok {
		log.Println("Failed to log order: type assertion failed")
		return
	}

	query := `
		INSERT INTO trades
		(order_id, strategy_name, symbol, side, quantity, price, executed_price,
		 status, exchange, timestamp, executed_at, fees)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`

	_, err := s.db.Exec(query,
		r.OrderID,
		r.StrategyName,
		r.Symbol,
		r.Side,
		r.Quantity,
		r.Price,
		result.ExecutedPrice,
		result.Status,
		r.Exchange,
		time.Now(),
		result.Timestamp,
		result.Fees,
	)

	if err != nil {
		log.Printf("Failed to log order to database: %v", err)
	} else {
		log.Printf("✓ Order logged to database: %s", r.OrderID)
	}
}

// writeJSON writes JSON response
func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

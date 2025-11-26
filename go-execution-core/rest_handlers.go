package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

func (s *Server) registerRESTEndpoints(mux *http.ServeMux) {
	// Submit order
	mux.HandleFunc("/api/v1/orders", s.handleSubmitOrder)

	// Get market data
	mux.HandleFunc("/api/v1/market/", s.handleGetMarketData)

	// Get balance
	mux.HandleFunc("/api/v1/balance/", s.handleGetBalance)

	// Get order status
	mux.HandleFunc("/api/v1/order_status", s.handleGetOrderStatus)
}

func (s *Server) handleSubmitOrder(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

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

	// Default values
	if req.Exchange == "" {
		req.Exchange = "binance"
	}
	if req.OrderType == "" {
		req.OrderType = "MARKET"
	}

	// Get exchange
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

	// Create order
	order := &Order{
		ID:           req.OrderID,
		Symbol:       req.Symbol,
		Side:         req.Side,
		Quantity:     req.Quantity,
		Price:        req.Price,
		OrderType:    req.OrderType,
		StrategyName: req.StrategyName,
	}

	// Submit order
	result, err := exchange.SubmitOrder(order)
	if err != nil {
		log.Printf("Order failed: %v", err)
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	// Log to database
	if s.db != nil {
		go s.logOrderToDB(req, result)
	}

	// Return success
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":            true,
		"order_id":           req.OrderID,
		"exchange_order_id":  result.ExchangeOrderID,
		"status":             result.Status,
		"executed_price":     result.ExecutedPrice,
		"executed_quantity":  result.ExecutedQuantity,
		"fees":               result.Fees,
	})
}

func (s *Server) handleGetMarketData(w http.ResponseWriter, r *http.Request) {
	// Parse URL: /api/v1/market/{exchange}/{symbol}
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
		"symbol":             symbol,
		"exchange":           exchange,
		"price":              data.Price,
		"bid":                data.Bid,
		"ask":                data.Ask,
		"volume_24h":         data.Volume24h,
		"high_24h":           data.High24h,
		"low_24h":            data.Low24h,
		"price_change_24h":   data.PriceChange,
		"timestamp":          data.Timestamp.Format(time.RFC3339),
	})
}

func (s *Server) handleGetBalance(w http.ResponseWriter, r *http.Request) {
	// Parse URL: /api/v1/balance/{exchange}
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

	// Convert to JSON-friendly format
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

func (s *Server) handleGetOrderStatus(w http.ResponseWriter, r *http.Request) {
	orderID := r.URL.Query().Get("order_id")
	if orderID == "" {
		http.Error(w, "order_id required", http.StatusBadRequest)
		return
	}

	// For now, just return a placeholder
	// In production, would query exchange
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"order_id": orderID,
		"status":   "FILLED",
		"message":  "Order status tracking coming soon",
	})
}

func (s *Server) logOrderToDB(req interface{}, result *OrderResult) {
	// Type assertion
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

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

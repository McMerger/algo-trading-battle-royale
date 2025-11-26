package main

import (
	"context"
	"fmt"
	"log"
	"time"

	pb "execution-engine/pb"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// Implement pb.UnimplementedExecutionServiceServer to satisfy the interface
// This ensures we implement all required methods from the generated code
func (s *Server) SubmitOrder(ctx context.Context, req *pb.OrderRequest) (*pb.OrderResponse, error) {
	log.Printf("gRPC Order: %s %s %.8f %s", req.Side, req.Symbol, req.Quantity, req.Exchange)

	// Validate request
	if req.Symbol == "" || req.Side == "" || req.Quantity <= 0 {
		return &pb.OrderResponse{
			Success:      false,
			OrderId:      req.OrderId,
			Status:       "REJECTED",
			ErrorMessage: "Invalid order parameters",
		}, nil
	}

	// Determine exchange (default to binance)
	exchange := req.Exchange
	if exchange == "" {
		exchange = "binance"
	}

	// Get exchange client
	s.mu.RLock()
	exchangeClient, exists := s.exchanges[exchange]
	s.mu.RUnlock()

	if !exists {
		return &pb.OrderResponse{
			Success:      false,
			OrderId:      req.OrderId,
			Status:       "REJECTED",
			ErrorMessage: fmt.Sprintf("Exchange %s not configured", exchange),
		}, nil
	}

	// Create order
	order := &Order{
		ID:           req.OrderId,
		Symbol:       req.Symbol,
		Side:         req.Side,
		Quantity:     req.Quantity,
		Price:        req.Price,
		OrderType:    req.OrderType,
		StrategyName: req.StrategyName,
	}

	// Submit to exchange
	result, err := exchangeClient.SubmitOrder(order)
	if err != nil {
		log.Printf("Order submission failed: %v", err)
		return &pb.OrderResponse{
			Success:      false,
			OrderId:      req.OrderId,
			Status:       "FAILED",
			ErrorMessage: err.Error(),
		}, nil
	}

	// Log to database
	if s.db != nil {
		go s.logOrderToDatabase(req, result)
	}

	// Return response
	return &pb.OrderResponse{
		Success:          true,
		OrderId:          req.OrderId,
		ExchangeOrderId:  result.ExchangeOrderID,
		Status:           result.Status,
		ExecutedPrice:    result.ExecutedPrice,
		ExecutedQuantity: result.ExecutedQuantity,
		Fees:             result.Fees,
		ExecutedAt:       timestamppb.New(result.Timestamp),
	}, nil
}

// GetMarketData retrieves current market data
func (s *Server) GetMarketData(ctx context.Context, req *pb.MarketDataRequest) (*pb.MarketDataResponse, error) {
	log.Printf("gRPC Market data: %s on %s", req.Symbol, req.Exchange)

	exchange := req.Exchange
	if exchange == "" {
		exchange = "binance"
	}

	s.mu.RLock()
	exchangeClient, exists := s.exchanges[exchange]
	s.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("exchange %s not configured", exchange)
	}

	data, err := exchangeClient.GetMarketData(req.Symbol)
	if err != nil {
		return nil, fmt.Errorf("failed to get market data: %w", err)
	}

	return &pb.MarketDataResponse{
		Symbol:            req.Symbol,
		Exchange:          exchange,
		Price:             data.Price,
		Bid:               data.Bid,
		Ask:               data.Ask,
		Volume_24H:        data.Volume24h,
		High_24H:          data.High24h,
		Low_24H:           data.Low24h,
		PriceChange_24H:   data.PriceChange,
		PriceChangePct_24H: (data.PriceChange / data.Price) * 100,
		Timestamp:         timestamppb.New(data.Timestamp),
	}, nil
}

// StreamPrices streams real-time price updates (stub for now)
func (s *Server) StreamPrices(req *pb.StreamRequest, stream pb.ExecutionService_StreamPricesServer) error {
	log.Printf("gRPC Stream prices: %v", req.Symbols)
	
	// TODO: Implement actual streaming
	// For now, return a single update
	for _, symbol := range req.Symbols {
		update := &pb.PriceUpdate{
			Symbol:    symbol,
			Price:     0.0,
			Volume:    0.0,
			Timestamp: timestamppb.Now(),
		}
		if err := stream.Send(update); err != nil {
			return err
		}
	}
	
	return nil
}

// GetOrderStatus retrieves order status
func (s *Server) GetOrderStatus(ctx context.Context, req *pb.OrderStatusRequest) (*pb.OrderStatusResponse, error) {
	log.Printf("gRPC Order status: %s", req.OrderId)

	// TODO: Implement actual order status tracking
	// For now, return a placeholder
	return &pb.OrderStatusResponse{
		OrderId:       req.OrderId,
		Status:        "FILLED",
		FilledQuantity: 0.0,
		AveragePrice:  0.0,
		Fees:          0.0,
		UpdatedAt:     timestamppb.Now(),
	}, nil
}

// GetBalance retrieves account balance
func (s *Server) GetBalance(ctx context.Context, req *pb.BalanceRequest) (*pb.BalanceResponse, error) {
	exchange := req.Exchange
	if exchange == "" {
		exchange = "binance"
	}

	log.Printf("gRPC Balance: %s", exchange)

	s.mu.RLock()
	exchangeClient, exists := s.exchanges[exchange]
	s.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("exchange %s not configured", exchange)
	}

	balance, err := exchangeClient.GetBalance()
	if err != nil {
		return nil, fmt.Errorf("failed to get balance: %w", err)
	}

	// Convert to proto format
	balances := make(map[string]*pb.AssetBalance)
	for asset, bal := range balance.Balances {
		balances[asset] = &pb.AssetBalance{
			Asset:    bal.Asset,
			Free:     bal.Free,
			Locked:   bal.Locked,
			Total:    bal.Total,
			ValueUsd: bal.ValueUSD,
		}
	}

	return &pb.BalanceResponse{
		Exchange:      exchange,
		Balances:      balances,
		TotalValueUsd: balance.TotalValueUSD,
		Timestamp:     timestamppb.New(balance.Timestamp),
	}, nil
}

// logOrderToDatabase logs order to PostgreSQL
func (s *Server) logOrderToDatabase(req *pb.OrderRequest, result *OrderResult) {
	query := `
		INSERT INTO trades
		(order_id, strategy_name, symbol, side, quantity, price, executed_price,
		 status, exchange, timestamp, executed_at, fees)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`

	_, err := s.db.Exec(query,
		req.OrderId,
		req.StrategyName,
		req.Symbol,
		req.Side,
		req.Quantity,
		req.Price,
		result.ExecutedPrice,
		result.Status,
		req.Exchange,
		time.Now(),
		result.Timestamp,
		result.Fees,
	)

	if err != nil {
		log.Printf("Failed to log order to database: %v", err)
	} else {
		log.Printf("✓ Order logged to database: %s", req.OrderId)
	}
}

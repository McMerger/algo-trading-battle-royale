package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"

	"google.golang.org/protobuf/types/known/timestamppb"
)

// ExecutionServiceServer implements the gRPC service
// Note: This uses manual struct definitions until protoc generates the actual types
type ExecutionServiceServer struct {
	server *Server
}

func NewExecutionServiceServer(s *Server) *ExecutionServiceServer {
	return &ExecutionServiceServer{server: s}
}

// SubmitOrder handles order submission requests
func (e *ExecutionServiceServer) SubmitOrder(ctx context.Context, req *OrderRequestProto) (*OrderResponseProto, error) {
	log.Printf("Received order: %s %s %s %.8f @ %.8f",
		req.Side, req.Quantity, req.Symbol, req.Quantity, req.Price)

	// Validate request
	if req.Symbol == "" || req.Side == "" || req.Quantity <= 0 {
		return &OrderResponseProto{
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
	e.server.mu.RLock()
	exchangeClient, exists := e.server.exchanges[exchange]
	e.server.mu.RUnlock()

	if !exists {
		return &OrderResponseProto{
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
		return &OrderResponseProto{
			Success:      false,
			OrderId:      req.OrderId,
			Status:       "FAILED",
			ErrorMessage: err.Error(),
		}, nil
	}

	// Log to database
	if e.server.db != nil {
		go e.logOrderToDatabase(req, result)
	}

	// Return response
	return &OrderResponseProto{
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
func (e *ExecutionServiceServer) GetMarketData(ctx context.Context, req *MarketDataRequestProto) (*MarketDataResponseProto, error) {
	log.Printf("Market data request: %s on %s", req.Symbol, req.Exchange)

	exchange := req.Exchange
	if exchange == "" {
		exchange = "binance"
	}

	e.server.mu.RLock()
	exchangeClient, exists := e.server.exchanges[exchange]
	e.server.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("exchange %s not configured", exchange)
	}

	data, err := exchangeClient.GetMarketData(req.Symbol)
	if err != nil {
		return nil, fmt.Errorf("failed to get market data: %w", err)
	}

	return &MarketDataResponseProto{
		Symbol:            req.Symbol,
		Exchange:          exchange,
		Price:             data.Price,
		Bid:               data.Bid,
		Ask:               data.Ask,
		Volume_24H:        data.Volume24h,
		High_24H:          data.High24h,
		Low_24H:           data.Low24h,
		PriceChange_24H:   data.PriceChange,
		Timestamp:         timestamppb.New(data.Timestamp),
	}, nil
}

// GetBalance retrieves account balance
func (e *ExecutionServiceServer) GetBalance(ctx context.Context, req *BalanceRequestProto) (*BalanceResponseProto, error) {
	exchange := req.Exchange
	if exchange == "" {
		exchange = "binance"
	}

	e.server.mu.RLock()
	exchangeClient, exists := e.server.exchanges[exchange]
	e.server.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("exchange %s not configured", exchange)
	}

	balance, err := exchangeClient.GetBalance()
	if err != nil {
		return nil, fmt.Errorf("failed to get balance: %w", err)
	}

	// Convert to proto format
	balances := make(map[string]*AssetBalanceProto)
	for asset, bal := range balance.Balances {
		balances[asset] = &AssetBalanceProto{
			Asset:    bal.Asset,
			Free:     bal.Free,
			Locked:   bal.Locked,
			Total:    bal.Total,
			ValueUsd: bal.ValueUSD,
		}
	}

	return &BalanceResponseProto{
		Exchange:      exchange,
		Balances:      balances,
		TotalValueUsd: balance.TotalValueUSD,
		Timestamp:     timestamppb.New(balance.Timestamp),
	}, nil
}

func (e *ExecutionServiceServer) logOrderToDatabase(req *OrderRequestProto, result *OrderResult) {
	query := `
		INSERT INTO trades
		(order_id, strategy_name, symbol, side, quantity, price, executed_price,
		 status, exchange, timestamp, executed_at, fees)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`

	_, err := e.server.db.Exec(query,
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
	}
}

// Temporary proto message types (until protoc generates real ones)
type OrderRequestProto struct {
	OrderId      string
	StrategyName string
	Symbol       string
	Side         string
	Quantity     float64
	Price        float64
	OrderType    string
	Exchange     string
	Timestamp    *timestamppb.Timestamp
	Metadata     map[string]string
}

type OrderResponseProto struct {
	Success          bool
	OrderId          string
	ExchangeOrderId  string
	Status           string
	ExecutedPrice    float64
	ExecutedQuantity float64
	Fees             float64
	ErrorMessage     string
	ExecutedAt       *timestamppb.Timestamp
}

type MarketDataRequestProto struct {
	Symbol            string
	Exchange          string
	IncludeOrderbook  bool
	OrderbookDepth    int32
}

type MarketDataResponseProto struct {
	Symbol            string
	Exchange          string
	Price             float64
	Bid               float64
	Ask               float64
	Volume_24H        float64
	High_24H          float64
	Low_24H           float64
	PriceChange_24H   float64
	Timestamp         *timestamppb.Timestamp
}

type BalanceRequestProto struct {
	Exchange string
	Assets   []string
}

type BalanceResponseProto struct {
	Exchange      string
	Balances      map[string]*AssetBalanceProto
	TotalValueUsd float64
	Timestamp     *timestamppb.Timestamp
}

type AssetBalanceProto struct {
	Asset    string
	Free     float64
	Locked   float64
	Total    float64
	ValueUsd float64
}

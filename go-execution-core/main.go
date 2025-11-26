// SignalOps Go Execution Engine
// Handles order routing, market data streaming, exchange APIs via gRPC

package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"

	pb "execution-engine/pb"
)

type Config struct {
	GRPCPort      string
	HTTPPort      string
	DatabaseURL   string
	RedisURL      string
	BinanceAPIKey string
	BinanceSecret string
}

type Server struct {
	pb.UnimplementedExecutionServiceServer
	config    *Config
	db        *sql.DB
	redis     *redis.Client
	exchanges map[string]Exchange
	mu        sync.RWMutex
}

func loadConfig() *Config {
	return &Config{
		GRPCPort:      getEnv("GRPC_PORT", "50050"),
		HTTPPort:      getEnv("HTTP_PORT", "8080"),
		DatabaseURL:   getEnv("DATABASE_URL", ""),
		RedisURL:      getEnv("REDIS_URL", "redis:6379"),
		BinanceAPIKey: getEnv("BINANCE_API_KEY", ""),
		BinanceSecret: getEnv("BINANCE_SECRET_KEY", ""),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	log.Println("Starting SignalOps Go Execution Engine...")

	config := loadConfig()

	// Initialize database
	db, err := initDatabase(config.DatabaseURL)
	if err != nil {
		log.Printf("Warning: Database connection failed: %v", err)
		db = nil // Continue without DB for now
	} else {
		defer db.Close()
		log.Println("✓ Connected to PostgreSQL")
	}

	// Initialize Redis
	redisClient := initRedis(config.RedisURL)
	defer redisClient.Close()

	// Ping Redis
	ctx := context.Background()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Printf("Warning: Redis connection failed: %v", err)
	} else {
		log.Println("✓ Connected to Redis")
	}

	// Create server
	server := &Server{
		config:    config,
		db:        db,
		redis:     redisClient,
		exchanges: make(map[string]Exchange),
	}

	// Initialize exchanges
	if config.BinanceAPIKey != "" {
		binance := NewBinanceExchange(config.BinanceAPIKey, config.BinanceSecret)
		server.exchanges["binance"] = binance
		log.Println("✓ Binance exchange initialized")
	}

	// Start gRPC server
	go server.startGRPCServer()

	// Start HTTP server (for health checks and REST fallback)
	go server.startHTTPServer()

	// Wait for shutdown signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down servers...")
}

func (s *Server) startGRPCServer() {
	lis, err := net.Listen("tcp", ":"+s.config.GRPCPort)
	if err != nil {
		log.Fatalf("Failed to listen on port %s: %v", s.config.GRPCPort, err)
	}

	grpcServer := grpc.NewServer()
	// Register gRPC ExecutionService
	pb.RegisterExecutionServiceServer(grpcServer, s)

	log.Printf("✓ gRPC server listening on port %s", s.config.GRPCPort)

	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve gRPC: %v", err)
	}
}

func (s *Server) startHTTPServer() {
	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"healthy","service":"signalops-go-execution"}`))
	})

	// Metrics endpoint (basic)
	mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintf(w, "# SignalOps Execution Engine Metrics\n")
		fmt.Fprintf(w, "signalops_exchanges_connected %d\n", len(s.exchanges))
		fmt.Fprintf(w, "signalops_uptime_seconds %.0f\n", time.Since(startTime).Seconds())
	})

	// REST API endpoints (fallback for Python client)
	s.registerRESTEndpoints(mux)

	// Strategy management endpoints
	s.registerStrategyEndpoints(mux)

	// Portfolio & risk endpoints
	s.registerPortfolioEndpoints(mux)

	log.Printf("✓ HTTP server listening on port %s", s.config.HTTPPort)

	if err := http.ListenAndServe(":"+s.config.HTTPPort, mux); err != nil {
		log.Fatalf("HTTP server failed: %v", err)
	}
}

func initDatabase(dbURL string) (*sql.DB, error) {
	if dbURL == "" {
		return nil, fmt.Errorf("DATABASE_URL not set")
	}

	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		return nil, err
	}

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		return nil, err
	}

	// Set connection pool settings
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	return db, nil
}

func initRedis(redisURL string) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:         redisURL,
		Password:     "",
		DB:           0,
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
		PoolSize:     10,
	})
}

var startTime = time.Now()

// Exchange interface for different exchange implementations
type Exchange interface {
	GetMarketData(symbol string) (*MarketData, error)
	SubmitOrder(order *Order) (*OrderResult, error)
	GetOrderStatus(orderID string) (*OrderStatus, error)
	GetBalance() (*Balance, error)
}

// Common types
type MarketData struct {
	Symbol      string
	Price       float64
	Bid         float64
	Ask         float64
	Volume24h   float64
	High24h     float64
	Low24h      float64
	PriceChange float64
	Timestamp   time.Time
}

type Order struct {
	ID           string
	Symbol       string
	Side         string
	Quantity     float64
	Price        float64
	OrderType    string
	StrategyName string
}

type OrderResult struct {
	OrderID          string
	ExchangeOrderID  string
	Status           string
	ExecutedPrice    float64
	ExecutedQuantity float64
	Fees             float64
	Timestamp        time.Time
}

type OrderStatus struct {
	OrderID      string
	Status       string
	FilledQty    float64
	AveragePrice float64
	Fees         float64
	UpdatedAt    time.Time
}

type Balance struct {
	Exchange      string
	Balances      map[string]AssetBalance
	TotalValueUSD float64
	Timestamp     time.Time
}

type AssetBalance struct {
	Asset    string
	Free     float64
	Locked   float64
	Total    float64
	ValueUSD float64
}

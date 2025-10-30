package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"google.golang.org/grpc"
)

// Order represents a trading order in the system
type Order struct {
	ID        string    `json:"id"`
	Symbol    string    `json:"symbol"`
	Side      string    `json:"side"` // "buy" or "sell"
	Quantity  float64   `json:"quantity"`
	Price     float64   `json:"price"`
	Status    string    `json:"status"` // "pending", "filled", "cancelled", "rejected"
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// OrderBook manages all orders in memory
type OrderBook struct {
	mu     sync.RWMutex
	orders map[string]*Order
}

// NewOrderBook creates a new order book instance
func NewOrderBook() *OrderBook {
	return &OrderBook{
		orders: make(map[string]*Order),
	}
}

// AddOrder adds a new order to the book
func (ob *OrderBook) AddOrder(order *Order) error {
	ob.mu.Lock()
	defer ob.mu.Unlock()

	if _, exists := ob.orders[order.ID]; exists {
		return fmt.Errorf("order %s already exists", order.ID)
	}

	order.Status = "pending"
	order.CreatedAt = time.Now()
	order.UpdatedAt = time.Now()
	ob.orders[order.ID] = order
	return nil
}

// GetOrder retrieves an order by ID
func (ob *OrderBook) GetOrder(id string) (*Order, error) {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	order, exists := ob.orders[id]
	if !exists {
		return nil, fmt.Errorf("order %s not found", id)
	}
	return order, nil
}

// UpdateOrderStatus updates the status of an existing order
func (ob *OrderBook) UpdateOrderStatus(id string, status string) error {
	ob.mu.Lock()
	defer ob.mu.Unlock()

	order, exists := ob.orders[id]
	if !exists {
		return fmt.Errorf("order %s not found", id)
	}

	order.Status = status
	order.UpdatedAt = time.Now()
	return nil
}

// ListOrders returns all orders
func (ob *OrderBook) ListOrders() []*Order {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	orders := make([]*Order, 0, len(ob.orders))
	for _, order := range ob.orders {
		orders = append(orders, order)
	}
	return orders
}

// ExecutionEngine handles order execution logic
type ExecutionEngine struct {
	book *OrderBook
	ctx  context.Context
}

// NewExecutionEngine creates a new execution engine
func NewExecutionEngine(ctx context.Context) *ExecutionEngine {
	return &ExecutionEngine{
		book: NewOrderBook(),
		ctx:  ctx,
	}
}

// ProcessOrder handles the order lifecycle
func (e *ExecutionEngine) ProcessOrder(order *Order) error {
	if err := e.validateOrder(order); err != nil {
		return err
	}

	if err := e.book.AddOrder(order); err != nil {
		return err
	}

	// Launch async execution
	go e.executeOrder(order.ID)
	return nil
}

// validateOrder checks if order parameters are valid
func (e *ExecutionEngine) validateOrder(order *Order) error {
	if order.Symbol == "" {
		return fmt.Errorf("symbol cannot be empty")
	}
	if order.Side != "buy" && order.Side != "sell" {
		return fmt.Errorf("side must be 'buy' or 'sell'")
	}
	if order.Quantity <= 0 {
		return fmt.Errorf("quantity must be positive")
	}
	if order.Price <= 0 {
		return fmt.Errorf("price must be positive")
	}
	return nil
}

// executeOrder simulates order execution with market conditions
func (e *ExecutionEngine) executeOrder(orderID string) {
	// Simulate processing time
	time.Sleep(100 * time.Millisecond)

	order, err := e.book.GetOrder(orderID)
	if err != nil {
		log.Printf("failed to get order %s: %v", orderID, err)
		return
	}

	// Simple execution logic - in production this would interface with exchanges
	if order.Quantity > 0 && order.Price > 0 {
		if err := e.book.UpdateOrderStatus(orderID, "filled"); err != nil {
			log.Printf("failed to update order %s: %v", orderID, err)
		}
		log.Printf("order %s filled: %s %f shares of %s at $%f",
			orderID, order.Side, order.Quantity, order.Symbol, order.Price)
	} else {
		if err := e.book.UpdateOrderStatus(orderID, "rejected"); err != nil {
			log.Printf("failed to update order %s: %v", orderID, err)
		}
	}
}

// REST API Handlers

// handleCreateOrder processes POST /orders requests
func (e *ExecutionEngine) handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var order Order
	if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
		http.Error(w, fmt.Sprintf("invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	if err := e.ProcessOrder(&order); err != nil {
		http.Error(w, fmt.Sprintf("failed to process order: %v", err), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(order)
}

// handleGetOrder processes GET /orders/{id} requests
func (e *ExecutionEngine) handleGetOrder(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	orderID := r.URL.Query().Get("id")
	if orderID == "" {
		http.Error(w, "order id required", http.StatusBadRequest)
		return
	}

	order, err := e.book.GetOrder(orderID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(order)
}

// handleListOrders processes GET /orders requests
func (e *ExecutionEngine) handleListOrders(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	orders := e.book.ListOrders()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(orders)
}

// handleHealth provides a simple health check endpoint
func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"status":"healthy","timestamp":"%s"}`, time.Now().Format(time.RFC3339))
}

// StartRESTServer initializes and runs the REST API server
func (e *ExecutionEngine) StartRESTServer(addr string) error {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/orders", e.handleListOrders)
	mux.HandleFunc("/order", e.handleGetOrder)
	mux.HandleFunc("/order/create", e.handleCreateOrder)

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	log.Printf("REST server listening on %s", addr)
	return server.ListenAndServe()
}

// StartGRPCServer initializes and runs the gRPC server
// Note: This requires protobuf definitions in a separate .proto file
func (e *ExecutionEngine) StartGRPCServer(addr string) error {
	listener, err := grpc.NewServer()
	if err != nil {
		return fmt.Errorf("failed to create gRPC server: %w", err)
	}

	// Register gRPC service handlers here once proto definitions are ready
	// pb.RegisterExecutionServiceServer(listener, e)

	log.Printf("gRPC server would listen on %s (needs proto definitions)", addr)
	return nil
}

func main() {
	ctx := context.Background()
	engine := NewExecutionEngine(ctx)

	// Start REST server in main goroutine
	if err := engine.StartRESTServer(":8080"); err != nil {
		log.Fatalf("REST server failed: %v", err)
	}
}

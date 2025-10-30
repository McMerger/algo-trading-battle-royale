// REST API, order/inventory tracking, market data handling.
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "sync"
    "time"
    "math/rand"
)

// Order represents a trade order for processing.
type Order struct {
    ID        string  `json:"id"`
    Symbol    string  `json:"symbol"`
    Side      string  `json:"side"` // "buy" or "sell"
    Qty       int     `json:"qty"`
    Price     float64 `json:"price"`
    Timestamp int64   `json:"timestamp"`
    Status    string  `json:"status"`
}

// Store holds orders and protects them with a mutex.
type Store struct {
    sync.Mutex
    orders map[string]*Order
}

func newStore() *Store {
    return &Store{
        orders: make(map[string]*Order),
    }
}

func (s *Store) addOrder(order *Order) {
    s.Lock()
    defer s.Unlock()
    s.orders[order.ID] = order
}

func (s *Store) getOrder(id string) (*Order, bool) {
    s.Lock()
    defer s.Unlock()
    o, ok := s.orders[id]
    return o, ok
}

// processOrder simulates execution with latency/slippage.
func processOrder(order *Order) {
    // Randomized network/market delay
    delay := time.Duration(rand.Intn(30)+10) * time.Millisecond
    time.Sleep(delay)
    order.Status = "filled"
    order.Price = applySlippage(order.Price)
}

func applySlippage(price float64) float64 {
    slip := (rand.Float64() - 0.5) * 0.02 * price // +/- 1% slippage
    return price + slip
}

func orderHandler(store *Store) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
            http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
            return
        }
        var order Order
        err := json.NewDecoder(r.Body).Decode(&order)
        if err != nil {
            http.Error(w, "Invalid payload", http.StatusBadRequest)
            return
        }
        order.ID = genOrderID()
        order.Timestamp = time.Now().UnixNano()
        order.Status = "received"
        store.addOrder(&order)
        go processOrder(&order) // Async fill
        resp, _ := json.Marshal(order)
        w.Header().Set("Content-Type", "application/json")
        w.Write(resp)
    }
}

func statusHandler(store *Store) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        id := r.URL.Query().Get("id")
        if id == "" {
            http.Error(w, "Order id required", http.StatusBadRequest)
            return
        }
        order, ok := store.getOrder(id)
        if !ok {
            http.Error(w, "Not found", http.StatusNotFound)
            return
        }
        resp, _ := json.Marshal(order)
        w.Header().Set("Content-Type", "application/json")
        w.Write(resp)
    }
}

func genOrderID() string {
    const letters = "abcdefghijklmnopqrstuvwxyz0123456789"
    b := make([]byte, 10)
    for i := range b {
        b[i] = letters[rand.Intn(len(letters))]
    }
    return string(b)
}

func main() {
    store := newStore()
    http.HandleFunc("/api/v1/orders", orderHandler(store))
    http.HandleFunc("/api/v1/order_status", statusHandler(store))
    log.Println("Execution engine started on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}

package execution

import (
    "context"
    "sync"
    "time"
    "github.com/McMerger/algo-trading-battle-royale/pkg/models"
)

type ExecutionEngine struct {
    orderBook     map[string]*OrderBook
    orderQueue    chan *models.Order
    fillQueue     chan *models.Fill
    mu            sync.RWMutex
    latencyConfig LatencyConfig
}

type LatencyConfig struct {
    MinLatency time.Duration
    MaxLatency time.Duration
    Slippage   float64
}

func NewExecutionEngine() *ExecutionEngine {
    return &ExecutionEngine{
        orderBook:  make(map[string]*OrderBook),
        orderQueue: make(chan *models.Order, 10000),
        fillQueue:  make(chan *models.Fill, 10000),
        latencyConfig: LatencyConfig{
            MinLatency: 10 * time.Microsecond,
            MaxLatency: 500 * time.Microsecond,
            Slippage:   0.0001, // 1 basis point
        },
    }
}

func (e *ExecutionEngine) Start(ctx context.Context) {
    // Start order processing workers
    for i := 0; i < 10; i++ {
        go e.processOrders(ctx)
    }
    
    // Start fill broadcasting
    go e.broadcastFills(ctx)
}

func (e *ExecutionEngine) processOrders(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        case order := <-e.orderQueue:
            // Simulate realistic latency
            time.Sleep(e.randomLatency())
            
            // Execute order with slippage
            fill := e.executeOrder(order)
            e.fillQueue <- fill
        }
    }
}

func (e *ExecutionEngine) executeOrder(order *models.Order) *models.Fill {
    e.mu.Lock()
    defer e.mu.Unlock()
    
    // Get or create order book for symbol
    book, exists := e.orderBook[order.Symbol]
    if !exists {
        book = NewOrderBook(order.Symbol)
        e.orderBook[order.Symbol] = book
    }
    
    // Apply realistic slippage based on order size
    slippage := e.calculateSlippage(order)
    fillPrice := order.Price * (1 + slippage)
    
    fill := &models.Fill{
        OrderID:   order.ID,
        Symbol:    order.Symbol,
        Price:     fillPrice,
        Quantity:  order.Quantity,
        Side:      order.Side,
        Timestamp: time.Now(),
        AgentName: order.AgentName,
    }
    
    return fill
}

func (e *ExecutionEngine) randomLatency() time.Duration {
    // Realistic latency simulation
    min := e.latencyConfig.MinLatency.Nanoseconds()
    max := e.latencyConfig.MaxLatency.Nanoseconds()
    latency := min + rand.Int63n(max-min)
    return time.Duration(latency)
}

func (e *ExecutionEngine) SubmitOrder(order *models.Order) error {
    select {
    case e.orderQueue <- order:
        return nil
    default:
        return errors.New("order queue full")
    }
}

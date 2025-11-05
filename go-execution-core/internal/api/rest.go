package api

import (
    "encoding/json"
    "net/http"
    "github.com/gorilla/mux"
    "github.com/McMerger/algo-trading-battle-royale/internal/execution"
)

type RestAPI struct {
    engine *execution.ExecutionEngine
    router *mux.Router
}

func NewRestAPI(engine *execution.ExecutionEngine) *RestAPI {
    api := &RestAPI{
        engine: engine,
        router: mux.NewRouter(),
    }
    api.setupRoutes()
    return api
}

func (api *RestAPI) setupRoutes() {
    api.router.HandleFunc("/api/v1/orders", api.submitOrder).Methods("POST")
    api.router.HandleFunc("/api/v1/health", api.health).Methods("GET")
    api.router.HandleFunc("/api/v1/metrics", api.metrics).Methods("GET")
}

func (api *RestAPI) submitOrder(w http.ResponseWriter, r *http.Request) {
    var order models.Order
    if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    if err := api.engine.SubmitOrder(&order); err != nil {
        http.Error(w, err.Error(), http.StatusServiceUnavailable)
        return
    }
    
    w.WriteHeader(http.StatusAccepted)
    json.NewEncoder(w).Encode(map[string]string{"status": "accepted"})
}

func (api *RestAPI) Start(addr string) error {
    return http.ListenAndServe(addr, api.router)
}

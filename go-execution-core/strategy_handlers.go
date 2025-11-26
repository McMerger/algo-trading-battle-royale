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

// Strategy management REST API handlers

func (s *Server) registerStrategyEndpoints(mux *http.ServeMux) {
	mux.HandleFunc("/api/v1/strategies", s.handleStrategies)
	mux.HandleFunc("/api/v1/strategies/", s.handleStrategyByName)
}

// handleStrategies handles GET (list all) and POST (create/update)
func (s *Server) handleStrategies(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.listStrategies(w, r)
	case http.MethodPost:
		s.createStrategy(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// handleStrategyByName handles GET (details), DELETE, and performance endpoints
func (s *Server) handleStrategyByName(w http.ResponseWriter, r *http.Request) {
	// Parse strategy name from URL: /api/v1/strategies/{name} or /api/v1/strategies/{name}/performance
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/strategies/")
	parts := strings.Split(path, "/")

	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "Strategy name required", http.StatusBadRequest)
		return
	}

	strategyName := parts[0]

	// Check if this is a performance request
	if len(parts) > 1 && parts[1] == "performance" {
		s.getStrategyPerformance(w, r, strategyName)
		return
	}

	// Handle strategy CRUD operations
	switch r.Method {
	case http.MethodGet:
		s.getStrategy(w, r, strategyName)
	case http.MethodDelete:
		s.deleteStrategy(w, r, strategyName)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// listStrategies returns all strategies
func (s *Server) listStrategies(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	// Query parameters for filtering
	activeOnly := r.URL.Query().Get("active") == "true"

	query := `
		SELECT name, description, config, is_active, created_at, updated_at, 
		       last_executed_at, total_pnl, win_rate, total_trades
		FROM strategies
	`

	if activeOnly {
		query += " WHERE is_active = true"
	}

	query += " ORDER BY name"

	rows, err := s.db.Query(query)
	if err != nil {
		log.Printf("Failed to query strategies: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch strategies",
		})
		return
	}
	defer rows.Close()

	strategies := make([]map[string]interface{}, 0)

	for rows.Next() {
		var name, description string
		var config []byte
		var isActive bool
		var createdAt, updatedAt time.Time
		var lastExecutedAt sql.NullTime
		var totalPnl sql.NullFloat64
		var winRate sql.NullFloat64
		var totalTrades sql.NullInt64

		err := rows.Scan(&name, &description, &config, &isActive, &createdAt, &updatedAt,
			&lastExecutedAt, &totalPnl, &winRate, &totalTrades)
		if err != nil {
			log.Printf("Failed to scan strategy row: %v", err)
			continue
		}

		// Parse config JSON
		var configMap map[string]interface{}
		if err := json.Unmarshal(config, &configMap); err != nil {
			log.Printf("Failed to parse config for %s: %v", name, err)
			configMap = make(map[string]interface{})
		}

		strategy := map[string]interface{}{
			"name":        name,
			"description": description,
			"config":      configMap,
			"is_active":   isActive,
			"created_at":  createdAt.Format(time.RFC3339),
			"updated_at":  updatedAt.Format(time.RFC3339),
		}

		if lastExecutedAt.Valid {
			strategy["last_executed_at"] = lastExecutedAt.Time.Format(time.RFC3339)
		}
		if totalPnl.Valid {
			strategy["total_pnl"] = totalPnl.Float64
		}
		if winRate.Valid {
			strategy["win_rate"] = winRate.Float64
		}
		if totalTrades.Valid {
			strategy["total_trades"] = totalTrades.Int64
		}

		strategies = append(strategies, strategy)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"strategies": strategies,
		"count":      len(strategies),
	})
}

// getStrategy returns details for a specific strategy
func (s *Server) getStrategy(w http.ResponseWriter, r *http.Request, name string) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	query := `
		SELECT name, description, config, is_active, created_by, created_at, updated_at,
		       last_executed_at, total_pnl, win_rate, total_trades, metadata
		FROM strategies
		WHERE name = $1
	`

	var strategyName, description string
	var createdBy sql.NullString
	var config, metadata []byte
	var isActive bool
	var createdAt, updatedAt time.Time
	var lastExecutedAt sql.NullTime
	var totalPnl sql.NullFloat64
	var winRate sql.NullFloat64
	var totalTrades sql.NullInt64

	err := s.db.QueryRow(query, name).Scan(
		&strategyName, &description, &config, &isActive, &createdBy, &createdAt, &updatedAt,
		&lastExecutedAt, &totalPnl, &winRate, &totalTrades, &metadata,
	)

	if err == sql.ErrNoRows {
		writeJSON(w, http.StatusNotFound, map[string]interface{}{
			"error": fmt.Sprintf("Strategy '%s' not found", name),
		})
		return
	}

	if err != nil {
		log.Printf("Failed to query strategy: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch strategy",
		})
		return
	}

	// Parse JSON fields
	var configMap, metadataMap map[string]interface{}
	json.Unmarshal(config, &configMap)
	if metadata != nil {
		json.Unmarshal(metadata, &metadataMap)
	}

	strategy := map[string]interface{}{
		"name":        strategyName,
		"description": description,
		"config":      configMap,
		"is_active":   isActive,
		"created_at":  createdAt.Format(time.RFC3339),
		"updated_at":  updatedAt.Format(time.RFC3339),
	}

	if createdBy.Valid {
		strategy["created_by"] = createdBy.String
	}
	if lastExecutedAt.Valid {
		strategy["last_executed_at"] = lastExecutedAt.Time.Format(time.RFC3339)
	}
	if totalPnl.Valid {
		strategy["total_pnl"] = totalPnl.Float64
	}
	if winRate.Valid {
		strategy["win_rate"] = winRate.Float64
	}
	if totalTrades.Valid {
		strategy["total_trades"] = totalTrades.Int64
	}
	if metadataMap != nil {
		strategy["metadata"] = metadataMap
	}

	writeJSON(w, http.StatusOK, strategy)
}

// createStrategy creates or updates a strategy
func (s *Server) createStrategy(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	var req struct {
		Name        string                 `json:"name"`
		Description string                 `json:"description"`
		Config      map[string]interface{} `json:"config"`
		IsActive    bool                   `json:"is_active"`
		CreatedBy   string                 `json:"created_by"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Invalid JSON",
		})
		return
	}

	// Validate required fields
	if req.Name == "" {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Strategy name is required",
		})
		return
	}

	if req.Config == nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Strategy config is required",
		})
		return
	}

	// Convert config to JSON
	configJSON, err := json.Marshal(req.Config)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]interface{}{
			"error": "Invalid config format",
		})
		return
	}

	// Insert or update strategy
	query := `
		INSERT INTO strategies (name, description, config, is_active, created_by)
		VALUES ($1, $2, $3, $4, $5)
		ON CONFLICT (name) DO UPDATE SET
			description = EXCLUDED.description,
			config = EXCLUDED.config,
			is_active = EXCLUDED.is_active,
			updated_at = NOW()
		RETURNING name, created_at, updated_at
	`

	var name string
	var createdAt, updatedAt time.Time

	err = s.db.QueryRow(query, req.Name, req.Description, configJSON, req.IsActive, req.CreatedBy).
		Scan(&name, &createdAt, &updatedAt)

	if err != nil {
		log.Printf("Failed to create/update strategy: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to save strategy",
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":    true,
		"name":       name,
		"created_at": createdAt.Format(time.RFC3339),
		"updated_at": updatedAt.Format(time.RFC3339),
		"message":    "Strategy saved successfully",
	})
}

// deleteStrategy deletes a strategy
func (s *Server) deleteStrategy(w http.ResponseWriter, r *http.Request, name string) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	query := `DELETE FROM strategies WHERE name = $1`

	result, err := s.db.Exec(query, name)
	if err != nil {
		log.Printf("Failed to delete strategy: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to delete strategy",
		})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		writeJSON(w, http.StatusNotFound, map[string]interface{}{
			"error": fmt.Sprintf("Strategy '%s' not found", name),
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"message": fmt.Sprintf("Strategy '%s' deleted successfully", name),
	})
}

// getStrategyPerformance returns performance metrics for a strategy
func (s *Server) getStrategyPerformance(w http.ResponseWriter, r *http.Request, name string) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	// Get overall strategy stats
	strategyQuery := `
		SELECT total_pnl, win_rate, total_trades, last_executed_at
		FROM strategies
		WHERE name = $1
	`

	var totalPnl sql.NullFloat64
	var winRate sql.NullFloat64
	var totalTrades sql.NullInt64
	var lastExecutedAt sql.NullTime

	err := s.db.QueryRow(strategyQuery, name).Scan(&totalPnl, &winRate, &totalTrades, &lastExecutedAt)
	if err == sql.ErrNoRows {
		writeJSON(w, http.StatusNotFound, map[string]interface{}{
			"error": fmt.Sprintf("Strategy '%s' not found", name),
		})
		return
	}
	if err != nil {
		log.Printf("Failed to query strategy performance: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch performance data",
		})
		return
	}

	// Get recent trades
	tradesQuery := `
		SELECT symbol, side, quantity, executed_price, pnl, executed_at
		FROM trades
		WHERE strategy_name = $1 AND executed_at IS NOT NULL
		ORDER BY executed_at DESC
		LIMIT 10
	`

	rows, err := s.db.Query(tradesQuery, name)
	if err != nil {
		log.Printf("Failed to query recent trades: %v", err)
	}

	recentTrades := make([]map[string]interface{}, 0)
	if rows != nil {
		defer rows.Close()
		for rows.Next() {
			var symbol, side string
			var quantity, executedPrice float64
			var pnl sql.NullFloat64
			var executedAt time.Time

			if err := rows.Scan(&symbol, &side, &quantity, &executedPrice, &pnl, &executedAt); err != nil {
				continue
			}

			trade := map[string]interface{}{
				"symbol":         symbol,
				"side":           side,
				"quantity":       quantity,
				"executed_price": executedPrice,
				"executed_at":    executedAt.Format(time.RFC3339),
			}
			if pnl.Valid {
				trade["pnl"] = pnl.Float64
			}

			recentTrades = append(recentTrades, trade)
		}
	}

	performance := map[string]interface{}{
		"strategy_name": name,
		"recent_trades": recentTrades,
	}

	if totalPnl.Valid {
		performance["total_pnl"] = totalPnl.Float64
	}
	if winRate.Valid {
		performance["win_rate"] = winRate.Float64
	}
	if totalTrades.Valid {
		performance["total_trades"] = totalTrades.Int64
	}
	if lastExecutedAt.Valid {
		performance["last_executed_at"] = lastExecutedAt.Time.Format(time.RFC3339)
	}

	writeJSON(w, http.StatusOK, performance)
}

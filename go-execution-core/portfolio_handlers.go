package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"time"
)

// Portfolio and risk management REST API handlers

func (s *Server) registerPortfolioEndpoints(mux *http.ServeMux) {
	mux.HandleFunc("/api/v1/portfolio/positions", s.handlePositions)
	mux.HandleFunc("/api/v1/portfolio/performance", s.handlePortfolioPerformance)
	mux.HandleFunc("/api/v1/portfolio/risk", s.handleRiskMetrics)
	mux.HandleFunc("/api/v1/portfolio/pnl", s.handlePnL)
	mux.HandleFunc("/api/v1/portfolio/balances", s.handleAllBalances)
}

// handlePositions returns current open positions
func (s *Server) handlePositions(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	query := `
		SELECT symbol, strategy_name, quantity, average_entry_price, current_price,
		       unrealized_pnl, realized_pnl, opened_at, last_updated
		FROM positions
		WHERE quantity != 0
		ORDER BY last_updated DESC
	`

	rows, err := s.db.Query(query)
	if err != nil {
		log.Printf("Failed to query positions: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch positions",
		})
		return
	}
	defer rows.Close()

	positions := make([]map[string]interface{}, 0)
	var totalUnrealizedPnL, totalRealizedPnL float64

	for rows.Next() {
		var symbol, strategyName string
		var quantity, avgEntryPrice float64
		var currentPrice, unrealizedPnL, realizedPnL sql.NullFloat64
		var openedAt, lastUpdated time.Time

		err := rows.Scan(&symbol, &strategyName, &quantity, &avgEntryPrice,
			&currentPrice, &unrealizedPnL, &realizedPnL, &openedAt, &lastUpdated)
		if err != nil {
			log.Printf("Failed to scan position row: %v", err)
			continue
		}

		position := map[string]interface{}{
			"symbol":              symbol,
			"strategy_name":       strategyName,
			"quantity":            quantity,
			"average_entry_price": avgEntryPrice,
			"opened_at":           openedAt.Format(time.RFC3339),
			"last_updated":        lastUpdated.Format(time.RFC3339),
		}

		if currentPrice.Valid {
			position["current_price"] = currentPrice.Float64
			position["market_value"] = currentPrice.Float64 * quantity
		}
		if unrealizedPnL.Valid {
			position["unrealized_pnl"] = unrealizedPnL.Float64
			totalUnrealizedPnL += unrealizedPnL.Float64
		}
		if realizedPnL.Valid {
			position["realized_pnl"] = realizedPnL.Float64
			totalRealizedPnL += realizedPnL.Float64
		}

		positions = append(positions, position)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"positions":            positions,
		"count":                len(positions),
		"total_unrealized_pnl": totalUnrealizedPnL,
		"total_realized_pnl":   totalRealizedPnL,
		"total_pnl":            totalUnrealizedPnL + totalRealizedPnL,
	})
}

// handlePortfolioPerformance returns overall portfolio performance metrics
func (s *Server) handlePortfolioPerformance(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	// Get aggregate statistics from trades
	query := `
		SELECT 
			COUNT(*) as total_trades,
			COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
			COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
			COALESCE(SUM(pnl), 0) as total_pnl,
			COALESCE(AVG(pnl), 0) as avg_pnl,
			COALESCE(MAX(pnl), 0) as max_win,
			COALESCE(MIN(pnl), 0) as max_loss
		FROM trades
		WHERE pnl IS NOT NULL AND status = 'FILLED'
	`

	var totalTrades, winningTrades, losingTrades int64
	var totalPnL, avgPnL, maxWin, maxLoss float64

	err := s.db.QueryRow(query).Scan(&totalTrades, &winningTrades, &losingTrades,
		&totalPnL, &avgPnL, &maxWin, &maxLoss)
	if err != nil {
		log.Printf("Failed to query performance: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch performance data",
		})
		return
	}

	winRate := 0.0
	if totalTrades > 0 {
		winRate = float64(winningTrades) / float64(totalTrades)
	}

	// Get performance by strategy
	strategyQuery := `
		SELECT strategy_name, COUNT(*) as trades, COALESCE(SUM(pnl), 0) as pnl
		FROM trades
		WHERE pnl IS NOT NULL AND status = 'FILLED'
		GROUP BY strategy_name
		ORDER BY pnl DESC
	`

	rows, err := s.db.Query(strategyQuery)
	if err != nil {
		log.Printf("Failed to query strategy performance: %v", err)
	}

	strategyPerformance := make([]map[string]interface{}, 0)
	if rows != nil {
		defer rows.Close()
		for rows.Next() {
			var strategyName string
			var trades int64
			var pnl float64

			if err := rows.Scan(&strategyName, &trades, &pnl); err != nil {
				continue
			}

			strategyPerformance = append(strategyPerformance, map[string]interface{}{
				"strategy_name": strategyName,
				"trades":        trades,
				"pnl":           pnl,
			})
		}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total_trades":          totalTrades,
		"winning_trades":        winningTrades,
		"losing_trades":         losingTrades,
		"win_rate":              winRate,
		"total_pnl":             totalPnL,
		"average_pnl_per_trade": avgPnL,
		"max_win":               maxWin,
		"max_loss":              maxLoss,
		"strategy_performance":  strategyPerformance,
	})
}

// handleRiskMetrics returns risk metrics
func (s *Server) handleRiskMetrics(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	// Calculate total exposure
	exposureQuery := `
		SELECT 
			COALESCE(SUM(ABS(quantity * average_entry_price)), 0) as total_exposure,
			COUNT(*) as open_positions
		FROM positions
		WHERE quantity != 0
	`

	var totalExposure float64
	var openPositions int64

	err := s.db.QueryRow(exposureQuery).Scan(&totalExposure, &openPositions)
	if err != nil {
		log.Printf("Failed to query exposure: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch risk metrics",
		})
		return
	}

	// Get recent risk events
	riskEventsQuery := `
		SELECT event_type, severity, description, timestamp
		FROM risk_events
		WHERE resolved = false
		ORDER BY timestamp DESC
		LIMIT 5
	`

	rows, err := s.db.Query(riskEventsQuery)
	if err != nil {
		log.Printf("Failed to query risk events: %v", err)
	}

	riskEvents := make([]map[string]interface{}, 0)
	if rows != nil {
		defer rows.Close()
		for rows.Next() {
			var eventType, severity, description string
			var timestamp time.Time

			if err := rows.Scan(&eventType, &severity, &description, &timestamp); err != nil {
				continue
			}

			riskEvents = append(riskEvents, map[string]interface{}{
				"event_type":  eventType,
				"severity":    severity,
				"description": description,
				"timestamp":   timestamp.Format(time.RFC3339),
			})
		}
	}

	// Simple VaR calculation (95% confidence, last 30 days)
	varQuery := `
		SELECT COALESCE(PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY pnl), 0) as var_95
		FROM trades
		WHERE pnl IS NOT NULL 
		  AND executed_at > NOW() - INTERVAL '30 days'
		  AND status = 'FILLED'
	`

	var var95 float64
	s.db.QueryRow(varQuery).Scan(&var95)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total_exposure": totalExposure,
		"open_positions": openPositions,
		"var_95_30d":     var95,
		"risk_events":    riskEvents,
		"risk_level":     calculateRiskLevel(openPositions, totalExposure),
	})
}

// handlePnL returns PnL calculation
func (s *Server) handlePnL(w http.ResponseWriter, r *http.Request) {
	if s.db == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]interface{}{
			"error": "Database not available",
		})
		return
	}

	// Get time period from query params (default: last 30 days)
	period := r.URL.Query().Get("period")
	if period == "" {
		period = "30 days"
	}

	query := fmt.Sprintf(`
		SELECT 
			DATE(executed_at) as date,
			COALESCE(SUM(pnl), 0) as daily_pnl,
			COUNT(*) as trades
		FROM trades
		WHERE pnl IS NOT NULL 
		  AND executed_at > NOW() - INTERVAL '%s'
		  AND status = 'FILLED'
		GROUP BY DATE(executed_at)
		ORDER BY date DESC
	`, period)

	rows, err := s.db.Query(query)
	if err != nil {
		log.Printf("Failed to query PnL: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]interface{}{
			"error": "Failed to fetch PnL data",
		})
		return
	}
	defer rows.Close()

	dailyPnL := make([]map[string]interface{}, 0)
	var cumulativePnL float64

	for rows.Next() {
		var date time.Time
		var pnl float64
		var trades int64

		if err := rows.Scan(&date, &pnl, &trades); err != nil {
			continue
		}

		cumulativePnL += pnl

		dailyPnL = append(dailyPnL, map[string]interface{}{
			"date":           date.Format("2006-01-02"),
			"daily_pnl":      pnl,
			"cumulative_pnl": cumulativePnL,
			"trades":         trades,
		})
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"period":         period,
		"daily_pnl":      dailyPnL,
		"cumulative_pnl": cumulativePnL,
	})
}

// handleAllBalances returns balances across all configured exchanges
func (s *Server) handleAllBalances(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	allBalances := make(map[string]interface{})
	var totalValueUSD float64

	for exchangeName, exchange := range s.exchanges {
		balance, err := exchange.GetBalance()
		if err != nil {
			log.Printf("Failed to get balance for %s: %v", exchangeName, err)
			allBalances[exchangeName] = map[string]interface{}{
				"error": err.Error(),
			}
			continue
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

		allBalances[exchangeName] = map[string]interface{}{
			"balances":        balances,
			"total_value_usd": balance.TotalValueUSD,
			"timestamp":       balance.Timestamp.Format(time.RFC3339),
		}

		totalValueUSD += balance.TotalValueUSD
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"exchanges":       allBalances,
		"total_value_usd": totalValueUSD,
		"timestamp":       time.Now().Format(time.RFC3339),
	})
}

// Helper function to calculate risk level
func calculateRiskLevel(openPositions int64, totalExposure float64) string {
	if openPositions == 0 {
		return "NONE"
	}
	if totalExposure < 10000 {
		return "LOW"
	}
	if totalExposure < 50000 {
		return "MEDIUM"
	}
	if totalExposure < 100000 {
		return "HIGH"
	}
	return "CRITICAL"
}

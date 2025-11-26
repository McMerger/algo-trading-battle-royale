package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// BinanceExchange implements Exchange interface for Binance
type BinanceExchange struct {
	apiKey    string
	apiSecret string
	baseURL   string
	client    *http.Client
}

func NewBinanceExchange(apiKey, apiSecret string) *BinanceExchange {
	return &BinanceExchange{
		apiKey:    apiKey,
		apiSecret: apiSecret,
		baseURL:   "https://api.binance.com",
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (b *BinanceExchange) GetMarketData(symbol string) (*MarketData, error) {
	// Get 24hr ticker data
	url := fmt.Sprintf("%s/api/v3/ticker/24hr?symbol=%s", b.baseURL, symbol)

	resp, err := b.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch market data: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("binance API error: %s - %s", resp.Status, string(body))
	}

	var ticker struct {
		Symbol             string `json:"symbol"`
		LastPrice          string `json:"lastPrice"`
		BidPrice           string `json:"bidPrice"`
		AskPrice           string `json:"askPrice"`
		Volume             string `json:"volume"`
		HighPrice          string `json:"highPrice"`
		LowPrice           string `json:"lowPrice"`
		PriceChange        string `json:"priceChange"`
		PriceChangePercent string `json:"priceChangePercent"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&ticker); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	// Parse string values to float64
	price, err := strconv.ParseFloat(ticker.LastPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid last price '%s': %w", ticker.LastPrice, err)
	}
	bid, err := strconv.ParseFloat(ticker.BidPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid bid price '%s': %w", ticker.BidPrice, err)
	}
	ask, err := strconv.ParseFloat(ticker.AskPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid ask price '%s': %w", ticker.AskPrice, err)
	}
	volume, err := strconv.ParseFloat(ticker.Volume, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid volume '%s': %w", ticker.Volume, err)
	}
	high, err := strconv.ParseFloat(ticker.HighPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid high price '%s': %w", ticker.HighPrice, err)
	}
	low, err := strconv.ParseFloat(ticker.LowPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid low price '%s': %w", ticker.LowPrice, err)
	}
	priceChange, err := strconv.ParseFloat(ticker.PriceChange, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid price change '%s': %w", ticker.PriceChange, err)
	}

	return &MarketData{
		Symbol:      symbol,
		Price:       price,
		Bid:         bid,
		Ask:         ask,
		Volume24h:   volume,
		High24h:     high,
		Low24h:      low,
		PriceChange: priceChange,
		Timestamp:   time.Now(),
	}, nil
}

func (b *BinanceExchange) SubmitOrder(order *Order) (*OrderResult, error) {
	// Build order parameters
	params := url.Values{}
	params.Set("symbol", order.Symbol)
	params.Set("side", order.Side)
	params.Set("type", order.OrderType)
	params.Set("quantity", fmt.Sprintf("%.8f", order.Quantity))

	if order.OrderType == "LIMIT" {
		params.Set("price", fmt.Sprintf("%.8f", order.Price))
		params.Set("timeInForce", "GTC")
	}

	params.Set("timestamp", fmt.Sprintf("%d", time.Now().UnixMilli()))

	// Sign request
	signature := b.sign(params.Encode())
	params.Set("signature", signature)

	// Make request
	reqURL := fmt.Sprintf("%s/api/v3/order?%s", b.baseURL, params.Encode())

	req, err := http.NewRequest("POST", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-MBX-APIKEY", b.apiKey)

	resp, err := b.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to submit order: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		return &OrderResult{
			OrderID: order.ID,
			Status:  "FAILED",
		}, fmt.Errorf("binance order failed: %s - %s", resp.Status, string(body))
	}

	var orderResp struct {
		OrderID       int64  `json:"orderId"`
		Symbol        string `json:"symbol"`
		Status        string `json:"status"`
		ExecutedQty   string `json:"executedQty"`
		CummulativeQuoteQty string `json:"cummulativeQuoteQty"`
		Fills         []struct {
			Price       string `json:"price"`
			Qty         string `json:"qty"`
			Commission  string `json:"commission"`
		} `json:"fills"`
	}

	if err := json.Unmarshal(body, &orderResp); err != nil {
		return nil, fmt.Errorf("failed to decode order response: %w", err)
	}

	// Calculate executed price and fees
	executedQty, err := strconv.ParseFloat(orderResp.ExecutedQty, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid executed quantity '%s': %w", orderResp.ExecutedQty, err)
	}
	var totalValue, totalFees float64

	for _, fill := range orderResp.Fills {
		fillPrice, err := strconv.ParseFloat(fill.Price, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid fill price '%s': %w", fill.Price, err)
		}
		fillQty, err := strconv.ParseFloat(fill.Qty, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid fill quantity '%s': %w", fill.Qty, err)
		}
		commission, err := strconv.ParseFloat(fill.Commission, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid commission '%s': %w", fill.Commission, err)
		}

		totalValue += fillPrice * fillQty
		totalFees += commission
	}

	avgPrice := 0.0
	if executedQty > 0 {
		avgPrice = totalValue / executedQty
	}

	return &OrderResult{
		OrderID:          order.ID,
		ExchangeOrderID:  fmt.Sprintf("%d", orderResp.OrderID),
		Status:           orderResp.Status,
		ExecutedPrice:    avgPrice,
		ExecutedQuantity: executedQty,
		Fees:             totalFees,
		Timestamp:        time.Now(),
	}, nil
}

func (b *BinanceExchange) GetOrderStatus(orderID string) (*OrderStatus, error) {
	params := url.Values{}
	params.Set("orderId", orderID)
	params.Set("timestamp", fmt.Sprintf("%d", time.Now().UnixMilli()))

	signature := b.sign(params.Encode())
	params.Set("signature", signature)

	reqURL := fmt.Sprintf("%s/api/v3/order?%s", b.baseURL, params.Encode())

	req, err := http.NewRequest("GET", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-MBX-APIKEY", b.apiKey)

	resp, err := b.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to get order status: %w", err)
	}
	defer resp.Body.Close()

	var orderResp struct {
		OrderID     int64  `json:"orderId"`
		Status      string `json:"status"`
		ExecutedQty string `json:"executedQty"`
		Price       string `json:"price"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&orderResp); err != nil {
		return nil, fmt.Errorf("failed to decode status response: %w", err)
	}

	filledQty, err := strconv.ParseFloat(orderResp.ExecutedQty, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid filled quantity '%s': %w", orderResp.ExecutedQty, err)
	}
	price, err := strconv.ParseFloat(orderResp.Price, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid price '%s': %w", orderResp.Price, err)
	}

	return &OrderStatus{
		OrderID:      fmt.Sprintf("%d", orderResp.OrderID),
		Status:       orderResp.Status,
		FilledQty:    filledQty,
		AveragePrice: price,
		UpdatedAt:    time.Now(),
	}, nil
}

func (b *BinanceExchange) GetBalance() (*Balance, error) {
	params := url.Values{}
	params.Set("timestamp", fmt.Sprintf("%d", time.Now().UnixMilli()))

	signature := b.sign(params.Encode())
	params.Set("signature", signature)

	reqURL := fmt.Sprintf("%s/api/v3/account?%s", b.baseURL, params.Encode())

	req, err := http.NewRequest("GET", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-MBX-APIKEY", b.apiKey)

	resp, err := b.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to get balance: %w", err)
	}
	defer resp.Body.Close()

	var accountResp struct {
		Balances []struct {
			Asset  string `json:"asset"`
			Free   string `json:"free"`
			Locked string `json:"locked"`
		} `json:"balances"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&accountResp); err != nil {
		return nil, fmt.Errorf("failed to decode balance response: %w", err)
	}

	balances := make(map[string]AssetBalance)

	for _, bal := range accountResp.Balances {
		free, err := strconv.ParseFloat(bal.Free, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid free balance for %s: '%s': %w", bal.Asset, bal.Free, err)
		}
		locked, err := strconv.ParseFloat(bal.Locked, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid locked balance for %s: '%s': %w", bal.Asset, bal.Locked, err)
		}

		if free > 0 || locked > 0 {
			balances[bal.Asset] = AssetBalance{
				Asset:  bal.Asset,
				Free:   free,
				Locked: locked,
				Total:  free + locked,
			}
		}
	}

	return &Balance{
		Exchange:  "binance",
		Balances:  balances,
		Timestamp: time.Now(),
	}, nil
}

func (b *BinanceExchange) sign(queryString string) string {
	mac := hmac.New(sha256.New, []byte(b.apiSecret))
	mac.Write([]byte(queryString))
	return hex.EncodeToString(mac.Sum(nil))
}

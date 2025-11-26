package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// GetHistoricalKlines fetches historical OHLCV data from Binance
func (b *BinanceExchange) GetHistoricalKlines(symbol, interval string, limit int) ([]Kline, error) {
	// Apply rate limiting
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.rateLimiter.Wait(ctx); err != nil {
		return nil, fmt.Errorf("rate limit wait failed: %w", err)
	}

	url := fmt.Sprintf("%s/api/v3/klines?symbol=%s&interval=%s&limit=%d",
		b.baseURL, symbol, interval, limit)

	resp, err := b.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch klines: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("binance API error: %s - %s", resp.Status, string(body))
	}

	var rawKlines [][]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&rawKlines); err != nil {
		return nil, fmt.Errorf("failed to decode klines: %w", err)
	}

	klines := make([]Kline, 0, len(rawKlines))
	for _, raw := range rawKlines {
		if len(raw) < 11 {
			continue
		}

		// Parse timestamp
		timestamp := int64(raw[0].(float64))

		// Parse OHLCV values
		open, _ := strconv.ParseFloat(raw[1].(string), 64)
		high, _ := strconv.ParseFloat(raw[2].(string), 64)
		low, _ := strconv.ParseFloat(raw[3].(string), 64)
		close, _ := strconv.ParseFloat(raw[4].(string), 64)
		volume, _ := strconv.ParseFloat(raw[5].(string), 64)

		klines = append(klines, Kline{
			OpenTime:  time.UnixMilli(timestamp),
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
			CloseTime: time.UnixMilli(int64(raw[6].(float64))),
		})
	}

	return klines, nil
}

// GetOrderBook fetches order book depth from Binance
func (b *BinanceExchange) GetOrderBook(symbol string, limit int) (*OrderBook, error) {
	// Apply rate limiting
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.rateLimiter.Wait(ctx); err != nil {
		return nil, fmt.Errorf("rate limit wait failed: %w", err)
	}

	url := fmt.Sprintf("%s/api/v3/depth?symbol=%s&limit=%d", b.baseURL, symbol, limit)

	resp, err := b.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch order book: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("binance API error: %s - %s", resp.Status, string(body))
	}

	var bookResp struct {
		LastUpdateID int64           `json:"lastUpdateId"`
		Bids         [][]interface{} `json:"bids"`
		Asks         [][]interface{} `json:"asks"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&bookResp); err != nil {
		return nil, fmt.Errorf("failed to decode order book: %w", err)
	}

	// Parse bids
	bids := make([]OrderBookLevel, 0, len(bookResp.Bids))
	for _, bid := range bookResp.Bids {
		if len(bid) >= 2 {
			price, _ := strconv.ParseFloat(bid[0].(string), 64)
			quantity, _ := strconv.ParseFloat(bid[1].(string), 64)
			bids = append(bids, OrderBookLevel{Price: price, Quantity: quantity})
		}
	}

	// Parse asks
	asks := make([]OrderBookLevel, 0, len(bookResp.Asks))
	for _, ask := range bookResp.Asks {
		if len(ask) >= 2 {
			price, _ := strconv.ParseFloat(ask[0].(string), 64)
			quantity, _ := strconv.ParseFloat(ask[1].(string), 64)
			asks = append(asks, OrderBookLevel{Price: price, Quantity: quantity})
		}
	}

	return &OrderBook{
		Symbol:       symbol,
		Bids:         bids,
		Asks:         asks,
		LastUpdateID: bookResp.LastUpdateID,
		Timestamp:    time.Now(),
	}, nil
}

// CancelOrder cancels an existing order on Binance
func (b *BinanceExchange) CancelOrder(symbol, orderID string) error {
	// Apply rate limiting
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.rateLimiter.Wait(ctx); err != nil {
		return fmt.Errorf("rate limit wait failed: %w", err)
	}

	params := url.Values{}
	params.Set("symbol", symbol)
	params.Set("orderId", orderID)
	params.Set("timestamp", fmt.Sprintf("%d", time.Now().UnixMilli()))

	signature := b.sign(params.Encode())
	params.Set("signature", signature)

	reqURL := fmt.Sprintf("%s/api/v3/order?%s", b.baseURL, params.Encode())

	req, err := http.NewRequest("DELETE", reqURL, nil)
	if err != nil {
		return err
	}

	req.Header.Set("X-MBX-APIKEY", b.apiKey)

	resp, err := b.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to cancel order: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("binance cancel failed: %s - %s", resp.Status, string(body))
	}

	return nil
}

// ModifyOrder modifies an existing order (cancel + replace)
func (b *BinanceExchange) ModifyOrder(symbol, orderID string, newQuantity, newPrice float64) (*OrderResult, error) {
	// First, cancel the existing order
	if err := b.CancelOrder(symbol, orderID); err != nil {
		return nil, fmt.Errorf("failed to cancel order for modification: %w", err)
	}

	// Then submit a new order with updated parameters
	newOrder := &Order{
		Symbol:    symbol,
		Side:      "BUY", // This should be determined from the original order
		Quantity:  newQuantity,
		Price:     newPrice,
		OrderType: "LIMIT",
	}

	return b.SubmitOrder(newOrder)
}

// GetAllTickers fetches ticker data for all symbols
func (b *BinanceExchange) GetAllTickers() ([]TickerData, error) {
	// Apply rate limiting
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.rateLimiter.Wait(ctx); err != nil {
		return nil, fmt.Errorf("rate limit wait failed: %w", err)
	}

	url := fmt.Sprintf("%s/api/v3/ticker/24hr", b.baseURL)

	resp, err := b.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch tickers: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("binance API error: %s - %s", resp.Status, string(body))
	}

	var rawTickers []struct {
		Symbol             string `json:"symbol"`
		LastPrice          string `json:"lastPrice"`
		PriceChange        string `json:"priceChange"`
		PriceChangePercent string `json:"priceChangePercent"`
		Volume             string `json:"volume"`
		QuoteVolume        string `json:"quoteVolume"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&rawTickers); err != nil {
		return nil, fmt.Errorf("failed to decode tickers: %w", err)
	}

	tickers := make([]TickerData, 0, len(rawTickers))
	for _, raw := range rawTickers {
		price, _ := strconv.ParseFloat(raw.LastPrice, 64)
		priceChange, _ := strconv.ParseFloat(raw.PriceChange, 64)
		priceChangePercent, _ := strconv.ParseFloat(raw.PriceChangePercent, 64)
		volume, _ := strconv.ParseFloat(raw.Volume, 64)
		quoteVolume, _ := strconv.ParseFloat(raw.QuoteVolume, 64)

		tickers = append(tickers, TickerData{
			Symbol:             raw.Symbol,
			Price:              price,
			PriceChange:        priceChange,
			PriceChangePercent: priceChangePercent,
			Volume:             volume,
			QuoteVolume:        quoteVolume,
		})
	}

	return tickers, nil
}

// Kline represents a candlestick data point
type Kline struct {
	OpenTime  time.Time
	Open      float64
	High      float64
	Low       float64
	Close     float64
	Volume    float64
	CloseTime time.Time
}

// OrderBook represents order book depth
type OrderBook struct {
	Symbol       string
	Bids         []OrderBookLevel
	Asks         []OrderBookLevel
	LastUpdateID int64
	Timestamp    time.Time
}

// OrderBookLevel represents a single price level in the order book
type OrderBookLevel struct {
	Price    float64
	Quantity float64
}

// TickerData represents 24hr ticker statistics
type TickerData struct {
	Symbol             string
	Price              float64
	PriceChange        float64
	PriceChangePercent float64
	Volume             float64
	QuoteVolume        float64
}

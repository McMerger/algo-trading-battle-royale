"""
Prediction market API adapters for Kalshi and Polymarket.

This is what sets this system apart: agents can trade on real-world event probabilities,
not just price data. When Fed hike odds jump from 40% to 75%, that's actionable signal.
"""

import requests
from typing import Dict, Optional, List
from datetime import datetime
import os


class KalshiAdapter:
    """
    Kalshi is a regulated prediction market for macro events.
    Good for: Fed rates, elections, economic indicators.
    
    Docs: https://trading-api.kalshi.com/docs
    """
    
    def __init__(self, api_key=None, use_demo=True):
        self.api_key = api_key or os.getenv('KALSHI_API_KEY')
        self.use_demo = use_demo or not self.api_key
        
        if self.use_demo:
            self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        else:
            self.base_url = "https://trading-api.kalshi.com/trade-api/v2"
        
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def get_market_odds(self, ticker):
        """
        Fetch current odds for a market.
        ticker example: 'FED-23DEC-T4.75' for Fed rate decision
        
        Returns dict with probabilities, or None if failed.
        """
        try:
            url = f"{self.base_url}/markets/{ticker}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            
            if not resp.ok:
                print(f"Kalshi API error {resp.status_code} for {ticker}")
                return None
            
            data = resp.json()
            market = data.get('market', {})
            
            # Kalshi prices are in cents, convert to probability
            yes_bid = market.get('yes_bid', 50)
            yes_ask = market.get('yes_ask', 50)
            
            # Use mid-price for probability estimate
            yes_prob = (yes_bid + yes_ask) / 200.0 if yes_ask else yes_bid / 100.0
            
            return {
                'source': 'kalshi',
                'market_id': ticker,
                'title': market.get('title', ''),
                'yes_probability': yes_prob,
                'no_probability': 1 - yes_prob,
                'volume': market.get('volume', 0),
                'close_time': market.get('close_time'),
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Failed to fetch Kalshi market {ticker}: {e}")
            return None
    
    def search_markets(self, series='FED', limit=10):
        """Find active markets in a series (FED, INXD, etc)."""
        try:
            url = f"{self.base_url}/markets"
            params = {'series_ticker': series, 'status': 'open', 'limit': limit}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if resp.ok:
                return resp.json().get('markets', [])
        except Exception as e:
            print(f"Kalshi search failed: {e}")
        
        return []
    
    def get_fed_odds(self):
        """Shortcut to get current Fed rate decision odds."""
        markets = self.search_markets(series='FED', limit=5)
        if markets:
            ticker = markets[0].get('ticker')
            if ticker:
                return self.get_market_odds(ticker)
        return None


class PolymarketAdapter:
    """
    Polymarket is crypto-native, broader event coverage.
    Good for: crypto events, politics, culture, some finance.
    
    Uses CLOB (order book) API.
    """
    
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.clob_url = "https://clob.polymarket.com"
    
    def get_market_odds(self, condition_id):
        """
        Fetch odds for a Polymarket condition.
        condition_id is typically a hex string starting with 0x.
        """
        try:
            url = f"{self.gamma_url}/markets/{condition_id}"
            resp = requests.get(url, timeout=10)
            
            if not resp.ok:
                print(f"Polymarket error {resp.status_code} for {condition_id}")
                return None
            
            market = resp.json()
            tokens = market.get('tokens', [])
            
            # Usually binary: YES and NO tokens
            yes_token = next((t for t in tokens if 'yes' in t.get('outcome', '').lower()), None)
            no_token = next((t for t in tokens if 'no' in t.get('outcome', '').lower()), None)
            
            yes_prob = float(yes_token.get('price', 0.5)) if yes_token else 0.5
            no_prob = float(no_token.get('price', 0.5)) if no_token else 0.5
            
            return {
                'source': 'polymarket',
                'market_id': condition_id,
                'title': market.get('question', ''),
                'yes_probability': yes_prob,
                'no_probability': no_prob,
                'volume': float(market.get('volume', 0)),
                'liquidity': float(market.get('liquidity', 0)),
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Failed to fetch Polymarket {condition_id}: {e}")
            return None
    
    def search_markets(self, query=None, limit=10):
        """Search for active markets."""
        try:
            url = f"{self.gamma_url}/markets"
            params = {'limit': limit, 'active': True}
            if query:
                params['query'] = query
            
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            print(f"Polymarket search failed: {e}")
        
        return []


class PredictionMarketFeed:
    """
    Main interface for getting event data.
    Handles both Kalshi and Polymarket, with mock data fallback for testing.
    
    This is what agents actually interact with.
    """
    
    def __init__(self, kalshi_key=None, use_mock=False):
        self.kalshi = KalshiAdapter(kalshi_key)
        self.polymarket = PolymarketAdapter()
        self.use_mock = use_mock
        self.cache = {}
        
        # Mock data for offline dev/testing
        self.mock_events = {
            'fed_hike': {
                'source': 'mock',
                'title': 'Fed Rate Hike (Mock)',
                'yes_probability': 0.68,
                'volume': 100000,
                'updated_at': datetime.now().isoformat()
            },
            'recession': {
                'source': 'mock',
                'title': 'US Recession 2024 (Mock)',
                'yes_probability': 0.32,
                'volume': 50000,
                'updated_at': datetime.now().isoformat()
            }
        }
    
    def get_events(self, event_config):
        """
        Fetch multiple event probabilities.
        
        event_config is a dict like:
        {
            'fed_hike': 'FED-DEC-T5.00',
            'election': '0xabc123',
            'recession': 'RECESSION-24'
        }
        
        Returns dict of event data with probabilities.
        """
        results = {}
        
        for event_name, market_id in event_config.items():
            # Try cache first (5 min TTL)
            cache_key = f"{event_name}_{market_id}"
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                cache_age = (datetime.now() - datetime.fromisoformat(cached['updated_at'])).seconds
                if cache_age < 300:  # 5 minutes
                    results[event_name] = cached
                    continue
            
            # Use mock if enabled
            if self.use_mock and event_name in self.mock_events:
                results[event_name] = self.mock_events[event_name]
                continue
            
            # Fetch from API
            odds = None
            if market_id.startswith('0x'):
                odds = self.polymarket.get_market_odds(market_id)
            else:
                odds = self.kalshi.get_market_odds(market_id)
            
            if odds:
                results[event_name] = odds
                self.cache[cache_key] = odds
            elif event_name in self.mock_events:
                # Fallback to mock if API fails
                print(f"Using mock fallback for {event_name}")
                results[event_name] = self.mock_events[event_name]
        
        return results
    
    def add_events_to_market_data(self, market_data, event_config):
        """
        This is the key integration: add event probabilities to standard market data.
        
        Agents get both price info AND event odds in one dict.
        """
        enriched = market_data.copy()
        enriched['events'] = self.get_events(event_config)
        return enriched
    
    def get_macro_snapshot(self):
        """Quick snapshot of key macro events for regime assessment."""
        snapshot = {'timestamp': datetime.now().isoformat(), 'events': {}}
        
        fed_data = self.kalshi.get_fed_odds()
        if fed_data:
            snapshot['events']['fed_hike'] = fed_data
        elif 'fed_hike' in self.mock_events:
            snapshot['events']['fed_hike'] = self.mock_events['fed_hike']
        
        return snapshot

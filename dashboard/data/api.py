import requests
import os
import feedparser
import pandas as pd
import streamlit as st
from .database import init_db_connection

# --- Constants ---
GO_API_URL = os.getenv("EXECUTION_ENGINE_URL", "http://localhost:8080")

def get_system_health():
    """Check health of backend services."""
    services = {"Go Engine": "UNKNOWN", "Python Strategy": "UNKNOWN", "Database": "UNKNOWN"}
    
    # Check Go
    try:
        r = requests.get(f"{GO_API_URL}/health", timeout=2)
        if r.status_code == 200:
            services["Go Engine"] = "ONLINE"
        else:
            services["Go Engine"] = "ERROR"
    except:
        services["Go Engine"] = "OFFLINE"
        
    # Check DB
    conn = init_db_connection()
    if conn and not conn.closed:
        services["Database"] = "ONLINE"
        conn.close()
    else:
        services["Database"] = "OFFLINE"
        
    return services

def get_market_data(symbol="BTCUSDT", exchange="binance"):
    """Fetch live market data from Go API."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/market/{exchange}/{symbol}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_balance(exchange="binance"):
    """Fetch account balance from Go API."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/balance/{exchange}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_all_balances():
    """Fetch balances across all exchanges."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/portfolio/balances", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def place_order(order_data):
    """Submit order to Go API."""
    try:
        r = requests.post(f"{GO_API_URL}/api/v1/orders", json=order_data, timeout=5)
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, r.text
    except Exception as e:
        return False, str(e)

def cancel_order(order_id, symbol, exchange="binance"):
    """Cancel an existing order."""
    try:
        r = requests.delete(
            f"{GO_API_URL}/api/v1/orders/{order_id}",
            json={"symbol": symbol, "exchange": exchange},
            timeout=5
        )
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, r.text
    except Exception as e:
        return False, str(e)

def get_recent_orders(limit=50):
    """Fetch recent orders."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/orders?limit={limit}", timeout=2)
        if r.status_code == 200:
            return r.json().get("orders", [])
    except:
        pass
    return []

# --- Strategy Management ---

def get_strategies(active_only=False):
    """Fetch all strategies."""
    try:
        url = f"{GO_API_URL}/api/v1/strategies"
        if active_only:
            url += "?active=true"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            return r.json().get("strategies", [])
    except:
        pass
    return []

def get_strategy(name):
    """Fetch strategy details."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/strategies/{name}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_strategy_performance(name):
    """Fetch strategy performance metrics."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/strategies/{name}/performance", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def create_strategy(strategy_data):
    """Create or update a strategy."""
    try:
        r = requests.post(f"{GO_API_URL}/api/v1/strategies", json=strategy_data, timeout=5)
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, r.text
    except Exception as e:
        return False, str(e)

def delete_strategy(name):
    """Delete a strategy."""
    try:
        r = requests.delete(f"{GO_API_URL}/api/v1/strategies/{name}", timeout=5)
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, r.text
    except Exception as e:
        return False, str(e)

# --- Portfolio & Risk ---

def get_positions():
    """Fetch current positions."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/portfolio/positions", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_portfolio_performance():
    """Fetch portfolio performance metrics."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/portfolio/performance", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_risk_metrics():
    """Fetch risk metrics."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/portfolio/risk", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_pnl(period="30 days"):
    """Fetch PnL data."""
    try:
        r = requests.get(f"{GO_API_URL}/api/v1/portfolio/pnl?period={period}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# --- Historical Data ---

@st.cache_data(ttl=60)
def get_historical_klines(symbol="BTCUSDT", interval="1h", limit=100):
    """Fetch historical kline data from Binance public API for charts."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Binance returns [open_time, open, high, low, close, volume, ...]
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", 
                "close_time", "quote_asset_volume", "number_of_trades", 
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching klines: {e}")
        return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_crypto_news():
    """Fetch latest crypto news from RSS."""
    try:
        feed = feedparser.parse("https://cointelegraph.com/rss")
        return feed.entries[:10]
    except Exception as e:
        return []

# --- Parallel Data Fetching ---
from concurrent.futures import ThreadPoolExecutor

def fetch_dashboard_data(symbol="BTCUSDT"):
    """
    Fetch all critical dashboard data in parallel to minimize UI blocking.
    Returns a dictionary with all data.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks
        future_health = executor.submit(get_system_health)
        future_market = executor.submit(get_market_data, symbol)
        future_balance = executor.submit(get_all_balances)
        future_positions = executor.submit(get_positions)
        future_perf = executor.submit(get_portfolio_performance)
        
        # Wait for results (with timeout protection)
        return {
            "health": future_health.result(timeout=3),
            "market": future_market.result(timeout=3),
            "balances": future_balance.result(timeout=3),
            "positions": future_positions.result(timeout=3),
            "performance": future_perf.result(timeout=3)
        }

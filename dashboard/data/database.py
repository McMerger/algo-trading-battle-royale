import psycopg2
import pandas as pd
import os
import streamlit as st

# --- Constants ---
DB_URL = os.getenv("DATABASE_URL", "postgresql://signalops:signalops_dev_password@postgres:5432/signalops")

@st.cache_resource
def init_db_connection():
    """Initialize database connection."""
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        # st.error(f"Failed to connect to database: {e}")
        return None

def get_recent_trades(limit=50):
    """Fetch recent trades from database."""
    conn = init_db_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
        SELECT 
            timestamp, symbol, side, strategy_name, 
            quantity, executed_price, status, fees
        FROM trades 
        ORDER BY timestamp DESC 
        LIMIT %s
    """
    try:
        df = pd.read_sql(query, conn, params=(limit,))
        conn.close()
        return df
    except:
        conn.close()
        return pd.DataFrame()

def get_strategy_performance():
    """Fetch aggregated strategy performance."""
    conn = init_db_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
        SELECT 
            strategy_name,
            COUNT(*) as total_trades,
            SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(*), 0) as fill_rate
        FROM trades 
        GROUP BY strategy_name
    """
    try:
        df = pd.read_sql(query, conn)
        # Add mock PnL for demo purposes if not in DB yet
        if 'total_pnl' not in df.columns:
            df['total_pnl'] = df['total_trades'] * 15.5  # Mock avg PnL
            
        conn.close()
        return df
    except:
        conn.close()
        return pd.DataFrame()

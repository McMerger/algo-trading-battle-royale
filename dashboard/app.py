"""
SignalOps Premium Dashboard
Real-time trading analytics and system monitoring.
"""

import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Import modular components
from styles.custom_css import load_css
from components.header import render_header
from components.sidebar import render_sidebar
from components.tabs import render_tabs

# --- Configuration ---
st.set_page_config(
    page_title="SignalOps Terminal",
    page_icon=None, # Removed emoji icon for cleaner look
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants ---
FAST_REFRESH = 2000   # 2 seconds (Price)
SLOW_REFRESH = 10000  # 10 seconds (Portfolio)

# Import parallel fetcher
from data.api import fetch_dashboard_data

def main():
    # 1. Load Custom Styles
    load_css()
    
    # 2. Initialize Session State
    if 'data' not in st.session_state:
        st.session_state.data = {}
    if 'last_slow_update' not in st.session_state:
        st.session_state.last_slow_update = 0
        
    # 3. Auto-refresh (Fast Interval)
    count = st_autorefresh(interval=FAST_REFRESH, key="data_refresh")
    
    # 4. Data Fetching Logic
    current_time = datetime.now().timestamp()
    
    # Determine if we need a full update (slow) or just market (fast)
    # Note: For simplicity in Streamlit, we'll fetch everything in parallel 
    # but we could optimize further by splitting the fetcher.
    # Given the parallel fetcher is fast, we'll call it every fast interval
    # but we can throttle heavy computations if needed.
    
    # Fetch all data in parallel
    # Default symbol from session state or default
    symbol = st.session_state.get("selected_symbol", "BTCUSDT")
    
    with st.spinner(""): # Invisible spinner to prevent UI jump
        new_data = fetch_dashboard_data(symbol)
        st.session_state.data = new_data
    
    # 5. Render Layout
    # Pass data to components to avoid re-fetching
    
    # Sidebar (Wallet & Controls)
    render_sidebar(st.session_state.data.get('balances'), st.session_state.data.get('positions'))
    
    # Header (System Status)
    render_header(st.session_state.data.get('health'))
    
    # Main Content
    render_tabs(st.session_state.data)
    
    # 6. Footer
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: #666; font-size: 0.8em;'>"
        f"SignalOps v1.1.0 • Last Update: {datetime.now().strftime('%H:%M:%S')} • "
        f"⚡ {int((datetime.now().timestamp() - current_time)*1000)}ms latency</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

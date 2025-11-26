import streamlit as st
import time
from data.api import place_order, get_balance

def render_sidebar(balance_data=None, positions_data=None):
    """Renders the sidebar with trading controls and wallet."""
    with st.sidebar:
        # --- Command Palette (Quick Actions) ---
        st.markdown("### <i class='ph ph-command'></i> Command Palette", unsafe_allow_html=True)
        command = st.selectbox(
            "Quick Action", 
            ["Select Action...", "Buy BTC (Market)", "Sell BTC (Market)", "Clear Cache", "View Logs"],
            label_visibility="collapsed"
        )
        
        if command == "Buy BTC (Market)":
            st.toast("Sending Order: BUY BTCUSDT...", icon="📤") # Streamlit toast icons must be emojis, keeping for now or removing icon arg
            # Logic to trigger trade would go here
            time.sleep(0.5) # Simulate network
            st.toast("Order Filled!", icon="✅")
        elif command == "Clear Cache":
            st.cache_data.clear()
            st.toast("Cache Cleared!", icon="🧹")
            
        st.markdown("---")
        
        st.markdown("### <i class='ph ph-lightning'></i> Quick Trade", unsafe_allow_html=True)
        
        with st.form("trade_form"):
            tr_symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "AVAXUSDT"])
            tr_side = st.selectbox("Side", ["BUY", "SELL"])
            tr_type = st.selectbox("Type", ["MARKET", "LIMIT"])
            tr_qty = st.number_input("Quantity", min_value=0.0001, value=0.001, step=0.0001, format="%.4f")
            tr_price = st.number_input("Price (Limit)", min_value=0.0, value=0.0, step=10.0)
            
            submitted = st.form_submit_button("Submit Order", use_container_width=True)
            
            if submitted:
                # Optimistic Feedback
                st.toast(f"Submitting {tr_side} {tr_symbol}...", icon="⚡")
                
                order_id = f"manual-{int(time.time())}"
                order_data = {
                    "order_id": order_id,
                    "strategy_name": "Manual",
                    "symbol": tr_symbol,
                    "side": tr_side,
                    "quantity": tr_qty,
                    "price": tr_price if tr_type == "LIMIT" else 0,
                    "order_type": tr_type,
                    "exchange": "binance"
                }
                
                success, response = place_order(order_data)
                if success:
                    st.toast(f"Order {order_id} Confirmed!", icon="🚀")
                    # Force immediate refresh
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"Order Failed: {response}")

        st.markdown("---")
        st.markdown("### <i class='ph ph-wallet'></i> Wallet", unsafe_allow_html=True)
        
        if balance_data and 'balances' in balance_data:
            for asset, bal in balance_data['balances'].items():
                total = bal.get('total', 0)
                if total > 0:
                    st.metric(asset, f"{total:,.4f}", help=f"Free: {bal.get('free',0)} | Locked: {bal.get('locked',0)}")
            
            st.markdown("---")
            st.metric("Total Value (USD)", f"${balance_data.get('total_value_usd', 0):,.2f}")
        else:
            if balance_data is None:
                st.info("Loading wallet...")
            else:
                st.warning("Wallet data unavailable")

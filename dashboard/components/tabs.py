import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.api import get_market_data, get_crypto_news, get_historical_klines
from data.database import get_recent_trades, get_strategy_performance

def render_tabs(data=None):
    """Renders the main dashboard tabs."""
    if data is None:
        data = {}
        
    tab1, tab2, tab3, tab4 = st.tabs(["Live Market", "Strategy Performance", "Trade Log", "News & Events"])

    with tab1:
        # Live Market Data
        c1, c2 = st.columns([1, 3])
        with c1:
            # Update session state on change
            current_symbol = st.session_state.get("selected_symbol", "BTCUSDT")
            symbol = st.selectbox(
                "Select Asset", 
                ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"], 
                index=["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"].index(current_symbol) if current_symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"] else 0,
                key="symbol_selector",
                on_change=lambda: st.session_state.update({"selected_symbol": st.session_state.symbol_selector})
            )
            interval = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
            
        market_data = data.get('market')
        
        if market_data:
            # Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price", f"${market_data.get('price', 0):,.2f}", f"{market_data.get('price_change_24h', 0):.2f}%")
            m2.metric("24h Volume", f"{market_data.get('volume_24h', 0):,.0f}")
            m3.metric("High", f"${market_data.get('high_24h', 0):,.2f}")
            m4.metric("Low", f"${market_data.get('low_24h', 0):,.2f}")
            
            # Interactive Candlestick Chart
            st.markdown("### <i class='ph ph-chart-line-up'></i> Price Action", unsafe_allow_html=True)
            # Note: Klines are still fetched separately as they are heavy and cached differently
            klines = get_historical_klines(symbol, interval=interval, limit=100)
            
            if not klines.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=klines['timestamp'],
                    open=klines['open'],
                    high=klines['high'],
                    low=klines['low'],
                    close=klines['close'],
                    increasing_line_color='#00FF7F', 
                    decreasing_line_color='#FF453A'
                )])
                
                fig.update_layout(
                    template="plotly_dark",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_rangeslider_visible=False,
                    height=500,
                    margin=dict(l=0, r=0, t=20, b=0),
                    font=dict(family="Inter, sans-serif")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Chart data unavailable")
        else:
            st.warning(f"Waiting for market data for {symbol}...")

    with tab2:
        # Strategy Performance
        perf_data = data.get('performance')
        
        if perf_data and 'strategy_performance' in perf_data:
            perf_df = pd.DataFrame(perf_data['strategy_performance'])
            
            if not perf_df.empty:
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    fig = px.bar(
                        perf_df, x="strategy_name", y="pnl",
                        color="pnl",
                        color_continuous_scale=["#FF453A", "#0E1117", "#00FF7F"],
                        title="PnL by Strategy",
                        template="plotly_dark"
                    )
                    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                    
                with c2:
                    st.markdown("### <i class='ph ph-trophy'></i> Leaderboard", unsafe_allow_html=True)
                    st.dataframe(
                        perf_df.style.format({
                            "pnl": "${:,.2f}"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("No active strategy performance data.")
        else:
            st.info("No completed trades yet. Start the strategy engine to see performance.")

    with tab3:
        # Trade Log
        st.markdown("### <i class='ph ph-list-dashes'></i> Recent Executions", unsafe_allow_html=True)
        # Still fetching recent trades separately as it's a list operation
        trades_df = pd.DataFrame(get_recent_trades())
        
        if not trades_df.empty:
            # Style the dataframe
            def color_side(val):
                color = '#00FF7F' if val == 'BUY' else '#FF453A'
                return f'color: {color}; font-weight: bold'
                
            st.dataframe(
                trades_df.style.applymap(color_side, subset=['side'])
                         .format({"executed_price": "${:,.2f}", "quantity": "{:.4f}"}),
                use_container_width=True,
                height=400
            )
        else:
            st.info("No trades found in database.")

    with tab4:
        st.markdown("### <i class='ph ph-newspaper'></i> Global Market Intelligence", unsafe_allow_html=True)
        news_items = get_crypto_news()
        
        if news_items:
            for item in news_items:
                with st.expander(f"{item.title} - {item.published}"):
                    st.markdown(f"**{item.summary}**")
                    st.markdown(f"[Read Full Story]({item.link})")
        else:
            st.info("News feed currently unavailable")

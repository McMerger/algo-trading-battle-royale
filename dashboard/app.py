# Streamlit dashboard shows live agent leaderboard, trade battle results, and English summaries.

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading Battle Dashboard", layout="wide")

st.title("Algo Trading Battle Royale Dashboard")

# API endpoints (adjust to match your infra)
STRATEGY_ENGINE_URL = "http://localhost:5000"
EXECUTION_ENGINE_URL = "http://localhost:8080"

def fetch_leaderboard():
    # Placeholder: demo scores for agents
    # Replace with call to strategy engine REST/GPRC
    return {
        "TrendFollower": 157,
        "ArbMaster": 134,
        "MomentumBot": 182,
        "MeanReverter": 101
    }

def fetch_recent_trades():
    # Placeholder: demo trade history, replace with live updates
    return [
        {"winner": "MomentumBot", "score": 32, "summary": "Won by entering early on breakout. Confidence 91%.", "time": datetime.now().strftime("%H:%M:%S")},
        {"winner": "TrendFollower", "score": 25, "summary": "Followed steady market uptrend. Sentiment positive.", "time": datetime.now().strftime("%H:%M:%S")},
        {"winner": "ArbMaster", "score": 19, "summary": "Spotted mispricing across books. Fast execution.", "time": datetime.now().strftime("%H:%M:%S")}
    ]

# Leaderboard
st.header("Agent Leaderboard")
scores = fetch_leaderboard()
score_df = pd.DataFrame(list(scores.items()), columns=["Agent", "Score"]).sort_values("Score", ascending=False)
st.table(score_df)

# Recent agent battles
st.header("Latest Battles")
trades = fetch_recent_trades()
for trade in trades:
    st.markdown(f"**{trade['time']}** — :trophy: Winner: {trade['winner']} (Score: {trade['score']})")
    st.info(trade["summary"])

st.write("Live updates and explanations will appear here as trading continues.")

# Note: Replace demo fetch functions with actual API requests to engines.

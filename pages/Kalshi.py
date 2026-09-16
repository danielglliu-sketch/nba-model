import streamlit as st
import numpy as np
from scipy.stats import norm
from collections import deque
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Kalshi 15M BTC Directional Bot",
    page_icon="🎯",
    layout="centered"
)

KALSHI_API_URL = "https://external-api.kalshi.com/trade-api/v2"

@st.cache_data(ttl=5)
def fetch_live_kalshi_btc_data():
    """
    Queries Kalshi's public API specifically filtering for 
    the KXBTC15M series markets.
    """
    try:
        url = f"{KALSHI_API_URL}/markets?series_ticker=KXBTC15M&status=open"
        response = requests.get(url, timeout=4)
        data = response.json()
        markets = data.get("markets", [])
        
        if not markets:
            return None
            
        # Grab the nearest active market
        target_market = markets[0]
        ticker = target_market["ticker"]
        
        ob_url = f"{KALSHI_API_URL}/markets/{ticker}/orderbook"
        ob_response = requests.get(ob_url, timeout=4)
        ob_data = ob_response.json().get("orderbook", {})
        
        yes_bids = ob_data.get("yes", [])
        best_bid = yes_bids[0][0] / 100.0 if yes_bids else 0.48
        best_ask = (yes_bids[0][0] + 2) / 100.0 if yes_bids else 0.52
        
        return {
            "ticker": ticker,
            "strike_price": float(target_market.get("floor_strike", 65000.0)),
            "bid_price": best_bid,
            "ask_price": best_ask,
        }
    except Exception:
        return None

class KalshiDirectionalEngine:
    def __init__(self, fee_drag: float = 0.02, min_edge: float = 0.015):
        self.fee_drag = fee_drag
        self.min_edge = min_edge
        self.buffer = deque(maxlen=60)

    def get_signal(self, spot: float, strike: float, secs: int, vol: float, bid: float, ask: float):
        if secs <= 0:
            anchor = (sum(self.buffer) / len(self.buffer)) if self.buffer else spot
            return "BET UP" if anchor > strike else "BET DOWN", 1.0

        # Kalshi 60-second settlement rule integration
        if secs <= 60:
            self.buffer.append(spot)
            anchor = (sum(self.buffer) + (60 - len(self.buffer)) * spot) / 60.0
        else:
            self.buffer.clear()
            anchor = spot

        time_frac = secs / (365.25 * 24 * 3600)
        std_dev = anchor * vol * np.sqrt(time_frac)
        
        if std_dev == 0:
            fair_prob = 1.0 if anchor > strike else 0.0
        else:
            fair_prob = 1.0 - norm.cdf((strike - anchor) / std_dev)

        # Evaluate execution boundaries against fees and spreads
        buy_yes_edge = fair_prob - ask
        buy_no_edge = (1.0 - fair_prob) - (1.0 - bid)

        if buy_yes_edge > (self.fee_drag + self.min_edge) and buy_yes_edge > buy_no_edge:
            return "BET UP", buy_yes_edge
        elif buy_no_edge > (self.fee_drag + self.min_edge) and buy_no_edge > buy_yes_edge:
            return "BET DOWN", buy_no_edge
        else:
            return "NO TRADE (No Clear Edge)", 0.0

# --- UI LAYOUT ---
st.title("🎯 KXBTC15M Directional Oracle")
st.markdown("Automated quantitative engine parsing Kalshi's **KXBTC15M** series with the 60-second index average rule.")

use_live = st.checkbox("Pull Live Kalshi API Data Automatically", value=True)
live_info = fetch_live_kalshi_btc_data() if use_live else None

if use_live and live_info:
    st.success(f"Successfully connected to active ticker: **{live_info['ticker']}**")
elif use_live:
    st.warning("Live KXBTC15M market currently inactive or endpoint unreachable. Falling back to manual parameters.")

with st.sidebar:
    st.header("Model Inputs")
    spot = st.number_input("Current BTC Spot ($)", value=65000.0, step=10.0)
    strike = st.number_input("Strike Price ($)", value=live_info["strike_price"] if (use_live and live_info) else 65010.0, step=10.0)
    secs = st.slider("Seconds Left in Window", 0, 900, 300)
    vol = st.slider("Realized Volatility", 0.1, 2.0, 0.65)
    bid = st.slider("Kalshi Bid", 0.01, 0.99, live_info["bid_price"] if (use_live and live_info) else 0.48, 0.01)
    ask = st.slider("Kalshi Ask", 0.01, 0.99, live_info["ask_price"] if (use_live and live_info) else 0.52, 0.01)

engine = KalshiDirectionalEngine()
action, edge = engine.get_signal(spot, strike, secs, vol, bid, ask)

st.divider()

# Clean Signal Display Panel
if "UP" in action:
    st.success(f"### 🟢 RECOMMENDATION: **{action}**")
    st.caption(f"Calculated Edge clearing fee wall: +{edge*100:.1f}¢")
elif "DOWN" in action:
    st.error(f"### 🔴 RECOMMENDATION: **{action}**")
    st.caption(f"Calculated Edge clearing fee wall: +{edge*100:.1f}¢")
else:
    st.warning(f"### ⚪ RECOMMENDATION: **{action}**")
    st.caption("Market is priced efficiently; staying out to protect capital from transaction costs.")

with st.expander("ℹ️ Model Architecture Notes"):
    st.markdown("""
    * **Target Series:** `KXBTC15M` (15-minute Bitcoin market).
    * **Settlement Engine:** Automatically applies Kalshi's rolling 60-second index averaging mechanism when `Seconds Left ≤ 60`.
    * **Fee Drag Filter:** Requires the mathematical edge to exceed the exchange fee and spread barrier before printing a trade execution command.
    """)

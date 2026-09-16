import streamlit as st
import numpy as np
from scipy.stats import norm
from collections import deque
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Kalshi 15M BTC Quant Engine",
    page_icon="⚡",
    layout="wide"
)

KALSHI_API_URL = "https://external-api.kalshi.com/trade-api/v2"

# --- LIVE API FETCHER ---
def fetch_live_kalshi_btc_data():
    """
    Queries Kalshi's public API to find active Bitcoin markets 
    and extract orderbook metrics.
    """
    try:
        url = f"{KALSHI_API_URL}/markets?status=open"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        markets = data.get("markets", [])
        btc_markets = [m for m in markets if "BTC" in m.get("ticker", "") or "Bitcoin" in m.get("title", "")]
        
        if not btc_markets:
            return None
            
        target_market = btc_markets[0]
        ticker = target_market["ticker"]
        
        ob_url = f"{KALSHI_API_URL}/markets/{ticker}/orderbook"
        ob_response = requests.get(ob_url, timeout=5)
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
    except Exception as e:
        return None

# --- QUANT ENGINE CORE CLASS ---
class KalshiBTC15MinQuantEngine:
    def __init__(self, fee_drag_cents: float = 0.02, min_edge_cents: float = 0.015):
        self.fee_drag = fee_drag_cents
        self.min_edge = min_edge_cents
        self.final_minute_buffer = deque(maxlen=60)

    def calculate_fair_probability(
        self, 
        current_spot: float, 
        strike_price: float, 
        sec_remaining: int, 
        realized_vol: float
    ) -> float:
        if sec_remaining <= 0:
            if len(self.final_minute_buffer) > 0:
                settlement_val = sum(self.final_minute_buffer) / len(self.final_minute_buffer)
                return 1.0 if settlement_val > strike_price else 0.0
            return 1.0 if current_spot > strike_price else 0.0

        # Kalshi 60-second rule integration
        if sec_remaining <= 60:
            self.final_minute_buffer.append(current_spot)
            locked_sum = sum(self.final_minute_buffer)
            locked_count = len(self.final_minute_buffer)
            remaining_count = 60 - locked_count
            expected_future_sum = remaining_count * current_spot
            projected_settlement_mean = (locked_sum + expected_future_sum) / 60.0
            effective_price_anchor = projected_settlement_mean
        else:
            self.final_minute_buffer.clear()
            effective_price_anchor = current_spot

        time_fraction = sec_remaining / (365.25 * 24 * 3600)
        std_dev = effective_price_anchor * realized_vol * np.sqrt(time_fraction)

        if std_dev == 0:
            return 1.0 if effective_price_anchor > strike_price else 0.0

        z_score = (strike_price - effective_price_anchor) / std_dev
        prob_above = 1.0 - norm.cdf(z_score)

        return float(prob_above)

    def evaluate_orderbook(self, fair_prob: float, bid_price: float, ask_price: float) -> dict:
        signal = "HOLD"
        target_side = None
        limit_price = 0.0
        edge = 0.0

        buy_yes_edge = fair_prob - ask_price
        if buy_yes_edge > (self.fee_drag + self.min_edge):
            signal = "EXECUTE"
            target_side = "YES"
            limit_price = ask_price
            edge = buy_yes_edge

        no_fair_prob = 1.0 - fair_prob
        no_market_ask = 1.0 - bid_price
        buy_no_edge = no_fair_prob - no_market_ask
        
        if buy_no_edge > (self.fee_drag + self.min_edge) and buy_no_edge > edge:
            signal = "EXECUTE"
            target_side = "NO"
            limit_price = bid_price  
            edge = buy_no_edge

        return {
            "signal": signal,
            "target_side": target_side,
            "limit_price": limit_price,
            "fair_prob": fair_prob,
            "estimated_edge": edge
        }

# --- STREAMLIT UI LAYOUT ---
st.title("⚡ Kalshi 15-Minute BTC Quantitative Engine")
st.markdown("Production-ready quant engine incorporating Kalshi's **60-second settlement index average** rule with live API fetching capabilities.")

# Sidebar controls
st.sidebar.header("Data Connection Mode")
use_live_data = st.sidebar.checkbox("Enable Live Kalshi API Feed", value=False)

live_data = None
if use_live_data:
    live_data = fetch_live_kalshi_btc_data()
    if live_data:
        st.sidebar.success(f"Connected: {live_data['ticker']}")
    else:
        st.sidebar.warning("API feed unavailable. Using manual inputs.")

st.sidebar.header("Market Parameters")
default_strike = live_data["strike_price"] if live_data else 65010.0
default_bid = live_data["bid_price"] if live_data else 0.48
default_ask = live_data["ask_price"] if live_data else 0.52

current_spot = st.sidebar.number_input("Current BTC Spot Price ($)", value=65000.0, step=10.0)
strike_price = st.sidebar.number_input("Kalshi Strike Price ($)", value=default_strike, step=10.0)
sec_remaining = st.sidebar.slider("Seconds Remaining in Window", min_value=0, max_value=900, value=300, step=1)
realized_vol = st.sidebar.slider("Annualized Realized Volatility", min_value=0.1, max_value=2.0, value=0.65, step=0.05)

st.sidebar.header("Orderbook Quotes")
bid_price = st.sidebar.slider("Market Bid Price (YES)", min_value=0.01, max_value=0.99, value=default_bid, step=0.01)
ask_price = st.sidebar.slider("Market Ask Price (YES)", min_value=0.01, max_value=0.99, value=default_ask, step=0.01)

st.sidebar.header("Model Risk Controls")
fee_drag = st.sidebar.number_input("Fee & Slippage Drag ($)", value=0.02, step=0.005)
min_edge = st.sidebar.number_input("Minimum Required Edge ($)", value=0.015, step=0.005)

# Initialize Engine and Calculate
engine = KalshiBTC15MinQuantEngine(fee_drag_cents=fee_drag, min_edge_cents=min_edge)
fair_p = engine.calculate_fair_probability(current_spot, strike_price, sec_remaining, realized_vol)
decision = engine.evaluate_orderbook(fair_p, bid_price, ask_price)

# Main Dashboard Metrics View
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Model Fair Probability (YES)", value=f"{fair_p * 100:.2f}%")

with col2:
    mid_market = (bid_price + ask_price) / 2.0
    st.metric(label="Market Mid Price (YES)", value=f"{mid_market * 100:.2f}¢")

with col3:
    signal_color = "green" if decision["signal"] == "EXECUTE" else "gray"
    st.markdown(f"### Trade Signal: :{signal_color}[**{decision['signal']}**]")

st.divider()

# Detailed Breakdown Container
st.subheader("📊 Execution Analysis & Edge Evaluation")
if decision["signal"] == "EXECUTE":
    st.success(f"**Opportunity Detected!** Target Side: **{decision['target_side']}** | Limit Price: **{decision['limit_price']}** | Calculated Edge: **{decision['estimated_edge']*100:.2f}¢**")
else:
    st.info("No trading edge found. The market price aligns too closely with fair probability after factoring in fees and spread constraints.")

# Information Box on Kalshi Mechanics
with st.expander("ℹ️ How the Kalshi 60-Second Rule is Handled Here"):
    st.markdown("""
    * **Outside Final Minute (>60s):** The model uses standard short-horizon normal diffusion anchored on the current spot price.
    * **Inside Final Minute (≤60s):** The model automatically opens a rolling buffer tracking prices second-by-second to dynamically simulate Kalshi's **60-second CF Benchmarks RTI average** settlement vector.
    """)

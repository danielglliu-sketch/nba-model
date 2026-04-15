import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Monte Carlo K-Model", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed! Re-running 10,000 simulations per pitcher.")

# --- LIVE ODDS API ---
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Live Odds Integration")
odds_api_key = st.sidebar.text_input("The Odds API Key (Optional):", type="password")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Simulation Modifiers")
use_ml_weights = st.sidebar.checkbox("🤖 Use ML Contextual Weights", value=True)

with st.sidebar.expander("1. Lineup Discipline & Aggression", expanded=False):
    high_k_lineups_input = st.text_area("HIGH-K LINEUPS", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]
    
    # MICHAEL KING FIX: Flag teams that take quick outs
    aggressive_lineups_input = st.text_area("EARLY COUNT SWINGERS (-Ks)", "SEA, COL, MIA, DET")
    AGGRESSIVE_LINEUPS = [x.strip() for x in aggressive_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS", "Reid Detmers, Ryan Weathers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

with st.sidebar.expander("2. Environment & Matchup", expanded=False):
    cold_weather = st.text_area("COLD/WIND IN GAMES", "MIN, CHW, DET, CLE, CHC, SF")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATED DATA: LIVE 2026 SEASON BASELINES
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_pitcher_mix(sp_name):
    mix = {
        'Michael King': {'Sinker': 0.36, 'Changeup': 0.26, 'Sweeper': 0.19, 'Four-Seamer': 0.15},
        'Dylan Cease': {'Slider': 0.45, 'Fastball': 0.40}
    }
    return mix.get(sp_name, {'Fastball': 0.50, 'Slider': 0.20})

@st.cache_data(ttl=86400)
def get_live_2026_baselines():
    """Pulls current season (2026) K-rates for total accuracy."""
    try:
        # Pulls live stats for the current 2026 season
        df = pyb.pitching_stats(2026, qual=1) 
        if df['K%'].dtype == object:
            df['K%'] = df['K%'].str.rstrip('%').astype('float') / 100.0
        return dict(zip(df['Name'], df['K%']))
    except:
        return {}

LIVE_K_DB = get_live_2026_baselines()

def get_baseline_k(pitcher_name):
    # Checks live 2026 DB first
    if pitcher_name in LIVE_K_DB: return float(LIVE_K_DB[pitcher_name])
    # Last name fallback
    for name, rate in LIVE_K_DB.items():
        if name.split(' ')[-1] == pitcher_name.split(' ')[-1]: return float(rate)
    return 0.22 # League average fallback

# ─────────────────────────────────────────────────────────────────────────────
# 1. FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate(date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if home and away:
                h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in home else 'TBD'
                a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in away else 'TBD'
                games.append({
                    'h': home['team']['abbreviation'], 'a': away['team']['abbreviation'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k_rate': get_baseline_k(h_sp), 'a_base_k_rate': get_baseline_k(a_sp)
                })
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 2. MONTE CARLO ENGINE (WITH LOGARITHMIC DAMPENING)
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, opp_team, park, is_home, pitch_limit=95, ppa=3.8, num_sims=10000):
    if sp_name == "TBD": return None
    factors = [f"📊 Live 2026 Baseline: {base_k_rate*100:.1f}%"] 
    pos, neg = [], []

    # Apply Situationals
    if opp_team in AGGRESSIVE_LINEUPS: neg.append(0.03); factors.append("⚠️ Quick Out Aggressor (-3.0%)")
    if opp_team in HIGH_K_LINEUPS: pos.append(0.03); factors.append("🏏 High-Chase Opponent (+3.0%)")
    elif opp_team in LOW_K_LINEUPS: neg.append(0.04); factors.append("🛡️ Elite Contact Opponent (-4.0%)")
    
    # Regularization (Anti-Double Count)
    pos.sort(reverse=True); neg.sort(reverse=True)
    adj_k_rate = base_k_rate + sum(v * (0.5**i) for i,v in enumerate(pos)) - sum(v * (0.5**i) for i,v in enumerate(neg))
    adj_k_rate = max(0.10, min(0.45, adj_k_rate))

    # Simulation
    is_boom = any(x.lower() in sp_name.lower() for x in BOOM_BUST_PITCHERS)
    rates = np.random.normal(adj_k_rate, (0.08 if is_boom else 0.03), num_sims)
    sims = np.random.binomial(int(pitch_limit/ppa), np.clip(rates, 0.05, 0.65))
    
    return {
        'simulations': sims,
        'distribution': (pd.DataFrame(sims, columns=['Ks'])['Ks'].value_counts(normalize=True).sort_index() * 100),
        'factors': factors
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Monte Carlo Simulator")
slate = get_mlb_slate(target_date_str)

if slate:
    for i, game in enumerate(slate):
        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']}"):
            col1, col2 = st.columns(2)
            for side, name, rate, opp, line_key in [('✈️', game['a_sp'], game['a_base_k_rate'], game['h'], 'ak'), ('🏠', game['h_sp'], game['h_base_k_rate'], game['a'], 'hk')]:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    proj = run_monte_carlo(name, rate, opp, game['h'], side=='🏠')
                    k_line = st.number_input("Line:", 5.5, key=f"{line_key}_{i}")
                    prob = (np.sum(proj['simulations'] > k_line) / 10000) * 100
                    if prob > 56: st.success(f"📈 {prob:.1f}% Chance OVER")
                    elif prob < 44: st.error(f"📉 {100-prob:.1f}% Chance UNDER")
                    st.bar_chart(proj['distribution'])
                    for f in proj['factors']: st.write(f"- {f}")

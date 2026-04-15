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
# 🤖 AUTOMATED DATA: 2026 SEASON BASELINES & EFFICIENCY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_live_pitcher_database():
    """Pulls 2026 K%, BB% (Command Tax), and IP/GS (Leash) for automation."""
    try:
        df = pyb.pitching_stats(2026, qual=1)
        # Convert percentages to floats
        for col in ['K%', 'BB%']:
            if df[col].dtype == object:
                df[col] = df[col].str.rstrip('%').astype('float') / 100.0
        
        # Calculate Leash: Avg Pitches per game (Proxy using IP/GS * 15 + 15)
        df['Leash'] = (df['IP'] / df['GS']) * 15 + 15
        df['Leash'] = df['Leash'].clip(60, 105) # Realistic bounds
        
        # Create a dictionary of all stats
        stats_db = {}
        for _, row in df.iterrows():
            stats_db[row['Name']] = {
                'K%': row['K%'],
                'BB%': row['BB%'],
                'Leash': row['Leash']
            }
        return stats_db
    except: return {}

STATS_DB = get_live_pitcher_database()

def get_pitcher_stats(pitcher_name):
    # Match by full name or last name
    match = STATS_DB.get(pitcher_name)
    if not match:
        for name, data in STATS_DB.items():
            if name.split(' ')[-1] == pitcher_name.split(' ')[-1]:
                match = data
                break
    
    if match:
        # AUTOMATION: High BB% = High PPA (Walk Tax)
        auto_ppa = 3.8 + (match['BB%'] * 2.5) # E.g. 20% BB adds 0.5 to PPA
        return match['K%'], match['Leash'], auto_ppa
    return 0.22, 95.0, 3.8 # Default

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
                
                h_k, h_leash, h_ppa = get_pitcher_stats(h_sp)
                a_k, a_leash, a_ppa = get_pitcher_stats(a_sp)

                games.append({
                    'h': home['team']['abbreviation'], 'a': away['team']['abbreviation'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k': h_k, 'h_leash': h_leash, 'h_ppa': h_ppa,
                    'a_base_k': a_k, 'a_leash': a_leash, 'a_ppa': a_ppa
                })
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 2. MONTE CARLO ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, opp_team, pitch_limit, ppa, num_sims=10000):
    if sp_name == "TBD": return None
    factors = [f"📊 Live 2026 Baseline: {base_k_rate*100:.1f}%"] 
    pos, neg = [], []

    if opp_team in AGGRESSIVE_LINEUPS: neg.append(0.03); factors.append("⚠️ Quick Out Aggressor (-3.0%)")
    if opp_team in HIGH_K_LINEUPS: pos.append(0.03); factors.append("🏏 High-Chase Opponent (+3.0%)")
    elif opp_team in LOW_K_LINEUPS: neg.append(0.04); factors.append("🛡️ Elite Contact Opponent (-4.0%)")
    
    # Regularization
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
            
            # Setup data for loop
            sides = [
                ('✈️', game['a_sp'], game['a_base_k'], game['a_leash'], game['a_ppa'], game['h'], 'ak'),
                ('🏠', game['h_sp'], game['h_base_k'], game['h_leash'], game['h_ppa'], game['a'], 'hk')
            ]

            for side, name, rate, leash, ppa, opp, line_key in sides:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    # AUTOMATED INPUTS AS DEFAULTS
                    pl = st.slider(f"{name} Max Pitches", 60, 115, int(leash), key=f"pl_{line_key}_{i}")
                    eff = st.slider(f"{opp} P/PA", 3.0, 5.0, float(ppa), step=0.1, key=f"eff_{line_key}_{i}")
                    
                    proj = run_monte_carlo(name, rate, opp, pl, eff)
                    k_line = st.number_input("Vegas Line:", 0.5, 12.5, 5.5, 0.5, key=f"{line_key}_{i}")
                    prob = (np.sum(proj['simulations'] > k_line) / 10000) * 100
                    
                    if prob > 56: st.success(f"📈 {prob:.1f}% Chance OVER")
                    elif prob < 44: st.error(f"📉 {100-prob:.1f}% Chance UNDER")
                    
                    st.bar_chart(proj['distribution'])
                    for f in proj['factors']: st.write(f"- {f}")

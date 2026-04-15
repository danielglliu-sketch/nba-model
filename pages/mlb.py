import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Restoration", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed!")

odds_api_key = st.sidebar.text_input("The Odds API Key (Optional):", type="password")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 SIMULATION MODIFIERS (PRESERVED)
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
use_ml_weights = st.sidebar.checkbox("🤖 Use ML Contextual Weights", value=True)

with st.sidebar.expander("1. Lineup Discipline & Aggression"):
    high_k_lineups_input = st.text_area("HIGH-K LINEUPS", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]
    aggressive_lineups_input = st.text_area("EARLY COUNT SWINGERS (-Ks)", "SEA, COL, MIA, DET")
    AGGRESSIVE_LINEUPS = [x.strip() for x in aggressive_lineups_input.split(',')]
    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS", "Reid Detmers, Ryan Weathers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATION: THE FUZZY DATA ENGINE
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    try:
        df = pyb.pitching_stats(2026, qual=0)
        for col in ['K%', 'BB%']:
            if df[col].dtype == object:
                df[col] = df[col].str.rstrip('%').astype('float') / 100.0
        df['Leash'] = ((df['IP'] / df['GS']) * 14 + 8).clip(55, 105)
        df['Auto_PPA'] = 3.8 + (df['BB%'] * 7.5) 
        return df.set_index('Name')[['K%', 'BB%', 'Leash', 'Auto_PPA']].to_dict('index')
    except: return {}

STATS_DB = get_pitcher_stats_database()

def get_automated_metrics(pitcher_name):
    all_names = list(STATS_DB.keys())
    matches = difflib.get_close_matches(pitcher_name, all_names, n=1, cutoff=0.55)
    if matches:
        match = STATS_DB[matches[0]]
        k_rate = match['K%']
        if match['BB%'] > 0.12:
            k_rate = k_rate * 0.70 # Command Decay Fix
        return k_rate, match['Leash'], match['Auto_PPA'], match['BB%'], matches[0]
    return 0.22, 95.0, 3.8, 0.08, "⚠️ LEAGUE AVERAGE"

# ─────────────────────────────────────────────────────────────────────────────
# 1. FETCHERS & ENGINE
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
                h_name = home['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in home else 'TBD'
                a_name = away['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in away else 'TBD'
                h_k, h_leash, h_ppa, h_bb, h_full = get_automated_metrics(h_name)
                a_k, a_leash, a_ppa, a_bb, a_full = get_automated_metrics(a_name)
                games.append({
                    'h_team': home['team']['abbreviation'], 'a_team': away['team']['abbreviation'],
                    'h_sp': h_name, 'a_sp': a_name, 'h_full': h_full, 'a_full': a_full,
                    'h_base_k': h_k, 'h_leash': h_leash, 'h_ppa': h_ppa, 'h_bb': h_bb,
                    'a_base_k': a_k, 'a_leash': a_leash, 'a_ppa': a_ppa, 'a_bb': a_bb
                })
        return games
    except: return []

def run_monte_carlo(sp_name, base_k_rate, bb_rate, opp_team, pitch_limit, ppa, num_sims=10000):
    if sp_name == "TBD": return None
    pos, neg = [], []
    factors = [f"📊 Adjusted K%: {base_k_rate*100:.1f}%"]
    if opp_team in AGGRESSIVE_LINEUPS: neg.append(0.025); factors.append("⚠️ Quick Out Aggressor")
    w_high_k = 0.03 if not use_ml_weights else 0.03 * (1.2 if opp_team in HIGH_K_LINEUPS else 1.0)
    if bb_rate > 0.12: w_high_k = w_high_k * 0.4 # Matchup Dampener
    if opp_team in HIGH_K_LINEUPS: pos.append(w_high_k)
    elif opp_team in LOW_K_LINEUPS: neg.append(0.04)
    adj_k_rate = base_k_rate + sum(v*(0.5**i) for i,v in enumerate(pos)) - sum(v*(0.5**i) for i,v in enumerate(neg))
    rates = np.random.normal(adj_k_rate, 0.03, num_sims)
    sims = np.random.binomial(int(pitch_limit / ppa), np.clip(rates, 0.05, 0.65))
    return {'sims': sims, 'factors': factors}

# ─────────────────────────────────────────────────────────────────────────────
# 3. UI & BEST BETS
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Best Bets Restored")

best_bets_container = st.container()
best_bets_data = []

slate = get_mlb_slate(target_date_str)

if slate:
    for i, game in enumerate(slate):
        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h_team']})"):
            st.info(f"🛡️ **DATA HUD** | Away: {game['a_full']} ({game['a_bb']*100:.1f}% BB) | Home: {game['h_full']} ({game['h_bb']*100:.1f}% BB)")
            col1, col2 = st.columns(2)
            for side, name, full, rate, leash, ppa, bb, opp, key in [
                ('✈️', game['a_sp'], game['a_full'], game['a_base_k'], game['a_leash'], game['a_ppa'], game['a_bb'], game['h_team'], 'a'),
                ('🏠', game['h_sp'], game['h_full'], game['h_base_k'], game['h_leash'], game['h_ppa'], game['h_bb'], game['a_team'], 'h')
            ]:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    pl = st.slider(f"{name} Cap", 40, 115, int(leash), key=f"pl_{key}_{i}")
                    eff = st.slider(f"{name} P/PA", 3.0, 5.5, float(ppa), step=0.1, key=f"eff_{key}_{i}")
                    res = run_monte_carlo(name, rate, bb, opp, pl, eff)
                    line = st.number_input("Vegas Line:", 0.5, 12.5, 5.5, 0.5, key=f"line_{key}_{i}")
                    prob = (np.sum(res['sims'] > line) / 10000) * 100
                    if prob > 58: st.success(f"📈 {prob:.1f}% OVER")
                    elif prob < 42: st.error(f"📉 {100-prob:.1f}% UNDER")
                    st.bar_chart(pd.Series(res['sims']).value_counts().sort_index())
                    
                    # Population of Best Bets
                    if "LEAGUE AVERAGE" not in full:
                        if prob >= 59.0 or prob <= 41.0:
                            best_bets_data.append({'sp': name, 'line': line, 'prob': prob, 'side': side})

    with best_bets_container:
        st.subheader("⭐ Premium Best Bets (Validated Data Only)")
        if not best_bets_data:
            st.info("No high-confidence bets identified for this slate.")
        else:
            for bet in best_bets_data:
                label = "OVER" if bet['prob'] > 50 else "UNDER"
                edge = bet['prob'] if label == "OVER" else 100 - bet['prob']
                st.success(f"**{bet['sp']}** ({bet['side']}) | **{label} {bet['line']} Ks** | Confidence: **{edge:.1f}%**")
        st.divider()

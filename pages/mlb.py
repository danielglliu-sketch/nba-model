import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - The Shrinkage Update", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed!")

odds_api_key = st.sidebar.text_input("The Odds API Key (Optional):", type="password")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS (PRESERVED)
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
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS", "Reid Detmers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATION: BAYESIAN SHRINKAGE ENGINE
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    try:
        df = pyb.pitching_stats(2026, qual=0)
        # TBF (Total Batters Faced) is our N for Shrinkage
        df['TBF'] = df['TBF'].fillna(50) 
        
        for col in ['K%', 'BB%']:
            if df[col].dtype == object:
                df[col] = df[col].str.rstrip('%').astype('float') / 100.0
        
        # --- NEW: BAYESIAN SHRINKAGE (FIXES OVERCONFIDENCE) ---
        # K-constant for BB% reliability is roughly 100 TBF
        # K-constant for K% reliability is roughly 70 TBF
        df['K%'] = (df['K%'] * df['TBF'] + 0.22 * 70) / (df['TBF'] + 70)
        df['BB%'] = (df['BB%'] * df['TBF'] + 0.08 * 100) / (df['TBF'] + 100)
        
        df['Leash'] = ((df['IP'] / df['GS']) * 14 + 10).clip(55, 105)
        df['Auto_PPA'] = 3.8 + (df['BB%'] * 6.5) 
        
        return df.set_index('Name')[['K%', 'BB%', 'Leash', 'Auto_PPA']].to_dict('index')
    except: return {}

STATS_DB = get_pitcher_stats_database()

def get_automated_pitcher_metrics(pitcher_name):
    all_names = list(STATS_DB.keys())
    matches = difflib.get_close_matches(pitcher_name, all_names, n=1, cutoff=0.55)
    match = STATS_DB[matches[0]] if matches else None
    
    if match:
        k_rate = match['K%']
        # COMMAND PENALTY (Kept but balanced by shrinkage)
        if match['BB%'] > 0.11: k_rate = k_rate * 0.75 
        return k_rate, match['Leash'], match['Auto_PPA'], match['BB%'], matches[0]
    return 0.22, 95.0, 3.8, 0.08, "⚠️ Data Missing"

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
                h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in home else 'TBD'
                a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in away else 'TBD'
                h_k, h_l, h_p, h_bb, h_f = get_automated_pitcher_metrics(h_sp)
                a_k, a_l, a_p, a_bb, a_f = get_automated_pitcher_metrics(a_sp)
                games.append({
                    'h': home['team']['abbreviation'], 'a': away['team']['abbreviation'],
                    'h_sp': h_sp, 'a_sp': a_sp, 'h_full': h_f, 'a_full': a_f,
                    'h_base_k': h_k, 'h_leash': h_l, 'h_ppa': h_p, 'h_bb': h_bb,
                    'a_base_k': a_k, 'a_leash': a_l, 'a_ppa': a_p, 'a_bb': a_bb
                })
        return games
    except: return []

def run_monte_carlo(sp_name, base_k_rate, bb_rate, opp_team, pitch_limit=95, ppa=3.8, num_sims=10000):
    if sp_name == "TBD": return None
    pos, neg = [], []
    w_high_k = 0.03 if not use_ml_weights else 0.03 * (1.2 if opp_team in HIGH_K_LINEUPS else 1.0)
    if bb_rate > 0.11: w_high_k = w_high_k * 0.5 # Dampener
    if opp_team in AGGRESSIVE_LINEUPS: neg.append(0.025)
    if opp_team in HIGH_K_LINEUPS: pos.append(w_high_k)
    elif opp_team in LOW_K_LINEUPS: neg.append(0.04)
    
    adj_k_rate = base_k_rate + sum(v*(0.5**i) for i,v in enumerate(pos)) - sum(v*(0.5**i) for i,v in enumerate(neg))
    # INCREASED VARIANCE (Scale 0.05 instead of 0.03 for early season chaos)
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=0.05, size=num_sims)
    sims = np.random.binomial(n=int(pitch_limit / ppa), p=np.clip(game_k_rates, 0.05, 0.65))
    return {'sims': sims, 'rate': adj_k_rate}

# ─────────────────────────────────────────────────────────────────────────────
# 3. UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: The Shrinkage Update")
st.divider()

best_bets_container = st.container()
best_bets_data = []

slate = get_mlb_slate(target_date_str)

if slate:
    for i, game in enumerate(slate):
        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']})"):
            st.caption(f"📊 **Data Source** | Away: {game['a_full']} ({game['a_bb']*100:.1f}% Regressed BB) | Home: {game['h_full']} ({game['h_bb']*100:.1f}% Regressed BB)")
            col1, col2 = st.columns(2)
            for side, name, rate, leash, ppa, bb, opp, key in [
                ('✈️', game['a_sp'], game['a_base_k'], game['a_leash'], game['a_ppa'], game['a_bb'], game['h'], 'a'),
                ('🏠', game['h_sp'], game['h_base_k'], game['h_leash'], game['h_ppa'], game['h_bb'], game['a'], 'h')
            ]:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    pl = st.slider(f"{name} Max Pitches", 40, 115, int(leash), key=f"pl_{key}_{i}")
                    eff = st.slider(f"{name} P/PA", 3.0, 5.5, float(ppa), step=0.1, key=f"eff_{key}_{i}")
                    res = run_monte_carlo(name, rate, bb, opp, pl, eff)
                    line = st.number_input("Line:", 0.5, 12.5, 5.5, 0.5, key=f"line_{key}_{i}")
                    prob = (np.sum(res['sims'] > line) / 10000) * 100
                    if prob > 57: st.success(f"📈 {prob:.1f}% OVER")
                    elif prob < 43: st.error(f"📉 {100-prob:.1f}% UNDER")
                    st.bar_chart(pd.Series(res['sims']).value_counts(normalize=True).sort_index() * 100)
                    if (prob >= 58.0 or prob <= 42.0) and not any(x.lower() in name.lower() for x in BOOM_BUST_PITCHERS if x):
                        best_bets_data.append({'sp': name, 'line': line, 'prob': prob, 'side': side})

    with best_bets_container:
        st.subheader("⭐ Quant Identified: Premium Best Bets")
        if not best_bets_data: st.info("No premium best bets identified.")
        else:
            for bet in best_bets_data:
                s = "OVER" if bet['prob'] > 50 else "UNDER"
                edge = bet['prob'] if s == "OVER" else 100 - bet['prob']
                st.success(f"**{bet['sp']}** ({bet['side']}) | **{s} {bet['line']} Ks** | Confidence: **{edge:.1f}%**")
        st.divider()

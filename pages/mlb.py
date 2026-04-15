import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Monte Carlo K-Model", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed! Re-running 10,000 simulations per pitcher.")

# --- LIVE ODDS API (CLV TRACKING) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Live Odds Integration")
st.sidebar.caption("Get a free key at the-odds-api.com to pull live Vegas lines and track CLV.")
odds_api_key = st.sidebar.text_input("The Odds API Key (Optional):", type="password")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Simulation Modifiers")

use_ml_weights = st.sidebar.checkbox("🤖 Use ML Contextual Weights (XGBoost Emulator)", value=True)

with st.sidebar.expander("1. Lineup Discipline & Aggression", expanded=False):
    high_k_lineups_input = st.text_area("HIGH-K LINEUPS", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    aggressive_lineups_input = st.text_area("EARLY COUNT SWINGERS (-Ks via Quick Outs)", "SEA, COL, MIA, DET")
    AGGRESSIVE_LINEUPS = [x.strip() for x in aggressive_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    
    # Reid is kept here to serve as the exclusion list for Best Bets
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS", "Reid Detmers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

with st.sidebar.expander("2. Environment & Matchup", expanded=False):
    cold_weather = st.text_area("COLD/WIND IN GAMES", "MIN, CHW, DET, CLE, CHC, SF")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

with st.sidebar.expander("3. Predictability (Best Bets Filter)", expanded=False):
    analytics_teams_input = st.text_area("STRICT ANALYTICS TEAMS", "TB, LAD, MIL, BAL")
    ANALYTICS_TEAMS = [x.strip() for x in analytics_teams_input.split(',')]

with st.sidebar.expander("4. Advanced Arsenal Matching", expanded=False):
    elite_arsenal_input = st.text_area("MANUAL OVERRIDE: ELITE PITCH MATCHUP", "")
    ELITE_ARSENAL = [x.strip() for x in elite_arsenal_input.split(',')] if elite_arsenal_input else []
    
    poor_arsenal_input = st.text_area("MANUAL OVERRIDE: POOR PITCH MATCHUP", "")
    POOR_ARSENAL = [x.strip() for x in poor_arsenal_input.split(',')] if poor_arsenal_input else []

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATED DATA
# ─────────────────────────────────────────────────────────────────────────────
TEAM_WHIFF_VULNERABILITY = {
    'SEA': {'Slider': 1.15, 'Fastball': 1.05, 'Curve': 1.10},
    'COL': {'Slider': 1.20, 'Fastball': 1.10, 'Changeup': 1.05},
    'CHW': {'Slider': 1.10, 'Fastball': 1.12, 'Curve': 1.08},
    'NYY': {'Slider': 0.92, 'Fastball': 0.95, 'Changeup': 0.98}, 
    'HOU': {'Slider': 0.85, 'Fastball': 0.88, 'Curve': 0.90}, 
}

@st.cache_data(ttl=3600)
def get_pitcher_mix(sp_name):
    mix = {
        'Dylan Cease': {'Slider': 0.45, 'Fastball': 0.40},
        'Logan Webb': {'Changeup': 0.35, 'Sinker': 0.35},
        'Corbin Burnes': {'Cutter': 0.45, 'Curve': 0.20},
        'Michael King': {'Sinker': 0.30, 'Slider': 0.25, 'Changeup': 0.20},
        'Shane McClanahan': {'Four-Seamer': 0.35, 'Changeup': 0.25, 'Curve': 0.20}
    }
    return mix.get(sp_name, {'Fastball': 0.50, 'Slider': 0.20})

def calculate_automated_arsenal_score(sp_name, opp_team):
    mix = get_pitcher_mix(sp_name)
    team_weakness = TEAM_WHIFF_VULNERABILITY.get(opp_team, {'Slider': 1.0, 'Fastball': 1.0, 'Curve': 1.0})
    score = 1.0
    for pitch, usage in mix.items():
        vulnerability = team_weakness.get(pitch, 1.0)
        score += (usage * (vulnerability - 1))
    return score

@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    try:
        # qual=0 ensures we catch Shane/King even with low inning counts
        df = pyb.pitching_stats(2026, qual=0)
        for col in ['K%', 'BB%']:
            if df[col].dtype == object:
                df[col] = df[col].str.rstrip('%').astype('float') / 100.0
        
        # Calculate Workload Logic
        df['Leash'] = ((df['IP'] / df['GS']) * 14 + 10).clip(55, 105)
        df['Auto_PPA'] = 3.8 + (df['BB%'] * 7.5)
        
        return df.set_index('Name')[['K%', 'BB%', 'Leash', 'Auto_PPA']].to_dict('index')
    except: return {}

STATS_DB = get_pitcher_stats_database()

def get_automated_pitcher_metrics(pitcher_name):
    all_names = list(STATS_DB.keys())
    matches = difflib.get_close_matches(pitcher_name, all_names, n=1, cutoff=0.55)
    
    match = None
    if matches:
        match = STATS_DB[matches[0]]
    
    if match:
        k_rate = match['K%']
        # SHANE FIX: Hard Command Penalty
        if match['BB%'] > 0.12:
            k_rate = k_rate * 0.70 
        return k_rate, match['Leash'], match['Auto_PPA'], match['BB%'], matches[0]
    return 0.22, 95.0, 3.8, 0.08, "⚠️ Data Missing"

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
                h_sp_raw = home['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in home else 'TBD'
                a_sp_raw = away['probables'][0].get('athlete', {}).get('displayName', 'TBD') if 'probables' in away else 'TBD'
                
                h_k, h_leash, h_ppa, h_bb, h_full = get_automated_pitcher_metrics(h_sp_raw)
                a_k, a_leash, a_ppa, a_bb, a_full = get_automated_pitcher_metrics(a_sp_raw)

                games.append({
                    'h': home['team']['abbreviation'], 'a': away['team']['abbreviation'],
                    'h_sp': h_sp_raw, 'a_sp': a_sp_raw, 'h_full': h_full, 'a_full': a_full,
                    'h_base_k_rate': h_k, 'h_leash': h_leash, 'h_ppa': h_ppa, 'h_bb': h_bb,
                    'a_base_k_rate': a_k, 'a_leash': a_leash, 'a_ppa': a_ppa, 'a_bb': a_bb
                })
        return games
    except: return []

@st.cache_data(ttl=300)
def get_live_odds(api_key):
    if not api_key: return {}
    try:
        url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={api_key}&regions=us&markets=pitcher_strikeouts&oddsFormat=american"
        resp = requests.get(url, timeout=5).json()
        lines = {}
        for game in resp:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'pitcher_strikeouts':
                        for outcome in market.get('outcomes', []):
                            player = outcome.get('description')
                            if player and player not in lines: lines[player] = outcome.get('point', 5.5)
        return lines
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 2. MONTE CARLO ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, bb_rate, opp_team, pitch_limit=95, ppa=3.8, num_sims=10000):
    if sp_name == "TBD": return None
    
    pos, neg = [], []
    w_high_k = 0.03 if not use_ml_weights else 0.03 * (1.2 if opp_team in HIGH_K_LINEUPS else 1.0)
    
    # SHANE FIX: Wild pitchers cannot exploit high-K lineups
    if bb_rate > 0.12:
        w_high_k = w_high_k * 0.4 

    if opp_team in AGGRESSIVE_LINEUPS: neg.append(0.025)
    if opp_team in HIGH_K_LINEUPS: pos.append(w_high_k)
    elif opp_team in LOW_K_LINEUPS: neg.append(0.04)

    arsenal_score = calculate_automated_arsenal_score(sp_name, opp_team)
    if arsenal_score > 1.02: pos.append((arsenal_score - 1.0) * 0.15)

    pos.sort(reverse=True); neg.sort(reverse=True)
    adj_k_rate = base_k_rate + sum(v * (0.5 ** i) for i, v in enumerate(pos)) - sum(v * (0.5 ** i) for i, v in enumerate(neg))

    is_high_variance = any(x.lower() in sp_name.lower() for x in BOOM_BUST_PITCHERS)
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=(0.08 if is_high_variance else 0.03), size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65) 

    batters_faced = int(pitch_limit / ppa)
    sims = np.random.binomial(n=batters_faced, p=game_k_rates)
    
    return {'sims': sims, 'adj_rate': adj_k_rate}

# ─────────────────────────────────────────────────────────────────────────────
# 3. UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Monte Carlo Simulator")
st.divider()

live_odds = get_live_odds(odds_api_key)
best_bets_container = st.container()
best_bets_data = []

slate = get_mlb_slate(target_date_str)

if not slate:
    st.info("No games found for this date. Check if the slate has started.")

if slate:
    for i, game in enumerate(slate):
        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']})"):
            st.caption(f"📊 **Data Source** | Away: {game['a_full']} ({game['a_bb']*100:.1f}% BB) | Home: {game['h_full']} ({game['h_bb']*100:.1f}% BB)")
            
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                pl_a = st.slider(f"{game['a_sp']} Max Pitches", 40, 115, int(game['a_leash']), key=f"pl_a_{i}")
                ppa_a = st.slider(f"{game['h']} P/PA", 3.0, 5.5, float(game['a_ppa']), step=0.1, key=f"ppa_a_{i}")
            with col_l2:
                pl_h = st.slider(f"{game['h_sp']} Max Pitches", 40, 115, int(game['h_leash']), key=f"pl_h_{i}")
                ppa_h = st.slider(f"{game['a']} P/PA", 3.0, 5.5, float(game['h_ppa']), step=0.1, key=f"ppa_h_{i}")
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['a_bb'], game['h'], pl_a, ppa_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['h_bb'], game['a'], pl_h, ppa_h)

            col1, col2 = st.columns(2)
            pitch_list = [
                ('✈️', a_proj, game['a_sp'], game['a'], game['h'], 'ak'), 
                ('🏠', h_proj, game['h_sp'], game['h'], game['a'], 'hk')
            ]
            
            for side, proj, name, team, opp, line_key in pitch_list:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    k_line = live_odds.get(name, st.number_input("Line:", 0.5, 12.5, 5.5, 0.5, key=f"{line_key}_{i}"))
                    prob = (np.sum(proj['sims'] > k_line) / 10000) * 100
                    
                    if prob > 60: st.success(f"📈 {prob:.1f}% OVER")
                    elif prob < 40: st.error(f"📉 {100-prob:.1f}% UNDER")
                    else: st.warning(f"⚖️ Line is sharp ({prob:.1f}% Over)")
                    
                    st.bar_chart(pd.Series(proj['sims']).value_counts(normalize=True).sort_index() * 100)
                    
                    # REID FILTER: Checks if name is in BOOM_BUST_PITCHERS before recommending
                    if (prob >= 58.0 or prob <= 42.0) and not any(x.lower() in name.lower() for x in BOOM_BUST_PITCHERS if x):
                        best_bets_data.append({'sp': name, 'line': k_line, 'prob': prob, 'side': side})

    with best_bets_container:
        st.subheader("⭐ Quant Identified: Premium Best Bets")
        if not best_bets_data: st.info("No high-confidence bets identified.")
        else:
            for bet in best_bets_data:
                s = "OVER" if bet['prob'] > 50 else "UNDER"
                edge = bet['prob'] if s == "OVER" else 100 - bet['prob']
                st.success(f"**{bet['sp']}** ({bet['side']}) | **{s} {bet['line']} Ks** | Confidence: **{edge:.1f}%**")
        st.divider()

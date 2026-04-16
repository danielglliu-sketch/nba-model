import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Autopilot Engine", page_icon="🤖", layout="wide")

st.sidebar.title("🤖 Quant Autopilot")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All APIs and Data Pipelines refreshed!")

# --- AUTOMATED DATABASES ---
# Coordinates for all 30 MLB Stadiums to pull live weather data
STADIUM_COORDS = {
    'ARI': (33.445, -112.067), 'ATL': (33.891, -84.468), 'BAL': (39.284, -76.622), 'BOS': (42.346, -71.097),
    'CHC': (41.948, -87.655), 'CHW': (41.830, -87.634), 'CIN': (39.097, -84.507), 'CLE': (41.496, -81.685),
    'COL': (39.756, -104.994), 'DET': (42.339, -83.048), 'HOU': (29.757, -95.355), 'KC': (39.051, -94.481),
    'LAA': (33.800, -117.883), 'LAD': (34.073, -118.240), 'MIA': (25.778, -80.220), 'MIL': (43.028, -87.971),
    'MIN': (44.981, -93.278), 'NYM': (40.757, -73.845), 'NYY': (40.830, -73.926), 'OAK': (37.751, -122.201),
    'PHI': (39.906, -75.166), 'PIT': (40.447, -80.006), 'SD': (32.707, -117.157), 'SF': (37.778, -122.389),
    'SEA': (47.591, -122.332), 'STL': (38.622, -90.193), 'TB': (27.768, -82.653), 'TEX': (32.751, -97.082),
    'TOR': (43.641, -79.389), 'WSH': (38.873, -77.007)
}

# Industry standard umpire profiles for strike-zone bias
UMPIRE_DATABASE = {
    "Pitcher Friendly": ["Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter", "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa"],
    "Hitter Friendly": ["Pat Hoberg", "Quinn Wolcott", "Doug Eddings", "Andy Fletcher", "Dan Bellino", "Lance Barrett", "CB Bucknor", "Ted Barrett"]
}

# Park Factor multipliers based on 5-year rolling strikeout variance
K_PARK_FACTORS = {
    'SEA': 1.06, 'TB': 1.05, 'MIA': 1.04, 'SD': 1.04, 'MIL': 1.03, 'OAK': 1.03, 'SF': 1.02, 'LAD': 1.02, 'NYM': 1.01, 'MIN': 1.01,
    'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 0.99, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98,
    'CHC': 0.97, 'STL': 0.97, 'PIT': 0.97, 'LAA': 0.96, 'HOU': 0.96, 'WSH': 0.95, 'CIN': 0.94, 'ARI': 0.93, 'COL': 0.85 
}

TEAM_MAP = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK',
    'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH'
}

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATED DATA PIPELINE (MLB & WEATHER APIs)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_live_temp(team_abbr):
    """Fetches real-time temperature from Open-Meteo for stadium coordinates."""
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords: return 70
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current_weather=true"
        data = requests.get(url, timeout=5).json()
        temp_c = data['current_weather']['temperature']
        return (temp_c * 9/5) + 32
    except: return 70

@st.cache_data(ttl=86400)
def get_automated_team_splits():
    """Fetches team strikeout rates vs Lefties and vs Righties independently."""
    splits = {}
    for hand in ['vL', 'vR']:
        h_code = 'L' if hand == 'vL' else 'R'
        url = f"https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=statSplits&sitCode={hand}"
        try:
            data = requests.get(url, timeout=10).json()
            for record in data['stats'][0]['splits']:
                abbr = TEAM_MAP.get(record['team']['name'])
                if abbr:
                    if abbr not in splits: splits[abbr] = {}
                    pa = record['stat'].get('plateAppearances', 1)
                    so = record['stat'].get('strikeOuts', 0)
                    splits[abbr][h_code] = so / pa
        except: pass
    return splits

SPLITS_DB = get_automated_team_splits()

@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    """Fetches official 2026 pitcher metrics and handedness."""
    url = "https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=1000"
    pitcher_db = {}
    try:
        data = requests.get(url, timeout=15).json()
        for record in data['stats'][0]['splits']:
            name = record['player']['fullName']
            pid = record['player']['id']
            
            # Fetch specific Handedness per pitcher
            p_info = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}").json()
            hand = p_info['people'][0].get('pitchHand', {}).get('code', 'R')
            
            stat = record['stat']
            tbf = stat.get('battersFaced', 0)
            so = stat.get('strikeOuts', 0)
            gs = stat.get('gamesStarted', 0)
            
            if tbf == 0: continue
            raw_k = so / tbf
            
            # Autopilot Workload Regression
            bf_per_start = max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))
            # Bayesian Shrinkage (April Weights)
            shrunk_k = (raw_k * tbf + 0.22 * 25) / (tbf + 25)
            
            pitcher_db[name] = {
                'K%': shrunk_k, 'Raw_K%': raw_k, 'Hand': hand,
                'SwStr%': raw_k * 0.5, 'BF_per_Start': bf_per_start
            }
        return pitcher_db
    except: return {}

STATS_DB = get_pitcher_stats_database()

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE MONTE CARLO ENGINE (AUDITED MATH)
# ─────────────────────────────────────────────────────────────────────────────

def run_monte_carlo(sp_name, base_k_rate, raw_k_rate, swstr_rate, opp_k_rate, park, batters_faced, temp, umpire, num_sims=10000):
    factors = []
    adj_k_rate = base_k_rate
    
    # 1. Automated Form Warning
    if raw_k_rate < (base_k_rate - 0.02):
        factors.append(f"📉 Form Warning: Season actual ({raw_k_rate*100:.1f}%) is lagging projection.")
    
    # 2. Automated Elite Whiff Proxy
    if swstr_rate > 0.135: 
        adj_k_rate += 0.04
        factors.append("🎯 Elite Whiff Boost (+4.0%)")

    # 3. Automated Split-Specific Opponent Multiplier (Softened)
    opp_ratio = 1.0 + (((opp_k_rate / 0.225) - 1.0) * 0.5)
    adj_k_rate *= opp_ratio
    factors.append(f"🏏 Opponent Split K% ({opp_k_rate*100:.1f}%) applied ({opp_ratio:.2f}x)")

    # 4. Automated Live Weather Correction
    if temp < 60:
        adj_k_rate += 0.02
        factors.append(f"🥶 Cold Weather detected ({temp:.0f}°F) (+2.0%)")
        
    # 5. Automated Umpire Profile
    if umpire in UMPIRE_DATABASE["Pitcher Friendly"]:
        adj_k_rate += 0.015
        factors.append(f"💎 Pitcher-Friendly Umpire ({umpire}) (+1.5%)")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly"]:
        adj_k_rate -= 0.015
        factors.append(f"🧱 Hitter-Friendly Umpire ({umpire}) (-1.5%)")

    # 6. Automated Park Factor
    pk = K_PARK_FACTORS.get(park, 1.0)
    adj_k_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ Park Factor ({((pk-1)*100):+.1f}%)")

    adj_k_rate = max(0.08, min(0.45, adj_k_rate))
    
    # --- FAT TAILS: DYNAMIC WORKLOAD VARIANCE ---
    variance_scale = 0.03
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=variance_scale, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65)
    z_scores = (game_k_rates - adj_k_rate) / variance_scale
    
    # Workload scales with performance: Good Stuff = Longer Outing
    dynamic_bf = np.clip(np.round(batters_faced + (z_scores * 2.5)).astype(int), 12, 32)
    
    simulations = np.random.binomial(n=dynamic_bf, p=game_k_rates)
    return {'simulations': simulations, 'factors': factors, 'mean_k': adj_k_rate}

def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob = win_prob_pct / 100.0
    payout_ratio = (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout_ratio) - (1.0 - prob)) * 100.0

# ─────────────────────────────────────────────────────────────────────────────
# 3. UI RENDERER
# ─────────────────────────────────────────────────────────────────────────────

st.title("🤖 MLB Quant AI - 100% Autopilot")
st.markdown("Contextual automation (Splits, Umpires, Weather) is active. Core Monte Carlo math is locked.")

# Fetch Schedule via Official MLB API
schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire"
try:
    slate_data = requests.get(schedule_url).json()
    games = slate_data.get('dates', [{}])[0].get('games', [])
except: games = []

if not games:
    st.info("No games found for the selected date. Ensure the date is correct.")
else:
    for game in games:
        home_team = TEAM_MAP.get(game['teams']['home']['team']['name'])
        away_team = TEAM_MAP.get(game['teams']['away']['team']['name'])
        
        # Confirmation check for starters
        h_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
        a_sp_name = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        if h_sp_name == "TBD" or a_sp_name == "TBD": continue
        
        # Automated Umpire Detection
        umpire = "Neutral"
        if 'officials' in game:
            for off in game['officials']:
                if off['officialType'] == 'Home Plate': 
                    umpire = off['official']['fullName']

        with st.expander(f"⚾ {away_team} @ {home_team} | Umpire: {umpire}"):
            # Automated Weather Fetch
            temp = get_live_temp(home_team)
            
            col1, col2 = st.columns(2)
            # Process Both Pitchers
            for side, sp_name, team, opp_team in [(col1, a_sp_name, away_team, home_team), (col2, h_sp_name, home_team, away_team)]:
                with side:
                    # Get pitcher profile
                    match = STATS_DB.get(sp_name, {'K%': 0.22, 'Raw_K%': 0.22, 'Hand': 'R', 'SwStr%': 0.11, 'BF_per_Start': 23})
                    
                    # Automate Handedness Split Logic
                    opp_k_rate = SPLITS_DB.get(opp_team, {}).get(match['Hand'], 0.225)
                    
                    # Run Engine
                    res = run_monte_carlo(sp_name, match['K%'], match['Raw_K%'], match['SwStr%'], opp_k_rate, home_team, match['BF_per_Start'], temp, umpire)
                    
                    st.markdown(f"### {sp_name} ({match['Hand']}HP)")
                    
                    # Market Inputs (Manual only to track profit)
                    line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"L_{sp_name}_{game['gamePk']}")
                    c_ev1, c_ev2 = st.columns(2)
                    with c_ev1: o_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"OO_{sp_name}_{game['gamePk']}")
                    with c_ev2: u_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"UO_{sp_name}_{game['gamePk']}")
                    
                    # Final Probability Calculation
                    o_prob = (np.sum(res['simulations'] > line) / 10000) * 100
                    u_prob = 100 - o_prob
                    o_ev = calculate_ev_percent(o_prob, o_odds)
                    u_ev = calculate_ev_percent(u_prob, u_odds)
                    
                    if o_prob > 60: st.success(f"📈 {o_prob:.1f}% Chance OVER")
                    elif u_prob > 60: st.error(f"📉 {u_prob:.1f}% Chance UNDER")
                    else: st.warning(f"⚖️ Neutral Matchup ({o_prob:.1f}% Over)")
                    
                    if o_ev > 2.0: st.success(f"🔥 +EV OVER: {o_ev:+.1f}% Edge")
                    elif u_ev > 2.0: st.success(f"🔥 +EV UNDER: {u_ev:+.1f}% Edge")
                    else: st.info(f"🛑 No Edge Found (Max EV: {max(o_ev, u_ev):+.1f}%)")
                    
                    # Visual Distribution
                    dist_data = pd.Series(res['simulations']).value_counts(normalize=True).sort_index()
                    st.bar_chart(dist_data)
                    
                    # Automation Factor Logging
                    for f in res['factors']: st.caption(f"- {f}")

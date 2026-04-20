import os
import math
import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# ==============================================================================
# CSV TRACKING LEDGER (Hitter Edition)
# ==============================================================================
def log_play_to_csv(date, player, team, opponent, line, pick, prob, ev, median_tb, weather):
    file_name = "hitter_quant_ledger.csv"
    file_exists = os.path.isfile(file_name)
    data = {
        "Date": date,
        "Player": player,
        "Team": team,
        "Opponent": opponent,
        "Line": line,
        "Pick": pick,
        "Prob_Pct": round(prob, 2),
        "EV_Pct": round(ev, 2),
        "Median_TB": round(median_tb, 2),
        "Weather": weather
    }
    df = pd.DataFrame([data])
    df.to_csv(file_name, mode='a', header=not file_exists, index=False)

# ==============================================================================
# PAGE SETUP
# ==============================================================================
st.set_page_config(page_title="MLB Hitter Quant - Total Bases", page_icon="🏏", layout="wide")
st.sidebar.title("🤖 Hitter Autopilot v1")
selected_date = st.sidebar.date_input("📅 Select Slate", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

# ==============================================================================
# STATIC DATABASES
# ==============================================================================
STADIUM_COORDS = {
    'ARI': (33.445, -112.067, 0),   'ATL': (33.891, -84.468, 110),  'BAL': (39.284, -76.622, 38),
    'BOS': (42.346, -71.097, 56),   'CHC': (41.948, -87.655, 45),   'CHW': (41.830, -87.634, 135),
    'CIN': (39.097, -84.507, 135),  'CLE': (41.496, -81.685, 0),    'COL': (39.756, -104.994, 0),
    'DET': (42.339, -83.048, 135),  'HOU': (29.757, -95.355, 337),  'KC':  (39.051, -94.481, 45),
    'LAA': (33.800, -117.883, 45),  'LAD': (34.073, -118.240, 28),  'MIA': (25.778, -80.220, 90),
    'MIL': (43.028, -87.971, 135),  'MIN': (44.981, -93.278, 45),   'NYM': (40.757, -73.845, 60),
    'NYY': (40.830, -73.926, 68),   'OAK': (37.751, -122.201, 35),  'PHI': (39.906, -75.166, 9),
    'PIT': (40.447, -80.006, 125),  'SD':  (32.707, -117.157, 0),   'SF':  (37.778, -122.389, 90),
    'SEA': (47.591, -122.332, 45),  'STL': (38.622, -90.193, 70),   'TB':  (27.768, -82.653, 60),
    'TEX': (32.751, -97.082, 70),   'TOR': (43.641, -79.389, 0),    'WSH': (38.873, -77.007, 25),
}

TEAM_MAP = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK',
    'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}

# ==============================================================================
# DATA FETCHING (Hitters)
# ==============================================================================
@st.cache_data(ttl=86400)
def get_hitter_stats():
    hitter_db = {}
    try:
        url = "https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&playerPool=ALL&season=2026"
        data = requests.get(url, timeout=10).json()
        for rec in data['stats'][0]['splits']:
            name, pid, s = rec['player']['fullName'], rec['player']['id'], rec['stat']
            pa = s.get('plateAppearances', 0)
            if pa < 20: continue
            
            # Calculate Base Probabilities
            h, d, t, hr = s.get('hits', 0), s.get('doubles', 0), s.get('triples', 0), s.get('homeRuns', 0)
            s_single = h - (d + t + hr)
            
            hitter_db[pid] = {
                'Name': name,
                'Team': TEAM_MAP.get(rec.get('team', {}).get('name', ''), 'UNK'),
                'PA_G': pa / s.get('gamesPlayed', 1),
                'P_1B': s_single / pa,
                'P_2B': d / pa,
                'P_3B': t / pa,
                'P_HR': hr / pa,
                'P_OUT': (pa - h - s.get('baseOnBalls', 0)) / pa
            }
        return hitter_db
    except: return {}

HITTER_DB = get_hitter_stats()

@st.cache_data(ttl=3600)
def get_weather(team_abbr, date_str):
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords: return 70.0, 0.0, 0.0, 0.0
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&start_date={date_str}&end_date={date_str}&daily=temperature_2m_max,wind_speed_10m_max,wind_direction_10m_dominant&timezone=auto")
        data = requests.get(url, timeout=5).json()
        temp_f = (data['daily']['temperature_2m_max'][0] * 9 / 5) + 32
        return temp_f, data['daily']['wind_speed_10m_max'][0], data['daily']['wind_direction_10m_dominant'][0], coords[2]
    except: return 70.0, 0.0, 0.0, 0.0

# ==============================================================================
# TB MONTE CARLO ENGINE
# ==============================================================================
def run_tb_sim(h_data, temp, wind_speed, wind_dir, azimuth, num_sims=10000):
    # Base Stats
    p_1, p_2, p_3, p_hr = h_data['P_1B'], h_data['P_2B'], h_data['P_3B'], h_data['P_HR']
    
    # Physics Penalty
    wind_factor = math.cos(math.radians(azimuth - wind_dir))
    effective_wind = wind_speed * wind_factor
    
    penalty = 1.0
    if temp < 55: penalty *= 0.92  # Cold air kills carry
    if effective_wind > 8.0: penalty *= 0.90 # Wind in kills carry
    elif effective_wind < -8.0: penalty *= 1.10 # Wind out boosts carry
    
    # Adjust Power Probabilities (HR and Extra Base Hits)
    p_hr *= penalty
    p_2 *= (1 + (penalty - 1) * 0.5)
    
    # Simulate Games
    results = []
    pa_per_game = np.random.normal(h_data['PA_G'], 0.5, num_sims).round().astype(int)
    
    for pa_count in pa_per_game:
        # 0=Out, 1=1B, 2=2B, 3=3B, 4=HR
        probs = [1 - (p_1+p_2+p_3+p_hr), p_1, p_2, p_3, p_hr]
        outcomes = np.random.choice([0, 1, 2, 3, 4], size=pa_count, p=probs)
        results.append(np.sum(outcomes))
        
    return np.array(results)

# ==============================================================================
# UI
# ==============================================================================
st.title("🏏 MLB Quant AI - Total Bases Edition")

try:
    schedule = requests.get(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}").json()
    games = schedule.get('dates', [{}])[0].get('games', [])
except: games = []

for game in games:
    home_abbr = TEAM_MAP.get(game['teams']['home']['team']['name'], 'UNK')
    away_abbr = TEAM_MAP.get(game['teams']['away']['team']['name'], 'UNK')
    
    temp, w_spd, w_dir, azm = get_weather(home_abbr, target_date_str)
    
    with st.expander(f"🏟️ {away_abbr} @ {home_abbr} | {temp:.0f}°F | Wind: {w_spd:.0f}mph"):
        # Select Hitters in this game
        game_hitters = [p for p in HITTER_DB.values() if p['Team'] in [home_abbr, away_abbr]]
        
        if game_hitters:
            target_hitter_name = st.selectbox("Select Hitter:", [p['Name'] for p in game_hitters], key=f"sel_{game['gamePk']}")
            h_data = next(p for p in game_hitters if p['Name'] == target_hitter_name)
            
            sim_results = run_tb_sim(h_data, temp, w_spd, w_dir, azm)
            
            line = st.number_input("TB Line:", value=1.5, step=0.5, key=f"line_{target_hitter_name}")
            h_prob = np.mean(sim_results > line) * 100
            l_prob = 100 - h_prob
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Higher Prob", f"{h_prob:.1f}%")
                if h_prob > 55: st.success("🔥 BEST BET: HIGHER")
            with col2:
                st.metric("Lower Prob", f"{l_prob:.1f}%")
                if l_prob > 55: st.error("❄️ BEST BET: LOWER")
            
            st.info(f"📊 Median TB: {np.median(sim_results)} | Avg PA: {h_data['PA_G']:.1f}")
            
            if st.button(f"💾 Log {target_hitter_name}", key=f"btn_{target_hitter_name}"):
                pick = "HIGHER" if h_prob > l_prob else "LOWER"
                log_play_to_csv(target_date_str, target_hitter_name, h_data['Team'], "OPP", line, pick, max(h_prob, l_prob), 0, np.median(sim_results), f"{temp:.0f}F {w_spd}mph")
                st.toast("Logged!")

# ==============================================================================
# LEDGER
# ==============================================================================
st.divider()
if os.path.exists("hitter_quant_ledger.csv"):
    st.header("📋 Hitter Ledger")
    st.dataframe(pd.read_csv("hitter_quant_ledger.csv").sort_index(ascending=False))

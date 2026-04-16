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

UMPIRE_DATABASE = {
    "Pitcher Friendly (Wide Zone)": [
        "Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter", 
        "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa", "Jeremie Rehak",
        "Vic Carapazza", "Lance Barksdale", "Doug Eddings", "Paul Emmel", "Cory Blaser",
        "Adrian Johnson", "John Tumpane", "Nic Lentz", "Ben May", "Ryan Blakney"
    ],
    "Hitter Friendly (Tight Zone)": [
        "Pat Hoberg", "Quinn Wolcott", "Andy Fletcher", "Dan Bellino", "Lance Barrett", 
        "CB Bucknor", "Ted Barrett", "Angel Hernandez", "Hunter Wendelstedt", "Mark Carlson",
        "Jeff Nelson", "Rob Drake", "Brian O'Nora", "Todd Tichenor", "Chad Fairchild",
        "Marvin Hudson", "Mike Muchlinski", "Adam Hamari", "Manny Gonzalez", "D.J. Reyburn"
    ]
}

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

# --- AUTOMATED DATA PIPELINE ---

@st.cache_data(ttl=3600)
def get_live_temp(team_abbr):
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
    url = "https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=1000"
    pitcher_db = {}
    try:
        people_url = "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026"
        people_data = requests.get(people_url).json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people_data['people']}
        data = requests.get(url, timeout=15).json()
        for record in data['stats'][0]['splits']:
            name = record['player']['fullName']
            pid = record['player']['id']
            hand = hand_map.get(pid, 'R')
            stat = record['stat']
            tbf = stat.get('battersFaced', 0)
            so = stat.get('strikeOuts', 0)
            bb = stat.get('baseOnBalls', 0)
            gs = stat.get('gamesStarted', 0)
            if tbf == 0: continue
            raw_k = so / tbf
            raw_bb = bb / tbf
            bf_per_start = max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))
            shrunk_k = (raw_k * tbf + 0.22 * 25) / (tbf + 25)
            pitcher_db[name] = {'K%': shrunk_k, 'Raw_K%': raw_k, 'BB%': raw_bb, 'Hand': hand, 'SwStr%': raw_k * 0.5, 'BF_per_Start': bf_per_start}
        return pitcher_db
    except: return {}

STATS_DB = get_pitcher_stats_database()

# --- THE MONTE CARLO ENGINE ---

def run_monte_carlo(sp_name, base_k_rate, raw_k_rate, bb_rate, swstr_rate, opp_k_rate, park, batters_faced, temp, umpire, num_sims=10000):
    factors = []
    adj_k_rate = base_k_rate
    
    # 1. Automated Form Warning (Underperformance)
    if raw_k_rate < (base_k_rate - 0.02): 
        factors.append("📉 Form Warning: Actual performance lagging projection.")
    
    # 2. SENSITIVE REGRESSION ALERT (Lowered to 1% to catch the Bubic fluke)
    if raw_k_rate > (base_k_rate + 0.01):
        factors.append("⚠️ Regression Risk: Pitcher is 'Hot Start' outlier (1%+ vs Baseline). High crash risk.")
    
    # 3. EFFICIENCY/WALK WARNING (The 'Early Exit' Failsafe)
    if bb_rate > 0.09:
        factors.append("⛽ Efficiency Warning: High Walk Rate increases risk of early pull.")
        
    if swstr_rate > 0.135: 
        adj_k_rate += 0.04
        factors.append("🎯 Elite Whiff Boost (+4.0%)")
        
    opp_ratio = 1.0 + (((opp_k_rate / 0.225) - 1.0) * 0.5)
    adj_k_rate *= opp_ratio
    factors.append(f"🏏 Opponent Split K% ({opp_k_rate*100:.1f}%) applied")
    
    if temp < 60:
        adj_k_rate += 0.02
        factors.append(f"🥶 Cold Weather detected ({temp:.0f}°F) (+2.0%)")
        
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]:
        adj_k_rate += 0.015
        factors.append(f"💎 Umpire: Wide Zone ({umpire}) (+1.5%)")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]:
        adj_k_rate -= 0.015
        factors.append(f"🧱 Umpire: Tight Zone ({umpire}) (-1.5%)")
    elif umpire != "Neutral":
        factors.append(f"⚖️ Umpire: Neutral Zone ({umpire})")
        
    pk = K_PARK_FACTORS.get(park, 1.0)
    adj_k_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ Park Factor ({((pk-1)*100):+.1f}%)")
    
    adj_k_rate = max(0.08, min(0.45, adj_k_rate))
    variance_scale = 0.03
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=variance_scale, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65)
    z_scores = (game_k_rates - adj_k_rate) / variance_scale
    dynamic_bf = np.clip(np.round(batters_faced + (z_scores * 2.5)).astype(int), 12, 32)
    simulations = np.random.binomial(n=dynamic_bf, p=game_k_rates)
    return {'simulations': simulations, 'factors': factors, 'mean_k': adj_k_rate}

def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob = win_prob_pct / 100.0
    payout_ratio = (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout_ratio) - (1.0 - prob)) * 100.0

st.title("🤖 MLB Quant AI - 100% Autopilot")
st.markdown("Ultra-Sensitive Regression Alert (1%) & Efficiency Failsafe enabled.")

schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire"
try:
    slate_data = requests.get(schedule_url).json()
    games = slate_data.get('dates', [{}])[0].get('games', [])
except: games = []

if not games:
    st.info("No games found. Please refresh or check date.")
else:
    for game in games:
        home_team = TEAM_MAP.get(game['teams']['home']['team']['name'])
        away_team = TEAM_MAP.get(game['teams']['away']['team']['name'])
        h_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
        a_sp_name = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        if h_sp_name == "TBD" or a_sp_name == "TBD": continue
        
        umpire = "Neutral"
        if 'officials' in game:
            for off in game['officials']:
                if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
        if umpire == "Neutral" and game['status']['abstractGameState'] == 'Final':
            try:
                bx_url = f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/boxscore"
                bx_data = requests.get(bx_url).json()
                for off in bx_data.get('officials', []):
                    if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
            except: pass

        with st.expander(f"⚾ {away_team} @ {home_team} | Umpire: {umpire}"):
            temp = get_live_temp(home_team)
            col1, col2 = st.columns(2)
            for side, sp_name, team, opp_team in [(col1, a_sp_name, away_team, home_team), (col2, h_sp_name, home_team, away_team)]:
                with side:
                    match = STATS_DB.get(sp_name, {'K%': 0.22, 'Raw_K%': 0.22, 'BB%': 0.08, 'Hand': 'R', 'SwStr%': 0.11, 'BF_per_Start': 23})
                    opp_k_rate = SPLITS_DB.get(opp_team, {}).get(match['Hand'], 0.225)
                    res = run_monte_carlo(sp_name, match['K%'], match['Raw_K%'], match['BB%'], match['SwStr%'], opp_k_rate, home_team, match['BF_per_Start'], temp, umpire)
                    
                    st.markdown(f"### {sp_name} ({match['Hand']}HP)")
                    line = st.number_input("Line:", value=5.5, step=0.5, key=f"L_{sp_name}_{game['gamePk']}")
                    o_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"OO_{sp_name}_{game['gamePk']}")
                    u_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"UO_{sp_name}_{game['gamePk']}")
                    
                    o_prob = (np.sum(res['simulations'] > line) / 10000) * 100
                    o_ev = calculate_ev_percent(o_prob, o_odds)
                    u_ev = calculate_ev_percent(100 - o_prob, u_odds)
                    
                    if o_prob > 60: st.success(f"📈 {o_prob:.1f}% Chance OVER")
                    elif o_prob < 40: st.error(f"📉 {100-o_prob:.1f}% Chance UNDER")
                    else: st.warning(f"⚖️ Neutral ({o_prob:.1f}% Over)")
                    
                    if o_ev > 2.0: st.success(f"🔥 +EV OVER: {o_ev:+.1f}% Edge")
                    elif u_ev > 2.0: st.success(f"🔥 +EV UNDER: {u_ev:+.1f}% Edge")
                    else: st.info(f"🛑 No Edge (EV: {max(o_ev, u_ev):+.1f}%)")
                    
                    st.bar_chart(pd.Series(res['simulations']).value_counts(normalize=True).sort_index())
                    for f in res['factors']: st.caption(f"- {f}")

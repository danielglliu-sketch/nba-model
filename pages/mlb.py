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
    "Pitcher Friendly (Wide Zone)": ["Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter", "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa", "Jeremie Rehak", "Vic Carapazza", "Lance Barksdale", "Doug Eddings", "Paul Emmel", "Cory Blaser", "Adrian Johnson", "John Tumpane", "Nic Lentz", "Ben May", "Ryan Blakney"],
    "Hitter Friendly (Tight Zone)": ["Pat Hoberg", "Quinn Wolcott", "Andy Fletcher", "Dan Bellino", "Lance Barrett", "CB Bucknor", "Ted Barrett", "Angel Hernandez", "Hunter Wendelstedt", "Mark Carlson", "Jeff Nelson", "Rob Drake", "Brian O'Nora", "Todd Tichenor", "Chad Fairchild", "Marvin Hudson", "Mike Muchlinski", "Adam Hamari", "Manny Gonzalez", "D.J. Reyburn"]
}

K_PARK_FACTORS = { 'SEA': 1.06, 'TB': 1.05, 'MIA': 1.04, 'SD': 1.04, 'MIL': 1.03, 'OAK': 1.03, 'SF': 1.02, 'LAD': 1.02, 'NYM': 1.01, 'MIN': 1.01, 'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 0.99, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98, 'CHC': 0.97, 'STL': 0.97, 'PIT': 0.97, 'LAA': 0.96, 'HOU': 0.96, 'WSH': 0.95, 'CIN': 0.94, 'ARI': 0.93, 'COL': 0.85 }

TEAM_MAP = { 'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC', 'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Sacramento Athletics': 'OAK', 'Athletics': 'OAK', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH' }

# --- DATA FETCHERS ---
@st.cache_data(ttl=86400)
def get_automated_team_splits():
    splits = {}
    for hand in ['vL', 'vR']:
        h_code = 'L' if hand == 'vL' else 'R'
        url = f"https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=statSplits&sitCode={hand}"
        try:
            data = requests.get(url, timeout=10).json()
            for record in data['stats'][0]['splits']:
                api_name = record['team']['name']
                abbr = TEAM_MAP.get(api_name, api_name)
                if abbr:
                    if abbr not in splits: splits[abbr] = {}
                    pa, so = record['stat'].get('plateAppearances', 1), record['stat'].get('strikeOuts', 0)
                    splits[abbr][h_code] = so / pa
        except: pass
    return splits

SPLITS_DB = get_automated_team_splits()

@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    url = "https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=1000"
    pitcher_db = {}
    try:
        people_data = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players?season=2026").json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people_data['people']}
        data = requests.get(url, timeout=15).json()
        for record in data['stats'][0]['splits']:
            name, pid = record['player']['fullName'], record['player']['id']
            stat = record['stat']
            tbf, so, bb, h, gs = stat.get('battersFaced', 0), stat.get('strikeOuts', 0), stat.get('baseOnBalls', 0), stat.get('hits', 0), stat.get('gamesStarted', 0)
            if tbf == 0: continue
            raw_k, raw_bb, raw_h = so/tbf, bb/tbf, h/tbf
            shrunk_k = (raw_k * tbf + 0.22 * 25) / (tbf + 25)
            pitcher_db[name] = {'K%': shrunk_k, 'Raw_K%': raw_k, 'BB%': raw_bb, 'H%': raw_h, 'Hand': hand_map.get(pid, 'R'), 'SwStr%': raw_k * 0.5, 'BF_per_Start': max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))}
        return pitcher_db
    except: return {}

STATS_DB = get_pitcher_stats_database()

# --- THE PITCHING OUTS & K ENGINE ---
def run_monte_carlo(sp_name, base_k_rate, raw_k_rate, bb_rate, h_rate, swstr_rate, opp_k_rate, park, batters_faced, temp, umpire, num_sims=10000):
    factors = []
    adj_k_rate = base_k_rate
    
    # K-Logic (Existing)
    if raw_k_rate < (base_k_rate - 0.02): factors.append("📉 Form Warning: Lagging K%")
    if raw_k_rate > (base_k_rate + 0.01): factors.append("⚠️ Regression Risk (K%)")
    if bb_rate > 0.09: factors.append("⛽ Efficiency Warning (Outs Risk)")
    if swstr_rate > 0.135: 
        adj_k_rate += 0.04
        factors.append("🎯 Elite Whiff Boost")
    
    opp_ratio = 1.0 + (((opp_k_rate / 0.225) - 1.0) * 0.5)
    adj_k_rate *= opp_ratio
    
    if temp < 60: adj_k_rate += 0.02
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_k_rate += 0.015
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]: adj_k_rate -= 0.015
    
    adj_k_rate = max(0.08, min(0.45, adj_k_rate * K_PARK_FACTORS.get(park, 1.0)))

    # --- SIMULATION ---
    variance_scale = 0.03
    game_k_rates = np.clip(np.random.normal(loc=adj_k_rate, scale=variance_scale, size=num_sims), 0.05, 0.65)
    z_scores = (game_k_rates - adj_k_rate) / variance_scale
    dynamic_bf = np.clip(np.round(batters_faced + (z_scores * 2.5)).astype(int), 12, 32)
    
    # Strikeouts
    k_sims = np.random.binomial(n=dynamic_bf, p=game_k_rates)
    
    # Outs Logic: Outs = BF - (Walks + Hits)
    # We simulate BB and H based on pitcher averages
    bb_sims = np.random.binomial(n=dynamic_bf, p=bb_rate)
    h_sims = np.random.binomial(n=dynamic_bf, p=h_rate)
    out_sims = dynamic_bf - (bb_sims + h_sims)
    
    return {'k_sims': k_sims, 'out_sims': out_sims, 'factors': factors}

# --- UI ---
st.title("🤖 MLB Quant AI - Autopilot Engine 3.0")
st.markdown("Strikeout & **Pitching Outs** Monte Carlo Simulation.")

schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire"
try:
    games = requests.get(schedule_url).json().get('dates', [{}])[0].get('games', [])
except: games = []

for game in games:
    h_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
    a_sp_name = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
    if h_sp_name == "TBD" or a_sp_name == "TBD": continue
    
    home_team = TEAM_MAP.get(game['teams']['home']['team']['name'], game['teams']['home']['team']['name'])
    away_team = TEAM_MAP.get(game['teams']['away']['team']['name'], game['teams']['away']['team']['name'])
    
    umpire = "Neutral"
    if 'officials' in game:
        for off in game['officials']:
            if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']

    with st.expander(f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | Ump: {umpire}"):
        col1, col2 = st.columns(2)
        for side, sp_name, team, opp_team in [(col1, a_sp_name, away_team, home_team), (col2, h_sp_name, home_team, away_team)]:
            with side:
                match = STATS_DB.get(sp_name, {'K%': 0.22, 'Raw_K%': 0.22, 'BB%': 0.08, 'H%': 0.25, 'Hand': 'R', 'SwStr%': 0.11, 'BF_per_Start': 23})
                opp_k = SPLITS_DB.get(opp_team, {}).get(match['Hand'], 0.225)
                res = run_monte_carlo(sp_name, match['K%'], match['Raw_K%'], match['BB%'], match['H%'], match['SwStr%'], opp_k, home_team, match['BF_per_Start'], 70, umpire)
                
                st.markdown(f"### {sp_name}")
                
                # Strikeout Tab
                t1, t2 = st.tabs(["🔥 Strikeouts", "📏 Pitching Outs"])
                with t1:
                    line_k = st.number_input("K Line:", 4.5, key=f"k_{sp_name}")
                    o_p = (np.sum(res['k_sims'] > line_k) / 10000) * 100
                    st.metric("Over Probability", f"{o_p:.1f}%")
                with t2:
                    line_o = st.number_input("Outs Line:", 17.5, key=f"o_{sp_name}")
                    o_p_out = (np.sum(res['out_sims'] > line_o) / 10000) * 100
                    st.metric("Over Probability", f"{o_p_out:.1f}%")
                    st.caption(f"Median Projected Outs: {np.median(res['out_sims']):.1f}")
                
                for f in res['factors']: st.caption(f"- {f}")

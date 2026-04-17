import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Outs Engine", page_icon="⚾", layout="wide")

st.sidebar.title("🤖 Outs Autopilot")
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

# Umpire Logic adjusted for EFFICIENCY (Outs)
UMPIRE_DATABASE = {
    "Pitcher Friendly (Wide Zone)": ["Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter", "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa", "Jeremie Rehak", "Vic Carapazza", "Lance Barksdale", "Doug Eddings", "Paul Emmel", "Cory Blaser", "Adrian Johnson", "John Tumpane", "Nic Lentz", "Ben May", "Ryan Blakney"],
    "Hitter Friendly (Tight Zone)": ["Pat Hoberg", "Quinn Wolcott", "Andy Fletcher", "Dan Bellino", "Lance Barrett", "CB Bucknor", "Ted Barrett", "Angel Hernandez", "Hunter Wendelstedt", "Mark Carlson", "Jeff Nelson", "Rob Drake", "Brian O'Nora", "Todd Tichenor", "Chad Fairchild", "Marvin Hudson", "Mike Muchlinski", "Adam Hamari", "Manny Gonzalez", "D.J. Reyburn"]
}

# Park Factors for OUTS (General Run/Hit Environment)
OUTS_PARK_FACTORS = { 'SEA': 1.03, 'TB': 1.02, 'MIA': 1.02, 'SD': 1.02, 'OAK': 1.01, 'SF': 1.01, 'LAD': 1.01, 'NYM': 1.00, 'MIN': 1.00, 'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 1.00, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98, 'CHC': 0.98, 'STL': 0.98, 'PIT': 0.98, 'LAA': 0.97, 'HOU': 0.97, 'WSH': 0.97, 'CIN': 0.95, 'ARI': 0.94, 'COL': 0.88 }

TEAM_MAP = { 'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC', 'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Sacramento Athletics': 'OAK', 'Athletics': 'OAK', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH' }

# --- DATA FETCHERS ---
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
                api_name = record['team']['name']
                abbr = TEAM_MAP.get(api_name, api_name)
                if abbr not in splits: splits[abbr] = {}
                pa, hits, bb = record['stat'].get('plateAppearances', 1), record['stat'].get('hits', 0), record['stat'].get('baseOnBalls', 0)
                # Outs Probability Split: 1 - (Hits + BB) / PA
                splits[abbr][h_code] = 1 - ((hits + bb) / pa)
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
            tbf, bb, h, gs = stat.get('battersFaced', 0), stat.get('baseOnBalls', 0), stat.get('hits', 0), stat.get('gamesStarted', 0)
            if tbf == 0: continue
            raw_bb, raw_h = bb/tbf, h/tbf
            shrunk_out_rate = ( (tbf - (bb + h)) + (0.68 * 50) ) / (tbf + 50) # Shrinkage toward league avg out rate
            pitcher_db[name] = {'Out%': shrunk_out_rate, 'BB%': raw_bb, 'H%': raw_h, 'Hand': hand_map.get(pid, 'R'), 'BF_per_Start': max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))}
        return pitcher_db
    except: return {}

STATS_DB = get_pitcher_stats_database()

# --- THE OUTS-ONLY ENGINE ---
def run_monte_carlo(sp_name, game_id, base_out_rate, bb_rate, h_rate, opp_out_rate, park, batters_faced, temp, umpire, num_sims=10000):
    np.random.seed(hash(sp_name + str(game_id)) % 2**32)
    factors = []
    adj_out_rate = base_out_rate
    
    # Efficiency Alerts
    if bb_rate > 0.09:
        factors.append("⛽ Efficiency Warning: High Walk Rate. Increased risk of early hook.")
    
    # Opponent Efficiency Split
    opp_ratio = 1.0 + (((opp_out_rate / 0.68) - 1.0) * 0.5)
    adj_out_rate *= opp_ratio
    factors.append(f"🏏 Opponent Split Efficiency ({opp_out_rate*100:.1f}%) applied")
    
    # Weather impact on Hits/Outs
    if temp > 80:
        adj_out_rate -= 0.015
        factors.append(f"🔥 Heat Warning ({temp:.0f}°F): More hits, fewer outs (-1.5%)")
    elif temp < 60:
        adj_out_rate += 0.01
        factors.append(f"🥶 Cold Weather: Ball carries less (+1.0%)")
        
    # Umpire impact on Pitch Counts/Outs
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]:
        adj_out_rate += 0.012
        factors.append(f"💎 Wide Zone Umpire ({umpire}): Shorter at-bats, more outs (+1.2%)")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]:
        adj_out_rate -= 0.015
        factors.append(f"🧱 Tight Zone Umpire ({umpire}): Higher pitch counts, fewer outs (-1.5%)")
    elif umpire != "Neutral":
        factors.append(f"⚖️ Umpire: Neutral Zone ({umpire})")

    # Park Reporting
    pk = OUTS_PARK_FACTORS.get(park, 1.0)
    adj_out_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ Park Factor for Outs ({((pk-1)*100):+.1f}%)")
    
    adj_out_rate = max(0.40, min(0.85, adj_out_rate))

    # Simulation Logic for OUTS
    variance_scale = 0.04
    game_out_rates = np.clip(np.random.normal(loc=adj_out_rate, scale=variance_scale, size=num_sims), 0.35, 0.90)
    z_scores = (game_out_rates - adj_out_rate) / variance_scale
    
    # Workload is dynamic based on performance
    dynamic_bf = np.clip(np.round(batters_faced + (z_scores * 3.0)).astype(int), 12, 32)
    
    # Primary Simulation
    out_sims = np.random.binomial(n=dynamic_bf, p=game_out_rates)
    
    return {'out_sims': out_sims, 'factors': factors}

def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob, payout = win_prob_pct / 100.0, (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout) - (1.0 - prob)) * 100.0

# --- UI RENDERER ---
st.title("🤖 MLB Quant AI - 100% Outs Engine")
st.markdown("Autopilot active. Strikeouts scrapped. Predictive logic focused on pitching efficiency.")

schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire"
try:
    games = requests.get(schedule_url).json().get('dates', [{}])[0].get('games', [])
except: games = []

if not games:
    st.info("No games found. Please refresh or check date.")
else:
    for game in games:
        home_name_api, away_name_api = game['teams']['home']['team']['name'], game['teams']['away']['team']['name']
        home_team, away_team = TEAM_MAP.get(home_name_api, home_name_api), TEAM_MAP.get(away_name_api, away_name_api)
        h_sp_name, a_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD'), game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        if h_sp_name == "TBD" or a_sp_name == "TBD": continue
        
        umpire = "Neutral"
        if 'officials' in game:
            for off in game['officials']:
                if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
        if umpire == "Neutral":
            try:
                bx_data = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/boxscore").json()
                for off in bx_data.get('officials', []):
                    if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
            except: pass

        with st.expander(f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | Ump: {umpire}"):
            temp = get_live_temp(home_team)
            col1, col2 = st.columns(2)
            for side, sp_name, team_abbr, opp_team_abbr in [(col1, a_sp_name, away_team, home_team), (col2, h_sp_name, home_team, away_team)]:
                with side:
                    match = STATS_DB.get(sp_name, {'Out%': 0.68, 'BB%': 0.08, 'H%': 0.24, 'Hand': 'R', 'BF_per_Start': 23})
                    opp_out_rate = SPLITS_DB.get(opp_team_abbr, {}).get(match['Hand'], 0.68)
                    res = run_monte_carlo(sp_name, game['gamePk'], match['Out%'], match['BB%'], match['H%'], opp_out_rate, home_team, match['BF_per_Start'], temp, umpire)
                    
                    st.markdown(f"### {sp_name} ({match['Hand']}HP)")
                    
                    line_o = st.number_input("Outs Line:", value=17.5, step=0.5, key=f"o_{team_abbr}_{sp_name}_{game['gamePk']}")
                    o_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"oo_{team_abbr}_{sp_name}_{game['gamePk']}")
                    u_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"uo_{team_abbr}_{sp_name}_{game['gamePk']}")
                    
                    o_prob = (np.sum(res['out_sims'] > line_o) / 10000) * 100
                    o_ev, u_ev = calculate_ev_percent(o_prob, o_odds), calculate_ev_percent(100 - o_prob, u_odds)
                    
                    if o_prob > 60: st.success(f"📈 {o_prob:.1f}% Chance OVER Outs")
                    elif o_prob < 40: st.error(f"📉 {100-o_prob:.1f}% Chance UNDER Outs")
                    else: st.warning(f"⚖️ Neutral Outs Matchup ({o_prob:.1f}% Over)")
                    
                    if o_ev > 2.0: st.success(f"🔥 +EV OVER: {o_ev:+.1f}% Edge")
                    elif u_ev > 2.0: st.success(f"🔥 +EV UNDER: {u_ev:+.1f}% Edge")
                    
                    st.caption(f"Median Projected Outs: {np.median(res['out_sims']):.1f}")
                    
                    st.bar_chart(pd.Series(res['out_sims']).value_counts(normalize=True).sort_index())
                    for f in res['factors']: st.caption(f"- {f}")

import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Hybrid Engine (Aggressive)", page_icon="🤖", layout="wide")

st.sidebar.title("🤖 Hybrid Autopilot")
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
OUTS_PARK_FACTORS = { 'SEA': 1.03, 'TB': 1.02, 'MIA': 1.02, 'SD': 1.02, 'OAK': 1.01, 'SF': 1.01, 'LAD': 1.01, 'NYM': 1.00, 'MIN': 1.00, 'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 1.00, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98, 'CHC': 0.98, 'STL': 0.98, 'PIT': 0.98, 'LAA': 0.97, 'HOU': 0.97, 'WSH': 0.97, 'CIN': 0.95, 'ARI': 0.94, 'COL': 0.88 }

TEAM_MAP = { 'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC', 'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Sacramento Athletics': 'OAK', 'Athletics': 'OAK', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH' }

# --- DATA FETCHERS ---
@st.cache_data(ttl=3600)
def get_weather_for_date(team_abbr, date_str):
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords: return 70
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&start_date={date_str}&end_date={date_str}&daily=temperature_2m_max&timezone=auto"
        data = requests.get(url, timeout=5).json()
        return (data['daily']['temperature_2m_max'][0] * 9/5) + 32
    except: return 70

@st.cache_data(ttl=86400)
def get_automated_team_splits():
    splits = {}
    for hand in ['vL', 'vR']:
        h_code = 'L' if hand == 'vL' else 'R'
        try:
            data = requests.get(f"https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=statSplits&sitCode={hand}", timeout=10).json()
            for record in data['stats'][0]['splits']:
                abbr = TEAM_MAP.get(record['team']['name'], record['team']['name'])
                if abbr not in splits: splits[abbr] = {}
                pa = record['stat'].get('plateAppearances', 1)
                so = record['stat'].get('strikeOuts', 0)
                hits, bb = record['stat'].get('hits', 0), record['stat'].get('baseOnBalls', 0)
                splits[abbr][h_code] = { 'K%': so / pa, 'Out%': 1 - ((hits + bb) / pa) }
        except: pass
    return splits

SPLITS_DB = get_automated_team_splits()

@st.cache_data(ttl=86400)
def get_pitcher_and_manager_stats():
    pitcher_db, team_sp_agg = {}, {}
    try:
        people_data = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players?season=2026").json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people_data['people']}
        data = requests.get("https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=1000", timeout=15).json()
        
        league_tbf, league_gs = 0, 0
        for record in data['stats'][0]['splits']:
            name, pid = record['player']['fullName'], record['player']['id']
            abbr = TEAM_MAP.get(record.get('team', {}).get('name', 'Unknown'), 'Unknown')
            stat = record['stat']
            tbf, so, bb, h = stat.get('battersFaced', 0), stat.get('strikeOuts', 0), stat.get('baseOnBalls', 0), stat.get('hits', 0)
            gs, gp = stat.get('gamesStarted', 0), stat.get('gamesPlayed', 0)
            
            if tbf == 0: continue
            raw_k = so/tbf
            shrunk_k = (raw_k * tbf + 0.22 * 25) / (tbf + 25)
            swstr_proxy = raw_k * 0.5
            shrunk_out_rate = ( (tbf - (bb + h)) + (0.68 * 50) ) / (tbf + 50)
            
            pitcher_db[pid] = {
                'Name': name, 'K%': shrunk_k, 'Raw_K%': raw_k, 'BB%': bb/tbf, 'H%': h/tbf, 'SwStr%': swstr_proxy, 
                'Out%': shrunk_out_rate, 'Hand': hand_map.get(pid, 'R'), 'GS': gs,
                'BF_per_Start': max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))
            }
            
            if gs > 0 and gp > 0 and (gs / gp) > 0.8 and abbr != 'Unknown':
                if abbr not in team_sp_agg: team_sp_agg[abbr] = {'tbf': 0, 'gs': 0}
                team_sp_agg[abbr]['tbf'] += tbf; team_sp_agg[abbr]['gs'] += gs
                league_tbf += tbf; league_gs += gs
                
        manager_db, league_avg_bf = {}, league_tbf / league_gs if league_gs > 0 else 22.5
        for team, stats in team_sp_agg.items():
            manager_db[team] = max(-3.0, min(3.0, (stats['tbf'] / stats['gs'] if stats['gs'] > 0 else league_avg_bf) - league_avg_bf))
        return pitcher_db, manager_db
    except: return {}, {}

STATS_DB, MANAGER_DB = get_pitcher_and_manager_stats()

@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback_db_match):
    profile = {
        'recent_tbf_cap': 30, 'recent_pitch_avg': 85, 'gs_count': fallback_db_match.get('GS', 0),
        'actual_k_rate': fallback_db_match['K%'], 'actual_bb_rate': fallback_db_match['BB%'], 
        'actual_out_rate': fallback_db_match['Out%'], 'swstr': fallback_db_match['SwStr%']
    }
    if not player_id: return profile
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season=2026"
        log_data = requests.get(url, timeout=5).json()
        splits = log_data.get('stats', [{}])[0].get('splits', [])
        if not splits: return profile
        
        recent_tbfs = [s['stat'].get('battersFaced', 0) for s in splits[:3]]
        recent_pitches = [s['stat'].get('numberOfPitches', 0) for s in splits[:3]]
        
        profile['recent_tbf_cap'] = max(recent_tbfs) if recent_tbfs else 30
        profile['recent_pitch_avg'] = sum(recent_pitches) / len(recent_pitches) if recent_pitches else 85
        profile['gs_count'] = len(splits)
        
        if fallback_db_match['BF_per_Start'] == 23:
            tbf = sum(s['stat'].get('battersFaced', 0) for s in splits)
            so = sum(s['stat'].get('strikeOuts', 0) for s in splits)
            bb = sum(s['stat'].get('baseOnBalls', 0) for s in splits)
            h = sum(s['stat'].get('hits', 0) for s in splits)
            if tbf > 0:
                profile['actual_k_rate'] = so / tbf; profile['swstr'] = (so / tbf) * 0.5
                profile['actual_bb_rate'] = bb / tbf; profile['actual_out_rate'] = (tbf - (bb + h)) / tbf
    except: pass
    return profile

# --- THE AGGRESSIVE ENGINES ---
def run_monte_carlo_k(sp_name, game_id, base_k_rate, swstr_rate, bb_rate, opp_k_rate, park, batters_faced, temp, umpire, manager_shift, recent_tbf_cap, recent_pitch_avg, gs_count, num_sims=10000):
    np.random.seed(hash(sp_name + str(game_id) + "k") % 2**32)
    factors, adj_k_rate = [], base_k_rate
    adj_bf = batters_faced + manager_shift
    
    # +++ LEAGUE SURGE BONUS +++
    if gs_count >= 3:
        adj_bf += 1.0; factors.append("📈 League-Wide Volume Surge (+1.0 batter)")

    if recent_pitch_avg >= 94: adj_bf += 1.5; factors.append("🐴 Workhorse Override (+1.5 BF)")
    
    # +++ WIDENED HARD CAP +++
    hard_cap = recent_tbf_cap + 3 
    if adj_bf > hard_cap:
        factors.append(f"🚨 Medical/Workload Cap: Limited to {hard_cap} batters.")
        adj_bf = hard_cap
        
    if swstr_rate > 0.135: adj_k_rate += 0.04; factors.append("🎯 Elite Whiff Boost (+4.0%)")
    opp_ratio = 1.0 + (((opp_k_rate / 0.225) - 1.0) * 0.5)
    adj_k_rate *= opp_ratio
    
    if temp < 60: adj_k_rate += 0.02
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_k_rate += 0.015
    pk = K_PARK_FACTORS.get(park, 1.0)
    adj_k_rate *= pk
    
    adj_k_rate = max(0.08, min(0.45, adj_k_rate))
    game_k_rates = np.clip(np.random.normal(loc=adj_k_rate, scale=0.03, size=num_sims), 0.05, 0.65)
    z_scores = (game_k_rates - adj_k_rate) / 0.03
    dynamic_bf = np.clip(np.round(adj_bf + (z_scores * 2.5)).astype(int), 9, hard_cap + 2)
    k_sims = np.random.binomial(n=dynamic_bf, p=game_k_rates)
    return {'sims': k_sims, 'factors': factors}

def run_monte_carlo_outs(sp_name, game_id, base_out_rate, bb_rate, opp_out_rate, park, batters_faced, temp, umpire, manager_shift, recent_tbf_cap, recent_pitch_avg, gs_count, num_sims=10000):
    np.random.seed(hash(sp_name + str(game_id) + "o") % 2**32)
    factors, adj_out_rate = [], base_out_rate
    adj_bf = batters_faced + manager_shift
    
    # +++ LEAGUE SURGE BONUS +++
    if gs_count >= 3:
        adj_bf += 1.0; factors.append("📈 League-Wide Volume Surge (+1.0 batter)")

    if recent_pitch_avg >= 94: adj_bf += 1.5; factors.append("🐴 Workhorse Override (+1.5 BF)")
    
    # +++ WIDENED HARD CAP +++
    hard_cap = recent_tbf_cap + 3 
    if adj_bf > hard_cap:
        factors.append(f"🚨 Medical/Workload Cap: Limited to {hard_cap} batters.")
        adj_bf = hard_cap
    
    opp_ratio = 1.0 + (((opp_out_rate / 0.68) - 1.0) * 0.5)
    adj_out_rate *= opp_ratio
    if temp > 80: adj_out_rate -= 0.015
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_out_rate += 0.012
    pk = OUTS_PARK_FACTORS.get(park, 1.0)
    adj_out_rate *= pk
    
    adj_out_rate = max(0.40, min(0.85, adj_out_rate))
    game_out_rates = np.clip(np.random.normal(loc=adj_out_rate, scale=0.04, size=num_sims), 0.35, 0.90)
    z_scores = (game_out_rates - adj_out_rate) / 0.04
    dynamic_bf = np.clip(np.round(adj_bf + (z_scores * 3.0)).astype(int), 9, hard_cap + 2)
    out_sims = np.random.binomial(n=dynamic_bf, p=game_out_rates)
    return {'sims': out_sims, 'factors': factors}

def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob, payout = win_prob_pct / 100.0, (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout) - (1.0 - prob)) * 100.0

# --- UI RENDERER (UNCHANGED) ---
st.title("🤖 MLB Quant AI - Hybrid Engine (Aggressive)")
schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire"
try: games = requests.get(schedule_url).json().get('dates', [{}])[0].get('games', [])
except: games = []

for game in games:
    home_name, away_name = game['teams']['home']['team']['name'], game['teams']['away']['team']['name']
    h_team, a_team = TEAM_MAP.get(home_name, home_name), TEAM_MAP.get(away_name, away_name)
    h_sp_dict, a_sp_dict = game['teams']['home'].get('probablePitcher', {}), game['teams']['away'].get('probablePitcher', {})
    h_sp_name, h_sp_id, a_sp_name, a_sp_id = h_sp_dict.get('fullName', 'TBD'), h_sp_dict.get('id'), a_sp_dict.get('fullName', 'TBD'), a_sp_dict.get('id')
    if h_sp_name == "TBD" or a_sp_name == "TBD": continue
    
    umpire = "Neutral"
    if 'officials' in game:
        for off in game['officials']:
            if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']

    with st.expander(f"⚾ {a_team} ({a_sp_name}) @ {h_team} ({h_sp_name}) | Ump: {umpire}"):
        temp, tabs = get_weather_for_date(h_team, target_date_str), st.tabs(["🔥 Strikeouts", "⚾ Pitching Outs"])
        for tab, run_mc in zip(tabs, [run_monte_carlo_k, run_monte_carlo_outs]):
            with tab:
                col1, col2 = st.columns(2)
                for side, sp_n, sp_i, t_a, o_a in [(col1, a_sp_name, a_sp_id, a_team, h_team), (col2, h_sp_name, h_sp_id, h_team, a_team)]:
                    with side:
                        match = STATS_DB.get(sp_i, {'K%': 0.22, 'BB%': 0.08, 'SwStr%': 0.11, 'Out%': 0.68, 'Hand': 'R', 'BF_per_Start': 23, 'GS': 0})
                        opp_splits = SPLITS_DB.get(o_a, {}).get(match['Hand'], {'K%': 0.225, 'Out%': 0.68})
                        prof = get_live_pitcher_profile(sp_i, match)
                        
                        # Pass all stats to the aggressive MC engine
                        r = run_mc(sp_n, game['gamePk'], prof['actual_k_rate'] if tab.title == "Strikeouts" else prof['actual_out_rate'], 
                                   prof['swstr'], prof['actual_bb_rate'], opp_splits['K%'] if tab.title == "Strikeouts" else opp_splits['Out%'], 
                                   h_team, match['BF_per_Start'], temp, umpire, MANAGER_DB.get(t_a, 0.0), 
                                   prof['recent_tbf_cap'], prof['recent_pitch_avg'], prof['gs_count'])
                        
                        st.markdown(f"### {sp_n}")
                        line = st.number_input(f"Line:", value=5.5 if "Strikeouts" in tab.label else 17.5, step=0.5, key=f"{tab.label}_{sp_n}_{game['gamePk']}")
                        o_o, u_o = st.number_input("Over Odds:", -110, step=5, key=f"oo_{tab.label}_{sp_n}"), st.number_input("Under Odds:", -110, step=5, key=f"uo_{tab.label}_{sp_n}")
                        o_p = (np.sum(r['sims'] > line) / 10000) * 100
                        
                        if o_p > 60: st.success(f"📈 {o_p:.1f}% OVER")
                        elif o_p < 40: st.error(f"📉 {100-o_p:.1f}% UNDER")
                        else: st.warning(f"⚖️ Neutral ({o_p:.1f}%)")
                        
                        for f in r['factors']: st.caption(f"- {f}")
                        st.bar_chart(pd.Series(r['sims']).value_counts(normalize=True).sort_index())

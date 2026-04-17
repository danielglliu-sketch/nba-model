import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Hybrid Engine", page_icon="🤖", layout="wide")

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
                # Store BOTH K% and Out% in the splits dictionary
                splits[abbr][h_code] = {
                    'K%': so / pa,
                    'Out%': 1 - ((hits + bb) / pa)
                }
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
                'Out%': shrunk_out_rate, 'Hand': hand_map.get(pid, 'R'), 
                'BF_per_Start': max(16, min(28, (tbf + (22.5 * 3)) / (gs + 3)))
            }
            
            if gs > 0 and gp > 0 and (gs / gp) > 0.8 and abbr != 'Unknown':
                if abbr not in team_sp_agg: team_sp_agg[abbr] = {'tbf': 0, 'gs': 0}
                team_sp_agg[abbr]['tbf'] += tbf
                team_sp_agg[abbr]['gs'] += gs
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
        'recent_tbf_cap': 30, 'recent_pitch_avg': 85, 
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
        
        if fallback_db_match['BF_per_Start'] == 23:
            tbf = sum(s['stat'].get('battersFaced', 0) for s in splits)
            so = sum(s['stat'].get('strikeOuts', 0) for s in splits)
            bb = sum(s['stat'].get('baseOnBalls', 0) for s in splits)
            h = sum(s['stat'].get('hits', 0) for s in splits)
            if tbf > 0:
                profile['actual_k_rate'] = so / tbf
                profile['swstr'] = (so / tbf) * 0.5
                profile['actual_bb_rate'] = bb / tbf
                profile['actual_out_rate'] = (tbf - (bb + h)) / tbf
    except: pass
    return profile

# --- THE MONTE CARLO ENGINES ---
def run_monte_carlo_k(sp_name, game_id, base_k_rate, swstr_rate, bb_rate, opp_k_rate, park, batters_faced, temp, umpire, manager_shift, recent_tbf_cap, recent_pitch_avg, num_sims=10000):
    np.random.seed(hash(sp_name + str(game_id) + "k") % 2**32)
    factors = []
    adj_k_rate = base_k_rate
    adj_bf = batters_faced + manager_shift
    
    factors.append(f"📊 Baseline: {recent_pitch_avg:.0f} Recent Pitches | {adj_k_rate*100:.1f}% Est. K Rate")
    
    if manager_shift > 0.75: factors.append(f"👔 Manager Tendency: Long Leash (+{manager_shift:.1f} batters)")
    elif manager_shift < -0.75: factors.append(f"👔 Manager Tendency: Quick Hook ({manager_shift:.1f} batters)")
    
    if recent_pitch_avg >= 94:
        factors.append(f"🐴 Workhorse Override: High traffic tolerated (+1.5 BF).")
        adj_bf += 1.5
    elif bb_rate > 0.09: 
        factors.append("⛽ Efficiency Warning: High Walk Rate.")
    
    hard_cap = recent_tbf_cap + 1 
    if adj_bf > hard_cap:
        factors.append(f"🚨 Medical/Workload Cap: Limited to {hard_cap} batters.")
        adj_bf = hard_cap
        
    if swstr_rate > 0.135: 
        adj_k_rate += 0.04; factors.append("🎯 Elite Whiff Boost (+4.0%)")
        
    opp_ratio = 1.0 + (((opp_k_rate / 0.225) - 1.0) * 0.5)
    adj_k_rate *= opp_ratio
    factors.append(f"🏏 Opponent Split K% ({opp_k_rate*100:.1f}%) applied")
    
    if temp < 60: adj_k_rate += 0.02; factors.append(f"🥶 Cold Weather (+2.0%)")
        
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_k_rate += 0.015; factors.append(f"💎 Wide Zone Umpire ({umpire}) (+1.5%)")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]: adj_k_rate -= 0.015; factors.append(f"🧱 Tight Zone Umpire ({umpire}) (-1.5%)")

    pk = K_PARK_FACTORS.get(park, 1.0)
    adj_k_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ K-Park Factor ({((pk-1)*100):+.1f}%)")
    
    adj_k_rate = max(0.08, min(0.45, adj_k_rate))
    variance_scale = 0.03
    game_k_rates = np.clip(np.random.normal(loc=adj_k_rate, scale=variance_scale, size=num_sims), 0.05, 0.65)
    z_scores = (game_k_rates - adj_k_rate) / variance_scale
    
    dynamic_bf = np.clip(np.round(adj_bf + (z_scores * 2.5)).astype(int), 9, hard_cap + 2)
    k_sims = np.random.binomial(n=dynamic_bf, p=game_k_rates)
    
    return {'sims': k_sims, 'factors': factors}

def run_monte_carlo_outs(sp_name, game_id, base_out_rate, bb_rate, opp_out_rate, park, batters_faced, temp, umpire, manager_shift, recent_tbf_cap, recent_pitch_avg, num_sims=10000):
    np.random.seed(hash(sp_name + str(game_id) + "o") % 2**32)
    factors = []
    adj_out_rate = base_out_rate
    adj_bf = batters_faced + manager_shift
    
    factors.append(f"📊 Baseline: {recent_pitch_avg:.0f} Recent Pitches | {adj_out_rate*100:.1f}% Est. Out Rate")
    
    if manager_shift > 0.75: factors.append(f"👔 Manager Tendency: Long Leash (+{manager_shift:.1f} batters)")
    elif manager_shift < -0.75: factors.append(f"👔 Manager Tendency: Quick Hook ({manager_shift:.1f} batters)")
    
    if recent_pitch_avg >= 94:
        factors.append(f"🐴 Workhorse Override: High traffic tolerated (+1.5 BF).")
        adj_bf += 1.5
    elif bb_rate > 0.09: 
        factors.append("⛽ Efficiency Warning: High Walk Rate.")
    
    hard_cap = recent_tbf_cap + 1 
    if adj_bf > hard_cap:
        factors.append(f"🚨 Medical/Workload Cap: Limited to {hard_cap} batters.")
        adj_bf = hard_cap
    
    opp_ratio = 1.0 + (((opp_out_rate / 0.68) - 1.0) * 0.5)
    adj_out_rate *= opp_ratio
    factors.append(f"🏏 Opponent Split Efficiency ({opp_out_rate*100:.1f}%) applied")
    
    if temp > 80: adj_out_rate -= 0.015; factors.append(f"🔥 Heat Warning ({temp:.0f}°F) (-1.5%)")
    elif temp < 60: adj_out_rate += 0.01; factors.append(f"🥶 Cold Weather (+1.0%)")
        
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_out_rate += 0.012; factors.append(f"💎 Wide Zone Umpire ({umpire}) (+1.2%)")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]: adj_out_rate -= 0.015; factors.append(f"🧱 Tight Zone Umpire ({umpire}) (-1.5%)")

    pk = OUTS_PARK_FACTORS.get(park, 1.0)
    adj_out_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ Park Factor for Outs ({((pk-1)*100):+.1f}%)")
    
    adj_out_rate = max(0.40, min(0.85, adj_out_rate))
    variance_scale = 0.04
    game_out_rates = np.clip(np.random.normal(loc=adj_out_rate, scale=variance_scale, size=num_sims), 0.35, 0.90)
    z_scores = (game_out_rates - adj_out_rate) / variance_scale
    
    dynamic_bf = np.clip(np.round(adj_bf + (z_scores * 3.0)).astype(int), 9, hard_cap + 2)
    out_sims = np.random.binomial(n=dynamic_bf, p=game_out_rates)
    
    return {'sims': out_sims, 'factors': factors}

def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob, payout = win_prob_pct / 100.0, (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout) - (1.0 - prob)) * 100.0

# --- UI RENDERER ---
st.title("🤖 MLB Quant AI - Hybrid Engine")
st.markdown("Autopilot active. Select a game below to view segregated tabs for **Strikeouts** and **Pitching Outs**.")

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
        
        h_sp_dict = game['teams']['home'].get('probablePitcher', {})
        a_sp_dict = game['teams']['away'].get('probablePitcher', {})
        h_sp_name, h_sp_id = h_sp_dict.get('fullName', 'TBD'), h_sp_dict.get('id')
        a_sp_name, a_sp_id = a_sp_dict.get('fullName', 'TBD'), a_sp_dict.get('id')
        
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
            temp = get_weather_for_date(home_team, target_date_str)
            
            # --- TABS FOR CLEAN SEPARATION ---
            tab_k, tab_outs = st.tabs(["🔥 Strikeouts", "⚾ Pitching Outs"])
            
            with tab_k:
                col1_k, col2_k = st.columns(2)
                for side, sp_name, sp_id, team_abbr, opp_team_abbr in [(col1_k, a_sp_name, a_sp_id, away_team, home_team), (col2_k, h_sp_name, h_sp_id, home_team, away_team)]:
                    with side:
                        match = STATS_DB.get(sp_id, {'K%': 0.22, 'BB%': 0.08, 'SwStr%': 0.11, 'Out%': 0.68, 'Hand': 'R', 'BF_per_Start': 23})
                        opp_splits = SPLITS_DB.get(opp_team_abbr, {}).get(match['Hand'], {'K%': 0.225, 'Out%': 0.68})
                        manager_shift = MANAGER_DB.get(team_abbr, 0.0)
                        
                        live_profile = get_live_pitcher_profile(sp_id, match)
                        
                        res = run_monte_carlo_k(
                            sp_name, game['gamePk'], live_profile['actual_k_rate'], live_profile['swstr'], 
                            live_profile['actual_bb_rate'], opp_splits['K%'], home_team, match['BF_per_Start'], 
                            temp, umpire, manager_shift, live_profile['recent_tbf_cap'], live_profile['recent_pitch_avg']
                        )
                        
                        st.markdown(f"### {sp_name} ({match['Hand']}HP)")
                        line_k = st.number_input("K Line:", value=5.5, step=0.5, key=f"k_{team_abbr}_{sp_name}_{game['gamePk']}")
                        o_odds_k = st.number_input("Over Odds:", value=-110, step=5, key=f"ook_{team_abbr}_{sp_name}_{game['gamePk']}")
                        u_odds_k = st.number_input("Under Odds:", value=-110, step=5, key=f"uok_{team_abbr}_{sp_name}_{game['gamePk']}")
                        
                        o_prob_k = (np.sum(res['sims'] > line_k) / 10000) * 100
                        o_ev_k, u_ev_k = calculate_ev_percent(o_prob_k, o_odds_k), calculate_ev_percent(100 - o_prob_k, u_odds_k)
                        
                        if o_prob_k > 60: st.success(f"📈 {o_prob_k:.1f}% Chance OVER Ks")
                        elif o_prob_k < 40: st.error(f"📉 {100-o_prob_k:.1f}% Chance UNDER Ks")
                        else: st.warning(f"⚖️ Neutral Matchup ({o_prob_k:.1f}% Over)")
                        
                        if o_ev_k > 2.0: st.success(f"🔥 +EV OVER: {o_ev_k:+.1f}% Edge")
                        elif u_ev_k > 2.0: st.success(f"🔥 +EV UNDER: {u_ev_k:+.1f}% Edge")
                        
                        st.caption(f"Median Projected Ks: {np.median(res['sims']):.1f}")
                        st.bar_chart(pd.Series(res['sims']).value_counts(normalize=True).sort_index())
                        for f in res['factors']: st.caption(f"- {f}")

            with tab_outs:
                col1_o, col2_o = st.columns(2)
                for side, sp_name, sp_id, team_abbr, opp_team_abbr in [(col1_o, a_sp_name, a_sp_id, away_team, home_team), (col2_o, h_sp_name, h_sp_id, home_team, away_team)]:
                    with side:
                        match = STATS_DB.get(sp_id, {'K%': 0.22, 'BB%': 0.08, 'SwStr%': 0.11, 'Out%': 0.68, 'Hand': 'R', 'BF_per_Start': 23})
                        opp_splits = SPLITS_DB.get(opp_team_abbr, {}).get(match['Hand'], {'K%': 0.225, 'Out%': 0.68})
                        manager_shift = MANAGER_DB.get(team_abbr, 0.0)
                        
                        live_profile = get_live_pitcher_profile(sp_id, match)
                        
                        res_outs = run_monte_carlo_outs(
                            sp_name, game['gamePk'], live_profile['actual_out_rate'], live_profile['actual_bb_rate'], 
                            opp_splits['Out%'], home_team, match['BF_per_Start'], temp, umpire, manager_shift, 
                            live_profile['recent_tbf_cap'], live_profile['recent_pitch_avg']
                        )
                        
                        st.markdown(f"### {sp_name} ({match['Hand']}HP)")
                        line_o = st.number_input("Outs Line:", value=17.5, step=0.5, key=f"o_{team_abbr}_{sp_name}_{game['gamePk']}")
                        o_odds_o = st.number_input("Over Odds:", value=-110, step=5, key=f"ooo_{team_abbr}_{sp_name}_{game['gamePk']}")
                        u_odds_o = st.number_input("Under Odds:", value=-110, step=5, key=f"uoo_{team_abbr}_{sp_name}_{game['gamePk']}")
                        
                        o_prob_o = (np.sum(res_outs['sims'] > line_o) / 10000) * 100
                        o_ev_o, u_ev_o = calculate_ev_percent(o_prob_o, o_odds_o), calculate_ev_percent(100 - o_prob_o, u_odds_o)
                        
                        if o_prob_o > 60: st.success(f"📈 {o_prob_o:.1f}% Chance OVER Outs")
                        elif o_prob_o < 40: st.error(f"📉 {100-o_prob_o:.1f}% Chance UNDER Outs")
                        else: st.warning(f"⚖️ Neutral Matchup ({o_prob_o:.1f}% Over)")
                        
                        if o_ev_o > 2.0: st.success(f"🔥 +EV OVER: {o_ev_o:+.1f}% Edge")
                        elif u_ev_o > 2.0: st.success(f"🔥 +EV UNDER: {u_ev_o:+.1f}% Edge")
                        
                        st.caption(f"Median Projected Outs: {np.median(res_outs['sims']):.1f}")
                        st.bar_chart(pd.Series(res_outs['sims']).value_counts(normalize=True).sort_index())
                        for f in res_outs['factors']: st.caption(f"- {f}")

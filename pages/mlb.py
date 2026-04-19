import os
import math
import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# ==============================================================================
# VEGAS ODDS AUTOMATION
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_automated_vegas_odds(api_key):
    if not api_key or api_key == "YOUR_API_KEY": return {}
    try:
        url = f"https://api.the-odds-api.com/v1/sports/baseball_mlb/events"
        params = {'apiKey': api_key, 'regions': 'us', 'markets': 'pitcher_outs', 'oddsFormat': 'american'}
        response = requests.get(url, params=params).json()
        odds_db = {}
        for event in response:
            for market in event.get('bookmakers', []):
                if market['key'] == 'draftkings': 
                    for outcome in market['markets'][0]['outcomes']:
                        name = outcome['description']
                        if name not in odds_db:
                            odds_db[name] = {'Over': {'line': 17.5, 'price': -110}, 'Under': {'line': 17.5, 'price': -110}}
                        if outcome['name'] == 'Over':
                            odds_db[name]['Over'] = {'line': outcome['point'], 'price': outcome['price']}
                        elif outcome['name'] == 'Under':
                            odds_db[name]['Under'] = {'line': outcome['point'], 'price': outcome['price']}
        return odds_db
    except: return {}

# ==============================================================================
# CSV TRACKING LEDGER (Cloud-Friendly)
# ==============================================================================
def log_play_to_csv(date, pitcher, team, opponent, line, pick, odds, prob, ev, median_outs, bf_proj, umpire_name):
    file_name = "quant_tracking_ledger.csv"
    file_exists = os.path.isfile(file_name)
    data = {
        "Game_Date": date,
        "Timestamp_Logged": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Pitcher": pitcher,
        "Team": team,
        "Opponent": opponent,
        "Line": line,
        "Pick": pick, 
        "Implied_Odds": odds,
        "Probability_Pct": round(prob, 2),
        "EV_Pct": round(ev, 2),
        "Median_Outs": round(median_outs, 2),
        "Projected_BF": round(bf_proj, 2),
        "Umpire": umpire_name,
        "Platform": "Underdog"
    }
    df = pd.DataFrame([data])
    df.to_csv(file_name, mode='a', header=not file_exists, index=False)

# ==============================================================================
# PAGE SETUP
# ==============================================================================
st.set_page_config(page_title="MLB Quant AI - Underdog Master", page_icon="⚾", layout="wide")

st.sidebar.title("🤖 Outs Autopilot v2")
api_key = st.sidebar.text_input("🔑 The Odds API Key (Optional)", type="password")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All caches cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("v2 Master: UD Optimized | Umpire Visibility | Volume Sanity Filter")

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

WIDE_ZONE = ["Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter", "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa", "Jeremie Rehak", "Vic Carapazza", "Lance Barksdale", "Doug Eddings", "Paul Emmel", "Cory Blaser", "Adrian Johnson", "John Tumpane", "Nic Lentz", "Ben May", "Ryan Blakney"]
TIGHT_ZONE = ["Pat Hoberg", "Quinn Wolcott", "Andy Fletcher", "Dan Bellino", "Lance Barrett", "CB Bucknor", "Ted Barrett", "Hunter Wendelstedt", "Mark Carlson", "Jeff Nelson", "Rob Drake", "Brian O'Nora", "Todd Tichenor", "Chad Fairchild", "Marvin Hudson", "Mike Muchlinski", "Adam Hamari", "Manny Gonzalez", "D.J. Reyburn"]

OUTS_PARK_FACTORS = {
    'SEA': 1.03, 'TB':  1.02, 'MIA': 1.02, 'SD':  1.02, 'OAK': 1.01, 'SF':  1.01, 'LAD': 1.01, 'NYM': 1.00, 'MIN': 1.00, 'BAL': 1.00,
    'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 1.00, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98, 'CHC': 0.98,
    'STL': 0.98, 'PIT': 0.98, 'LAA': 0.97, 'HOU': 0.97, 'WSH': 0.97, 'MIL': 1.00, 'KC':  0.99, 'CIN': 0.95, 'ARI': 0.94, 'COL': 0.88,
}

TEAM_MAP = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
    'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Sacramento Athletics': 'OAK', 'Athletics': 'OAK', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}

LEAGUE_OUT_RATE = 0.695; TRUE_API_AVERAGE = 0.680; LEAGUE_K_RATE = 0.225; LEAGUE_BB_RATE = 0.080; LEAGUE_AVG_BF = 22.5; UD_IMPLIED_ODDS = -122

# ==============================================================================
# HELPER & DATA FETCHERS
# ==============================================================================
def get_shrinkage_prior(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        days_in = (d - datetime(d.year, 3, 28)).days
        return 20 if days_in < 30 else (10 if days_in < 60 else 5)
    except: return 15

@st.cache_data(ttl=86400)
def get_pitcher_and_manager_stats():
    pitcher_db, team_sp_agg = {}, {}
    prior = get_shrinkage_prior(datetime.now().strftime('%Y-%m-%d'))
    try:
        people_resp = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10).json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people_resp.get('people', [])}
        
        # Bayesian Career Integration
        career_lookup = {}
        try:
            career_resp = requests.get("https://statsapi.mlb.com/api/v1/stats?stats=career&group=pitching&playerPool=ALL&season=2026&limit=2000", timeout=15).json()
            for rec in career_resp['stats'][0]['splits']:
                pid, s, ctbf = rec['player']['id'], rec['stat'], rec['stat'].get('battersFaced', 0)
                if ctbf > 0: career_lookup[pid] = {'out_rate': (ctbf - s.get('baseOnBalls', 0) - s.get('hits', 0)) / ctbf, 'k_rate': s.get('strikeOuts', 0) / ctbf}
        except: pass

        season_resp = requests.get("https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=2000", timeout=15).json()
        l_tbf = l_gs = 0
        for rec in season_resp['stats'][0]['splits']:
            name, pid, s = rec['player']['fullName'], rec['player']['id'], rec['stat']
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', 'Unknown'), 'Unknown')
            tbf, bb, h, so, gs = s.get('battersFaced', 0), s.get('baseOnBalls', 0), s.get('hits', 0), s.get('strikeOuts', 0), s.get('gamesStarted', 0)
            if tbf == 0: continue
            shrunk_out = ((tbf - bb - h) + LEAGUE_OUT_RATE * prior) / (tbf + prior)
            if pid in career_lookup:
                w = min(tbf / 300.0, 0.70)
                shrunk_out = shrunk_out * w + career_lookup[pid]['out_rate'] * (1.0 - w)
            pitcher_db[pid] = {'Name': name, 'Out%': shrunk_out, 'K%': (so + LEAGUE_K_RATE * prior) / (tbf + prior), 'BB%': (bb + LEAGUE_BB_RATE * prior) / (tbf + prior), 'Hand': hand_map.get(pid, 'R'), 'BF_per_Start': max(16.0, min(28.0, (tbf + LEAGUE_AVG_BF * 2) / (gs + 2))) if gs > 0 else LEAGUE_AVG_BF, 'GS': gs, 'IsGhost': tbf < 10}
            if gs > 0 and abbr != 'Unknown':
                if abbr not in team_sp_agg: team_sp_agg[abbr] = {'tbf': 0, 'gs': 0}
                team_sp_agg[abbr]['tbf'] += tbf; team_sp_agg[abbr]['gs'] += gs
                l_tbf += tbf; l_gs += gs
        l_avg_bf = l_tbf / l_gs if l_gs > 0 else LEAGUE_AVG_BF
        manager_db = {team: max(-3.0, min(3.0, (agg['tbf'] / agg['gs']) - l_avg_bf)) for team, agg in team_sp_agg.items()}
        return pitcher_db, manager_db
    except: return {}, {}

STATS_DB, MANAGER_DB = get_pitcher_and_manager_stats()

@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback, target_date_str):
    profile = {'actual_out_rate': fallback['Out%'], 'actual_k_rate': fallback['K%'], 'actual_bb_rate': fallback['BB%'], 'pitch_budget': 95.0, 'pitches_per_batter': 4.1, 'days_rest': 5, 'starts_count': fallback['GS'], 'is_ghost': fallback['IsGhost']}
    if not player_id: return profile
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season=2026"
        splits = requests.get(url, timeout=6).json().get('stats', [{}])[0].get('splits', [])
        starts = [s for s in splits if s['stat'].get('gamesStarted', 0) == 1]
        if starts:
            profile['starts_count'] = len(starts)
            t_pitches = sum(s['stat'].get('numberOfPitches', 0) for s in starts[:5])
            t_tbf = sum(s['stat'].get('battersFaced', 0) for s in starts[:5])
            if t_tbf > 0: profile['pitches_per_batter'] = max(3.5, t_pitches / t_tbf)
            peak_pitches = max(s['stat'].get('numberOfPitches', 0) for s in starts[:3])
            profile['pitch_budget'] = float(peak_pitches) if peak_pitches < 65 else max(peak_pitches, 95.0)
    except: pass
    return profile

# ==============================================================================
# ENGINE (Volume Sanity Filter Restored)
# ==============================================================================
def run_monte_carlo(sp_name, base_out_rate, k_rate, bb_rate, opp_data, park, temp, wind_speed, wind_dir, azimuth, umpire, manager_shift, pitch_budget, pitches_per_batter, starts_count, num_sims=10000):
    factors = []
    
    # VOLUME SANITY FILTER: Ray Fix
    raw_bf = (pitch_budget / max(pitches_per_batter, 3.5)) + 2.0 + (manager_shift * 0.5)
    adj_bf = min(raw_bf, 26.5) # Hard cap at 26.5 BF to prevent 9-inning hallucinations
    if sp_name in ["Logan Gilbert", "Zack Wheeler", "Corbin Burnes", "Gerrit Cole"]: adj_bf = raw_bf
    
    adj_out_rate = base_out_rate + (k_rate - LEAGUE_K_RATE) * 0.30
    opp_out_rate = opp_data.get('out_rate', TRUE_API_AVERAGE)
    adj_out_rate *= 1.0 + ((opp_out_rate / TRUE_API_AVERAGE) - 1.0) * 0.50
    
    wind_factor = math.cos(math.radians(azimuth - wind_dir))
    if wind_speed * wind_factor >= 8.0: adj_out_rate += 0.015
    elif wind_speed * wind_factor <= -8.0: adj_out_rate -= 0.020; adj_bf -= 0.5

    if umpire in WIDE_ZONE: adj_out_rate += 0.012; factors.append(f"🧑‍⚖️ Ump: Wide Zone (+1.2%)")
    elif umpire in TIGHT_ZONE: adj_out_rate -= 0.015; factors.append(f"🧑‍⚖️ Ump: Tight Zone (-1.5%)")
    
    adj_out_rate *= OUTS_PARK_FACTORS.get(park, 1.0)
    
    or_std = 0.045 if starts_count < 5 else 0.038
    game_out_rates = np.clip(np.random.normal(adj_out_rate, or_std, num_sims), 0.30, 0.95)
    performance_z = (game_out_rates - adj_out_rate) / or_std
    bf_modifier = np.where(performance_z > 0, performance_z * 2.5, performance_z * 1.8)
    dynamic_bf = np.clip(np.round(np.random.normal(adj_bf + bf_modifier, 1.8, num_sims)).astype(int), 9, 30)
    out_sims = np.random.binomial(dynamic_bf, game_out_rates)
    
    factors.append(f"🎯 Target BF: {adj_bf:.1f} | 📊 Adj OR: {adj_out_rate*100:.1f}%")
    return {'out_sims': out_sims, 'factors': factors, 'adj_out_rate': adj_out_rate, 'adj_bf': adj_bf}

# ==============================================================================
# UI Loop (Full Metrics Restored)
# ==============================================================================
st.title("⚾ Underdog Quant AI — Outs Engine v2 Master")
vegas_lines = fetch_automated_vegas_odds(api_key)

try:
    games = requests.get(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire", timeout=8).json().get('dates', [{}])[0].get('games', [])
except: games = []

if not games: st.info("No games found."); st.stop()

for game in games:
    home_team = TEAM_MAP.get(game['teams']['home']['team']['name'], game['teams']['home']['team']['name'])
    away_team = TEAM_MAP.get(game['teams']['away']['team']['name'], game['teams']['away']['team']['name'])
    h_sp_name, a_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD'), game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
    h_sp_id, a_sp_id = game['teams']['home'].get('probablePitcher', {}).get('id'), game['teams']['away'].get('probablePitcher', {}).get('id')
    if h_sp_name == 'TBD' or a_sp_name == 'TBD': continue

    api_ump = "Neutral"
    try:
        for off in game.get('officials', []):
            if off['officialType'] == 'Home Plate': api_ump = off['official']['fullName']
    except: pass

    temp, wind_spd, wind_dir, azimuth = get_weather_for_date(home_team, target_date_str)
    with st.expander(f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | 🧑‍⚖️ {api_ump}"):
        col1, col2 = st.columns(2)
        for side, sp_name, sp_id, team_abbr, opp_abbr in [(col1, a_sp_name, a_sp_id, away_team, home_team), (col2, h_sp_name, h_sp_id, home_team, away_team)]:
            with side:
                match = STATS_DB.get(sp_id, {'Out%': LEAGUE_OUT_RATE, 'K%': LEAGUE_K_RATE, 'BB%': LEAGUE_BB_RATE, 'Hand': 'R', 'GS': 0, 'IsGhost': True})
                opp_data = SPLITS_DB.get(opp_abbr, {}).get(match['Hand'], {'out_rate': TRUE_API_AVERAGE})
                lp = get_live_pitcher_profile(sp_id, match, target_date_str)
                
                ump_choice = st.selectbox(f"Umpire Override ({sp_name}):", ["API Assigned ("+api_ump+")", "Neutral"] + WIDE_ZONE + TIGHT_ZONE, key=f"ump_{sp_id}")
                final_ump = api_ump if "API" in ump_choice else ump_choice
                res = run_monte_carlo(sp_name, lp['actual_out_rate'], lp['actual_k_rate'], lp['actual_bb_rate'], opp_data, home_team, temp, wind_spd, wind_dir, azimuth, final_ump, MANAGER_DB.get(team_abbr, 0.0), lp['pitch_budget'], lp['pitches_per_batter'], lp['starts_count'])
                
                st.markdown(f"### {sp_name}")
                # FULL METRICS RESTORED
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Out%", f"{lp['actual_out_rate']*100:.1f}%")
                m2.metric("K%", f"{lp['actual_k_rate']*100:.1f}%")
                m3.metric("BB%", f"{lp['actual_bb_rate']*100:.1f}%")
                m4.metric("Starts", lp['starts_count'])
                
                m5, m6, m7 = st.columns(3)
                m5.metric("P/Batter", f"{lp['pitches_per_batter']:.2f}")
                m6.metric("Pitch Budget", f"{lp['pitch_budget']:.0f}")
                m7.metric("Ump Effect", "Wide" if final_ump in WIDE_ZONE else ("Tight" if final_ump in TIGHT_ZONE else "Neutral"))

                line_val = st.number_input("UD Line:", value=17.5, step=0.5, key=f"l_{sp_id}")
                h_prob = float(np.sum(res['out_sims'] > line_val)) / 10000 * 100
                l_prob = 100.0 - h_prob
                
                # EV Logic Locked to -122 Break-even
                target_prob = h_prob if h_prob > l_prob else l_prob
                ev = ((target_prob / 100.0) * (100.0 / 122.0)) - (1.0 - (target_prob / 100.0))
                
                if h_prob > 55.1: st.success(f"🔥 HIGHER: {h_prob:.1f}% | EV: {ev*100:+.1f}%")
                elif l_prob > 55.1: st.error(f"❄️ LOWER: {l_prob:.1f}% | EV: {ev*100:+.1f}%")
                else: st.warning(f"⚖️ NO PLAY: {max(h_prob, l_prob):.1f}%")
                
                st.info(f"📊 Median: {np.median(res['out_sims']):.1f} | Projected BF: {res['adj_bf']:.1f}")
                if st.button(f"💾 Log Result", key=f"log_{sp_id}"):
                    log_play_to_csv(target_date_str, sp_name, team_abbr, opp_abbr, line_val, "HIGHER" if h_prob > l_prob else "LOWER", UD_IMPLIED_ODDS, target_prob, ev*100, np.median(res['out_sims']), res['adj_bf'], final_ump)
                with st.expander("🔬 Model Breakdown"):
                    for f in res['factors']: st.caption(f"- {f}")

# ==============================================================================
# LEDGER VIEWER (Cloud-Friendly)
# ==============================================================================
st.divider()
st.header("📊 Betting Ledger")
if os.path.exists("quant_tracking_ledger.csv"):
    df = pd.read_csv("quant_tracking_ledger.csv")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    st.download_button("📥 Download Full CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="mlb_ledger.csv", mime="text/csv")
else: st.info("No plays logged.")

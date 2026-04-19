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
    """Pulls live pitcher_outs lines from The Odds API."""
    if not api_key or api_key == "YOUR_API_KEY":
        return {}
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
    except:
        return {}

# ==============================================================================
# CSV TRACKING LEDGER
# ==============================================================================
def log_play_to_csv(date, pitcher, team, opponent, line, pick, odds, prob, ev, median_outs, bf_proj):
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
        "Odds": odds,
        "Probability_Pct": round(prob, 2),
        "EV_Pct": round(ev, 2),
        "Median_Outs": round(median_outs, 2),
        "Projected_BF": round(bf_proj, 2)
    }
    
    df = pd.DataFrame([data])
    df.to_csv(file_name, mode='a', header=not file_exists, index=False)

# ==============================================================================
# PAGE SETUP
# ==============================================================================
st.set_page_config(page_title="MLB Quant AI - Outs Engine v2", page_icon="⚾", layout="wide")

st.sidebar.title("🤖 Outs Autopilot v2")
api_key = st.sidebar.text_input("🔑 The Odds API Key (Optional)", type="password")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All caches cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("v2 Master: No Ceilings | Desynced Relativity | Correlated Variance | Light Bayesian")

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

UMPIRE_DATABASE = {
    "Pitcher Friendly (Wide Zone)": [
        "Bill Miller", "Bill Welke", "Laz Diaz", "Larry Vanover", "Alan Porter",
        "Jordan Baker", "Mark Wegner", "Chris Guccione", "Ron Kulpa", "Jeremie Rehak",
        "Vic Carapazza", "Lance Barksdale", "Doug Eddings", "Paul Emmel", "Cory Blaser",
        "Adrian Johnson", "John Tumpane", "Nic Lentz", "Ben May", "Ryan Blakney",
    ],
    "Hitter Friendly (Tight Zone)": [
        "Pat Hoberg", "Quinn Wolcott", "Andy Fletcher", "Dan Bellino", "Lance Barrett",
        "CB Bucknor", "Ted Barrett", "Hunter Wendelstedt", "Mark Carlson",
        "Jeff Nelson", "Rob Drake", "Brian O'Nora", "Todd Tichenor", "Chad Fairchild",
        "Marvin Hudson", "Mike Muchlinski", "Adam Hamari", "Manny Gonzalez", "D.J. Reyburn",
    ],
}

OUTS_PARK_FACTORS = {
    'SEA': 1.03, 'TB':  1.02, 'MIA': 1.02, 'SD':  1.02, 'OAK': 1.01,
    'SF':  1.01, 'LAD': 1.01, 'NYM': 1.00, 'MIN': 1.00, 'BAL': 1.00,
    'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 1.00,
    'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98, 'CHC': 0.98,
    'STL': 0.98, 'PIT': 0.98, 'LAA': 0.97, 'HOU': 0.97, 'WSH': 0.97,
    'MIL': 1.00, 'KC':  0.99, 'CIN': 0.95, 'ARI': 0.94, 'COL': 0.88,
}

TEAM_MAP = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CHW',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
    'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Sacramento Athletics': 'OAK',
    'Athletics': 'OAK', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA',
    'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}

# ── LEAGUE CONSTANTS ──
LEAGUE_OUT_RATE = 0.695  # The pitcher's baseline boost for April
TRUE_API_AVERAGE = 0.680 # The mathematical average used to prevent opponent desync
LEAGUE_K_RATE   = 0.225
LEAGUE_BB_RATE  = 0.080
LEAGUE_AVG_BF   = 22.5

# ==============================================================================
# HELPER & DATA FETCHERS
# ==============================================================================
def get_shrinkage_prior(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        days_in = (d - datetime(d.year, 3, 28)).days
        if days_in < 30:   return 20
        elif days_in < 60: return 10
        else:              return 5
    except:
        return 15

@st.cache_data(ttl=3600)
def get_weather_for_date(team_abbr: str, date_str: str):
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords: return 70.0, 0.0, 0.0, 0.0
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={coords[0]}&longitude={coords[1]}"
            f"&start_date={date_str}&end_date={date_str}"
            f"&daily=temperature_2m_max,wind_speed_10m_max,wind_direction_10m_dominant"
            f"&timezone=auto"
        )
        data = requests.get(url, timeout=5).json()
        temp_f = (data['daily']['temperature_2m_max'][0] * 9 / 5) + 32
        wind_spd   = data['daily'].get('wind_speed_10m_max', [0])[0]
        wind_dir   = data['daily'].get('wind_direction_10m_dominant', [0])[0]
        return float(temp_f), float(wind_spd), float(wind_dir), float(coords[2])
    except: return 70.0, 0.0, 0.0, 0.0

@st.cache_data(ttl=86400)
def get_automated_team_splits() -> dict:
    splits: dict = {}
    for hand_code, api_code in [('L', 'vL'), ('R', 'vR')]:
        try:
            url = f"https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=statSplits&sitCode={api_code}"
            data = requests.get(url, timeout=10).json()
            for rec in data['stats'][0]['splits']:
                abbr = TEAM_MAP.get(rec['team']['name'], rec['team']['name'])
                if abbr not in splits: splits[abbr] = {}
                s  = rec['stat']
                pa = max(s.get('plateAppearances', 1), 1)
                splits[abbr][hand_code] = {
                    'out_rate': 1.0 - (s.get('hits', 0) + s.get('baseOnBalls', 0)) / pa,
                    'k_rate':   s.get('strikeOuts', 0) / pa,
                }
        except: pass
    return splits

SPLITS_DB = get_automated_team_splits()

@st.cache_data(ttl=86400)
def get_pitcher_and_manager_stats():
    pitcher_db:  dict = {}
    team_sp_agg: dict = {}
    prior = get_shrinkage_prior(datetime.now().strftime('%Y-%m-%d'))

    try:
        people_resp = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10).json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people_resp.get('people', [])}

        career_lookup: dict = {}
        try:
            career_resp = requests.get("https://statsapi.mlb.com/api/v1/stats?stats=career&group=pitching&playerPool=ALL&season=2026&limit=2000", timeout=15).json()
            for rec in career_resp['stats'][0]['splits']:
                pid, s, ctbf = rec['player']['id'], rec['stat'], rec['stat'].get('battersFaced', 0)
                if ctbf > 0:
                    career_lookup[pid] = {
                        'out_rate': (ctbf - s.get('baseOnBalls', 0) - s.get('hits', 0)) / ctbf,
                        'k_rate': s.get('strikeOuts', 0) / ctbf, 'tbf': ctbf
                    }
        except: pass

        season_resp = requests.get("https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=2000", timeout=15).json()
        league_tbf = league_gs = 0

        for rec in season_resp['stats'][0]['splits']:
            name, pid = rec['player']['fullName'], rec['player']['id']
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', 'Unknown'), 'Unknown')
            s = rec['stat']

            tbf, bb, h, so = s.get('battersFaced', 0), s.get('baseOnBalls', 0), s.get('hits', 0), s.get('strikeOuts', 0)
            gs, gp = s.get('gamesStarted', 0), s.get('gamesPlayed', 0)

            if tbf == 0: continue

            shrunk_out = ((tbf - bb - h) + LEAGUE_OUT_RATE * prior) / (tbf + prior)
            shrunk_k   = (so + LEAGUE_K_RATE * prior) / (tbf + prior)
            shrunk_bb  = (bb + LEAGUE_BB_RATE * prior) / (tbf + prior)

            if pid in career_lookup and career_lookup[pid]['tbf'] > 250:
                c, w = career_lookup[pid], min(tbf / 300.0, 0.70)
                shrunk_out = shrunk_out * w + c['out_rate'] * (1.0 - w)
                shrunk_k   = shrunk_k * w + c['k_rate'] * (1.0 - w)

            phantom = 2 if gs >= 4 else 3
            bf_per_start = max(16.0, min(28.0, (tbf + LEAGUE_AVG_BF * phantom) / (gs + phantom))) if gs > 0 else LEAGUE_AVG_BF

            pitcher_db[pid] = {
                'Name': name, 'Out%': shrunk_out, 'K%': shrunk_k, 'BB%': shrunk_bb,
                'Hand': hand_map.get(pid, 'R'), 'BF_per_Start': bf_per_start,
                'TBF': tbf, 'GS': gs, 'IsGhost': tbf < 10,
            }

            if gs > 0 and gp > 0 and (gs / gp) > 0.8 and abbr != 'Unknown':
                if abbr not in team_sp_agg: team_sp_agg[abbr] = {'tbf': 0, 'gs': 0}
                team_sp_agg[abbr]['tbf'] += tbf
                team_sp_agg[abbr]['gs']  += gs
                league_tbf += tbf; league_gs += gs

        league_avg_bf = league_tbf / league_gs if league_gs > 0 else LEAGUE_AVG_BF
        manager_db: dict = {}
        for team, agg in team_sp_agg.items():
            raw = agg['tbf'] / agg['gs'] if agg['gs'] > 0 else league_avg_bf
            manager_db[team] = max(-3.0, min(3.0, raw - league_avg_bf))

        return pitcher_db, manager_db
    except Exception as e:
        st.warning(f"Stats fetch error: {e}")
        return {}, {}

STATS_DB, MANAGER_DB = get_pitcher_and_manager_stats()

_DEFAULT_MATCH = {
    'Out%': LEAGUE_OUT_RATE, 'K%': LEAGUE_K_RATE, 'BB%': LEAGUE_BB_RATE,
    'Hand': 'R', 'BF_per_Start': LEAGUE_AVG_BF, 'TBF': 0, 'GS': 0, 'IsGhost': True,
}

@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback: dict, target_date_str: str) -> dict:
    season_avg_bf = fallback.get('BF_per_Start', LEAGUE_AVG_BF)
    profile = {
        'actual_out_rate': fallback['Out%'], 'actual_k_rate': fallback.get('K%', LEAGUE_K_RATE),
        'actual_bb_rate': fallback['BB%'], 'season_avg_bf': season_avg_bf, 'recent_tbf_cap': season_avg_bf,
        'pitch_budget': 95.0, 'pitches_per_batter': 3.9, 'recent_pitch_avg': 88.0,
        'days_rest': 5, 'starts_count': fallback.get('GS', 0), 'is_ghost': fallback.get('IsGhost', False),
    }

    if not player_id: return profile

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season=2026"
        splits = requests.get(url, timeout=6).json().get('stats', [{}])[0].get('splits', [])
        if not splits: return profile

        splits.sort(key=lambda x: x.get('date', '2000-01-01'), reverse=True)
        starts = [s for s in splits if s['stat'].get('gamesStarted', 0) == 1]
        profile['starts_count'] = len(starts)

        try:
            target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')
            if splits:
                last_date = datetime.strptime(splits[0].get('date', ''), '%Y-%m-%d')
                profile['days_rest'] = max(0, (target_dt - last_date).days)
        except: pass

        recent = starts[:5]
        if recent:
            total_pitches = sum(s['stat'].get('numberOfPitches', 0) for s in recent)
            total_tbf     = sum(s['stat'].get('battersFaced',    0) for s in recent)
            profile['recent_pitch_avg'] = total_pitches / len(recent)
            if total_tbf > 0: profile['pitches_per_batter'] = max(3.2, total_pitches / total_tbf)

        if len(recent) >= 2:
            peak_pitches = max(s['stat'].get('numberOfPitches', 0) for s in recent[:3])
            profile['pitch_budget'] = float(peak_pitches) if peak_pitches < 65 else max(peak_pitches, 95.0)
        else: profile['pitch_budget'] = 95.0

        if fallback.get('IsGhost', False) and len(starts) >= 2:
            tbf = sum(s['stat'].get('battersFaced', 0) for s in starts)
            bb  = sum(s['stat'].get('baseOnBalls', 0) for s in starts)
            h   = sum(s['stat'].get('hits', 0) for s in starts)
            so  = sum(s['stat'].get('strikeOuts', 0) for s in starts)
            if tbf > 0:
                profile['actual_out_rate'] = (tbf - bb - h) / tbf
                profile['actual_k_rate']   = so / tbf
                profile['actual_bb_rate']  = bb / tbf

        if len(starts) >= 3:
            recent3 = starts[:3]
            r_tbf = sum(s['stat'].get('battersFaced', 0) for s in recent3)
            r_bb  = sum(s['stat'].get('baseOnBalls',  0) for s in recent3)
            r_h   = sum(s['stat'].get('hits',         0) for s in recent3)
            r_so  = sum(s['stat'].get('strikeOuts',   0) for s in recent3)
            if r_tbf > 0:
                recent_out_rate = (r_tbf - r_bb - r_h) / r_tbf
                recent_k_rate   = r_so / r_tbf
                profile['actual_out_rate'] = profile['actual_out_rate'] * 0.75 + recent_out_rate * 0.25
                profile['actual_k_rate'] = profile['actual_k_rate'] * 0.75 + recent_k_rate * 0.25

    except Exception: pass
    return profile

# ==============================================================================
# MONTE CARLO ENGINE  (v2 Master - No Ceilings)
# ==============================================================================
def run_monte_carlo(
    sp_name: str, base_out_rate: float, k_rate: float, bb_rate: float, opp_data: dict,
    park: str, temp: float, wind_speed: float, wind_direction: float,
    stadium_azimuth: float, umpire: str, manager_shift: float,
    pitch_budget: float, pitches_per_batter: float, days_rest: int,
    starts_count: int, num_sims: int = 10_000
) -> dict:
    factors = []
    adj_out_rate = base_out_rate

    ACE_LIST = ["Zac Gallen", "Logan Gilbert", "Zack Wheeler", "Corbin Burnes", "Gerrit Cole", "Tarik Skubal", "Chris Sale"]
    if sp_name in ACE_LIST: pitch_budget = max(pitch_budget, 100.0)

    pitch_count_bf = pitch_budget / max(pitches_per_batter, 3.4)
    adj_bf = pitch_count_bf + 2.5 + (manager_shift * 0.50)
    
    if sp_name in ACE_LIST: adj_bf += 1.5
    
    hard_cap_bf = pitch_count_bf + 6.0   

    factors.append(f"📊 Baseline: {adj_out_rate*100:.1f}% Out Rate | {k_rate*100:.1f}% K% | Budget: {pitch_budget:.0f}")
    factors.append(f"🎯 Projected BF: {adj_bf:.1f} (Includes Vegas Survivor Bias & Inning Grace)")

    k_bonus = (k_rate - LEAGUE_K_RATE) * 0.30
    adj_out_rate += k_bonus

    if days_rest < 4:
        adj_out_rate -= 0.020; adj_bf -= 1.5
        factors.append(f"😓 Short Rest ({days_rest}d): -2% out rate, -1.5 BF")
    elif 5 <= days_rest <= 6:
        adj_out_rate += 0.005
    elif days_rest > 13:
        adj_out_rate -= 0.015; adj_bf -= 1.0
        factors.append(f"🦀 Extended Rest ({days_rest}d): -1.5% out rate, -1 BF")

    if manager_shift > 0.75: factors.append(f"👔 Manager: Long Leash (+{manager_shift:.1f} BF)")
    elif manager_shift < -0.75: factors.append(f"👔 Manager: Quick Hook ({manager_shift:.1f} BF)")

    if bb_rate > 0.10: adj_bf -= 0.8; factors.append(f"⛽ High BB% ({bb_rate*100:.1f}%): -0.8 BF")
    elif bb_rate < 0.06: adj_bf += 0.5; factors.append(f"🎯 Elite Command ({bb_rate*100:.1f}% BB): +0.5 BF")

    if adj_bf > hard_cap_bf: adj_bf = hard_cap_bf

    opp_out_rate = opp_data.get('out_rate', TRUE_API_AVERAGE)
    opp_k_rate   = opp_data.get('k_rate',  LEAGUE_K_RATE)
    
    adj_out_rate *= 1.0 + ((opp_out_rate / TRUE_API_AVERAGE) - 1.0) * 0.50
    
    if opp_k_rate > 0.26: adj_out_rate += 0.010; factors.append(f"🎰 High-K Lineup: +1.0% out rate")
    elif opp_k_rate < 0.18: adj_out_rate -= 0.010; factors.append(f"🏏 Contact Lineup: -1.0% out rate")

    if temp > 85: adj_out_rate -= 0.020; adj_bf -= 0.5
    elif temp > 78: adj_out_rate -= 0.010
    elif temp < 50: adj_out_rate += 0.015
    elif temp < 62: adj_out_rate += 0.008

    if wind_speed > 10:
        wind_factor = math.cos(math.radians(stadium_azimuth - wind_direction))
        effective_wind = wind_speed * wind_factor 
        if effective_wind >= 8.0: adj_out_rate += 0.015; factors.append(f"🧱 Wind IN: +1.5% out rate")
        elif effective_wind <= -8.0: adj_out_rate -= 0.020; adj_bf -= 0.5; factors.append(f"🚀 Wind OUT: -2.0% OR, -0.5 BF")
        elif abs(effective_wind) < 5.0 and wind_speed > 15: adj_out_rate -= 0.008

    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]: adj_out_rate += 0.012
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]: adj_out_rate -= 0.015

    pk = OUTS_PARK_FACTORS.get(park, 1.0)
    adj_out_rate *= pk
    if pk != 1.0: factors.append(f"🏟️ Park Factor ({park}): {(pk-1)*100:+.1f}%")

    if starts_count >= 3: adj_bf = max(adj_bf, 18.0)
    
    adj_out_rate = float(np.clip(adj_out_rate, 0.40, 0.85))
    adj_bf       = float(np.clip(adj_bf, 9.0, hard_cap_bf + 2.0))

    # ── CORRELATED SIMULATION (NO CEILINGS) ──
    or_std = 0.045 if starts_count < 5 else 0.038
    
    # 1. Simulate the out rates (how well they pitched in 10,000 parallel universes)
    game_out_rates = np.clip(np.random.normal(loc=adj_out_rate, scale=or_std, size=num_sims), 0.30, 0.95)

    # 2. Performance Z-Score: Did they pitch a gem or get shelled?
    performance_z = (game_out_rates - adj_out_rate) / or_std
    
    # 3. MASSIVE Leash Extension: If they pitch well, managers let them keep going. 
    # Give them up to +3 to +5 extra batters for elite performances.
    bf_modifier = np.where(performance_z > 0, performance_z * 2.8, performance_z * 2.0)
    sim_specific_bf = adj_bf + bf_modifier
    
    # 4. Generate the batters faced, completely ignoring the 'hard_cap_bf'
    bf_std = 2.0 if starts_count < 5 else 1.5 
    raw_bf = np.random.normal(loc=sim_specific_bf, scale=bf_std, size=num_sims)
    
    # 5. REMOVED THE HARD CAP: Let them pitch complete games (max 36 batters) if they earn it
    dynamic_bf = np.clip(np.round(raw_bf).astype(int), 9, 36)

    # 6. Run the final outs calculation
    out_sims = np.random.binomial(n=dynamic_bf, p=game_out_rates)

    return {'out_sims': out_sims, 'factors': factors, 'adj_out_rate': adj_out_rate, 'adj_bf': adj_bf, 'hard_cap_bf': hard_cap_bf}

def calculate_ev_percent(win_prob_pct: float, american_odds: int) -> float:
    if american_odds == 0: return 0.0
    prob = win_prob_pct / 100.0
    payout = (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout) - (1.0 - prob)) * 100.0

# ==============================================================================
# UI Loop
# ==============================================================================
st.title("⚾ MLB Quant AI — Pitcher Outs Engine v2 Master")
vegas_lines = fetch_automated_vegas_odds(api_key)

try:
    games = requests.get(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}&hydrate=probablePitcher,decisions,umpire", timeout=8).json().get('dates', [{}])[0].get('games', [])
except: games = []

if not games: st.info("No games found for this date."); st.stop()

NUM_SIMS = 10_000

for game in games:
    home_team = TEAM_MAP.get(game['teams']['home']['team']['name'], game['teams']['home']['team']['name'])
    away_team = TEAM_MAP.get(game['teams']['away']['team']['name'], game['teams']['away']['team']['name'])
    
    h_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
    a_sp_name = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
    h_sp_id = game['teams']['home'].get('probablePitcher', {}).get('id')
    a_sp_id = game['teams']['away'].get('probablePitcher', {}).get('id')

    if h_sp_name == 'TBD' or a_sp_name == 'TBD': continue

    umpire = "Neutral"
    if 'officials' in game:
        for off in game['officials']:
            if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
    if umpire == "Neutral":
        try:
            bx = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/boxscore", timeout=5).json()
            for off in bx.get('officials', []):
                if off['officialType'] == 'Home Plate': umpire = off['official']['fullName']
        except: pass

    temp, wind_speed, wind_dir, azimuth = get_weather_for_date(home_team, target_date_str)
    ump_tag = f" | 🧑‍⚖️ {umpire}" if umpire != "Neutral" else ""
    label = f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | {temp:.0f}°F 💨{wind_speed:.0f}mph{ump_tag}"

    with st.expander(label):
        col1, col2 = st.columns(2)
        for side, sp_name, sp_id, team_abbr, opp_abbr in [(col1, a_sp_name, a_sp_id, away_team, home_team), (col2, h_sp_name, h_sp_id, home_team, away_team)]:
            with side:
                match = STATS_DB.get(sp_id, dict(_DEFAULT_MATCH))
                opp_data = SPLITS_DB.get(opp_abbr, {}).get(match['Hand'], {'out_rate': LEAGUE_OUT_RATE, 'k_rate': LEAGUE_K_RATE})
                manager_shift = MANAGER_DB.get(team_abbr, 0.0)
                lp = get_live_pitcher_profile(sp_id, match, target_date_str)

                res = run_monte_carlo(
                    sp_name=sp_name, base_out_rate=lp['actual_out_rate'], k_rate=lp['actual_k_rate'], bb_rate=lp['actual_bb_rate'],
                    opp_data=opp_data, park=home_team, temp=temp, wind_speed=wind_speed, wind_direction=wind_dir,
                    stadium_azimuth=azimuth, umpire=umpire, manager_shift=manager_shift, pitch_budget=lp['pitch_budget'],
                    pitches_per_batter=lp['pitches_per_batter'], days_rest=lp['days_rest'], starts_count=lp['starts_count'], num_sims=NUM_SIMS
                )
                out_sims = res['out_sims']
                
                ghost_tag = " ⚠️ Limited Data" if lp['is_ghost'] else ""
                st.markdown(f"### {sp_name} ({match['Hand']}HP){ghost_tag}")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Out%", f"{lp['actual_out_rate']*100:.1f}%")
                m2.metric("K%", f"{lp['actual_k_rate']*100:.1f}%")
                m3.metric("BB%", f"{lp['actual_bb_rate']*100:.1f}%")
                m4.metric("Rest", f"{lp['days_rest']}d")

                m5, m6, m7 = st.columns(3)
                m5.metric("Starts", lp['starts_count'])
                m6.metric("P/BF", f"{lp['pitches_per_batter']:.2f}")
                m7.metric("Pitch Bdgt", f"{lp['pitch_budget']:.0f}")

                st.divider()

                vegas_data = vegas_lines.get(sp_name, {'Over': {'line': 17.5, 'price': -110}, 'Under': {'line': 17.5, 'price': -110}})
                key_base = f"{team_abbr}_{sp_id}_{game['gamePk']}"
                
                line_o = st.number_input("Outs Line:", value=float(vegas_data['Over']['line']), step=0.5, key=f"o_{key_base}")
                oc1, oc2 = st.columns(2)
                with oc1: o_odds = st.number_input("Over Odds:", value=int(vegas_data['Over']['price']), step=5, key=f"oo_{key_base}")
                with oc2: u_odds = st.number_input("Under Odds:", value=int(vegas_data['Under']['price']), step=5, key=f"uo_{key_base}")

                o_prob = float(np.sum(out_sims > line_o)) / NUM_SIMS * 100
                u_prob = 100.0 - o_prob
                o_ev = calculate_ev_percent(o_prob, o_odds)
                u_ev = calculate_ev_percent(u_prob, u_odds)

                if o_prob > 60: st.success(f"📈 OVER {o_prob:.1f}%  |  UNDER {u_prob:.1f}%")
                elif o_prob < 40: st.error(f"📉 UNDER {u_prob:.1f}%  |  OVER {o_prob:.1f}%")
                else: st.warning(f"⚖️ Neutral  |  OVER {o_prob:.1f}%  |  UNDER {u_prob:.1f}%")

                ev1, ev2 = st.columns(2)
                with ev1:
                    if o_ev > 3.0: st.success(f"🔥 OVER +EV: {o_ev:+.1f}%")
                    elif o_ev > 1.0: st.info(f"OVER EV: {o_ev:+.1f}%")
                    else: st.caption(f"OVER EV: {o_ev:+.1f}%")
                with ev2:
                    if u_ev > 3.0: st.success(f"🔥 UNDER +EV: {u_ev:+.1f}%")
                    elif u_ev > 1.0: st.info(f"UNDER EV: {u_ev:+.1f}%")
                    else: st.caption(f"UNDER EV: {u_ev:+.1f}%")

                median_outs = float(np.median(out_sims))
                p10, p25, p75, p90 = float(np.percentile(out_sims, 10)), float(np.percentile(out_sims, 25)), float(np.percentile(out_sims, 75)), float(np.percentile(out_sims, 90))
                st.info(f"📊 Median: **{median_outs:.1f}** | Est. BF: **{res['adj_bf']:.1f}**")

                log1, log2 = st.columns(2)
                with log1:
                    if st.button(f"💾 Log OVER {line_o}", key=f"log_o_{key_base}"):
                        log_play_to_csv(target_date_str, sp_name, team_abbr, opp_abbr, line_o, "OVER", o_odds, o_prob, o_ev, median_outs, res['adj_bf'])
                        st.toast(f"Logged OVER {line_o} for {sp_name}!")
                with log2:
                    if st.button(f"💾 Log UNDER {line_o}", key=f"log_u_{key_base}"):
                        log_play_to_csv(target_date_str, sp_name, team_abbr, opp_abbr, line_o, "UNDER", u_odds, u_prob, u_ev, median_outs, res['adj_bf'])
                        st.toast(f"Logged UNDER {line_o} for {sp_name}!")

                dist_series = pd.Series(out_sims).value_counts(normalize=True).sort_index().rename("Probability")
                st.bar_chart(dist_series)

                with st.expander("🔬 Model Factor Breakdown"):
                    for f in res['factors']: st.caption(f"- {f}")

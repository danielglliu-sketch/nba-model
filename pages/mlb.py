import os
import math
import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from io import StringIO
import difflib

# ==============================================================================
# CONSTANTS
# ==============================================================================
LEAGUE_K_RATE           = 0.225   # ~22.5% of BF result in strikeout
LEAGUE_BB_RATE          = 0.080
LEAGUE_AVG_BF           = 22.5
LEAGUE_SWSTR_RATE       = 0.108   # ~10.8% swinging strike rate league avg
UD_IMPLIED_ODDS         = -122    # Underdog break-even
SWSTR_TO_K_SLOPE        = 1.85    # regression coefficient: K% ≈ 0.45 + 1.85 × SwStr%
STUFF_K_PER_10          = 0.015   # +10 Stuff+ points ≈ +1.5% K rate
SWSTR_PENALTY_THRESHOLD = 0.095   # Just below league avg (0.108); clearly below-avg whiff rate
ACE_BF_THRESHOLD        = 24.0    # Pitchers averaging >=24 BF/start bypass the 26.5 cap

K_PARK_FACTORS = {
    'SEA': 1.03, 'TB':  1.02, 'MIA': 1.02, 'SD':  1.01, 'OAK': 1.01,
    'SF':  1.01, 'LAD': 1.01, 'NYM': 1.00, 'MIN': 1.00, 'BAL': 0.99,
    'TOR': 1.00, 'TEX': 0.99, 'ATL': 1.00, 'DET': 0.99, 'CLE': 1.00,
    'NYY': 1.00, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.99, 'CHC': 0.98,
    'STL': 0.99, 'PIT': 0.99, 'LAA': 0.99, 'HOU': 1.00, 'WSH': 0.99,
    'MIL': 1.00, 'KC':  0.99, 'CIN': 0.97, 'ARI': 0.98, 'COL': 0.93,
}

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

WIDE_ZONE  = ["Bill Miller","Bill Welke","Laz Diaz","Larry Vanover","Alan Porter","Jordan Baker",
               "Mark Wegner","Chris Guccione","Ron Kulpa","Jeremie Rehak","Vic Carapazza",
               "Lance Barksdale","Doug Eddings","Paul Emmel","Cory Blaser","Adrian Johnson",
               "John Tumpane","Nic Lentz","Ben May","Ryan Blakney"]
TIGHT_ZONE = ["Pat Hoberg","Quinn Wolcott","Andy Fletcher","Dan Bellino","Lance Barrett",
               "CB Bucknor","Ted Barrett","Hunter Wendelstedt","Mark Carlson","Jeff Nelson",
               "Rob Drake","Brian O'Nora","Todd Tichenor","Chad Fairchild","Marvin Hudson",
               "Mike Muchlinski","Adam Hamari","Manny Gonzalez","D.J. Reyburn"]

TEAM_MAP = {
    'Arizona Diamondbacks':'ARI','Atlanta Braves':'ATL','Baltimore Orioles':'BAL','Boston Red Sox':'BOS',
    'Chicago Cubs':'CHC','Chicago White Sox':'CHW','Cincinnati Reds':'CIN','Cleveland Guardians':'CLE',
    'Colorado Rockies':'COL','Detroit Tigers':'DET','Houston Astros':'HOU','Kansas City Royals':'KC',
    'Los Angeles Angels':'LAA','Los Angeles Dodgers':'LAD','Miami Marlins':'MIA','Milwaukee Brewers':'MIL',
    'Minnesota Twins':'MIN','New York Mets':'NYM','New York Yankees':'NYY','Oakland Athletics':'OAK',
    'Sacramento Athletics':'OAK','Athletics':'OAK','Philadelphia Phillies':'PHI','Pittsburgh Pirates':'PIT',
    'San Diego Padres':'SD','San Francisco Giants':'SF','Seattle Mariners':'SEA','St. Louis Cardinals':'STL',
    'Tampa Bay Rays':'TB','Texas Rangers':'TEX','Toronto Blue Jays':'TOR','Washington Nationals':'WSH',
}

# ==============================================================================
# PAGE SETUP
# ==============================================================================
st.set_page_config(page_title="MLB K Quant AI", page_icon="🔥", layout="wide")
st.sidebar.title("🔥 K Autopilot v2.1")
api_key         = st.sidebar.text_input("🔑 The Odds API Key (Optional)", type="password")
selected_date   = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All caches cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("v2.1: Lineup Splits | Dynamic BF Cap | SwStr Fix | Sample-Weighted Opp K | Live EV Odds")


# ==============================================================================
# HELPER: American odds → decimal payout per $1 risked
# ==============================================================================
def american_to_payout(american_odds: int) -> float:
    """Convert American odds (e.g. -115, +130) to decimal payout per $1 risked."""
    if american_odds < 0:
        return 100.0 / abs(american_odds)
    else:
        return float(american_odds) / 100.0


# ==============================================================================
# BASEBALL SAVANT — SwStr% + Stuff+
# ==============================================================================
@st.cache_data(ttl=86400)
def fetch_savant_data():
    savant_db    = {}
    savant_names = {}
    headers      = {'User-Agent': 'Mozilla/5.0 (compatible; MLBQuantBot/2.0)'}
    base         = "https://baseballsavant.mlb.com/leaderboard/custom"

    # --- SwStr% (whiff_percent) ---
    try:
        r = requests.get(base, params={
            'year': '2026', 'type': 'pitcher', 'filter': '', 'sort': '1',
            'sortDir': 'desc', 'min': '1', 'selections': 'whiff_percent',
            'player_type': 'pitcher', 'csv': 'true'
        }, headers=headers, timeout=10)
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.lower().strip() for c in df.columns]
        pid_col   = next((c for c in df.columns if 'player_id' in c or c == 'pitcher'), None)
        swstr_col = next((c for c in df.columns if 'whiff' in c), None)
        name_col  = next((c for c in df.columns if 'name' in c), None)

        if pid_col and swstr_col:
            for _, row in df.iterrows():
                try:
                    pid       = int(row[pid_col])
                    raw_whiff = float(row[swstr_col])
                    raw_whiff = raw_whiff / 100.0 if raw_whiff > 1 else raw_whiff
                    
                    # Convert Whiff% to true SwStr% using the 0.47 multiplier
                    swstr = raw_whiff * 0.47
                    
                    savant_db[pid] = {'swstr': swstr, 'stuff_plus': 100.0}
                    if name_col:
                        raw_name = str(row[name_col])
                        if ',' in raw_name:
                            parts    = raw_name.split(',')
                            fmt_name = f"{parts[1].strip()} {parts[0].strip()}".title()
                        else:
                            fmt_name = raw_name.strip().title()
                        savant_names[fmt_name] = {'swstr': swstr, 'stuff_plus': 100.0}
                except:
                    pass
    except Exception as e:
        st.sidebar.warning(f"⚠️ Savant SwStr% unavailable: {e}")

    # --- Stuff+ ---
    try:
        r = requests.get(base, params={
            'year': '2026', 'type': 'pitcher', 'filter': '', 'sort': '1',
            'sortDir': 'desc', 'min': '1', 'selections': 'stuff_plus_stuff',
            'player_type': 'pitcher', 'csv': 'true'
        }, headers=headers, timeout=10)
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.lower().strip() for c in df.columns]
        pid_col   = next((c for c in df.columns if 'player_id' in c or c == 'pitcher'), None)
        stuff_col = next((c for c in df.columns if 'stuff' in c), None)
        name_col  = next((c for c in df.columns if 'name' in c), None)

        if pid_col and stuff_col:
            for _, row in df.iterrows():
                try:
                    pid   = int(row[pid_col])
                    stuff = float(row[stuff_col])
                    if pid in savant_db:
                        savant_db[pid]['stuff_plus'] = stuff
                    else:
                        savant_db[pid] = {'swstr': LEAGUE_SWSTR_RATE, 'stuff_plus': stuff}
                    if name_col:
                        raw_name = str(row[name_col])
                        if ',' in raw_name:
                            parts    = raw_name.split(',')
                            fmt_name = f"{parts[1].strip()} {parts[0].strip()}".title()
                        else:
                            fmt_name = raw_name.strip().title()
                        if fmt_name in savant_names:
                            savant_names[fmt_name]['stuff_plus'] = stuff
                        else:
                            savant_names[fmt_name] = {'swstr': LEAGUE_SWSTR_RATE, 'stuff_plus': stuff}
                except:
                    pass
    except Exception as e:
        st.sidebar.warning(f"⚠️ Savant Stuff+ unavailable: {e}")

    loaded = len(savant_db)
    if loaded > 0:
        st.sidebar.success(f"✅ Savant data: {loaded} pitchers loaded")
    return savant_db, savant_names


# ==============================================================================
# VEGAS ODDS — K Props
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_automated_vegas_odds(api_key):
    if not api_key or api_key == "YOUR_API_KEY":
        return {}
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/baseball_mlb/events",
            params={'apiKey': api_key, 'regions': 'us',
                    'markets': 'pitcher_strikeouts', 'oddsFormat': 'american'},
            timeout=8
        ).json()
        odds_db = {}
        for event in r:
            for book in event.get('bookmakers', []):
                if book['key'] == 'draftkings':
                    for outcome in book['markets'][0]['outcomes']:
                        name = outcome['description']
                        if name not in odds_db:
                            odds_db[name] = {'Over':  {'line': 5.5, 'price': UD_IMPLIED_ODDS},
                                             'Under': {'line': 5.5, 'price': UD_IMPLIED_ODDS}}
                        if outcome['name'] == 'Over':
                            odds_db[name]['Over']  = {'line': outcome['point'], 'price': outcome['price']}
                        elif outcome['name'] == 'Under':
                            odds_db[name]['Under'] = {'line': outcome['point'], 'price': outcome['price']}
        return odds_db
    except:
        return {}


# ==============================================================================
# WEATHER — Open-Meteo (free, no key required)
# ==============================================================================
@st.cache_data(ttl=3600)
def get_weather_for_date(team_abbr, date_str):
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords:
        return 72.0, 5.0, 180.0, 180.0
    lat, lon, azimuth = coords
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={'latitude': lat, 'longitude': lon,
                    'hourly': 'temperature_2m,windspeed_10m,winddirection_10m',
                    'timezone': 'auto', 'forecast_days': 2},
            timeout=6
        ).json()
        times    = r['hourly']['time']
        target   = date_str + "T19:00"
        idx      = next((i for i, t in enumerate(times) if t == target), 12)
        temp_f   = r['hourly']['temperature_2m'][idx] * 9 / 5 + 32
        wind_spd = r['hourly']['windspeed_10m'][idx] * 0.621371
        wind_dir = r['hourly']['winddirection_10m'][idx]
        return temp_f, wind_spd, wind_dir, float(azimuth)
    except:
        return 72.0, 5.0, 180.0, 180.0


# ==============================================================================
# All-player bat/pitch handedness map (used for lineup splits)
# ==============================================================================
@st.cache_data(ttl=86400)
def get_all_player_hands():
    hand_map = {}
    try:
        people = requests.get(
            "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026",
            timeout=10
        ).json()
        for p in people.get('people', []):
            pid = p['id']
            hand_map[pid] = {
                'bat':   p.get('batSide',   {}).get('code', 'R'),
                'pitch': p.get('pitchHand', {}).get('code', 'R'),
            }
    except:
        pass
    return hand_map


# ==============================================================================
# Lineup handedness adjustment
# ==============================================================================
@st.cache_data(ttl=1800)
def get_lineup_hand_adjustment(game_pk, opp_is_home, pitcher_hand, base_opp_k_rate):
    hand_map = get_all_player_hands()
    if not hand_map:
        return base_opp_k_rate, ""

    try:
        bx   = requests.get(
            f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore",
            timeout=6
        ).json()
        side = 'home' if opp_is_home else 'away'
        batting_order = bx['teams'][side].get('battingOrder', [])

        if not batting_order:
            return base_opp_k_rate, "⚠️ Lineup not yet posted — using team K% baseline"

        same_hand = 0.0
        total     = 0

        for pid in batting_order[:9]:          # Starting nine only
            bat_hand = hand_map.get(int(pid), {}).get('bat', 'R')
            if bat_hand == 'S':                
                same_hand += 0.0               # They will always take the opposite-hand advantage
            elif bat_hand == pitcher_hand:
                same_hand += 1.0
            total += 1

        if total == 0:
            return base_opp_k_rate, ""

        same_pct    = same_hand / total
        platoon_adj = float(np.clip((same_pct - 0.50) * 0.15, -0.075, 0.075))
        adj_k       = base_opp_k_rate * (1.0 + platoon_adj)
        note        = (f"🆚 Lineup splits: {same_hand:.1f}/{total} same-hand batters "
                       f"({platoon_adj * 100:+.1f}% opp K adj)")
        return adj_k, note

    except Exception as e:
        return base_opp_k_rate, f"⚠️ Lineup fetch failed ({e}) — using team K% baseline"


# ==============================================================================
# MLB API — Team K rates + games played 
# ==============================================================================
@st.cache_data(ttl=86400)
def get_team_k_rates():
    team_k     = {}
    team_games = {}
    try:
        r = requests.get(
            "https://statsapi.mlb.com/api/v1/teams/stats",
            params={'stats': 'season', 'group': 'hitting',
                    'season': '2026', 'gameType': 'R'},
            timeout=8
        ).json()
        for rec in r.get('stats', [{}])[0].get('splits', []):
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', ''), '')
            if not abbr:
                continue
            s  = rec['stat']
            ab = s.get('atBats', 0)
            so = s.get('strikeOuts', 0)
            gp = s.get('gamesPlayed', 0)    
            if ab > 0:
                k_rate          = so / ab
                team_k[abbr]    = {'L': k_rate, 'R': k_rate}
                team_games[abbr] = gp
    except:
        pass
    return team_k, team_games


# ==============================================================================
# MLB API — Pitcher Season Stats
# ==============================================================================
def get_shrinkage_prior(date_str):
    try:
        d       = datetime.strptime(date_str, '%Y-%m-%d')
        days_in = (d - datetime(d.year, 3, 28)).days
        return 20 if days_in < 30 else (10 if days_in < 60 else 5)
    except:
        return 15


@st.cache_data(ttl=86400)
def get_pitcher_stats():
    pitcher_db = {}
    manager_db = {}
    prior      = get_shrinkage_prior(datetime.now().strftime('%Y-%m-%d'))
    try:
        people   = requests.get(
            "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10
        ).json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R')
                    for p in people.get('people', [])}

        career_k = {}
        try:
            cr = requests.get(
                "https://statsapi.mlb.com/api/v1/stats?stats=career&group=pitching"
                "&playerPool=ALL&season=2026&limit=2000",
                timeout=15
            ).json()
            for rec in cr['stats'][0]['splits']:
                pid = rec['player']['id']
                s   = rec['stat']
                tbf = s.get('battersFaced', 0)
                so  = s.get('strikeOuts', 0)
                if tbf > 0:
                    career_k[pid] = so / tbf
        except:
            pass

        sr     = requests.get(
            "https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching"
            "&playerPool=ALL&season=2026&limit=2000",
            timeout=15
        ).json()
        l_tbf = l_gs = 0
        for rec in sr['stats'][0]['splits']:
            name = rec['player']['fullName']
            pid  = rec['player']['id']
            s    = rec['stat']
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', 'Unknown'), 'Unknown')
            tbf  = s.get('battersFaced', 0)
            so   = s.get('strikeOuts', 0)
            bb   = s.get('baseOnBalls', 0)
            gs   = s.get('gamesStarted', 0)
            if tbf == 0:
                continue

            shrunk_k = (so + LEAGUE_K_RATE * prior) / (tbf + prior)
            if pid in career_k:
                w        = min(tbf / 300.0, 0.70)
                shrunk_k = shrunk_k * w + career_k[pid] * (1.0 - w)

            avg_bf_per_start = (
                max(16.0, min(28.0, (tbf + LEAGUE_AVG_BF * 2) / (gs + 2)))
                if gs > 0 else LEAGUE_AVG_BF
            )

            pitcher_db[pid] = {
                'Name':            name,
                'K%':              shrunk_k,
                'BB%':             (bb + LEAGUE_BB_RATE * prior) / (tbf + prior),
                'Hand':            hand_map.get(pid, 'R'),
                'BF_per_Start':    avg_bf_per_start,
                'AvgBFperStart':   avg_bf_per_start, 
                'GS':              gs,
                'IsGhost':         tbf < 10,
                'TBF':             tbf,
            }

            if gs > 0 and abbr != 'Unknown':
                if abbr not in manager_db:
                    manager_db[abbr] = {'tbf': 0, 'gs': 0}
                manager_db[abbr]['tbf'] += tbf
                manager_db[abbr]['gs']  += gs
                l_tbf += tbf
                l_gs  += gs

        l_avg_bf   = l_tbf / l_gs if l_gs > 0 else LEAGUE_AVG_BF
        manager_db = {t: max(-3.0, min(3.0, (v['tbf'] / v['gs']) - l_avg_bf))
                      for t, v in manager_db.items() if v['gs'] > 0}

    except Exception as e:
        st.sidebar.error(f"MLB API error: {e}")
        return {}, {}

    return pitcher_db, manager_db


# ==============================================================================
# LIVE PITCHER GAME LOG
# ==============================================================================
@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback, target_date_str):
    profile = {
        'k_rate':             fallback['K%'],
        'bb_rate':            fallback['BB%'],
        'pitch_budget':       95.0,
        'pitches_per_batter': 4.1,
        'starts_count':       fallback['GS'],
        'is_ghost':           fallback['IsGhost'],
        'recent_k_trend':     0.0,
        'avg_bf_per_start':   fallback.get('AvgBFperStart', LEAGUE_AVG_BF),
    }
    if not player_id:
        return profile
    try:
        url    = (f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
                  f"?stats=gameLog&group=pitching&season=2026")
        splits = requests.get(url, timeout=6).json().get('stats', [{}])[0].get('splits', [])
        starts = [s for s in splits if s['stat'].get('gamesStarted', 0) == 1]

        if starts:
            profile['starts_count'] = len(starts)

            recent_pitches       = [s['stat'].get('numberOfPitches', 0) for s in starts[:3]]
            peak                 = max(recent_pitches) if recent_pitches else 0
            profile['pitch_budget'] = float(peak) if 65 <= peak <= 120 else 95.0

            t_p = sum(s['stat'].get('numberOfPitches', 0) for s in starts[:5])
            t_b = sum(s['stat'].get('battersFaced', 0)    for s in starts[:5])
            if t_b > 0:
                profile['pitches_per_batter'] = max(3.5, t_p / t_b)

            all_bf = [s['stat'].get('battersFaced', 0) for s in starts if s['stat'].get('battersFaced', 0) > 0]
            if all_bf:
                profile['avg_bf_per_start'] = sum(all_bf) / len(all_bf)

            if len(starts) >= 3:
                recent_k  = sum(s['stat'].get('strikeOuts', 0)    for s in starts[:3]) / 3
                recent_bf = sum(s['stat'].get('battersFaced', 0)   for s in starts[:3]) / 3
                if recent_bf > 0:
                    profile['recent_k_trend'] = (recent_k / recent_bf) - fallback['K%']

    except:
        pass
    return profile


# ==============================================================================
# CSV LEDGER
# ==============================================================================
def log_play_to_csv(date, pitcher, team, opponent, line, pick, odds, prob, ev,
                    median_k, bf_proj, umpire_name, swstr, stuff_plus):
    fname       = "k_tracking_ledger.csv"
    file_exists = os.path.isfile(fname)
    data        = {
        "Game_Date":        date,
        "Timestamp_Logged": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Pitcher":          pitcher,
        "Team":             team,
        "Opponent":         opponent,
        "Line":             line,
        "Pick":             pick,
        "Implied_Odds":     odds,
        "Probability_Pct":  round(prob, 2),
        "EV_Pct":           round(ev, 2),
        "Median_Ks":        round(median_k, 2),
        "Projected_BF":     round(bf_proj, 2),
        "SwStr_Pct":        round(swstr * 100, 1),
        "Stuff_Plus":       round(stuff_plus, 1),
        "Umpire":           umpire_name,
        "Platform":         "Underdog",
        "Result":           "",
        "Actual_Ks":        "",
    }
    pd.DataFrame([data]).to_csv(fname, mode='a', header=not file_exists, index=False)


# ==============================================================================
# MONTE CARLO ENGINE
# ==============================================================================
def run_monte_carlo_k(sp_name, base_k_rate, bb_rate, opp_k_rate, swstr_rate,
                      stuff_plus, recent_k_trend, park, temp_f, wind_speed,
                      wind_dir, azimuth, umpire, manager_shift,
                      pitch_budget, pitches_per_batter, starts_count, sp_id,
                      avg_bf_per_start=LEAGUE_AVG_BF,   
                      opp_sample_games=30,               
                      num_sims=10000):

    today_int = int(datetime.now().strftime('%Y%m%d'))
    np.random.seed(sp_id + today_int)

    factors = []
    adj_k   = base_k_rate

    # ── SwStr% adjustment ──────────────────────────────────────────────────────
    swstr_delta = swstr_rate - LEAGUE_SWSTR_RATE
    swstr_adj   = swstr_delta * SWSTR_TO_K_SLOPE
    adj_k      += swstr_adj * 0.60
    if abs(swstr_adj) > 0.005:
        direction = "⬆️" if swstr_adj > 0 else "⬇️"
        factors.append(f"🌀 SwStr%: {swstr_rate*100:.1f}% {direction} ({swstr_adj*100:+.1f}% K adj)")

    # ── Stuff+ adjustment ──────────────────────────────────────────────────────
    stuff_adj = (stuff_plus - 100.0) * (STUFF_K_PER_10 / 10.0)
    adj_k    += stuff_adj * 0.40
    if abs(stuff_adj) > 0.003:
        factors.append(f"💪 Stuff+: {stuff_plus:.0f} ({stuff_adj*100:+.1f}% K adj)")

    # ── Opponent K rate ────────────────────────────────────────────────────────
    league_avg_opp_k = 0.215
    if not (opp_k_rate and math.isfinite(opp_k_rate) and opp_k_rate > 0):
        opp_k_rate = league_avg_opp_k

    sample_weight = float(np.clip(opp_sample_games / 30.0, 0.10, 1.0))
    raw_opp_adj   = (opp_k_rate - league_avg_opp_k) / league_avg_opp_k * 0.12
    opp_adj       = float(np.clip(raw_opp_adj * sample_weight, -0.15, 0.15))
    adj_k        *= (1.0 + opp_adj)
    factors.append(
        f"👥 Opp K%: {opp_k_rate*100:.1f}% ({opp_adj*100:+.1f}%) "
        f"[sample weight: {sample_weight:.0%} / {opp_sample_games}g]"
    )

    # ── Recent trend ───────────────────────────────────────────────────────────
    adj_k += recent_k_trend * 0.25
    if abs(recent_k_trend) > 0.010:
        factors.append(f"📈 Recent K trend: {recent_k_trend*100:+.1f}% vs season avg")

    # ── Umpire ─────────────────────────────────────────────────────────────────
    if umpire in WIDE_ZONE:
        adj_k += 0.025
        factors.append("🧑‍⚖️ Ump: Wide Zone (+2.5% K rate)")
    elif umpire in TIGHT_ZONE:
        adj_k -= 0.030
        factors.append("🧑‍⚖️ Ump: Tight Zone (-3.0% K rate)")

    # ── Park factor ────────────────────────────────────────────────────────────
    park_pf = K_PARK_FACTORS.get(park, 1.0)
    adj_k  *= park_pf
    if park_pf != 1.0:
        factors.append(f"🏟️ Park: {park} (×{park_pf:.2f})")

    # ── Temperature ────────────────────────────────────────────────────────────
    if temp_f < 45:
        adj_k -= 0.012
        factors.append(f"🥶 Cold ({temp_f:.0f}°F): -1.2% K adj")
    elif temp_f > 85:
        adj_k += 0.006
        factors.append(f"☀️ Hot ({temp_f:.0f}°F): +0.6% K adj")

    # ── BF projection ──────────────────────────────────────────────────────────
    raw_bf  = (pitch_budget / max(pitches_per_batter, 3.5)) + 2.0 + (manager_shift * 0.5)
    adj_bf  = raw_bf if avg_bf_per_start >= ACE_BF_THRESHOLD else min(raw_bf, 26.5)
    factors.append(
        f"🎯 Target BF: {adj_bf:.1f} (avg {avg_bf_per_start:.1f}/start) | Adj K%: {adj_k*100:.1f}%"
    )

    if not math.isfinite(adj_k):
        adj_k = LEAGUE_K_RATE
    adj_k = float(np.clip(adj_k, 0.05, 0.55))

    # ── Simulate ───────────────────────────────────────────────────────────────
    k_std        = 0.040 if starts_count < 5 else 0.032
    game_k_rates = np.clip(np.random.normal(adj_k, k_std, num_sims), 0.05, 0.55)
    game_k_rates = np.where(np.isfinite(game_k_rates), game_k_rates, adj_k)

    perf_z     = (game_k_rates - adj_k) / k_std
    bf_mod     = np.where(perf_z > 0, perf_z * 2.5, perf_z * 1.8)
    dynamic_bf = np.clip(
        np.round(np.random.normal(adj_bf + bf_mod, 1.8, num_sims)).astype(int),
        9, 30
    )
    k_sims = np.random.binomial(dynamic_bf, game_k_rates)
    np.random.seed(None)

    return {
        'k_sims':     k_sims,
        'factors':    factors,
        'adj_k_rate': adj_k,
        'adj_bf':     adj_bf,
    }


# ==============================================================================
# LOAD GLOBAL DATA
# ==============================================================================
STATS_DB, MANAGER_DB       = get_pitcher_stats()
SAVANT_DB, SAVANT_NAMES    = fetch_savant_data()
TEAM_K_DB, TEAM_GAMES_DB   = get_team_k_rates()
vegas_lines                = fetch_automated_vegas_odds(api_key)


# ==============================================================================
# MAIN UI
# ==============================================================================
st.title("🔥 Underdog Quant AI — Strikeout Engine v2.1")
st.caption(
    "Lineup Hand Splits | Dynamic BF Cap | Fixed SwStr% Penalty | "
    "Sample-Weighted Opp K | Live Odds EV"
)

with st.sidebar:
    st.markdown("---")
    st.markdown("**🌀 Savant Data Status**")
    if SAVANT_DB:
        avg_swstr = np.mean([v['swstr']      for v in SAVANT_DB.values() if not math.isnan(v['swstr'])])
        avg_stuff = np.mean([v['stuff_plus'] for v in SAVANT_DB.values() if not math.isnan(v['stuff_plus'])])
        st.metric("Pitchers Loaded", len(SAVANT_DB))
        st.metric("Avg SwStr%",      f"{avg_swstr*100:.1f}%")
        st.metric("Avg Stuff+",      f"{avg_stuff:.0f}")
    else:
        st.warning("No Savant data — model using MLB API stats only")

try:
    games = requests.get(
        f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date_str}"
        f"&hydrate=probablePitcher,decisions,officials",
        timeout=8
    ).json().get('dates', [{}])[0].get('games', [])
except:
    games = []

if not games:
    st.info("No games found for selected date.")
    st.stop()

for game in games:
    home_name = game['teams']['home']['team']['name']
    away_name = game['teams']['away']['team']['name']
    home_team = TEAM_MAP.get(home_name, home_name)
    away_team = TEAM_MAP.get(away_name, away_name)

    h_sp_name = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
    a_sp_name = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
    h_sp_id   = game['teams']['home'].get('probablePitcher', {}).get('id')
    a_sp_id   = game['teams']['away'].get('probablePitcher', {}).get('id')

    if h_sp_name == 'TBD' or a_sp_name == 'TBD':
        continue

    api_ump = "Neutral"
    try:
        for off in game.get('officials', []):
            role = off.get('officialType', '')
            if 'Home Plate' in role or role == 'HP':
                name = off.get('official', {}).get('fullName', '')
                if name:
                    api_ump = name
                    break
    except:
        pass

    temp_f, wind_spd, wind_dir, azimuth = get_weather_for_date(home_team, target_date_str)

    with st.expander(
        f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | 🧑‍⚖️ {api_ump}"
    ):
        try:
            bx             = requests.get(
                f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/boxscore", timeout=5
            ).json()
            away_starters  = bx['teams']['away'].get('starters', [])
            home_starters  = bx['teams']['home'].get('starters', [])

            for pid in away_starters:
                player = bx['teams']['away']['players'].get(f'ID{pid}')
                if player and player['position']['abbreviation'] == 'P':
                    a_sp_name = player['person']['fullName']
                    a_sp_id   = pid
                    break

            for pid in home_starters:
                player = bx['teams']['home']['players'].get(f'ID{pid}')
                if player and player['position']['abbreviation'] == 'P':
                    h_sp_name = player['person']['fullName']
                    h_sp_id   = pid
                    break
        except:
            pass

        col1, col2 = st.columns(2)

        for side, sp_name, sp_id, team_abbr, opp_abbr, opp_is_home in [
            (col1, a_sp_name, a_sp_id, away_team, home_team, True),  
            (col2, h_sp_name, h_sp_id, home_team, away_team, False), 
        ]:
            with side:
                match = STATS_DB.get(sp_id, {
                    'K%': LEAGUE_K_RATE, 'BB%': LEAGUE_BB_RATE,
                    'Hand': 'R', 'GS': 0, 'IsGhost': True, 'TBF': 0,
                    'AvgBFperStart': LEAGUE_AVG_BF,
                })

                savant = SAVANT_DB.get(sp_id)
                if not savant:
                    matches = difflib.get_close_matches(
                        sp_name.title(), SAVANT_NAMES.keys(), n=1, cutoff=0.7
                    )
                    if matches:
                        savant = SAVANT_NAMES[matches[0]]
                        st.caption(f"*(Fuzzy matched Savant data: {matches[0]})*")
                    else:
                        savant = {}

                swstr      = savant.get('swstr',      LEAGUE_SWSTR_RATE)
                stuff_plus = savant.get('stuff_plus', 100.0)
                if math.isnan(swstr):      swstr      = LEAGUE_SWSTR_RATE
                if math.isnan(stuff_plus): stuff_plus = 100.0

                hand      = match.get('Hand', 'R')
                opp_data  = TEAM_K_DB.get(opp_abbr, {})
                opp_k_rate = opp_data.get(hand, 0.215)

                opp_k_rate, lineup_note = get_lineup_hand_adjustment(
                    game['gamePk'], opp_is_home, hand, opp_k_rate
                )

                opp_sample_games = TEAM_GAMES_DB.get(opp_abbr, 10)

                lp = get_live_pitcher_profile(sp_id, match, target_date_str)
                avg_bf_per_start = lp.get('avg_bf_per_start', match.get('AvgBFperStart', LEAGUE_AVG_BF))

                ump_options = [f"API Assigned ({api_ump})", "Neutral"] + WIDE_ZONE + TIGHT_ZONE
                ump_choice  = st.selectbox(f"Umpire Override ({sp_name}):",
                                           ump_options, key=f"ump_{team_abbr}_{sp_id}")
                final_ump   = api_ump if "API" in ump_choice else ump_choice

                res = run_monte_carlo_k(
                    sp_name, lp['k_rate'], lp['bb_rate'], opp_k_rate, swstr, stuff_plus,
                    lp['recent_k_trend'], home_team, temp_f, wind_spd, wind_dir, azimuth,
                    final_ump, MANAGER_DB.get(team_abbr, 0.0), lp['pitch_budget'],
                    lp['pitches_per_batter'], lp['starts_count'], sp_id,
                    avg_bf_per_start=avg_bf_per_start,   
                    opp_sample_games=opp_sample_games,   
                )

                # ── Display ────────────────────────────────────────────────────
                st.markdown(f"### {sp_name}")
                if match.get('IsGhost'):
                    st.warning("⚠️ Limited MLB data — projections use league averages")

                if lineup_note:
                    st.caption(lineup_note)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("K%",     f"{lp['k_rate']*100:.1f}%")
                m2.metric("SwStr%", f"{swstr*100:.1f}%", delta="savant" if savant else "est.")
                m3.metric("Stuff+", f"{stuff_plus:.0f}",
                          delta=f"{stuff_plus-100:+.0f}" if savant else None)
                m4.metric("Starts", lp['starts_count'])

                m5, m6, m7 = st.columns(3)
                m5.metric("P/Batter",  f"{lp['pitches_per_batter']:.2f}")
                m6.metric("P Budget",  f"{lp['pitch_budget']:.0f}")
                ump_label = ("Wide 🟢" if final_ump in WIDE_ZONE
                             else ("Tight 🔴" if final_ump in TIGHT_ZONE else "Neutral ⚪"))
                m7.metric("Ump Zone", ump_label)

                if abs(lp['recent_k_trend']) > 0.010:
                    trend_dir = "📈 Running HOT" if lp['recent_k_trend'] > 0 else "📉 Running COLD"
                    st.caption(f"{trend_dir}: {lp['recent_k_trend']*100:+.1f}% vs season K%")

                cap_status = ("✅ No BF cap" if avg_bf_per_start >= ACE_BF_THRESHOLD
                              else f"🔒 BF capped at 26.5 (avg {avg_bf_per_start:.1f}/start)")
                st.caption(cap_status)

                default_line = 5.5
                if sp_name in vegas_lines:
                    default_line = vegas_lines[sp_name]['Over']['line']

                line_val = st.number_input("UD Line (Ks):", value=default_line,
                                           step=0.5, min_value=0.5, max_value=15.0,
                                           key=f"l_{team_abbr}_{sp_id}")

                # ── Raw probabilities ──────────────────────────────────────────
                raw_h_prob   = float(np.sum(res['k_sims'] > line_val)) / 10000 * 100
                raw_l_prob   = 100.0 - raw_h_prob
                target_prob  = raw_h_prob if raw_h_prob > raw_l_prob else raw_l_prob
                pick_is_over = (target_prob == raw_h_prob)
                h_prob       = raw_h_prob
                l_prob       = raw_l_prob

                # ── Forward-testing penalties ──────────────────────────────────
                if pick_is_over:
                    if line_val <= 4.5 and stuff_plus == 100.0:
                        target_prob -= 15.0
                        res['factors'].append(
                            "⚠️ PENALTY: Trap Line (≤4.5) & Missing Stuff+ (-15% Prob)")

                    if swstr < SWSTR_PENALTY_THRESHOLD:
                        target_prob -= 15.0
                        res['factors'].append(
                            f"⚠️ PENALTY: Sub-{SWSTR_PENALTY_THRESHOLD*100:.1f}% SwStr% "
                            f"(below-avg whiff rate) (-15% Prob)")

                    h_prob = target_prob

                # ── EV ──────────────────────────────────────────────────────────
                if pick_is_over:
                    actual_price = (vegas_lines[sp_name]['Over']['price']
                                    if sp_name in vegas_lines else UD_IMPLIED_ODDS)
                else:
                    actual_price = (vegas_lines[sp_name]['Under']['price']
                                    if sp_name in vegas_lines else UD_IMPLIED_ODDS)

                payout     = american_to_payout(actual_price)
                ev         = (target_prob / 100.0) * payout - (1.0 - target_prob / 100.0)
                odds_label = f"@{actual_price:+d}" if actual_price != UD_IMPLIED_ODDS else f"@{UD_IMPLIED_ODDS} (UD default)"


                # ── Bet recommendation ─────────────────────────────────────────
                if (ev * 100) > 15.0:
                    if pick_is_over:
                        st.success(
                            f"🔥 BEST BET: OVER {line_val:.1f} ({h_prob:.1f}%) "
                            f"| EV: {ev*100:+.1f}% {odds_label}")
                    else:
                        if avg_bf_per_start >= ACE_BF_THRESHOLD:
                            st.warning(
                                f"⚠️ ELITE ACE WARNING: UNDER {line_val:.1f} ({l_prob:.1f}%) "
                                f"| EV: {ev*100:+.1f}% {odds_label} (Consider Passing)")
                        else:
                            st.success(
                                f"🔥 BEST BET: UNDER {line_val:.1f} ({l_prob:.1f}%) "
                                f"| EV: {ev*100:+.1f}% {odds_label}")
                elif target_prob > 55.1:
                    if pick_is_over:
                        st.info(
                            f"✅ OVER {line_val:.1f}: {h_prob:.1f}% "
                            f"| EV: {ev*100:+.1f}% {odds_label} (No Play: EV < 15%)")
                    else:
                        if avg_bf_per_start >= ACE_BF_THRESHOLD:
                            st.warning(
                                f"⚠️ ELITE ACE WARNING: UNDER {line_val:.1f} ({l_prob:.1f}%) "
                                f"| EV: {ev*100:+.1f}% {odds_label} (No Play: EV < 15%)")
                        else:
                            st.info(
                                f"✅ UNDER {line_val:.1f}: {l_prob:.1f}% "
                                f"| EV: {ev*100:+.1f}% {odds_label} (No Play: EV < 15%)")
                else:
                    st.warning(f"⚖️ NO PLAY: Edge too small (Max Prob: {target_prob:.1f}%)")

                p25, p50, p75 = np.percentile(res['k_sims'], [25, 50, 75])
                st.info(
                    f"📊 Median: {p50:.1f}K | 25th: {p25:.0f} | 75th: {p75:.0f} "
                    f"| BF: {res['adj_bf']:.1f}"
                )

                if st.button(f"💾 Log Play", key=f"log_{team_abbr}_{sp_id}"):
                    log_play_to_csv(
                        target_date_str, sp_name, team_abbr, opp_abbr,
                        line_val,
                        "OVER" if pick_is_over else "UNDER",
                        actual_price, target_prob, ev * 100,
                        p50, res['adj_bf'], final_ump, swstr, stuff_plus
                    )
                    st.success("✅ Logged to k_tracking_ledger.csv")

                with st.expander("🔬 Model Breakdown"):
                    for f in res['factors']:
                        st.caption(f"• {f}")
                    if savant:
                        st.caption("• 🌀 SwStr% source: Baseball Savant")
                        st.caption("• 💪 Stuff+ source: Baseball Savant")
                    else:
                        st.caption("• ⚠️ No Savant data — using league avg SwStr%/Stuff+")

                    st.caption(
                        f"• 📐 BF cap logic: avg {avg_bf_per_start:.1f} BF/start → "
                        f"{'no cap applied' if avg_bf_per_start >= ACE_BF_THRESHOLD else 'cap at 26.5'}"
                    )
                    st.caption(
                        f"• 📊 Opp K% sample weight: {min(opp_sample_games/30,1):.0%} "
                        f"({opp_sample_games} games played)"
                    )
                    st.caption(
                        f"• 💵 EV odds used: {odds_label}"
                    )
                    st.caption(
                        f"• 🌀 SwStr% penalty threshold: {SWSTR_PENALTY_THRESHOLD*100:.1f}% "
                        f"(league avg: {LEAGUE_SWSTR_RATE*100:.1f}%)"
                    )

                    st.markdown("**🔍 Savant Raw Debug**")
                    if savant:
                        st.json({
                            "pitcher_name": sp_name,
                            "swstr_raw":    savant.get('swstr'),
                            "swstr_pct":    f"{savant.get('swstr', 0)*100:.2f}%",
                            "stuff_plus":   savant.get('stuff_plus'),
                        })
                    else:
                        st.caption(f"❌ No Savant entry found for {sp_name}")


# ==============================================================================
# LEDGER VIEWER
# ==============================================================================
st.divider()
st.header("📊 K Betting Ledger")
if os.path.exists("k_tracking_ledger.csv"):
    df = pd.read_csv("k_tracking_ledger.csv")

    total = len(df)
    if total > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Plays", total)
        avg_ev   = df['EV_Pct'].mean()
        avg_prob = df['Probability_Pct'].mean()
        c2.metric("Avg EV%",      f"{avg_ev:+.1f}%")
        c3.metric("Avg Win Prob", f"{avg_prob:.1f}%")
        over_pct = (df['Pick'] == 'OVER').mean() * 100
        c4.metric("Over%",        f"{over_pct:.0f}%")

    if 'Result'    not in df.columns: df['Result']    = ""
    if 'Actual_Ks' not in df.columns: df['Actual_Ks'] = ""

    if st.button("🗑️ Clear Entire Ledger", type="primary"):
        if os.path.exists("k_tracking_ledger.csv"):
            os.remove("k_tracking_ledger.csv")
            st.success("Ledger completely cleared!")
            st.rerun()

    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

    st.markdown("**✏️ Update Results**")
    edited_df = st.data_editor(
        df[['Game_Date', 'Pitcher', 'Line', 'Pick', 'Median_Ks', 'Result', 'Actual_Ks']],
        column_config={
            "Result":    st.column_config.SelectboxColumn("Result", options=["", "W", "L", "PUSH"]),
            "Actual_Ks": st.column_config.NumberColumn("Actual Ks", min_value=0, max_value=20, step=1),
        },
        use_container_width=True,
        hide_index=True,
        key="ledger_editor",
    )
    if st.button("💾 Save Results to CSV"):
        df['Result']    = edited_df['Result'].values
        df['Actual_Ks'] = edited_df['Actual_Ks'].values
        df.to_csv("k_tracking_ledger.csv", index=False)
        st.success("✅ Results saved!")

        filled = df[df['Result'].isin(['W', 'L'])]
        if len(filled) > 0:
            wins          = (filled['Result'] == 'W').sum()
            total_graded  = len(filled)
            st.metric("Record", f"{wins}-{total_graded - wins}",
                      delta=f"{wins / total_graded * 100:.1f}% win rate")

    st.download_button(
        "📥 Download K Ledger CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="mlb_k_ledger.csv",
        mime="text/csv",
    )
else:
    st.info("No plays logged yet. Run the model and click 💾 Log Play to start tracking.")

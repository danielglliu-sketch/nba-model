import os
import math
import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from io import StringIO

# ==============================================================================
# CONSTANTS
# ==============================================================================
LEAGUE_K_RATE      = 0.225   # ~22.5% of BF result in strikeout
LEAGUE_BB_RATE     = 0.080
LEAGUE_AVG_BF      = 22.5
LEAGUE_SWSTR_RATE  = 0.108   # ~10.8% swinging strike rate league avg
UD_IMPLIED_ODDS    = -122    # Underdog break-even
SWSTR_TO_K_SLOPE   = 1.85    # regression coefficient: K% ≈ 0.45 + 1.85 × SwStr%
STUFF_K_PER_10     = 0.015   # +10 Stuff+ points ≈ +1.5% K rate

# K Park Factors — how much each park boosts/suppresses strikeouts
# Domed/sea-level parks help Ks; hitter-friendly / high-altitude parks suppress
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

# Umpires — effect on Ks is STRONGER than on outs (~2.5x)
# Wide zone = more called K3s, expanded chases; Tight = batters lay off, walk more
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
st.sidebar.title("🔥 K Autopilot v1")
api_key        = st.sidebar.text_input("🔑 The Odds API Key (Optional)", type="password")
selected_date  = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All caches cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("v1 K Master: SwStr% + Stuff+ | Umpire Enhanced | Underdog Optimized")

# ==============================================================================
# BASEBALL SAVANT — SwStr% + Stuff+
# Whiff rate (SwStr%) is the single best predictor of K rate.
# Stuff+ captures raw arsenal quality independent of results.
# ==============================================================================
@st.cache_data(ttl=86400)
def fetch_savant_data():
    """
    Returns dict: {mlb_player_id (int): {'swstr': float, 'stuff_plus': float}}
    Falls back gracefully if Savant is unreachable.
    """
    savant_db = {}
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; MLBQuantBot/1.0)'}
    base = "https://baseballsavant.mlb.com/leaderboard/custom"

    # --- SwStr% (whiff_percent) ---
    try:
        r = requests.get(base, params={
            'year': '2026', 'type': 'pitcher', 'filter': '', 'sort': '1',
            'sortDir': 'desc', 'min': '1', 'selections': 'whiff_percent',
            'player_type': 'pitcher', 'csv': 'true'
        }, headers=headers, timeout=10)
        df = pd.read_csv(StringIO(r.text))
        # column name varies slightly by year — normalize
        df.columns = [c.lower().strip() for c in df.columns]
        pid_col    = next((c for c in df.columns if 'player_id' in c or c == 'pitcher'), None)
        swstr_col  = next((c for c in df.columns if 'whiff' in c), None)
        if pid_col and swstr_col:
            for _, row in df.iterrows():
                try:
                    pid   = int(row[pid_col])
                    swstr = float(row[swstr_col])
                    # Savant returns as percentage (e.g. 12.3 = 12.3%)
                    savant_db[pid] = {'swstr': swstr / 100.0 if swstr > 1 else swstr,
                                      'stuff_plus': 100.0}
                except: pass
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
        if pid_col and stuff_col:
            for _, row in df.iterrows():
                try:
                    pid   = int(row[pid_col])
                    stuff = float(row[stuff_col])
                    if pid in savant_db:
                        savant_db[pid]['stuff_plus'] = stuff
                    else:
                        savant_db[pid] = {'swstr': LEAGUE_SWSTR_RATE, 'stuff_plus': stuff}
                except: pass
    except Exception as e:
        st.sidebar.warning(f"⚠️ Savant Stuff+ unavailable: {e}")

    loaded = len(savant_db)
    if loaded > 0:
        st.sidebar.success(f"✅ Savant data: {loaded} pitchers loaded")
    return savant_db


# ==============================================================================
# VEGAS ODDS — K Props
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_automated_vegas_odds(api_key):
    if not api_key or api_key == "YOUR_API_KEY": return {}
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
                            odds_db[name] = {'Over': {'line': 5.5, 'price': -115},
                                             'Under': {'line': 5.5, 'price': -115}}
                        if outcome['name'] == 'Over':
                            odds_db[name]['Over'] = {'line': outcome['point'], 'price': outcome['price']}
                        elif outcome['name'] == 'Under':
                            odds_db[name]['Under'] = {'line': outcome['point'], 'price': outcome['price']}
        return odds_db
    except: return {}


# ==============================================================================
# WEATHER — Open-Meteo (free, no key required)
# Wind matters LESS for Ks than for outs but high temp = looser pitching arm
# ==============================================================================
@st.cache_data(ttl=3600)
def get_weather_for_date(team_abbr, date_str):
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords: return 72.0, 5.0, 180.0, 180.0
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
        temp_f   = r['hourly']['temperature_2m'][idx] * 9/5 + 32
        wind_spd = r['hourly']['windspeed_10m'][idx] * 0.621371
        wind_dir = r['hourly']['winddirection_10m'][idx]
        return temp_f, wind_spd, wind_dir, float(azimuth)
    except:
        return 72.0, 5.0, 180.0, 180.0


# ==============================================================================
# MLB API — Team K rates vs L/R (opponent quality adjustment)
# ==============================================================================
@st.cache_data(ttl=86400)
def get_team_k_rates():
    """
    Returns {team_abbr: {'L': k_rate, 'R': k_rate}}
    Higher = team strikes out more (good for the pitcher prop).
    """
    team_k = {}
    try:
        r = requests.get(
            "https://statsapi.mlb.com/api/v1/teams/stats",
            params={'stats': 'season', 'group': 'hitting',
                    'season': '2026', 'gameType': 'R'},
            timeout=8
        ).json()
        for rec in r.get('stats', [{}])[0].get('splits', []):
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', ''), '')
            if not abbr: continue
            s  = rec['stat']
            ab = s.get('atBats', 0)
            so = s.get('strikeOuts', 0)
            if ab > 0:
                team_k[abbr] = {'L': so / ab, 'R': so / ab}  # same for both until splits available
    except: pass
    return team_k


# ==============================================================================
# MLB API — Pitcher Season Stats (Bayesian-shrunk K rate)
# ==============================================================================
def get_shrinkage_prior(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        days_in = (d - datetime(d.year, 3, 28)).days
        return 20 if days_in < 30 else (10 if days_in < 60 else 5)
    except: return 15

@st.cache_data(ttl=86400)
def get_pitcher_stats():
    pitcher_db, manager_db = {}, {}
    prior = get_shrinkage_prior(datetime.now().strftime('%Y-%m-%d'))
    try:
        # Handedness map
        people = requests.get(
            "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10
        ).json()
        hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in people.get('people', [])}

        # Career K% for Bayesian blend
        career_k = {}
        try:
            cr = requests.get(
                "https://statsapi.mlb.com/api/v1/stats?stats=career&group=pitching&playerPool=ALL&season=2026&limit=2000",
                timeout=15
            ).json()
            for rec in cr['stats'][0]['splits']:
                pid = rec['player']['id']
                s   = rec['stat']
                tbf = s.get('battersFaced', 0)
                so  = s.get('strikeOuts', 0)
                if tbf > 0:
                    career_k[pid] = so / tbf
        except: pass

        # Season stats
        sr = requests.get(
            "https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerPool=ALL&season=2026&limit=2000",
            timeout=15
        ).json()
        l_tbf = l_gs = 0
        for rec in sr['stats'][0]['splits']:
            name  = rec['player']['fullName']
            pid   = rec['player']['id']
            s     = rec['stat']
            abbr  = TEAM_MAP.get(rec.get('team', {}).get('name', 'Unknown'), 'Unknown')
            tbf   = s.get('battersFaced', 0)
            so    = s.get('strikeOuts', 0)
            bb    = s.get('baseOnBalls', 0)
            gs    = s.get('gamesStarted', 0)
            if tbf == 0: continue

            # Bayesian shrinkage toward league K rate
            shrunk_k = (so + LEAGUE_K_RATE * prior) / (tbf + prior)

            # Blend with career if enough data
            if pid in career_k:
                w        = min(tbf / 300.0, 0.70)
                shrunk_k = shrunk_k * w + career_k[pid] * (1.0 - w)

            pitcher_db[pid] = {
                'Name':        name,
                'K%':          shrunk_k,
                'BB%':         (bb + LEAGUE_BB_RATE * prior) / (tbf + prior),
                'Hand':        hand_map.get(pid, 'R'),
                'BF_per_Start': max(16.0, min(28.0, (tbf + LEAGUE_AVG_BF * 2) / (gs + 2))) if gs > 0 else LEAGUE_AVG_BF,
                'GS':          gs,
                'IsGhost':     tbf < 10,
                'TBF':         tbf,
            }

            if gs > 0 and abbr != 'Unknown':
                if abbr not in manager_db: manager_db[abbr] = {'tbf': 0, 'gs': 0}
                manager_db[abbr]['tbf'] += tbf
                manager_db[abbr]['gs']  += gs
                l_tbf += tbf; l_gs += gs

        l_avg_bf = l_tbf / l_gs if l_gs > 0 else LEAGUE_AVG_BF
        manager_db = {t: max(-3.0, min(3.0, (v['tbf'] / v['gs']) - l_avg_bf))
                      for t, v in manager_db.items() if v['gs'] > 0}

    except Exception as e:
        st.sidebar.error(f"MLB API error: {e}")
        return {}, {}

    return pitcher_db, manager_db


# ==============================================================================
# LIVE PITCHER GAME LOG — pitch budget, P/BF, recent K trend
# ==============================================================================
@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback, target_date_str):
    profile = {
        'k_rate':           fallback['K%'],
        'bb_rate':          fallback['BB%'],
        'pitch_budget':     95.0,
        'pitches_per_batter': 4.1,
        'starts_count':     fallback['GS'],
        'is_ghost':         fallback['IsGhost'],
        'recent_k_trend':   0.0,   # rolling K/start vs season avg
    }
    if not player_id: return profile
    try:
        url    = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season=2026"
        splits = requests.get(url, timeout=6).json().get('stats', [{}])[0].get('splits', [])
        starts = [s for s in splits if s['stat'].get('gamesStarted', 0) == 1]
        if starts:
            profile['starts_count'] = len(starts)

            # Pitch budget (from peak of last 3 starts)
            recent_pitches = [s['stat'].get('numberOfPitches', 0) for s in starts[:3]]
            peak           = max(recent_pitches) if recent_pitches else 0
            profile['pitch_budget'] = float(peak) if 65 <= peak <= 120 else 95.0

            # Pitches per batter (last 5)
            t_p = sum(s['stat'].get('numberOfPitches', 0) for s in starts[:5])
            t_b = sum(s['stat'].get('battersFaced', 0)    for s in starts[:5])
            if t_b > 0:
                profile['pitches_per_batter'] = max(3.5, t_p / t_b)

            # Recent K trend: avg Ks last 3 starts vs season rate
            if len(starts) >= 3:
                recent_k  = sum(s['stat'].get('strikeOuts', 0) for s in starts[:3]) / 3
                recent_bf = sum(s['stat'].get('battersFaced', 0) for s in starts[:3]) / 3
                if recent_bf > 0:
                    recent_rate           = recent_k / recent_bf
                    profile['recent_k_trend'] = recent_rate - fallback['K%']
    except: pass
    return profile


# ==============================================================================
# CSV LEDGER
# ==============================================================================
def log_play_to_csv(date, pitcher, team, opponent, line, pick, odds, prob, ev,
                    median_k, bf_proj, umpire_name, swstr, stuff_plus):
    fname      = "k_tracking_ledger.csv"
    file_exists = os.path.isfile(fname)
    data = {
        "Game_Date":       date,
        "Timestamp_Logged": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Pitcher":         pitcher,
        "Team":            team,
        "Opponent":        opponent,
        "Line":            line,
        "Pick":            pick,
        "Implied_Odds":    odds,
        "Probability_Pct": round(prob, 2),
        "EV_Pct":          round(ev, 2),
        "Median_Ks":       round(median_k, 2),
        "Projected_BF":    round(bf_proj, 2),
        "SwStr_Pct":       round(swstr * 100, 1),
        "Stuff_Plus":      round(stuff_plus, 1),
        "Umpire":          umpire_name,
        "Platform":        "Underdog",
        "Result":          "",   # fill in manually: W, L, or PUSH
        "Actual_Ks":       "",   # fill in actual K total after game
    }
    pd.DataFrame([data]).to_csv(fname, mode='a', header=not file_exists, index=False)


# ==============================================================================
# MONTE CARLO ENGINE — Strikeouts
#
# The core change from the outs model:
#   k_sims = np.random.binomial(dynamic_bf, game_k_rates)
#
# New inputs:
#   swstr_rate  — swinging strike rate (from Savant); strongest K predictor
#   stuff_plus  — Savant Stuff+ (arsenal quality independent of results)
#   opp_k_rate  — opponent team K% (how often they strike out)
#   recent_k_trend — last-3-start K rate vs season avg
#
# Umpire effect is LARGER here than in the outs model (~2.5% vs ~1.2%)
# because wide zones directly produce called K3s and expand chases.
# ==============================================================================
def run_monte_carlo_k(sp_name, base_k_rate, bb_rate, opp_k_rate, swstr_rate,
                      stuff_plus, recent_k_trend, park, temp_f, wind_speed,
                      wind_dir, azimuth, umpire, manager_shift,
                      pitch_budget, pitches_per_batter, starts_count,
                      num_sims=10000):
    factors = []

    # ── 1. Base K rate (already Bayesian-shrunk from season stats) ──────────
    adj_k = base_k_rate

    # ── 2. SwStr% adjustment — best single predictor ─────────────────────────
    # Expected K% from SwStr% alone: K% ≈ 0.45 + 1.85 × SwStr%
    # We use the DELTA between pitcher's SwStr% and league avg as the edge
    swstr_delta = swstr_rate - LEAGUE_SWSTR_RATE
    swstr_adj   = swstr_delta * SWSTR_TO_K_SLOPE
    adj_k      += swstr_adj * 0.60   # 60% weight — blended with observed K%
    if abs(swstr_adj) > 0.005:
        direction = "⬆️" if swstr_adj > 0 else "⬇️"
        factors.append(f"🌀 SwStr%: {swstr_rate*100:.1f}% {direction} ({swstr_adj*100:+.1f}% K adj)")

    # ── 3. Stuff+ adjustment ─────────────────────────────────────────────────
    stuff_adj = (stuff_plus - 100.0) * (STUFF_K_PER_10 / 10.0)
    adj_k    += stuff_adj * 0.40   # 40% weight — arsenal quality signal
    if abs(stuff_adj) > 0.003:
        factors.append(f"💪 Stuff+: {stuff_plus:.0f} ({stuff_adj*100:+.1f}% K adj)")

    # ── 4. Opponent K% adjustment ────────────────────────────────────────────
    # If the opposing lineup K's more than average, pitcher's K rate gets a boost
    league_avg_opp_k = 0.215   # league avg team K/AB
    # Guard: early-season API returns 0 atBats → division by zero → inf/NaN cascade
    if not (opp_k_rate and math.isfinite(opp_k_rate) and opp_k_rate > 0):
        opp_k_rate = league_avg_opp_k
    opp_adj  = (opp_k_rate - league_avg_opp_k) / league_avg_opp_k * 0.12
    opp_adj  = float(np.clip(opp_adj, -0.15, 0.15))   # cap so no single factor blows up adj_k
    adj_k   *= (1.0 + opp_adj)
    factors.append(f"👥 Opp K%: {opp_k_rate*100:.1f}% ({opp_adj*100:+.1f}%)")

    # ── 5. Recent K trend (last 3 starts) ────────────────────────────────────
    # 25% weight — recency signal without overreacting to small samples
    adj_k += recent_k_trend * 0.25
    if abs(recent_k_trend) > 0.010:
        factors.append(f"📈 Recent K trend: {recent_k_trend*100:+.1f}% vs season avg")

    # ── 6. Umpire — STRONGER effect on Ks than on outs ───────────────────────
    # Wide zone → called K3s, expanded chases = +2.5% K rate
    # Tight zone → batters lay off borderline pitches, more walks = -3.0% K rate
    if umpire in WIDE_ZONE:
        adj_k += 0.025
        factors.append("🧑‍⚖️ Ump: Wide Zone (+2.5% K rate)")
    elif umpire in TIGHT_ZONE:
        adj_k -= 0.030
        factors.append("🧑‍⚖️ Ump: Tight Zone (-3.0% K rate)")

    # ── 7. Park factor ────────────────────────────────────────────────────────
    park_pf = K_PARK_FACTORS.get(park, 1.0)
    adj_k  *= park_pf
    if park_pf != 1.0:
        factors.append(f"🏟️ Park: {park} (×{park_pf:.2f})")

    # ── 8. Temperature — cold air = stiffer arm = fewer Ks ───────────────────
    if temp_f < 45:
        adj_k -= 0.012
        factors.append(f"🥶 Cold ({temp_f:.0f}°F): -1.2% K adj")
    elif temp_f > 85:
        adj_k += 0.006
        factors.append(f"☀️ Hot ({temp_f:.0f}°F): +0.6% K adj")

    # ── 9. BF projection (same volume model as outs engine) ─────────────────
    raw_bf  = (pitch_budget / max(pitches_per_batter, 3.5)) + 2.0 + (manager_shift * 0.5)
    adj_bf  = min(raw_bf, 26.5)
    # Elite workhorses bypass the BF cap
    if sp_name in ["Logan Gilbert","Zack Wheeler","Corbin Burnes","Gerrit Cole",
                   "Spencer Strider","Dylan Cease","Kevin Gausman"]:
        adj_bf = raw_bf
    factors.append(f"🎯 Target BF: {adj_bf:.1f} | Adj K%: {adj_k*100:.1f}%")

    # ── 10. Monte Carlo simulation ────────────────────────────────────────────
    # Final NaN/inf guard — any upstream factor that produced NaN falls back to league avg
    if not math.isfinite(adj_k):
        adj_k = LEAGUE_K_RATE
    adj_k  = float(np.clip(adj_k, 0.05, 0.55))

    k_std  = 0.040 if starts_count < 5 else 0.032   # K rate is more stable than out rate
    game_k_rates = np.clip(np.random.normal(adj_k, k_std, num_sims), 0.05, 0.55)
    # np.clip passes NaN through silently — replace any survivors with adj_k
    game_k_rates = np.where(np.isfinite(game_k_rates), game_k_rates, adj_k)

    # BF variance tied to performance (throwing well → more BF opportunity)
    perf_z    = (game_k_rates - adj_k) / k_std
    bf_mod    = np.where(perf_z > 0, perf_z * 2.5, perf_z * 1.8)
    dynamic_bf = np.clip(
        np.round(np.random.normal(adj_bf + bf_mod, 1.8, num_sims)).astype(int),
        9, 30
    )

    # THE KEY LINE — binomial K draws per simulated start
    k_sims = np.random.binomial(dynamic_bf, game_k_rates)

    return {
        'k_sims':    k_sims,
        'factors':   factors,
        'adj_k_rate': adj_k,
        'adj_bf':    adj_bf,
    }


# ==============================================================================
# LOAD GLOBAL DATA
# ==============================================================================
STATS_DB, MANAGER_DB = get_pitcher_stats()
SAVANT_DB            = fetch_savant_data()
TEAM_K_DB            = get_team_k_rates()
vegas_lines          = fetch_automated_vegas_odds(api_key)


# ==============================================================================
# MAIN UI
# ==============================================================================
st.title("🔥 Underdog Quant AI — Strikeout Engine v1")
st.caption("SwStr% + Stuff+ integrated | Umpire K-zone enhanced | Bayesian K-rate shrinkage")

# Sidebar Savant summary
with st.sidebar:
    st.markdown("---")
    st.markdown("**🌀 Savant Data Status**")
    if SAVANT_DB:
        avg_swstr  = np.mean([v['swstr']      for v in SAVANT_DB.values()])
        avg_stuff  = np.mean([v['stuff_plus'] for v in SAVANT_DB.values()])
        st.metric("Pitchers Loaded", len(SAVANT_DB))
        st.metric("Avg SwStr%",      f"{avg_swstr*100:.1f}%")
        st.metric("Avg Stuff+",      f"{avg_stuff:.0f}")
    else:
        st.warning("No Savant data — model using MLB API stats only")

# Fetch today's schedule
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

    if h_sp_name == 'TBD' or a_sp_name == 'TBD': continue

    # Umpire from API
    api_ump = "Neutral"
    try:
        for off in game.get('officials', []):
            role = off.get('officialType', '')
            if 'Home Plate' in role or role == 'HP':
                name = off.get('official', {}).get('fullName', '')
                if name:
                    api_ump = name
                    break
    except: pass

    temp_f, wind_spd, wind_dir, azimuth = get_weather_for_date(home_team, target_date_str)

    with st.expander(f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name}) | 🧑‍⚖️ {api_ump}"):
        col1, col2 = st.columns(2)

        for side, sp_name, sp_id, team_abbr, opp_abbr in [
            (col1, a_sp_name, a_sp_id, away_team, home_team),
            (col2, h_sp_name, h_sp_id, home_team, away_team)
        ]:
            with side:
                # Pitcher base stats
                match = STATS_DB.get(sp_id, {
                    'K%': LEAGUE_K_RATE, 'BB%': LEAGUE_BB_RATE,
                    'Hand': 'R', 'GS': 0, 'IsGhost': True, 'TBF': 0
                })

                # Savant data
                savant    = SAVANT_DB.get(sp_id, {})
                swstr     = savant.get('swstr',      LEAGUE_SWSTR_RATE)
                stuff_plus= savant.get('stuff_plus', 100.0)

                # Opponent K rate (vs pitcher handedness)
                hand      = match.get('Hand', 'R')
                opp_data  = TEAM_K_DB.get(opp_abbr, {})
                opp_k_rate= opp_data.get(hand, 0.215)

                # Live game-log profile
                lp = get_live_pitcher_profile(sp_id, match, target_date_str)

                # Umpire override
                ump_options = [f"API Assigned ({api_ump})", "Neutral"] + WIDE_ZONE + TIGHT_ZONE
                ump_choice  = st.selectbox(f"Umpire Override ({sp_name}):",
                                           ump_options, key=f"ump_{team_abbr}_{sp_id}")
                final_ump   = api_ump if "API" in ump_choice else ump_choice

                # Run simulation
                res = run_monte_carlo_k(
                    sp_name,
                    lp['k_rate'],
                    lp['bb_rate'],
                    opp_k_rate,
                    swstr,
                    stuff_plus,
                    lp['recent_k_trend'],
                    home_team,
                    temp_f, wind_spd, wind_dir, azimuth,
                    final_ump,
                    MANAGER_DB.get(team_abbr, 0.0),
                    lp['pitch_budget'],
                    lp['pitches_per_batter'],
                    lp['starts_count'],
                )

                # ── Display ───────────────────────────────────────────────
                st.markdown(f"### {sp_name}")

                # Ghost pitcher warning
                if match.get('IsGhost'):
                    st.warning("⚠️ Limited MLB data — projections use league averages")

                # Core metrics (K-focused)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("K%",        f"{lp['k_rate']*100:.1f}%")
                m2.metric("SwStr%",    f"{swstr*100:.1f}%",
                          delta="savant" if sp_id in SAVANT_DB else "est.")
                m3.metric("Stuff+",    f"{stuff_plus:.0f}",
                          delta=f"{stuff_plus-100:+.0f}" if sp_id in SAVANT_DB else None)
                m4.metric("Starts",    lp['starts_count'])

                m5, m6, m7 = st.columns(3)
                m5.metric("P/Batter",  f"{lp['pitches_per_batter']:.2f}")
                m6.metric("P Budget",  f"{lp['pitch_budget']:.0f}")
                ump_label = ("Wide 🟢" if final_ump in WIDE_ZONE
                             else ("Tight 🔴" if final_ump in TIGHT_ZONE else "Neutral ⚪"))
                m7.metric("Ump Zone", ump_label)

                # K trend indicator
                if abs(lp['recent_k_trend']) > 0.010:
                    trend_dir = "📈 Running HOT" if lp['recent_k_trend'] > 0 else "📉 Running COLD"
                    st.caption(f"{trend_dir}: {lp['recent_k_trend']*100:+.1f}% vs season K%")

                # ── Line input + EV ───────────────────────────────────────
                # Pull from Vegas / Odds API if available; default 5.5
                default_line = 5.5
                if sp_name in vegas_lines:
                    default_line = vegas_lines[sp_name]['Over']['line']

                line_val = st.number_input("UD Line (Ks):", value=default_line,
                                           step=0.5, min_value=0.5, max_value=15.0,
                                           key=f"l_{team_abbr}_{sp_id}")

                h_prob = float(np.sum(res['k_sims'] > line_val)) / 10000 * 100
                l_prob = 100.0 - h_prob

                # EV locked to -122 break-even (Underdog standard)
                target_prob = h_prob if h_prob > l_prob else l_prob
                ev = ((target_prob / 100.0) * (100.0 / 122.0)) - (1.0 - target_prob / 100.0)

                # Signal threshold: 55.1% (meaningful edge over -122 implied 45%)
                if h_prob > 55.1:
                    if line_val < 4.5:
                        st.warning(f"⚠️ LOW LINE FILTER: OVER {line_val:.1f} ({h_prob:.1f}%) — line below 4.5 minimum, likely model noise not a real edge")
                    else:
                        st.success(f"🔥 OVER {line_val:.1f}: {h_prob:.1f}% | EV: {ev*100:+.1f}%")
                elif l_prob > 55.1:
                    st.error(f"❄️ UNDER {line_val:.1f}: {l_prob:.1f}% | EV: {ev*100:+.1f}%")
                else:
                    st.warning(f"⚖️ NO PLAY: {max(h_prob, l_prob):.1f}% (need >55.1%)")

                # Distribution summary
                p25, p50, p75 = np.percentile(res['k_sims'], [25, 50, 75])
                st.info(f"📊 Median: {p50:.1f}K | 25th: {p25:.0f} | 75th: {p75:.0f} | BF: {res['adj_bf']:.1f}")

                # Log button
                if st.button(f"💾 Log Play", key=f"log_{team_abbr}_{sp_id}"):
                    log_play_to_csv(
                        target_date_str, sp_name, team_abbr, opp_abbr,
                        line_val,
                        "OVER" if h_prob > l_prob else "UNDER",
                        UD_IMPLIED_ODDS, target_prob, ev * 100,
                        p50, res['adj_bf'], final_ump, swstr, stuff_plus
                    )
                    st.success("✅ Logged to k_tracking_ledger.csv")

                # Model breakdown
                with st.expander("🔬 Model Breakdown"):
                    for f in res['factors']:
                        st.caption(f"• {f}")
                    if sp_id in SAVANT_DB:
                        st.caption(f"• 🌀 SwStr% source: Baseball Savant (live)")
                        st.caption(f"• 💪 Stuff+ source: Baseball Savant (live)")
                    else:
                        st.caption("• ⚠️ No Savant data for this pitcher — using league avg SwStr%/Stuff+")
                    # Savant raw debug — use this to verify correct column parsing
                    st.markdown("**🔍 Savant Raw Debug**")
                    raw_savant = SAVANT_DB.get(sp_id, {})
                    if raw_savant:
                        st.json({
                            "player_id":   sp_id,
                            "swstr_raw":   raw_savant.get('swstr'),
                            "swstr_pct":   f"{raw_savant.get('swstr', 0)*100:.2f}%",
                            "stuff_plus":  raw_savant.get('stuff_plus'),
                        })
                    else:
                        st.caption(f"❌ No Savant entry found for player_id={sp_id} — check if ID matches Savant's player_id column")

# ==============================================================================
# LEDGER VIEWER
# ==============================================================================
st.divider()
st.header("📊 K Betting Ledger")
if os.path.exists("k_tracking_ledger.csv"):
    df = pd.read_csv("k_tracking_ledger.csv")

    # Summary stats
    total = len(df)
    if total > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Plays", total)
        avg_ev  = df['EV_Pct'].mean()
        avg_prob = df['Probability_Pct'].mean()
        c2.metric("Avg EV%", f"{avg_ev:+.1f}%")
        c3.metric("Avg Win Prob", f"{avg_prob:.1f}%")
        over_pct = (df['Pick'] == 'OVER').mean() * 100
        c4.metric("Over%", f"{over_pct:.0f}%")

    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

    # Result entry — edit W/L/PUSH and actual Ks then save back to CSV
    st.markdown("**✏️ Update Results**")
    edited_df = st.data_editor(
        df[['Game_Date','Pitcher','Line','Pick','Median_Ks','Result','Actual_Ks']],
        column_config={
            "Result":     st.column_config.SelectboxColumn("Result", options=["", "W", "L", "PUSH"]),
            "Actual_Ks":  st.column_config.NumberColumn("Actual Ks", min_value=0, max_value=20, step=1),
        },
        use_container_width=True,
        hide_index=True,
        key="ledger_editor",
    )
    if st.button("💾 Save Results to CSV"):
        df['Result']     = edited_df['Result'].values
        df['Actual_Ks']  = edited_df['Actual_Ks'].values
        df.to_csv("k_tracking_ledger.csv", index=False)
        st.success("✅ Results saved!")
        # Show quick W/L summary if results exist
        filled = df[df['Result'].isin(['W','L'])]
        if len(filled) > 0:
            wins  = (filled['Result'] == 'W').sum()
            total = len(filled)
            st.metric("Record", f"{wins}-{total-wins}", delta=f"{wins/total*100:.1f}% win rate")
    st.download_button(
        "📥 Download K Ledger CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="mlb_k_ledger.csv",
        mime="text/csv"
    )
else:
    st.info("No plays logged yet. Run the model and click 💾 Log Play to start tracking.")

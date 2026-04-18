import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ==============================================================================
# PAGE SETUP
# ==============================================================================
st.set_page_config(page_title="MLB Quant AI - Outs Engine v2", page_icon="⚾", layout="wide")

st.sidebar.title("🤖 Outs Autopilot v2")
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.sidebar.success("All caches cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("v2: Pitch Count Model | K% Integration | Rest/Fatigue | Career Blending | Decoupled BF Variance")

# ==============================================================================
# STATIC DATABASES
# ==============================================================================

STADIUM_COORDS = {
    'ARI': (33.445, -112.067), 'ATL': (33.891, -84.468), 'BAL': (39.284, -76.622),
    'BOS': (42.346, -71.097), 'CHC': (41.948, -87.655), 'CHW': (41.830, -87.634),
    'CIN': (39.097, -84.507), 'CLE': (41.496, -81.685), 'COL': (39.756, -104.994),
    'DET': (42.339, -83.048), 'HOU': (29.757, -95.355), 'KC':  (39.051, -94.481),
    'LAA': (33.800, -117.883), 'LAD': (34.073, -118.240), 'MIA': (25.778, -80.220),
    'MIL': (43.028, -87.971), 'MIN': (44.981, -93.278), 'NYM': (40.757, -73.845),
    'NYY': (40.830, -73.926), 'OAK': (37.751, -122.201), 'PHI': (39.906, -75.166),
    'PIT': (40.447, -80.006), 'SD':  (32.707, -117.157), 'SF':  (37.778, -122.389),
    'SEA': (47.591, -122.332), 'STL': (38.622, -90.193), 'TB':  (27.768, -82.653),
    'TEX': (32.751, -97.082), 'TOR': (43.641, -79.389), 'WSH': (38.873, -77.007),
}

# Updated 2025/26 - removed retired umpires (e.g. Angel Hernandez retired after 2023)
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

# Park factors for pitcher outs — MIL and KC now included
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

# League-average constants
LEAGUE_OUT_RATE = 0.68
LEAGUE_K_RATE   = 0.225
LEAGUE_BB_RATE  = 0.080
LEAGUE_AVG_BF   = 22.5


# ==============================================================================
# HELPER: ADAPTIVE SHRINKAGE PRIOR
# ==============================================================================
def get_shrinkage_prior(date_str: str) -> int:
    """
    Return a heavier Bayesian prior early in the season when sample sizes are tiny.
    April → 150, May → 100, June+ → 50
    """
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        days_in = (d - datetime(d.year, 3, 28)).days
        if days_in < 30:  return 150
        elif days_in < 60: return 100
        else:              return 50
    except:
        return 100


# ==============================================================================
# DATA FETCHERS
# ==============================================================================

@st.cache_data(ttl=3600)
def get_weather_for_date(team_abbr: str, date_str: str):
    """Returns (temp_f, wind_mph) for the stadium on the given date."""
    coords = STADIUM_COORDS.get(team_abbr)
    if not coords:
        return 70.0, 0.0
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={coords[0]}&longitude={coords[1]}"
            f"&start_date={date_str}&end_date={date_str}"
            f"&daily=temperature_2m_max,wind_speed_10m_max"
            f"&timezone=auto"
        )
        data = requests.get(url, timeout=5).json()
        temp_f = (data['daily']['temperature_2m_max'][0] * 9 / 5) + 32
        wind   = data['daily'].get('wind_speed_10m_max', [0])[0]
        return float(temp_f), float(wind)
    except:
        return 70.0, 0.0


@st.cache_data(ttl=86400)
def get_automated_team_splits() -> dict:
    """
    Pull 2026 team hitting splits vs LHP / RHP.
    Returns: { 'NYY': { 'L': {'out_rate': 0.68, 'k_rate': 0.22}, 'R': {...} }, ... }
    """
    splits: dict = {}
    for hand_code, api_code in [('L', 'vL'), ('R', 'vR')]:
        try:
            url = (
                f"https://statsapi.mlb.com/api/v1/teams/stats"
                f"?season=2026&group=hitting&stats=statSplits&sitCode={api_code}"
            )
            data = requests.get(url, timeout=10).json()
            for rec in data['stats'][0]['splits']:
                abbr = TEAM_MAP.get(rec['team']['name'], rec['team']['name'])
                if abbr not in splits:
                    splits[abbr] = {}
                s  = rec['stat']
                pa = max(s.get('plateAppearances', 1), 1)
                splits[abbr][hand_code] = {
                    'out_rate': 1.0 - (s.get('hits', 0) + s.get('baseOnBalls', 0)) / pa,
                    'k_rate':   s.get('strikeOuts', 0) / pa,
                }
        except:
            pass
    return splits


SPLITS_DB = get_automated_team_splits()


@st.cache_data(ttl=86400)
def get_pitcher_and_manager_stats():
    """
    Pull 2026 season + career pitching stats.
    Returns (pitcher_db, manager_db).

    pitcher_db keyed by MLB player ID (int).
    Fixes vs v1:
      - Ghost detection uses TBF < 10, NOT BF_per_Start == 23
      - Career blending: 70% season / 30% career once season sample is large enough
      - K% added with shrinkage
      - Adaptive prior based on current date
    """
    pitcher_db:  dict = {}
    team_sp_agg: dict = {}
    prior = get_shrinkage_prior(datetime.now().strftime('%Y-%m-%d'))

    try:
        # Handedness map
        people_resp = requests.get(
            "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10
        ).json()
        hand_map = {
            p['id']: p.get('pitchHand', {}).get('code', 'R')
            for p in people_resp.get('people', [])
        }

        # Career stats for blending
        career_lookup: dict = {}
        try:
            career_resp = requests.get(
                "https://statsapi.mlb.com/api/v1/stats"
                "?stats=career&group=pitching&playerPool=ALL&season=2026&limit=2000",
                timeout=15,
            ).json()
            for rec in career_resp['stats'][0]['splits']:
                pid  = rec['player']['id']
                s    = rec['stat']
                ctbf = s.get('battersFaced', 0)
                if ctbf > 0:
                    career_lookup[pid] = {
                        'out_rate': (ctbf - s.get('baseOnBalls', 0) - s.get('hits', 0)) / ctbf,
                        'k_rate':   s.get('strikeOuts', 0) / ctbf,
                        'tbf':      ctbf,
                    }
        except:
            pass

        # 2026 season stats
        season_resp = requests.get(
            "https://statsapi.mlb.com/api/v1/stats"
            "?stats=season&group=pitching&playerPool=ALL&season=2026&limit=2000",
            timeout=15,
        ).json()

        league_tbf = league_gs = 0

        for rec in season_resp['stats'][0]['splits']:
            name = rec['player']['fullName']
            pid  = rec['player']['id']
            abbr = TEAM_MAP.get(rec.get('team', {}).get('name', 'Unknown'), 'Unknown')
            s    = rec['stat']

            tbf = s.get('battersFaced', 0)
            bb  = s.get('baseOnBalls', 0)
            h   = s.get('hits', 0)
            so  = s.get('strikeOuts', 0)
            gs  = s.get('gamesStarted', 0)
            gp  = s.get('gamesPlayed', 0)

            if tbf == 0:
                continue

            # ----- Bayesian shrinkage toward league average -----
            shrunk_out = ((tbf - bb - h) + LEAGUE_OUT_RATE * prior) / (tbf + prior)
            shrunk_k   = (so               + LEAGUE_K_RATE  * prior) / (tbf + prior)
            shrunk_bb  = (bb               + LEAGUE_BB_RATE * prior) / (tbf + prior)

            # ----- Career blend (only when career sample > 500 TBF) -----
            if pid in career_lookup and career_lookup[pid]['tbf'] > 500:
                c = career_lookup[pid]
                # Weight current season by how much data we have (max 70%)
                w = min(tbf / 300.0, 0.70)
                shrunk_out = shrunk_out * w + c['out_rate'] * (1.0 - w)
                shrunk_k   = shrunk_k   * w + c['k_rate']   * (1.0 - w)

            # BF per start (shrunk with 3 phantom league-average starts)
            bf_per_start = max(16.0, min(28.0, (tbf + LEAGUE_AVG_BF * 3) / (gs + 3))) if gs > 0 else LEAGUE_AVG_BF

            is_ghost = tbf < 10  # Fix: use actual threshold, not magic number

            pitcher_db[pid] = {
                'Name':         name,
                'Out%':         shrunk_out,
                'K%':           shrunk_k,
                'BB%':          shrunk_bb,
                'Hand':         hand_map.get(pid, 'R'),
                'BF_per_Start': bf_per_start,
                'TBF':          tbf,
                'GS':           gs,
                'IsGhost':      is_ghost,
            }

            if gs > 0 and gp > 0 and (gs / gp) > 0.8 and abbr != 'Unknown':
                if abbr not in team_sp_agg:
                    team_sp_agg[abbr] = {'tbf': 0, 'gs': 0}
                team_sp_agg[abbr]['tbf'] += tbf
                team_sp_agg[abbr]['gs']  += gs
                league_tbf += tbf
                league_gs  += gs

        # Manager leash index (BF/start delta from league average)
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

# Default profile used when we have no data at all
_DEFAULT_MATCH = {
    'Out%': LEAGUE_OUT_RATE, 'K%': LEAGUE_K_RATE, 'BB%': LEAGUE_BB_RATE,
    'Hand': 'R', 'BF_per_Start': LEAGUE_AVG_BF, 'TBF': 0, 'GS': 0, 'IsGhost': True,
}


@st.cache_data(ttl=3600)
def get_live_pitcher_profile(player_id, fallback: dict, target_date_str: str) -> dict:
    """
    Build a rich live profile from the game log.

    Improvements vs v1:
      - Pitch count model: estimates BF from pitch budget / pitches-per-batter
      - Days rest calculation from last start date
      - Blended BF cap: 50% season avg + 30% recent max + 20% pitch-count estimate
      - Ghost correction uses IsGhost flag (not magic BF number)
      - Manager pitch budget inferred from recent max pitch count * 0.95
    """
    season_avg_bf = fallback.get('BF_per_Start', LEAGUE_AVG_BF)

    profile = {
        'actual_out_rate':   fallback['Out%'],
        'actual_k_rate':     fallback.get('K%', LEAGUE_K_RATE),
        'actual_bb_rate':    fallback['BB%'],
        'season_avg_bf':     season_avg_bf,
        'recent_tbf_cap':    season_avg_bf,          # blended cap
        'pitch_budget':      95.0,                   # manager's implied limit
        'pitches_per_batter': 3.9,                   # league average
        'recent_pitch_avg':  88.0,
        'days_rest':         5,
        'starts_count':      fallback.get('GS', 0),
        'is_ghost':          fallback.get('IsGhost', False),
    }

    if not player_id:
        return profile

    try:
        url = (
            f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
            f"?stats=gameLog&group=pitching&season=2026"
        )
        log_data = requests.get(url, timeout=6).json()
        splits = log_data.get('stats', [{}])[0].get('splits', [])
        if not splits:
            return profile

        # Only consider starts
        starts = [s for s in splits if s['stat'].get('gamesStarted', 0) == 1]
        profile['starts_count'] = len(starts)

        # ── Days rest ──────────────────────────────────────────────────────────
        try:
            target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')
            if starts:
                last_date = datetime.strptime(starts[0].get('date', ''), '%Y-%m-%d')
                profile['days_rest'] = max(0, (target_dt - last_date).days)
        except:
            pass

        # ── Pitch count efficiency (last 5 starts) ────────────────────────────
        recent = starts[:5]
        if recent:
            total_pitches = sum(s['stat'].get('numberOfPitches', 0) for s in recent)
            total_tbf     = sum(s['stat'].get('battersFaced',    0) for s in recent)
            profile['recent_pitch_avg'] = total_pitches / len(recent)
            if total_tbf > 0:
                profile['pitches_per_batter'] = max(3.2, total_pitches / total_tbf)

        # ── Manager pitch budget ───────────────────────────────────────────────
        # Use peak as-is with a hard floor of 90 — early season peaks are
        # artificially low (managers building up), so discounting them further
        # causes systematic BF underestimation.
        if len(recent) >= 2:
            peak_pitches = max(s['stat'].get('numberOfPitches', 0) for s in recent[:3])
            profile['pitch_budget'] = max(peak_pitches, 90.0)
        else:
            profile['pitch_budget'] = 95.0

        # ── Blended BF cap ────────────────────────────────────────────────────
        # Season avg gets 65% weight — early season recent_max can come from
        # a deliberately short outing and shouldn't dominate the cap.
        if starts:
            recent_max  = max(s['stat'].get('battersFaced', 0) for s in starts[:3])
            pitch_est   = profile['pitch_budget'] / max(profile['pitches_per_batter'], 3.5)
            profile['recent_tbf_cap'] = (
                season_avg_bf  * 0.65 +
                recent_max     * 0.20 +
                pitch_est      * 0.15
            )

        # ── Ghost profile correction ───────────────────────────────────────────
        if fallback.get('IsGhost', False) and len(starts) >= 2:
            tbf = sum(s['stat'].get('battersFaced',  0) for s in starts)
            bb  = sum(s['stat'].get('baseOnBalls',   0) for s in starts)
            h   = sum(s['stat'].get('hits',          0) for s in starts)
            so  = sum(s['stat'].get('strikeOuts',    0) for s in starts)
            if tbf > 0:
                profile['actual_out_rate'] = (tbf - bb - h) / tbf
                profile['actual_k_rate']   = so / tbf
                profile['actual_bb_rate']  = bb / tbf

    except Exception:
        pass

    return profile


# ==============================================================================
# MONTE CARLO ENGINE  (v2)
# ==============================================================================

def run_monte_carlo(
    sp_name:            str,
    base_out_rate:      float,
    k_rate:             float,
    bb_rate:            float,
    opp_data:           dict,
    park:               str,
    season_avg_bf:      float,
    temp:               float,
    wind:               float,
    umpire:             str,
    manager_shift:      float,
    recent_tbf_cap:     float,
    pitch_budget:       float,
    pitches_per_batter: float,
    days_rest:          int,
    starts_count:       int,
    num_sims:           int = 10_000,
) -> dict:
    """
    Fully revamped simulation.

    Key fixes vs v1:
      1. No fixed seed — results are probabilistic, not deterministic
      2. BF and out-rate distributions are DECOUPLED (independent noise)
      3. BF cap driven by pitch-count model, not just recent max + 1
      4. K% incorporated into out-rate adjustment
      5. Days rest / fatigue applied
      6. Workhorse logic fixed (high recent pitches = trust signal, not fatigue alone)
      7. Wind added
      8. Opponent K% used (high-K lineups make pitcher outs more reliable)
      9. Small-sample variance widened automatically
    """
    factors       = []
    adj_out_rate  = base_out_rate

    # ── Pitch-count BF estimate ────────────────────────────────────────────────
    pitch_count_bf = pitch_budget / max(pitches_per_batter, 3.5)
    hard_cap_bf    = pitch_count_bf + 3.0   # physical ceiling — +1 was too tight

    # Blended BF projection — pitch model weight drops when sample is small,
    # because early-season pitch counts underrepresent true workload capacity.
    if starts_count < 5:
        pc_w, sa_w, ms_w = 0.20, 0.55, 0.25   # trust season avg / career more
    else:
        pc_w, sa_w, ms_w = 0.35, 0.40, 0.25   # trust pitch model more

    adj_bf = (
        pitch_count_bf                  * pc_w +
        season_avg_bf                   * sa_w +
        (season_avg_bf + manager_shift) * ms_w
    )

    factors.append(
        f"📊 Baseline: {adj_out_rate*100:.1f}% Out Rate | {k_rate*100:.1f}% K% | "
        f"{bb_rate*100:.1f}% BB% | Pitch Budget: {pitch_budget:.0f}"
    )
    factors.append(
        f"🎯 Projected BF: {adj_bf:.1f} "
        f"(Pitch Model: {pitch_count_bf:.1f} | Season Avg: {season_avg_bf:.1f})"
    )

    # ── K-rate adjustment ─────────────────────────────────────────────────────
    # Strikeouts are guaranteed outs; above-average K% improves out-rate reliability
    k_bonus = (k_rate - LEAGUE_K_RATE) * 0.30
    adj_out_rate += k_bonus
    if abs(k_bonus) > 0.004:
        factors.append(
            f"⚡ K-Rate ({k_rate*100:.1f}%): {'+' if k_bonus>0 else ''}{k_bonus*100:.1f}% out-rate adj"
        )

    # ── Days rest / fatigue ────────────────────────────────────────────────────
    if days_rest < 4:
        adj_out_rate -= 0.020
        adj_bf       -= 1.5
        factors.append(f"😓 Short Rest ({days_rest}d): -2% out rate, -1.5 BF")
    elif 5 <= days_rest <= 6:
        adj_out_rate += 0.005
        factors.append(f"💪 Well Rested ({days_rest}d): +0.5% out rate")
    elif days_rest > 13:
        adj_out_rate -= 0.015
        adj_bf       -= 1.0
        factors.append(f"🦀 Extended Rest ({days_rest}d): Rustiness risk, -1.5% out rate, -1 BF")

    # ── Manager leash ─────────────────────────────────────────────────────────
    adj_bf += manager_shift * 0.50
    if manager_shift > 0.75:
        factors.append(f"👔 Manager: Long Leash (+{manager_shift:.1f} BF tendency)")
    elif manager_shift < -0.75:
        factors.append(f"👔 Manager: Quick Hook ({manager_shift:.1f} BF tendency)")

    # ── Walk-rate efficiency ──────────────────────────────────────────────────
    if bb_rate > 0.10:
        adj_bf -= 1.5
        factors.append(f"⛽ High BB% ({bb_rate*100:.1f}%): Efficiency warning, -1.5 BF")
    elif bb_rate < 0.06:
        adj_bf += 0.5
        factors.append(f"🎯 Elite Command ({bb_rate*100:.1f}% BB): +0.5 BF")

    # ── Pitch-count hard cap ──────────────────────────────────────────────────
    if adj_bf > hard_cap_bf:
        factors.append(
            f"🚨 Pitch Count Cap: BF limited to {hard_cap_bf:.1f} "
            f"({pitch_budget:.0f}-pitch budget / {pitches_per_batter:.2f} P/BF)"
        )
        adj_bf = hard_cap_bf

    # ── Opponent adjustment ────────────────────────────────────────────────────
    opp_out_rate = opp_data.get('out_rate', LEAGUE_OUT_RATE)
    opp_k_rate   = opp_data.get('k_rate',  LEAGUE_K_RATE)
    opp_ratio    = 1.0 + ((opp_out_rate / LEAGUE_OUT_RATE) - 1.0) * 0.50
    adj_out_rate *= opp_ratio
    if opp_k_rate > 0.26:
        adj_out_rate += 0.010
        factors.append(f"🎰 High-K Lineup ({opp_k_rate*100:.1f}%): +1.0% out rate")
    elif opp_k_rate < 0.18:
        adj_out_rate -= 0.010
        factors.append(f"🏏 Contact Lineup ({opp_k_rate*100:.1f}%): -1.0% out rate")

    # ── Weather ───────────────────────────────────────────────────────────────
    if temp > 85:
        adj_out_rate -= 0.020
        adj_bf       -= 0.5
        factors.append(f"🔥 Extreme Heat ({temp:.0f}°F): -2.0% out rate, -0.5 BF")
    elif temp > 78:
        adj_out_rate -= 0.010
        factors.append(f"☀️ Hot ({temp:.0f}°F): -1.0% out rate")
    elif temp < 50:
        adj_out_rate += 0.015
        factors.append(f"🥶 Cold ({temp:.0f}°F): +1.5% out rate")
    elif temp < 62:
        adj_out_rate += 0.008
        factors.append(f"🌬️ Cool ({temp:.0f}°F): +0.8% out rate")

    if wind > 15:
        adj_out_rate -= 0.008
        factors.append(f"💨 High Wind ({wind:.0f} mph): Conditions tricky, -0.8% out rate")

    # ── Umpire ────────────────────────────────────────────────────────────────
    if umpire in UMPIRE_DATABASE["Pitcher Friendly (Wide Zone)"]:
        adj_out_rate += 0.012
        factors.append(f"💎 Wide Zone Ump ({umpire}): +1.2% out rate")
    elif umpire in UMPIRE_DATABASE["Hitter Friendly (Tight Zone)"]:
        adj_out_rate -= 0.015
        factors.append(f"🧱 Tight Zone Ump ({umpire}): -1.5% out rate")

    # ── Park factor ───────────────────────────────────────────────────────────
    pk = OUTS_PARK_FACTORS.get(park, 1.0)
    adj_out_rate *= pk
    if pk != 1.0:
        factors.append(f"🏟️ Park ({park}): {(pk-1)*100:+.1f}%")

    # ── Small-sample warning ──────────────────────────────────────────────────
    if starts_count < 5:
        factors.append(f"⚠️ Small Sample ({starts_count} starts): Wider uncertainty intervals")

    # ── Final clamp ───────────────────────────────────────────────────────────
    # Floor of 18 BF for any starter with 3+ starts — stacked penalties
    # (short rest + high BB + cold weather etc.) were producing unrealistically
    # low BF projections and causing systematic under bias.
    if starts_count >= 3:
        adj_bf = max(adj_bf, 18.0)
    adj_out_rate = float(np.clip(adj_out_rate, 0.40, 0.85))
    adj_bf       = float(np.clip(adj_bf, 9.0, hard_cap_bf + 2.0))

    # ── SIMULATION ────────────────────────────────────────────────────────────
    # No fixed seed — allow true distributional uncertainty

    # Out-rate distribution (wider early-season)
    or_std = 0.045 if starts_count < 5 else 0.038
    game_out_rates = np.clip(
        np.random.normal(loc=adj_out_rate, scale=or_std, size=num_sims),
        0.30, 0.92
    )

    # BF distribution — INDEPENDENT of out-rate (key fix from v1)
    bf_std = 2.8 if starts_count < 5 else 2.2
    raw_bf = np.random.normal(loc=adj_bf, scale=bf_std, size=num_sims)
    dynamic_bf = np.clip(np.round(raw_bf).astype(int), 9, int(np.ceil(hard_cap_bf)) + 2)

    # Binomial draw of outs
    out_sims = np.random.binomial(n=dynamic_bf, p=game_out_rates)

    return {
        'out_sims':    out_sims,
        'factors':     factors,
        'adj_out_rate': adj_out_rate,
        'adj_bf':      adj_bf,
        'hard_cap_bf': hard_cap_bf,
    }


# ==============================================================================
# EV CALCULATOR
# ==============================================================================

def calculate_ev_percent(win_prob_pct: float, american_odds: int) -> float:
    if american_odds == 0:
        return 0.0
    prob    = win_prob_pct / 100.0
    payout  = (american_odds / 100.0) if american_odds > 0 else (100.0 / abs(american_odds))
    return ((prob * payout) - (1.0 - prob)) * 100.0


# ==============================================================================
# UI
# ==============================================================================

st.title("⚾ MLB Quant AI — Pitcher Outs Engine v2")
st.markdown(
    "_Pitch Count Model · K% Integration · Days Rest / Fatigue · "
    "Career Blending · Decoupled BF Variance · Adaptive Shrinkage_"
)

# Fetch schedule
schedule_url = (
    f"https://statsapi.mlb.com/api/v1/schedule"
    f"?sportId=1&date={target_date_str}"
    f"&hydrate=probablePitcher,decisions,umpire"
)
try:
    games = requests.get(schedule_url, timeout=8).json().get('dates', [{}])[0].get('games', [])
except:
    games = []

if not games:
    st.info("No games found for this date. Try refreshing or adjusting the date.")
    st.stop()

NUM_SIMS = 10_000  # defined once here, used throughout

# ── Game loop ─────────────────────────────────────────────────────────────────
for game in games:
    home_name = game['teams']['home']['team']['name']
    away_name = game['teams']['away']['team']['name']
    home_team = TEAM_MAP.get(home_name, home_name)
    away_team = TEAM_MAP.get(away_name, away_name)

    h_sp_dict = game['teams']['home'].get('probablePitcher', {})
    a_sp_dict = game['teams']['away'].get('probablePitcher', {})
    h_sp_name = h_sp_dict.get('fullName', 'TBD')
    a_sp_name = a_sp_dict.get('fullName', 'TBD')
    h_sp_id   = h_sp_dict.get('id')
    a_sp_id   = a_sp_dict.get('id')

    if h_sp_name == 'TBD' or a_sp_name == 'TBD':
        continue

    # Umpire lookup
    umpire = "Neutral"
    if 'officials' in game:
        for off in game['officials']:
            if off['officialType'] == 'Home Plate':
                umpire = off['official']['fullName']
    if umpire == "Neutral":
        try:
            bx = requests.get(
                f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/boxscore",
                timeout=5
            ).json()
            for off in bx.get('officials', []):
                if off['officialType'] == 'Home Plate':
                    umpire = off['official']['fullName']
        except:
            pass

    temp, wind = get_weather_for_date(home_team, target_date_str)
    ump_tag    = f" | 🧑‍⚖️ {umpire}" if umpire != "Neutral" else ""
    label      = (
        f"⚾ {away_team} ({a_sp_name}) @ {home_team} ({h_sp_name})"
        f" | {temp:.0f}°F 💨{wind:.0f}mph{ump_tag}"
    )

    with st.expander(label):
        col1, col2 = st.columns(2)

        for side, sp_name, sp_id, team_abbr, opp_abbr in [
            (col1, a_sp_name, a_sp_id, away_team, home_team),
            (col2, h_sp_name, h_sp_id, home_team, away_team),
        ]:
            with side:
                # Pitcher stats lookup (by ID — never by name)
                match = STATS_DB.get(sp_id, dict(_DEFAULT_MATCH))

                # Opponent splits vs pitcher handedness
                opp_data = SPLITS_DB.get(opp_abbr, {}).get(
                    match['Hand'],
                    {'out_rate': LEAGUE_OUT_RATE, 'k_rate': LEAGUE_K_RATE}
                )

                manager_shift = MANAGER_DB.get(team_abbr, 0.0)

                # Live game-log profile
                lp = get_live_pitcher_profile(sp_id, match, target_date_str)

                # Run simulation
                res = run_monte_carlo(
                    sp_name            = sp_name,
                    base_out_rate      = lp['actual_out_rate'],
                    k_rate             = lp['actual_k_rate'],
                    bb_rate            = lp['actual_bb_rate'],
                    opp_data           = opp_data,
                    park               = home_team,
                    season_avg_bf      = lp['season_avg_bf'],
                    temp               = temp,
                    wind               = wind,
                    umpire             = umpire,
                    manager_shift      = manager_shift,
                    recent_tbf_cap     = lp['recent_tbf_cap'],
                    pitch_budget       = lp['pitch_budget'],
                    pitches_per_batter = lp['pitches_per_batter'],
                    days_rest          = lp['days_rest'],
                    starts_count       = lp['starts_count'],
                    num_sims           = NUM_SIMS,
                )

                out_sims = res['out_sims']

                # ── Header ───────────────────────────────────────────────────
                ghost_tag = " ⚠️ Limited Data" if lp['is_ghost'] else ""
                st.markdown(f"### {sp_name} ({match['Hand']}HP){ghost_tag}")

                # ── Stats mini-dashboard ──────────────────────────────────────
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Out%",   f"{lp['actual_out_rate']*100:.1f}%")
                m2.metric("K%",     f"{lp['actual_k_rate']*100:.1f}%")
                m3.metric("BB%",    f"{lp['actual_bb_rate']*100:.1f}%")
                m4.metric("Rest",   f"{lp['days_rest']}d")

                m5, m6, m7 = st.columns(3)
                m5.metric("Starts",     lp['starts_count'])
                m6.metric("P/BF",       f"{lp['pitches_per_batter']:.2f}")
                m7.metric("Pitch Bdgt", f"{lp['pitch_budget']:.0f}")

                st.divider()

                # ── Line / odds inputs ────────────────────────────────────────
                key_base = f"{team_abbr}_{sp_id}_{game['gamePk']}"
                line_o   = st.number_input("Outs Line:", value=17.5, step=0.5, key=f"o_{key_base}")
                oc1, oc2 = st.columns(2)
                with oc1:
                    o_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"oo_{key_base}")
                with oc2:
                    u_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"uo_{key_base}")

                # ── Probabilities ─────────────────────────────────────────────
                o_prob = float(np.sum(out_sims > line_o)) / NUM_SIMS * 100
                u_prob = 100.0 - o_prob
                o_ev   = calculate_ev_percent(o_prob, o_odds)
                u_ev   = calculate_ev_percent(u_prob, u_odds)

                if o_prob > 60:
                    st.success(f"📈 OVER {o_prob:.1f}%  |  UNDER {u_prob:.1f}%")
                elif o_prob < 40:
                    st.error(f"📉 UNDER {u_prob:.1f}%  |  OVER {o_prob:.1f}%")
                else:
                    st.warning(f"⚖️ Neutral  |  OVER {o_prob:.1f}%  |  UNDER {u_prob:.1f}%")

                # ── EV display ────────────────────────────────────────────────
                ev1, ev2 = st.columns(2)
                with ev1:
                    if o_ev > 3.0:   st.success(f"🔥 OVER +EV: {o_ev:+.1f}%")
                    elif o_ev > 1.0: st.info(f"OVER EV: {o_ev:+.1f}%")
                    else:            st.caption(f"OVER EV: {o_ev:+.1f}%")
                with ev2:
                    if u_ev > 3.0:   st.success(f"🔥 UNDER +EV: {u_ev:+.1f}%")
                    elif u_ev > 1.0: st.info(f"UNDER EV: {u_ev:+.1f}%")
                    else:            st.caption(f"UNDER EV: {u_ev:+.1f}%")

                # ── Projection summary with full percentile range ─────────────
                median_outs = float(np.median(out_sims))
                p10  = float(np.percentile(out_sims, 10))
                p25  = float(np.percentile(out_sims, 25))
                p75  = float(np.percentile(out_sims, 75))
                p90  = float(np.percentile(out_sims, 90))
                st.info(
                    f"📊 Median: **{median_outs:.1f}** outs  "
                    f"| 25th–75th: **{p25:.0f}–{p75:.0f}**  "
                    f"| 10th–90th: **{p10:.0f}–{p90:.0f}**  "
                    f"| Est. BF: **{res['adj_bf']:.1f}**"
                )

                # ── Distribution chart ────────────────────────────────────────
                dist_series = (
                    pd.Series(out_sims)
                    .value_counts(normalize=True)
                    .sort_index()
                    .rename("Probability")
                )
                st.bar_chart(dist_series)

                # ── Factor breakdown ──────────────────────────────────────────
                with st.expander("🔬 Model Factor Breakdown"):
                    for f in res['factors']:
                        st.caption(f"- {f}")

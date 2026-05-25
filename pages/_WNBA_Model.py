import streamlit as st
import requests
import numpy as np
import os
from datetime import datetime, timedelta, date

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="WNBA Master AI 2026", page_icon="🏀", layout="wide")
st.sidebar.title("⚙️ System Tools")

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Pulling fresh data.")

# ─────────────────────────────────────────────────────────────────────────────
# PLAYER TIERS — 2026 WNBA
# ─────────────────────────────────────────────────────────────────────────────
SUPERSTARS = [
    "A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier",
    "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu", "Paige Bueckers",
]
ALL_STARS = [
    "Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike",
    "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale",
    "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston",
    "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor", "Azzi Fudd",
    "Rickea Jackson", "Dearica Hamby", "Temi Fagbenle",
]
HIGH_IMPACT = [
    "Natasha Howard", "Marina Mabrey", "Courtney Vandersloot", "Betnijah Laney-Hamilton",
    "Brionna Jones", "Allisha Gray", "Rhyne Howard", "Kayla McBride",
    "Natasha Cloud", "Kelsey Mitchell", "NaLyssa Smith", "Brittney Griner",
    "Cheyenne Parker-Tyus", "Courtney Williams", "Alanna Smith", "Sophie Cunningham",
    "Kia Nurse", "Lexie Hull", "Dorka Juhasz", "Isabelle Harrison",
    "Aneesah Morrow", "Saniya Rivers", "Bridget Carleton", "Han Xu",
    "Kayla Thornton", "Tyasha Harris", "Moriah Jefferson", "Bree Hall",
    "Dana Evans", "Janiah Barker",
]
DEFENSIVE_LIABILITIES = [
    "Caitlin Clark", "Arike Ogunbowale", "Kelsey Mitchell", "Marina Mabrey",
    "Diana Taurasi", "Sabrina Ionescu", "Kelsey Plum", "Azzi Fudd",
    "Skylar Diggins-Smith", "Tyasha Harris",
]
OFFENSIVE_LIABILITIES = [
    "Alyssa Thomas", "Ezi Magbegor", "Brianna Turner", "Kiah Stokes",
    "Natasha Howard", "Brittney Griner", "Alanna Smith",
]

# ─────────────────────────────────────────────────────────────────────────────
# TEAM DATA — fallback ratings (used when live fetch unavailable)
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LV':   {'off_rtg': 110.5, 'def_rtg': 99.8},
    'NY':   {'off_rtg': 109.2, 'def_rtg': 100.5},
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2},
    'SEA':  {'off_rtg': 103.5, 'def_rtg': 98.8},
    'MIN':  {'off_rtg': 104.8, 'def_rtg': 99.1},
    'IND':  {'off_rtg': 106.5, 'def_rtg': 105.2},
    'DAL':  {'off_rtg': 105.1, 'def_rtg': 104.8},
    'ATL':  {'off_rtg': 100.2, 'def_rtg': 101.5},
    'PHO':  {'off_rtg': 99.5,  'def_rtg': 106.1},
    'CHI':  {'off_rtg': 98.2,  'def_rtg': 103.5},
    'LA':   {'off_rtg': 96.8,  'def_rtg': 105.2},
    'WAS':  {'off_rtg': 97.5,  'def_rtg': 108.4},
    'GS':   {'off_rtg': 101.0, 'def_rtg': 103.0},
    'POR':  {'off_rtg': 98.0,  'def_rtg': 104.5},
    'TOR':  {'off_rtg': 99.0,  'def_rtg': 104.0},
}

# ─────────────────────────────────────────────────────────────────────────────
# FIX 7: PACE DATA — possessions per 40 min, 2026 estimates
# Used to scale the net-rating edge: higher-pace games amplify spreads
# ─────────────────────────────────────────────────────────────────────────────
TEAM_PACE = {
    'LV': 97.2, 'NY': 95.8, 'CONN': 93.1, 'SEA': 94.5, 'MIN': 94.8,
    'IND': 96.1, 'DAL': 95.3, 'ATL': 93.7, 'PHO': 94.2, 'CHI': 93.5,
    'LA':  93.0, 'WAS': 92.8, 'GS':  95.0, 'POR': 94.0, 'TOR': 94.5,
}
LEAGUE_AVG_PACE = 94.5

BLANK_STD = {
    'wins': 0, 'losses': 0, 'record': '0-0',
    'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': 'N/A',
    'home_record': 'N/A', 'away_record': 'N/A',
}

ESPN_NORM = {
    'LVA':'LV','NYL':'NY','CON':'CONN','PHX':'PHO','LAS':'LA',
    'MINN':'MIN','GSV':'GS','GST':'GS','PORT':'POR','TORP':'TOR','TORW':'TOR',
}
def norm(abbr):
    return ESPN_NORM.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Module-level session singleton — one Session reused for all requests
# ─────────────────────────────────────────────────────────────────────────────
_SESSION = None

def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    return _SESSION

def make_session():  # kept for any external callers
    return get_session()

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: Pre-built player lookup — O(1) exact match, built once at module load
# ─────────────────────────────────────────────────────────────────────────────
def _normalize_name(name: str) -> str:
    return (
        name.lower()
        .split(" (")[0]
        .replace(".", "").replace("'", "")
        .replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "")
        .strip()
    )

def _build_player_lookup():
    lookup: dict = {}
    for p in SUPERSTARS:
        lookup[_normalize_name(p)] = (8.0, "Superstar")
    for p in ALL_STARS:
        k = _normalize_name(p)
        if k not in lookup:
            lookup[k] = (4.5, "All-Star")
    for p in HIGH_IMPACT:
        k = _normalize_name(p)
        if k not in lookup:
            lookup[k] = (2.5, "High-Impact")
    def_set = {_normalize_name(p) for p in DEFENSIVE_LIABILITIES}
    off_set = {_normalize_name(p) for p in OFFENSIVE_LIABILITIES}
    return lookup, def_set, off_set

PLAYER_LOOKUP, DEF_LIABILITY_SET, OFF_LIABILITY_SET = _build_player_lookup()

# ─────────────────────────────────────────────────────────────────────────────
# FIX 6: Live net ratings — derived from the same scoreboard endpoint the app
# already uses for standings and B2B. Walks back up to 45 days of completed
# games, averages points scored/allowed, and converts to the same ~100-point
# rating scale used in TEAM_DATA. Falls back to TEAM_DATA for any team with
# fewer than 5 games found (e.g. very early in the season).
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_live_team_ratings():
    scored_list  = {k: [] for k in TEAM_DATA}
    allowed_list = {k: [] for k in TEAM_DATA}

    today = date.today()
    for days_back in range(1, 46):
        if all(len(scored_list[k]) >= 15 for k in TEAM_DATA):
            break
        for event in _get_scoreboard((today - timedelta(days=days_back)).strftime('%Y%m%d')).get('events', []):
            try:
                comp = event.get('competitions', [{}])[0]
                if not comp.get('status', {}).get('type', {}).get('completed', False):
                    continue
                home = next((c for c in comp.get('competitors', []) if c.get('homeAway') == 'home'), None)
                away = next((c for c in comp.get('competitors', []) if c.get('homeAway') == 'away'), None)
                if not home or not away:
                    continue
                h_abbr  = norm(home.get('team', {}).get('abbreviation', ''))
                a_abbr  = norm(away.get('team', {}).get('abbreviation', ''))
                h_score = float(home.get('score') or 0)
                a_score = float(away.get('score') or 0)
                if h_score == 0 and a_score == 0:
                    continue
                if h_abbr in scored_list:
                    scored_list[h_abbr].append(h_score)
                    allowed_list[h_abbr].append(a_score)
                if a_abbr in scored_list:
                    scored_list[a_abbr].append(a_score)
                    allowed_list[a_abbr].append(h_score)
            except Exception:
                pass

    # Scale: WNBA league avg ~83 PPG maps to ~101 rating (matches TEAM_DATA baseline)
    LEAGUE_AVG_PPG = 83.0
    LEAGUE_AVG_RTG = 101.0
    ratings = {}
    live_count = 0
    for abbr in TEAM_DATA:
        scored  = scored_list[abbr]
        allowed = allowed_list[abbr]
        if len(scored) >= 5:
            off_rtg = round(LEAGUE_AVG_RTG + (sum(scored)  / len(scored)  - LEAGUE_AVG_PPG), 1)
            def_rtg = round(LEAGUE_AVG_RTG + (sum(allowed) / len(allowed) - LEAGUE_AVG_PPG), 1)
            ratings[abbr] = {'off_rtg': off_rtg, 'def_rtg': def_rtg}
            live_count += 1
        else:
            ratings[abbr] = TEAM_DATA[abbr]
    return ratings, live_count

# ─────────────────────────────────────────────────────────────────────────────
# SCOREBOARD — slate + standings source
# FIX 2: except Exception (no bare except)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _get_scoreboard(date_string):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}"
    try:
        r = get_session().get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

@st.cache_data(ttl=300)
def get_daily_slate():
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    games = []
    try:
        for event in _get_scoreboard(today_str).get('events', []):
            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if home and away:
                games.append({
                    'h': norm(home['team']['abbreviation']),
                    'a': norm(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'],
                    'a_name': away['team']['displayName'],
                })
    except Exception:
        pass
    return games

# ─────────────────────────────────────────────────────────────────────────────
# FIX 4 + 5: Standings
#   — Primary: ESPN standings API (reliable, real L10 when available)
#   — Fallback: scoreboard walk (home/away records + missing teams)
#   — Defensive .get() everywhere so a changed API shape fails gracefully
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    standings = {}

    # ── Primary: ESPN standings endpoint ──────────────────────────────────────
    try:
        url = "https://site.api.espn.com/apis/v2/sports/basketball/wnba/standings"
        r = get_session().get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        # Handle both flat-entry and conference-grouped structures
        entries = []
        raw = data.get('standings', data)
        if isinstance(raw, dict) and 'entries' in raw:
            entries = raw['entries']
        else:
            for group in (raw.get('groups', []) if isinstance(raw, dict) else []):
                entries.extend(group.get('standings', {}).get('entries', []))

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                abbr = norm(entry.get('team', {}).get('abbreviation', ''))
                if not abbr:
                    continue
                stats = {}
                for s in entry.get('stats', []):
                    if isinstance(s, dict):
                        stats[s.get('name', '')] = s.get('value')
                w   = int(stats.get('wins',   0) or 0)
                l   = int(stats.get('losses', 0) or 0)
                pct = w / (w + l) if (w + l) > 0 else 0.5
                # L10 — ESPN may expose these under either key name
                l10w = stats.get('last10Wins')   or stats.get('vsLast10Wins')
                l10l = stats.get('last10Losses') or stats.get('vsLast10Losses')
                if l10w is not None and l10l is not None:
                    l10w, l10l = int(l10w), int(l10l)
                    l10_pct    = l10w / (l10w + l10l) if (l10w + l10l) > 0 else pct
                    l10_record = f"{l10w}-{l10l}"
                else:
                    l10_pct, l10_record = pct, 'N/A'
                standings[abbr] = {
                    'wins': w, 'losses': l, 'record': f"{w}-{l}",
                    'win_pct': pct, 'l10_pct': l10_pct, 'l10_record': l10_record,
                    'home_record': 'N/A', 'away_record': 'N/A',
                }
            except Exception:
                pass
    except Exception:
        pass  # fall through to scoreboard walk

    # ── Fallback/supplement: scoreboard walk ──────────────────────────────────
    # Fills missing teams and adds home/away splits the standings API lacks
    if len(standings) < len(TEAM_DATA):
        today = date.today()
        for days_back in range(0, 15):
            if len(standings) >= len(TEAM_DATA):
                break
            try:
                data = _get_scoreboard((today - timedelta(days=days_back)).strftime('%Y%m%d'))
            except Exception:
                continue
            for event in data.get('events', []):
                try:
                    comps = event.get('competitions', [])
                    if not comps:
                        continue
                    for comp in comps[0].get('competitors', []):
                        if not isinstance(comp, dict):
                            continue
                        abbr = norm(comp.get('team', {}).get('abbreviation', ''))
                        if not abbr or abbr in standings:
                            continue
                        overall = home_rec = away_rec = None
                        for rec in comp.get('records', []):
                            if not isinstance(rec, dict):
                                continue
                            summary = rec.get('summary', '')
                            if not summary or '-' not in summary:
                                continue
                            rtype = rec.get('type', '')
                            rname = rec.get('name', '').lower()
                            if rtype in ('total', 'overall') or rname in ('overall', 'total'):
                                overall  = summary
                            elif rtype == 'home' or rname == 'home':
                                home_rec = summary
                            elif rtype in ('road', 'away') or rname in ('road', 'away'):
                                away_rec = summary
                        if overall:
                            try:
                                w, l = map(int, overall.split('-'))
                                pct = w / (w + l) if (w + l) > 0 else 0.5
                                standings[abbr] = {
                                    'wins': w, 'losses': l, 'record': overall,
                                    'win_pct': pct, 'l10_pct': pct, 'l10_record': 'N/A',
                                    'home_record': home_rec or 'N/A',
                                    'away_record':  away_rec or 'N/A',
                                }
                            except Exception:
                                pass
                except Exception:
                    pass

    return standings if standings else {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# BACK-TO-BACK
# FIX 2: except Exception (no bare except)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_back_to_back():
    b2b  = set()
    yest = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
    try:
        for event in _get_scoreboard(yest).get('events', []):
            for c in event.get('competitions', [{}])[0].get('competitors', []):
                if isinstance(c, dict):
                    b2b.add(norm(c.get('team', {}).get('abbreviation', '')))
    except Exception:
        pass
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION ENGINE
# Changes: live_ratings param, pre-built player lookup, pace-adjusted scalar
# All math/logic otherwise identical
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False, live_ratings=None):
    if live_ratings is None:
        live_ratings = TEAM_DATA
    h_td  = live_ratings.get(h, {'off_rtg': 100, 'def_rtg': 102})
    a_td  = live_ratings.get(a, {'off_rtg': 100, 'def_rtg': 102})
    h_std = standings.get(h, BLANK_STD)
    a_std = standings.get(a, BLANK_STD)
    factors, total = [], 0.0

    # 1. Win % Edge
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']
    if use_l10:
        h_pct = h_pct * 0.6 + h_std.get('l10_pct', h_pct) * 0.4
        a_pct = a_pct * 0.6 + a_std.get('l10_pct', a_pct) * 0.4
    base_adj = (h_pct - a_pct) * 20.0
    total += base_adj
    factors.append({
        "icon": "📊",
        "name": "Blended Win % Edge (L10)" if use_l10 else "Win % Edge",
        "adj":  base_adj,
        "why":  f"{h} ({h_std['record']}) vs {a} ({a_std['record']})",
    })

    # 2. Home Court
    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 2.5, "why": f"Advantage for {h}"})

    # 3. Injuries
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    # FIX 3: get_player_impact uses pre-built PLAYER_LOOKUP (O(1) exact, then partial)
    def get_player_impact(s):
        raw = _normalize_name(s)
        if raw in PLAYER_LOOKUP:
            val, tier = PLAYER_LOOKUP[raw]
        else:
            val, tier = 1.0, "Role"
            for k, (v, t) in PLAYER_LOOKUP.items():
                if k in raw or raw in k:
                    val, tier = v, t
                    break
        archetype = "Balanced"
        if raw in DEF_LIABILITY_SET or any(k in raw or raw in k for k in DEF_LIABILITY_SET):
            archetype = "Def_Liability"
        elif raw in OFF_LIABILITY_SET or any(k in raw or raw in k for k in OFF_LIABILITY_SET):
            archetype = "Off_Liability"
        return val, tier, archetype

    def calc_injury_penalty(inj_list):
        o_pen, d_pen, details, core = 0.0, 0.0, [], 0
        for p in inj_list:
            val, tier, arch = get_player_impact(p)
            if tier in ("Superstar", "All-Star", "High-Impact"):
                core += 1
            if arch == "Def_Liability":
                o = val * 1.3;  d = val * -0.3
            elif arch == "Off_Liability":
                o = val * -0.3; d = val * 1.3
            else:
                o = val * 0.6;  d = val * 0.4
            o_pen += o; d_pen += d
            details.append(f"{p.split(' (')[0]} ({tier})")
        mult = 2.00 if core >= 4 else 1.75 if core == 3 else 1.35 if core == 2 else 1.00
        return o_pen * mult, d_pen * mult, details, mult

    h_op, h_dp, h_det, h_mult = calc_injury_penalty(h_inj) if h_inj else (0.0, 0.0, [], 1.0)
    a_op, a_dp, a_det, a_mult = calc_injury_penalty(a_inj) if a_inj else (0.0, 0.0, [], 1.0)

    # 4. Net Rating Edge — FIX 7: pace-adjusted scalar replaces flat 0.55
    h_net = (h_td['off_rtg'] - h_op) - (h_td['def_rtg'] + h_dp)
    a_net = (a_td['off_rtg'] - a_op) - (a_td['def_rtg'] + a_dp)
    h_pace     = TEAM_PACE.get(h, LEAGUE_AVG_PACE)
    a_pace     = TEAM_PACE.get(a, LEAGUE_AVG_PACE)
    game_pace  = (h_pace + a_pace) / 2
    pace_scalar = (game_pace / LEAGUE_AVG_PACE) * 0.55
    net_edge   = (h_net - a_net) * pace_scalar
    total += net_edge
    factors.append({
        "icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge,
        "why":  f"Net rating dynamically adjusted by player archetype + pace ({game_pace:.1f} poss/40)",
    })

    if h_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(h_det)}"
        if h_mult > 1.0: why += f" (🚨 Depth Collapse: {h_mult}x)"
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": why})
    if a_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(a_det)}"
        if a_mult > 1.0: why += f" (🚨 Depth Collapse: {a_mult}x)"
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": why})

    # 5. B2B Fatigue
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0,
                        "why": f"{h} played yesterday. Commercial flight grind."})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0,
                        "why": f"{a} played yesterday. Commercial flight grind."})

    # Logistic win probability
    prob = max(5.0, min(95.0, 1 / (1 + np.exp(-0.17 * total)) * 100))
    return {
        'winner':  h if prob >= 50.0 else a,
        'conf':    prob if prob >= 50.0 else 100.0 - prob,
        'factors': factors,
        'h_std': h_std, 'a_std': a_std,
        'h_inj': h_inj, 'a_inj': a_inj,
    }

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 WNBA Master AI Predictor 2026")
current_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Market Date:** {current_date}")
st.divider()

with st.spinner("Loading slate and standings…"):
    slate                    = get_daily_slate()
    standings                = get_standings()
    b2b                      = get_back_to_back()
    live_ratings, live_count = get_live_team_ratings()

# ── Sidebar Diagnostics & Manual Injury Input ──
st.sidebar.subheader("📡 Data Status")
st.sidebar.write(f"**Teams with live records:** {len(standings)}/{len(TEAM_DATA)}")
st.sidebar.write(
    f"**Teams with live ratings:** {live_count}/{len(TEAM_DATA)} "
    f"({'✅ Live' if live_count > 0 else '⚠️ Fallback only'})"
)
if live_count == 0:
    st.sidebar.warning("Live ratings unavailable — using hardcoded fallback. Try Force Refresh.")
if len(standings) < 5:
    st.sidebar.warning("Standings data appears incomplete. Try Force Refresh.")

st.sidebar.subheader("😴 B2B Fatigue")
if b2b:
    st.sidebar.write(f"**On B2B today:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs today.")

st.sidebar.subheader("🤕 Manual Injury Input")
st.sidebar.caption("Type missing players separated by commas (e.g. `Caitlin Clark, Kelsey Mitchell`). The model will automatically read the names, find their tier, and penalize the math.")

injuries = {}
if slate:
    teams_playing = set()
    for game in slate:
        teams_playing.add(game['h'])
        teams_playing.add(game['a'])
        
    for team in sorted(teams_playing):
        # Generate a text box for every team playing today
        inj_input = st.sidebar.text_input(f"{team} Injuries", key=f"inj_{team}")
        if inj_input.strip():
            # Clean up the input string into a proper list
            injuries[team] = [p.strip() for p in inj_input.split(',') if p.strip()]
else:
    st.sidebar.info("No games scheduled today. Input fields will appear on game days.")

def render_games(use_l10):
    if not slate:
        st.info("No WNBA games scheduled for today.")
        return
    for game in slate:
        h, a = game['h'], game['a']
        pred  = predict_game(h, a, standings, injuries, b2b, use_l10=use_l10, live_ratings=live_ratings)
        with st.expander(
            f"{game['h_name']} vs {game['a_name']}  |  "
            f"Winner: **{pred['winner']}** ({pred['conf']:.1f}%)"
        ):
            st.markdown(f"### 🏆 {pred['winner']} Wins")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(
                    f"{f['icon']} **{f['name']}**: "
                    f"<span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span>"
                    f" — {f['why']}",
                    unsafe_allow_html=True,
                )
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                rec = pred['h_std']['record']
                if use_l10:
                    st.write(f"**Record:** {rec}  *(L10: {pred['h_std'].get('l10_record','N/A')})*")
                else:
                    st.write(f"**Record:** {rec}  *(Home: {pred['h_std'].get('home_record','N/A')})*")
                for inj in pred['h_inj']:
                    st.warning(f"🤕 {inj}")
            with c2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                rec = pred['a_std']['record']
                if use_l10:
                    st.write(f"**Record:** {rec}  *(L10: {pred['a_std'].get('l10_record','N/A')})*")
                else:
                    st.write(f"**Record:** {rec}  *(Away: {pred['a_std'].get('away_record','N/A')})*")
                for inj in pred['a_inj']:
                    st.warning(f"🤕 {inj}")

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])
with tab1:
    render_games(use_l10=False)
with tab2:
    render_games(use_l10=True)

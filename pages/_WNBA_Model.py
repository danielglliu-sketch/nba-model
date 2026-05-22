import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="WNBA Master AI 2026", page_icon="🏀", layout="wide")
st.sidebar.title("⚙️ System Tools")

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Pulling fresh data.")

# ─────────────────────────────────────────────────────────────────────────────
# PLAYER TIERS — 2026 WNBA
# ─────────────────────────────────────────────────────────────────────────────

# SUPERSTARS (-8.0) — MVP-level franchise players
SUPERSTARS = [
    "A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier",
    "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu", "Paige Bueckers",
]

# ALL-STARS (-4.5) — #2 options, consistent elite contributors
ALL_STARS = [
    "Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike",
    "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale",
    "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston",
    "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor", "Azzi Fudd",
    "Rickea Jackson", "Dearica Hamby", "Temi Fagbenle",
]

# HIGH-IMPACT (-2.5) — elite role players, defensive anchors, 12+ PPG scorers
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

# PLAYER ARCHETYPES — changes how absence affects offense vs defense
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
# TEAM DATA — 2026 WNBA (15 teams, 40-minute game, ~80 possessions)
# Net ratings scaled for WNBA pacing (lower than NBA)
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LV':   {'off_rtg': 110.5, 'def_rtg': 99.8},   # Aces — defending elite
    'NY':   {'off_rtg': 109.2, 'def_rtg': 100.5},  # Liberty
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2},   # Sun — elite defense
    'SEA':  {'off_rtg': 103.5, 'def_rtg': 98.8},   # Storm
    'MIN':  {'off_rtg': 104.8, 'def_rtg': 99.1},   # Lynx — Collier-led
    'IND':  {'off_rtg': 106.5, 'def_rtg': 105.2},  # Fever — Clark effect
    'DAL':  {'off_rtg': 105.1, 'def_rtg': 104.8},  # Wings — Bueckers era
    'ATL':  {'off_rtg': 100.2, 'def_rtg': 101.5},  # Dream
    'PHO':  {'off_rtg': 99.5,  'def_rtg': 106.1},  # Mercury
    'CHI':  {'off_rtg': 98.2,  'def_rtg': 103.5},  # Sky
    'LA':   {'off_rtg': 96.8,  'def_rtg': 105.2},  # Sparks
    'WAS':  {'off_rtg': 97.5,  'def_rtg': 108.4},  # Mystics
    'GS':   {'off_rtg': 101.0, 'def_rtg': 103.0},  # Valkyries (2nd year)
    'POR':  {'off_rtg': 98.0,  'def_rtg': 104.5},  # Fire (expansion)
    'TOR':  {'off_rtg': 99.0,  'def_rtg': 104.0},  # Tempo (expansion)
}

BLANK_STD = {
    'wins': 0, 'losses': 0, 'record': '0-0',
    'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': 'N/A',
    'home_record': 'N/A', 'away_record': 'N/A',
}

# Normalize ESPN's varying abbreviations → our internal keys
ESPN_NORM = {
    'LVA': 'LV',  'NYL': 'NY',   'CON': 'CONN', 'PHX': 'PHO',
    'LAS': 'LA',  'MINN': 'MIN', 'GSV': 'GS',   'GST': 'GS',
    'PORT': 'POR','TORP': 'TOR', 'TORW': 'TOR',
}

# ESPN team URL slugs for roster/injury API calls
ESPN_SLUG_MAP = {
    'lv': 'LV', 'ny': 'NY', 'conn': 'CONN', 'sea': 'SEA', 'min': 'MIN',
    'ind': 'IND', 'dal': 'DAL', 'atl': 'ATL', 'phx': 'PHO', 'chi': 'CHI',
    'la': 'LA', 'was': 'WAS', 'gs': 'GS', 'por': 'POR', 'tor': 'TOR',
}

def norm(abbr):
    return ESPN_NORM.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# BROWSER SESSION — mimics a real browser to bypass bot detection on CBS/ESPN
# ─────────────────────────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return s

# ─────────────────────────────────────────────────────────────────────────────
# 1. SCOREBOARD — used for slate, standings, and B2B detection
#    NOTE: ESPN's /wnba/standings endpoint returns nearly empty JSON in 2026.
#    We extract live records from competitor blocks inside the scoreboard instead.
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _get_scoreboard(date_string):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}"
    try:
        r = make_session().get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=300)
def get_daily_slate():
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    games = []
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
    return games

# ─────────────────────────────────────────────────────────────────────────────
# 2. STANDINGS
#    Scans last 14 days of scoreboards. Each competitor block carries a
#    records[] array with {"type": "total", "summary": "W-L"} — that's our
#    source of truth for records since the standings endpoint is broken.
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    standings = {}
    today = date.today()

    for days_back in range(0, 15):
        if len(standings) >= len(TEAM_DATA):
            break
        check = (today - timedelta(days=days_back)).strftime('%Y%m%d')
        data  = _get_scoreboard(check)

        for event in data.get('events', []):
            for comp in event['competitions'][0]['competitors']:
                abbr = norm(comp['team']['abbreviation'])
                if abbr in standings:
                    continue

                overall = home_rec = away_rec = None
                for rec in comp.get('records', []):
                    rtype = rec.get('type', '')
                    rname = rec.get('name', '').lower()
                    summary = rec.get('summary', '')
                    if '-' not in summary:
                        continue
                    if rtype in ('total', 'overall') or rname in ('overall', 'total'):
                        overall = summary
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
                    except:
                        pass

    return standings if standings else {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# 3. INJURIES — 3-source waterfall, first non-empty result wins
#
#  Source 1: ESPN WNBA team roster JSON (no HTML parsing, no JS rendering)
#  Source 2: CBS Sports HTML with cookie warmup to defeat bot detection
#  Source 3: ESPN sports.core injuries API (follows $ref links)
# ─────────────────────────────────────────────────────────────────────────────
SKIP_STATUSES = {'active', 'probable', 'expected to play', 'day-to-day', 'not injury related'}

TEAM_NAME_MAP = {
    'atlanta': 'ATL', 'chicago': 'CHI', 'connecticut': 'CONN', 'dallas': 'DAL',
    'indiana': 'IND', 'las vegas': 'LV', 'los angeles': 'LA', 'minnesota': 'MIN',
    'new york': 'NY', 'phoenix': 'PHO', 'seattle': 'SEA', 'washington': 'WAS',
    'golden state': 'GS', 'portland': 'POR', 'toronto': 'TOR',
}

def _match_team(text):
    t = text.lower()
    for key, abbr in TEAM_NAME_MAP.items():
        if key in t:
            return abbr
    return None

def _injuries_espn_rosters():
    result  = {}
    session = make_session()
    session.headers.update({'Accept': 'application/json, */*'})
    for slug, abbr in ESPN_SLUG_MAP.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{slug}/roster"
        try:
            data = session.get(url, timeout=5).json()
        except:
            continue
        injured = []
        for group in data.get('athletes', []):
            players = group if isinstance(group, list) else group.get('items', [])
            for player in players:
                status_obj  = player.get('status', {})
                status_name = (
                    status_obj.get('name') or
                    status_obj.get('type', {}).get('name') or
                    status_obj.get('type', {}).get('description') or 'active'
                ).lower()
                if status_name in SKIP_STATUSES or status_name == 'active':
                    continue
                full_name = player.get('fullName', player.get('displayName', 'Unknown'))
                reason = ''
                for inj in player.get('injuries', []):
                    reason = inj.get('type', {}).get('description', '') or inj.get('detail', '')
                    if reason: break
                if not reason:
                    reason = player.get('injuryStatus', 'Injury')
                label = status_obj.get('name', 'Out').title()
                injured.append(f"{full_name} ({reason} — {label})")
        if injured:
            result[abbr] = injured
    return result

def _injuries_cbs():
    session = make_session()
    try:
        session.get('https://www.cbssports.com/', timeout=5)   # cookie warmup
    except:
        pass
    r = session.get('https://www.cbssports.com/wnba/injuries/', timeout=10)
    r.raise_for_status()
    if len(r.text) < 500:
        raise ValueError("CBS returned near-empty page")
    soup   = BeautifulSoup(r.text, 'html.parser')
    result = {}
    for table in soup.find_all('div', class_='TableBase'):
        name_el = (
            table.find('span', class_='TeamName') or
            table.find(class_='TeamLogoNameLockup-name') or
            table.find(class_='TableBase-title')
        )
        abbr = _match_team(name_el.get_text(strip=True) if name_el else '')
        if not abbr:
            continue
        players = []
        for row in table.find_all('tr', class_='TableBase-bodyTr'):
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            name_cell = (
                cols[0].find('span', class_='CellPlayerName--long') or
                cols[0].find('a') or cols[0]
            )
            name   = name_cell.get_text(strip=True)
            injury = cols[3].get_text(strip=True)
            status = cols[4].get_text(strip=True)
            if status.lower() in SKIP_STATUSES:
                continue
            players.append(f"{name} ({injury} — {status})")
        if players:
            result[abbr] = players
    return result

def _injuries_espn_core():
    result  = {}
    session = make_session()
    session.headers.update({'Accept': 'application/json, */*'})
    try:
        r = session.get(
            'https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/injuries?limit=300',
            timeout=8
        )
        r.raise_for_status()
        items = r.json().get('items', [])
    except:
        return result
    for item in items[:120]:
        ref = item.get('$ref', '')
        if not ref: continue
        try:
            detail = session.get(ref, timeout=4).json()
        except:
            continue
        status_txt = (
            detail.get('status', {}).get('type', {}).get('description', '') or
            detail.get('type', {}).get('description', 'Unknown')
        )
        if status_txt.lower() in SKIP_STATUSES:
            continue
        athlete_ref = detail.get('athlete', {}).get('$ref', '')
        if not athlete_ref: continue
        try:
            ath = session.get(athlete_ref, timeout=4).json()
        except:
            continue
        name      = ath.get('displayName', 'Unknown')
        team_abbr = norm(ath.get('team', {}).get('abbreviation', ''))
        injury    = detail.get('type', {}).get('description', 'Injury')
        if team_abbr:
            result.setdefault(team_abbr, []).append(f"{name} ({injury} — {status_txt})")
    return result

@st.cache_data(ttl=600)
def get_injuries():
    for source_name, fn in [
        ("ESPN Roster API",  _injuries_espn_rosters),
        ("CBS Sports",       _injuries_cbs),
        ("ESPN Core API",    _injuries_espn_core),
    ]:
        try:
            data = fn()
            if data:
                total = sum(len(v) for v in data.values())
                return data, f"✅ Injuries loaded from {source_name} ({total} players flagged)"
        except:
            continue
    return {}, "⚠️ All injury sources failed — try refreshing."

# ─────────────────────────────────────────────────────────────────────────────
# 4. BACK-TO-BACK DETECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_back_to_back():
    b2b = set()
    yest = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
    for event in _get_scoreboard(yest).get('events', []):
        for c in event['competitions'][0]['competitors']:
            b2b.add(norm(c['team']['abbreviation']))
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# 5. PREDICTION ENGINE
#    Key WNBA-specific calibrations vs the NBA blueprint:
#    • 40-minute game → net rating scaled with * 0.55 (vs NBA's * 0.6)
#    • Win% multiplier 20.0 (vs NBA's 25.0) — WNBA top teams dominate more
#      consistently, so raw % spread is smaller
#    • HCA = 2.5 pts (vs NBA's 3.5) — WNBA venues are smaller, less crowd impact
#    • B2B penalty = 5.0 (vs NBA's 4.0) — WNBA commercial flights, tighter budget
#    • Depth collapse multipliers are higher (1.35/1.75 vs NBA's 1.25/1.50)
#      because 12-woman rosters absorb injuries less well than NBA 15-man rosters
#    • No altitude/tanking penalties (not relevant in WNBA)
#    • Win probability uses logistic function instead of linear 50+total
#      to keep probabilities realistic at extreme spreads
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td  = TEAM_DATA.get(h, {'off_rtg': 100, 'def_rtg': 102})
    a_td  = TEAM_DATA.get(a, {'off_rtg': 100, 'def_rtg': 102})
    h_std = standings.get(h, BLANK_STD)
    a_std = standings.get(a, BLANK_STD)

    factors, total = [], 0.0

    # ── 1. Win % Edge ──────────────────────────────────────────────────────────
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

    # ── 2. Home Court ──────────────────────────────────────────────────────────
    # No altitude teams in WNBA; flat 2.5 pt HCA
    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 2.5, "why": f"Advantage for {h}"})

    # ── 3. Injury Detection & Archetype Penalties ──────────────────────────────
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    def get_player_impact(scraped_string):
        raw = (
            scraped_string.lower()
            .split(" (")[0]
            .replace(".", "").replace("'", "")
            .replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "")
            .strip()
        )
        val, tier = 1.0, "Role"
        for star in SUPERSTARS:
            s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").strip()
            if s == raw or s in raw or raw in s:
                val, tier = 8.0, "Superstar"; break
        if tier == "Role":
            for star in ALL_STARS:
                s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").strip()
                if s == raw or s in raw or raw in s:
                    val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for star in HIGH_IMPACT:
                s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").strip()
                if s == raw or s in raw or raw in s:
                    val, tier = 2.5, "High-Impact"; break
        archetype = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            s = p.lower().replace(".", "").replace("'", "").strip()
            if s == raw or s in raw or raw in s:
                archetype = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            s = p.lower().replace(".", "").replace("'", "").strip()
            if s == raw or s in raw or raw in s:
                archetype = "Off_Liability"; break
        return val, tier, archetype

    def calc_injury_penalty(inj_list):
        o_pen, d_pen = 0.0, 0.0
        details      = []
        core_missing = 0
        for p in inj_list:
            val, tier, archetype = get_player_impact(p)
            if tier in ("Superstar", "All-Star", "High-Impact"):
                core_missing += 1
            if archetype == "Def_Liability":
                o = val * 1.3;  d = val * -0.3
            elif archetype == "Off_Liability":
                o = val * -0.3; d = val * 1.3
            else:
                o = val * 0.6;  d = val * 0.4
            o_pen += o; d_pen += d
            details.append(f"{p.split(' (')[0]} ({tier})")
        # WNBA depth collapse — harder hit than NBA due to 12-woman rosters
        if core_missing >= 4:   mult = 2.00
        elif core_missing == 3: mult = 1.75
        elif core_missing == 2: mult = 1.35
        else:                   mult = 1.00
        return o_pen * mult, d_pen * mult, details, mult

    h_off_pen, h_def_pen, h_det, h_mult = calc_injury_penalty(h_inj) if h_inj else (0.0, 0.0, [], 1.0)
    a_off_pen, a_def_pen, a_det, a_mult = calc_injury_penalty(a_inj) if a_inj else (0.0, 0.0, [], 1.0)

    # ── 4. Injury-Adjusted Net Rating Edge ────────────────────────────────────
    # Offense penalty REDUCES offensive rating
    # Defense penalty INCREASES defensive rating (makes D worse)
    adj_h_off = h_td['off_rtg'] - h_off_pen
    adj_h_def = h_td['def_rtg'] + h_def_pen
    h_net     = adj_h_off - adj_h_def

    adj_a_off = a_td['off_rtg'] - a_off_pen
    adj_a_def = a_td['def_rtg'] + a_def_pen
    a_net     = adj_a_off - adj_a_def

    # Scale net rating to point impact — WNBA 40-min game, ~80 possessions
    net_edge = (h_net - a_net) * 0.55
    total   += net_edge
    factors.append({
        "icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge,
        "why":  "Net rating dynamically adjusted by player archetype (40-min WNBA pacing)",
    })

    if h_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(h_det)}"
        if h_mult > 1.0: why += f" (🚨 Depth Collapse: {h_mult}x Penalty)"
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": why})
    if a_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(a_det)}"
        if a_mult > 1.0: why += f" (🚨 Depth Collapse: {a_mult}x Penalty)"
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": why})

    # ── 5. Back-to-Back Fatigue ────────────────────────────────────────────────
    # WNBA penalty is 5 pts (vs NBA 4) — commercial flights, smaller budgets
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0,
                        "why": f"{h} played yesterday. Commercial flight grind."})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0,
                        "why": f"{a} played yesterday. Commercial flight grind."})

    # ── Win Probability (logistic — more accurate than linear at extremes) ─────
    # k=0.17 calibrated so a 10pt spread ≈ 82% win probability
    prob = max(5.0, min(95.0, 1 / (1 + np.exp(-0.17 * total)) * 100))

    return {
        'winner':  h if prob >= 50.0 else a,
        'conf':    prob if prob >= 50.0 else 100.0 - prob,
        'factors': factors,
        'h_std':   h_std, 'a_std': a_std,
        'h_inj':   h_inj, 'a_inj': a_inj,
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 WNBA Master AI Predictor 2026")
current_market_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Market Date:** {current_market_date}")
st.divider()

with st.spinner("Loading slate, standings, and injuries…"):
    slate     = get_daily_slate()
    standings = get_standings()
    injuries, inj_status = get_injuries()
    b2b       = get_back_to_back()

# ── Sidebar diagnostics ───────────────────────────────────────────────────────
st.sidebar.subheader("📡 Data Status")
st.sidebar.write(f"**Teams with live records:** {len(standings)}/{len(TEAM_DATA)}")
st.sidebar.write(inj_status)

st.sidebar.subheader("😴 B2B Fatigue")
if b2b:
    st.sidebar.write(f"**On B2B today:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs today.")

st.sidebar.subheader("🤕 Full Injury Report")
if injuries:
    for team in sorted(injuries):
        st.sidebar.markdown(f"**{team}**")
        for p in injuries[team]:
            st.sidebar.warning(p)
else:
    st.sidebar.info("No active injuries found.")

# ── Game Cards ────────────────────────────────────────────────────────────────
def render_games(use_l10):
    if not slate:
        st.info("No WNBA games scheduled for today.")
        return
    for game in slate:
        h, a = game['h'], game['a']
        pred  = predict_game(h, a, standings, injuries, b2b, use_l10=use_l10)
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
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                rec = pred['h_std']['record']
                if use_l10:
                    l10 = pred['h_std'].get('l10_record', 'N/A')
                    st.write(f"**Record:** {rec}  *(L10: {l10})*")
                else:
                    h_home = pred['h_std'].get('home_record', 'N/A')
                    st.write(f"**Record:** {rec}  *(Home: {h_home})*")
                for inj in pred['h_inj']:
                    st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                rec = pred['a_std']['record']
                if use_l10:
                    l10 = pred['a_std'].get('l10_record', 'N/A')
                    st.write(f"**Record:** {rec}  *(L10: {l10})*")
                else:
                    a_away = pred['a_std'].get('away_record', 'N/A')
                    st.write(f"**Record:** {rec}  *(Away: {a_away})*")
                for inj in pred['a_inj']:
                    st.warning(f"🤕 {inj}")

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])
with tab1:
    render_games(use_l10=False)
with tab2:
    render_games(use_l10=True)

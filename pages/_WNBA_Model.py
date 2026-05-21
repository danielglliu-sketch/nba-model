import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta, date

# --- PAGE SETUP ---
st.set_page_config(page_title="WNBA Quant AI 2026", page_icon="🏀", layout="wide")
st.sidebar.title("⚙️ System Tools")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')
yest_date_str   = (selected_date - timedelta(days=1)).strftime('%Y%m%d')
display_date_str = selected_date.strftime('%B %d, %Y')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("WNBA v1.2 | 2026 Season | 15 Teams")

# ─────────────────────────────────────────────────────────────────────────────
# PLAYER TIERS
# ─────────────────────────────────────────────────────────────────────────────
SUPERSTARS = [
    "A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier",
    "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu"
]
ALL_STARS = [
    "Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike",
    "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale",
    "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston",
    "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor", "Azzi Fudd"
]
HIGH_IMPACT = [
    "Natasha Howard", "Marina Mabrey", "Courtney Vandersloot", "Betnijah Laney-Hamilton",
    "Brionna Jones", "Dearica Hamby", "Allisha Gray", "Rhyne Howard", "Kayla McBride",
    "Natasha Cloud", "Kelsey Mitchell", "NaLyssa Smith", "Brittney Griner",
    "Cheyenne Parker-Tyus", "Courtney Williams", "Alanna Smith", "Sophie Cunningham",
    "Kia Nurse", "Lexie Hull"
]
DEFENSIVE_LIABILITIES = [
    "Caitlin Clark", "Arike Ogunbowale", "Kelsey Mitchell", "Marina Mabrey", "Diana Taurasi"
]
OFFENSIVE_LIABILITIES = [
    "Alyssa Thomas", "Ezi Magbegor", "Brianna Turner", "Kiah Stokes"
]

# ─────────────────────────────────────────────────────────────────────────────
# TEAM DATA — Updated for 15-team 2026 season
# Abbreviation normalization covers ESPN's various abbreviations
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LV':   {'off_rtg': 110.5, 'def_rtg': 99.8},
    'NY':   {'off_rtg': 109.2, 'def_rtg': 100.5},
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2},
    'SEA':  {'off_rtg': 103.5, 'def_rtg': 98.8},
    'MIN':  {'off_rtg': 102.8, 'def_rtg': 99.1},
    'IND':  {'off_rtg': 106.5, 'def_rtg': 105.2},
    'DAL':  {'off_rtg': 105.1, 'def_rtg': 104.8},
    'ATL':  {'off_rtg': 100.2, 'def_rtg': 101.5},
    'PHO':  {'off_rtg': 99.5,  'def_rtg': 106.1},
    'CHI':  {'off_rtg': 98.2,  'def_rtg': 103.5},
    'LA':   {'off_rtg': 96.8,  'def_rtg': 105.2},
    'WAS':  {'off_rtg': 97.5,  'def_rtg': 108.4},
    'GS':   {'off_rtg': 101.0, 'def_rtg': 103.0},   # Golden State Valkyries
    'POR':  {'off_rtg': 98.0,  'def_rtg': 104.5},   # Portland Fire (expansion)
    'TOR':  {'off_rtg': 99.0,  'def_rtg': 104.0},   # Toronto Tempo (expansion)
}

BLANK_STD = {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': 'N/A'}

def norm(abbr):
    """Normalize ESPN's varying abbreviations to our internal keys."""
    mapping = {
        'LVA': 'LV',  'NYL': 'NY',  'CON': 'CONN', 'PHX': 'PHO',
        'LAS': 'LA',  'MINN': 'MIN','GSV': 'GS',   'GST': 'GS',
        'GOLST': 'GS','PORT': 'POR','TOR': 'TOR',
    }
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# SCOREBOARD — used for both today's slate AND building standings
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_scoreboard(date_string):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}"
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {}

@st.cache_data(ttl=300)
def get_daily_slate(date_string):
    data = get_scoreboard(date_string)
    games = []
    for event in data.get('events', []):
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
# STANDINGS — extracted from scoreboard competitor records
#
# FIX: ESPN's /standings endpoint returns almost nothing in 2026.
# Instead we scan the last 14 days of scoreboards; each competitor
# has a "records" array with {"type": "total", "summary": "W-L"}.
# We take the most recent appearance of each team.
# ─────────────────────────────────────────────────────────────────────────────
def _parse_record_from_competitor(comp):
    """Pull overall W-L from an ESPN competitor block."""
    for rec in comp.get('records', []):
        rtype = rec.get('type', '')
        rname = rec.get('name', '').lower()
        if rtype == 'total' or rname in ('overall', 'total'):
            summary = rec.get('summary', '')
            if '-' in summary:
                try:
                    w, l = map(int, summary.split('-'))
                    return w, l, summary
                except:
                    pass
    return None

@st.cache_data(ttl=600)
def get_standings():
    standings = {}
    today = date.today()
    errors = []

    # Scan up to 14 days back to find each team's most recent record
    for days_back in range(0, 15):
        if len(standings) >= len(TEAM_DATA):
            break
        check_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
        data = get_scoreboard(check_date)
        if not data.get('events'):
            continue
        for event in data['events']:
            for comp in event['competitions'][0]['competitors']:
                abbr = norm(comp['team']['abbreviation'])
                if abbr in standings:
                    continue  # already have a more recent entry
                result = _parse_record_from_competitor(comp)
                if result:
                    w, l, summary = result
                    win_pct = w / (w + l) if (w + l) > 0 else 0.5
                    standings[abbr] = {
                        'wins': w, 'losses': l, 'record': summary,
                        'win_pct': win_pct, 'l10_pct': win_pct, 'l10_record': 'N/A',
                    }

    if standings:
        return standings
    # Hard fallback — neutral 0-0 so at least records show something real
    return {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# INJURIES
#
# FIX: CBS scraper was silently failing (bot block / changed HTML).
# Strategy:
#   1. Try ESPN /wnba/injuries HTML (primary — structured tables)
#   2. Try CBS Sports /wnba/injuries/ HTML (fallback)
#   3. Return {} with a visible warning if both fail
# ─────────────────────────────────────────────────────────────────────────────
INJURY_SKIP = {'active', 'probable', 'expected to play'}
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

def _scrape_espn_injuries():
    """Scrape https://www.espn.com/wnba/injuries"""
    from bs4 import BeautifulSoup
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get("https://www.espn.com/wnba/injuries", headers=headers, timeout=8)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    result = {}

    # ESPN injuries page: each team block has an <h2>/<h3> with team name
    # followed by a <table> of players
    # Structure varies — try multiple patterns
    for section in soup.select('section.injuries-table, div.ResponsiveTable'):
        # Team name: look for a headline sibling or parent heading
        heading = section.find_previous(['h2', 'h3', 'h4'])
        abbr = _match_team(heading.get_text() if heading else '') if heading else None

        if not abbr:
            cap = section.find(class_=lambda c: c and 'Caption' in c)
            if cap:
                abbr = _match_team(cap.get_text())

        if not abbr:
            continue

        players = []
        for row in section.select('tr'):
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            name = cells[0].get_text(strip=True)
            # status is typically last or second-to-last column
            status = cells[-1].get_text(strip=True)
            injury_type = cells[-2].get_text(strip=True) if len(cells) >= 2 else 'Injury'
            if not name or status.lower() in INJURY_SKIP:
                continue
            players.append(f"{name} ({injury_type} — {status})")
        if players:
            result[abbr] = players

    return result

def _scrape_cbs_injuries():
    """Scrape https://www.cbssports.com/wnba/injuries/ as fallback."""
    from bs4 import BeautifulSoup
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get("https://www.cbssports.com/wnba/injuries/", headers=headers, timeout=8)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    result = {}

    for table in soup.find_all('div', class_='TableBase'):
        # Team name
        team_el = (table.find('span', class_='TeamName') or
                   table.find(class_='TeamLogoNameLockup-name') or
                   table.find(class_='TeamName'))
        abbr = _match_team(team_el.get_text() if team_el else '')
        if not abbr:
            continue

        players = []
        for row in table.find_all('tr', class_='TableBase-bodyTr'):
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            name_el = (cols[0].find('span', class_='CellPlayerName--long') or
                       cols[0].find('a') or cols[0])
            name   = name_el.get_text(strip=True)
            injury = cols[3].get_text(strip=True)
            status = cols[4].get_text(strip=True)
            if status.lower() in INJURY_SKIP:
                continue
            players.append(f"{name} ({injury} — {status})")
        if players:
            result[abbr] = players

    return result

@st.cache_data(ttl=600)
def get_injuries():
    sources = [
        ("ESPN", _scrape_espn_injuries),
        ("CBS Sports", _scrape_cbs_injuries),
    ]
    for name, fn in sources:
        try:
            data = fn()
            if data:   # non-empty = success
                return data, f"✅ Injuries loaded from {name}"
        except Exception as e:
            continue
    return {}, "⚠️ Injury data unavailable (both ESPN and CBS blocked or changed structure)"

@st.cache_data(ttl=600)
def get_back_to_back(yest_date_string):
    b2b = set()
    data = get_scoreboard(yest_date_string)
    for event in data.get('events', []):
        for c in event['competitions'][0]['competitors']:
            b2b.add(norm(c['team']['abbreviation']))
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td  = TEAM_DATA.get(h, {'off_rtg': 100, 'def_rtg': 100})
    a_td  = TEAM_DATA.get(a, {'off_rtg': 100, 'def_rtg': 100})
    h_std = standings.get(h, BLANK_STD)
    a_std = standings.get(a, BLANK_STD)

    factors, total = [], 0.0

    # 1. Win % Edge
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']
    if use_l10:
        h_pct = h_pct * 0.7 + h_std.get('l10_pct', h_pct) * 0.3
        a_pct = a_pct * 0.7 + a_std.get('l10_pct', a_pct) * 0.3
    base_adj = (h_pct - a_pct) * 20.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Blended Win% Edge (L10)" if use_l10 else "Win % Edge",
                    "adj": base_adj, "why": f"{h} {h_std['record']} vs {a} {a_std['record']}"})

    # 2. Home Court
    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 2.5, "why": f"Advantage for {h}"})

    # 3. Injury penalties
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    def player_impact(s):
        raw = s.lower().split(" (")[0].replace(".", "").replace("'", "").strip()
        val, tier = 1.0, "Role"
        for p in SUPERSTARS:
            if p.lower().replace(".", "").replace("'", "") in raw:
                return 8.0, "Superstar", next(
                    ("Def_Liability" if p in DEFENSIVE_LIABILITIES else
                     "Off_Liability" if p in OFFENSIVE_LIABILITIES else "Balanced"), "Balanced")
        for p in ALL_STARS:
            if p.lower().replace(".", "").replace("'", "") in raw:
                val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for p in HIGH_IMPACT:
                if p.lower().replace(".", "").replace("'", "") in raw:
                    val, tier = 2.5, "High-Impact"; break
        arch = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                arch = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                arch = "Off_Liability"; break
        return val, tier, arch

    def injury_penalty(inj_list):
        o, d, details, core = 0.0, 0.0, [], 0
        for p in inj_list:
            val, tier, arch = player_impact(p)
            if tier != "Role":
                core += 1
            if arch == "Def_Liability":
                o += val * 1.3; d += val * -0.3
            elif arch == "Off_Liability":
                o += val * -0.3; d += val * 1.3
            else:
                o += val * 0.6; d += val * 0.4
            details.append(f"{p.split(' (')[0]} ({tier})")
        mult = 1.35 if core == 2 else 1.75 if core >= 3 else 1.0
        return o * mult, d * mult, details, mult

    h_op, h_dp, h_det, h_mult = injury_penalty(h_inj)
    a_op, a_dp, a_det, a_mult = injury_penalty(a_inj)

    # 4. Net Rating Edge
    h_net = (h_td['off_rtg'] - h_op) - (h_td['def_rtg'] + h_dp)
    a_net = (a_td['off_rtg'] - a_op) - (a_td['def_rtg'] + a_dp)
    net_edge = ((h_net - a_net) / 100.0) * 82.0 * 0.6
    total += net_edge
    factors.append({"icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge,
                    "why": "Adjusted for 40-minute WNBA pacing"})

    if h_inj:
        why = f"Missing: {', '.join(h_det)}"
        if h_mult > 1: why += f" 🚨 Depth collapse ×{h_mult}"
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": why})
    if a_inj:
        why = f"Missing: {', '.join(a_det)}"
        if a_mult > 1: why += f" 🚨 Depth collapse ×{a_mult}"
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": why})

    # 5. Back-to-back fatigue
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0, "why": "Played yesterday"})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0, "why": "Played yesterday"})

    prob = max(5.0, min(95.0, 1 / (1 + np.exp(-0.17 * total)) * 100))
    return {
        'winner': h if prob >= 50 else a,
        'conf':   prob if prob >= 50 else 100 - prob,
        'factors': factors,
        'h_std': h_std, 'a_std': a_std,
        'h_inj': h_inj, 'a_inj': a_inj,
    }

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 WNBA Quant AI v1.2")
st.markdown(f"**Market Date:** {display_date_str}")
st.divider()

with st.spinner("Fetching slate, standings, and injuries…"):
    slate      = get_daily_slate(target_date_str)
    standings  = get_standings()
    injuries, inj_status = get_injuries()
    b2b        = get_back_to_back(yest_date_str)

# Sidebar diagnostics
st.sidebar.subheader("📡 Data Status")
st.sidebar.write(f"**Teams with records:** {len(standings)}/15")
st.sidebar.write(inj_status)

st.sidebar.subheader("📊 Fatigue Status")
if b2b:
    st.sidebar.write(f"**Teams on B2B:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs.")

st.sidebar.subheader("🤕 Injury Report")
if injuries:
    for team, players in sorted(injuries.items()):
        st.sidebar.markdown(f"**{team}**")
        for p in players:
            st.sidebar.warning(p)
else:
    st.sidebar.info("No active injuries found.")

def render_games(use_l10):
    if not slate:
        st.info(f"No games found for {display_date_str}.")
        return
    for game in slate:
        h, a = game['h'], game['a']
        pred = predict_game(h, a, standings, injuries, b2b, use_l10=use_l10)
        label = f"{game['h_name']} vs {game['a_name']}  |  Winner: **{pred['winner']}** ({pred['conf']:.1f}%)"
        with st.expander(label):
            st.markdown(f"### 🏆 {pred['winner']} Wins")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888"
                st.markdown(
                    f"{f['icon']} **{f['name']}**: "
                    f"<span style='color:{color};font-weight:bold'>{f['adj']:+.1f} pts</span>"
                    f" — {f['why']}",
                    unsafe_allow_html=True,
                )
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                rec = pred['h_std']['record']
                l10 = pred['h_std'].get('l10_record', 'N/A')
                st.write(f"**Record:** {rec}" + (f"  *(L10: {l10})*" if use_l10 else ""))
                for inj in pred['h_inj']:
                    st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                rec = pred['a_std']['record']
                l10 = pred['a_std'].get('l10_record', 'N/A')
                st.write(f"**Record:** {rec}" + (f"  *(L10: {l10})*" if use_l10 else ""))
                for inj in pred['a_inj']:
                    st.warning(f"🤕 {inj}")

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])
with tab1:
    render_games(use_l10=False)
with tab2:
    render_games(use_l10=True)

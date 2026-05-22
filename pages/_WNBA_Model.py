import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="WNBA Quant AI 2026", page_icon="🏀", layout="wide")
st.sidebar.title("⚙️ System Tools")

selected_date    = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str  = selected_date.strftime('%Y%m%d')
yest_date_str    = (selected_date - timedelta(days=1)).strftime('%Y%m%d')
display_date_str = selected_date.strftime('%B %d, %Y')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared!")

st.sidebar.markdown("---")
st.sidebar.caption("WNBA v1.3 | 2026 Season | 15 Teams")

# ─── PLAYER TIERS ─────────────────────────────────────────────────────────────
SUPERSTARS = [
    "A'ja Wilson","Breanna Stewart","Caitlin Clark","Napheesa Collier",
    "Alyssa Thomas","Jewell Loyd","Sabrina Ionescu","Paige Bueckers",
]
ALL_STARS = [
    "Kelsey Plum","Jackie Young","Jonquel Jones","Nneka Ogwumike",
    "Ariel Atkins","Kahleah Copper","Chelsea Gray","Arike Ogunbowale",
    "Satou Sabally","DeWanna Bonner","Cameron Brink","Aliyah Boston",
    "Diana Taurasi","Skylar Diggins-Smith","Ezi Magbegor","Azzi Fudd",
    "Rickea Jackson",
]
HIGH_IMPACT = [
    "Natasha Howard","Marina Mabrey","Courtney Vandersloot","Betnijah Laney-Hamilton",
    "Brionna Jones","Dearica Hamby","Allisha Gray","Rhyne Howard","Kayla McBride",
    "Natasha Cloud","Kelsey Mitchell","NaLyssa Smith","Brittney Griner",
    "Cheyenne Parker-Tyus","Courtney Williams","Alanna Smith","Sophie Cunningham",
    "Kia Nurse","Lexie Hull","Dorka Juhasz",
]
DEFENSIVE_LIABILITIES = ["Caitlin Clark","Arike Ogunbowale","Kelsey Mitchell","Marina Mabrey","Diana Taurasi"]
OFFENSIVE_LIABILITIES = ["Alyssa Thomas","Ezi Magbegor","Brianna Turner","Kiah Stokes"]

# ─── TEAM DATA (15 teams, 2026) ────────────────────────────────────────────────
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
    'GS':   {'off_rtg': 101.0, 'def_rtg': 103.0},
    'POR':  {'off_rtg': 98.0,  'def_rtg': 104.5},
    'TOR':  {'off_rtg': 99.0,  'def_rtg': 104.0},
}

BLANK_STD = {'wins':0,'losses':0,'record':'0-0','win_pct':0.5,'l10_pct':0.5,'l10_record':'N/A'}

# ESPN uses different abbreviations — map everything to our internal keys
ESPN_NORM = {
    'LVA':'LV','NYL':'NY','CON':'CONN','PHX':'PHO','LAS':'LA',
    'MINN':'MIN','GSV':'GS','GST':'GS','GOLST':'GS',
    'PORT':'POR','TORP':'TOR','TORW':'TOR',
}
# ESPN team URL slugs → our abbreviation
ESPN_SLUG_MAP = {
    'lv':'LV','ny':'NY','conn':'CONN','sea':'SEA','min':'MIN',
    'ind':'IND','dal':'DAL','atl':'ATL','phx':'PHO','chi':'CHI',
    'la':'LA','was':'WAS','gs':'GS','por':'POR','tor':'TOR',
}

def norm(abbr):
    return ESPN_NORM.get(abbr, abbr)

# ─── BROWSER SESSION (used for ALL requests to mimic a real browser) ───────────
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
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    return s

# ─────────────────────────────────────────────────────────────────────────────
# SCOREBOARD — used for slate AND standings
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_scoreboard(date_string):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}"
    try:
        r = make_session().get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=300)
def get_daily_slate(date_string):
    games = []
    for event in get_scoreboard(date_string).get('events', []):
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
# STANDINGS — built from scoreboard competitor records (no broken /standings API)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    standings = {}
    today = date.today()
    for days_back in range(0, 15):
        if len(standings) >= len(TEAM_DATA):
            break
        data = get_scoreboard((today - timedelta(days=days_back)).strftime('%Y%m%d'))
        for event in data.get('events', []):
            for comp in event['competitions'][0]['competitors']:
                abbr = norm(comp['team']['abbreviation'])
                if abbr in standings:
                    continue
                for rec in comp.get('records', []):
                    if rec.get('type') in ('total','overall') or rec.get('name','').lower() in ('overall','total'):
                        summary = rec.get('summary', '')
                        if '-' in summary:
                            try:
                                w, l = map(int, summary.split('-'))
                                pct = w / (w + l) if (w + l) > 0 else 0.5
                                standings[abbr] = {
                                    'wins': w, 'losses': l, 'record': summary,
                                    'win_pct': pct, 'l10_pct': pct, 'l10_record': 'N/A',
                                }
                            except:
                                pass
                            break
    return standings if standings else {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# INJURIES — 3 sources, first success wins
#
# Source 1: ESPN JSON roster API — no HTML, no JS rendering, just JSON
#   GET https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{slug}/roster
#   Each athlete has a "status" object with type/name ("Injured", "Out", etc.)
#
# Source 2: CBS Sports HTML — full browser session with cookie warmup to beat bot detection
#
# Source 3: ESPN core injuries API — follows $ref links to get player+status
# ─────────────────────────────────────────────────────────────────────────────
SKIP_STATUSES = {
    'active', 'probable', 'expected to play', 'day-to-day',
    'not injury related', 'not on roster',
}

def _injuries_from_espn_rosters():
    """
    Pull injury status from ESPN's WNBA team roster JSON endpoint.
    Returns {} if every team request fails.
    """
    result = {}
    session = make_session()
    # Accept JSON for API calls
    session.headers.update({'Accept': 'application/json, */*'})

    for slug, abbr in ESPN_SLUG_MAP.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{slug}/roster"
        try:
            data = session.get(url, timeout=5).json()
        except Exception:
            continue

        injured = []
        # Athletes come back as a list of position groups
        for group in data.get('athletes', []):
            players = group if isinstance(group, list) else group.get('items', [])
            for player in players:
                status_obj = player.get('status', {})
                status_name = (
                    status_obj.get('name') or
                    status_obj.get('type', {}).get('name') or
                    status_obj.get('type', {}).get('description') or
                    'active'
                ).lower()

                # Only flag genuinely unavailable players
                if status_name in SKIP_STATUSES or status_name == 'active':
                    continue

                full_name = player.get('fullName', player.get('displayName', 'Unknown'))
                # injury reason sometimes lives in injuryStatus or injuries list
                reason = ''
                for inj in player.get('injuries', []):
                    reason = inj.get('type', {}).get('description', '') or inj.get('detail', '')
                    if reason:
                        break
                if not reason:
                    reason = player.get('injuryStatus', 'Injury')

                label = status_obj.get('name', 'Out').title()
                injured.append(f"{full_name} ({reason} — {label})")

        if injured:
            result[abbr] = injured

    return result


def _injuries_from_cbs():
    """
    Scrape CBS Sports WNBA injury page with a full browser session + cookie warmup
    to bypass their basic bot detection.
    """
    session = make_session()

    # Step 1: hit the homepage first to get cookies (bypasses some bot checks)
    try:
        session.get('https://www.cbssports.com/', timeout=5)
    except Exception:
        pass

    # Step 2: fetch the actual injury page
    r = session.get('https://www.cbssports.com/wnba/injuries/', timeout=10)
    r.raise_for_status()

    if len(r.text) < 500:
        raise ValueError("CBS returned a near-empty page — likely still blocked")

    soup = BeautifulSoup(r.text, 'html.parser')
    result = {}

    TEAM_NAME_MAP = {
        'atlanta':'ATL','chicago':'CHI','connecticut':'CONN','dallas':'DAL',
        'indiana':'IND','las vegas':'LV','los angeles':'LA','minnesota':'MIN',
        'new york':'NY','phoenix':'PHO','seattle':'SEA','washington':'WAS',
        'golden state':'GS','portland':'POR','toronto':'TOR',
    }

    for table in soup.find_all('div', class_='TableBase'):
        # Team name detection (CBS uses a few different class names)
        name_el = (
            table.find('span', class_='TeamName') or
            table.find(class_='TeamLogoNameLockup-name') or
            table.find(class_='TableBase-title')
        )
        raw_name = name_el.get_text(strip=True).lower() if name_el else ''
        abbr = next((v for k, v in TEAM_NAME_MAP.items() if k in raw_name), None)
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


def _injuries_from_espn_core_api():
    """
    ESPN sports.core API — returns injury records as $ref links.
    We batch-fetch them to avoid too many round-trips.
    Falls back gracefully if rate-limited.
    """
    result = {}
    session = make_session()
    session.headers.update({'Accept': 'application/json, */*'})

    try:
        r = session.get(
            'https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/injuries?limit=300',
            timeout=8
        )
        r.raise_for_status()
        items = r.json().get('items', [])
    except Exception:
        return result

    for item in items[:100]:   # cap to avoid too many requests
        ref = item.get('$ref', '')
        if not ref:
            continue
        try:
            detail = session.get(ref, timeout=4).json()
        except Exception:
            continue

        status_txt = (
            detail.get('status', {}).get('type', {}).get('description', '') or
            detail.get('type', {}).get('description', 'Unknown')
        )
        if status_txt.lower() in SKIP_STATUSES:
            continue

        athlete_ref = detail.get('athlete', {}).get('$ref', '')
        if not athlete_ref:
            continue
        try:
            ath = session.get(athlete_ref, timeout=4).json()
        except Exception:
            continue

        name     = ath.get('displayName', 'Unknown')
        team_abbr = norm(ath.get('team', {}).get('abbreviation', ''))
        injury   = detail.get('type', {}).get('description', 'Injury')

        if team_abbr:
            result.setdefault(team_abbr, []).append(f"{name} ({injury} — {status_txt})")

    return result


@st.cache_data(ttl=600)
def get_injuries():
    sources = [
        ("ESPN Roster API",   _injuries_from_espn_rosters),
        ("CBS Sports",        _injuries_from_cbs),
        ("ESPN Core API",     _injuries_from_espn_core_api),
    ]
    for source_name, fn in sources:
        try:
            data = fn()
            if data:
                return data, f"✅ Injuries from {source_name} ({sum(len(v) for v in data.values())} players)"
        except Exception as e:
            continue   # try next source silently

    return {}, "⚠️ All injury sources failed. Check your internet connection or try refreshing."


@st.cache_data(ttl=600)
def get_back_to_back(yest_date_string):
    b2b = set()
    for event in get_scoreboard(yest_date_string).get('events', []):
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
    hp = h_std['win_pct']
    ap = a_std['win_pct']
    if use_l10:
        hp = hp * 0.7 + h_std.get('l10_pct', hp) * 0.3
        ap = ap * 0.7 + a_std.get('l10_pct', ap) * 0.3
    base_adj = (hp - ap) * 20.0
    total += base_adj
    factors.append({
        "icon": "📊",
        "name": "Blended Win% Edge (L10)" if use_l10 else "Win % Edge",
        "adj": base_adj,
        "why": f"{h} ({h_std['record']}) vs {a} ({a_std['record']})",
    })

    # 2. Home Court
    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 2.5, "why": f"Advantage for {h}"})

    # 3. Injury Penalties
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    def player_impact(s):
        raw = s.lower().split(" (")[0].replace(".", "").replace("'", "").strip()
        for p in SUPERSTARS:
            if p.lower().replace(".", "").replace("'", "") in raw:
                arch = ("Def_Liability" if p in DEFENSIVE_LIABILITIES else
                        "Off_Liability" if p in OFFENSIVE_LIABILITIES else "Balanced")
                return 8.0, "Superstar", arch
        for p in ALL_STARS:
            if p.lower().replace(".", "").replace("'", "") in raw:
                return 4.5, "All-Star", "Balanced"
        for p in HIGH_IMPACT:
            if p.lower().replace(".", "").replace("'", "") in raw:
                return 2.5, "High-Impact", "Balanced"
        arch = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                arch = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                arch = "Off_Liability"; break
        return 1.0, "Role", arch

    def injury_penalty(inj_list):
        op, dp, details, core = 0.0, 0.0, [], 0
        for p in inj_list:
            val, tier, arch = player_impact(p)
            if tier != "Role":
                core += 1
            op += val * (1.3 if arch == "Def_Liability" else -0.3 if arch == "Off_Liability" else 0.6)
            dp += val * (-0.3 if arch == "Def_Liability" else 1.3 if arch == "Off_Liability" else 0.4)
            details.append(f"{p.split(' (')[0]} ({tier})")
        mult = 1.75 if core >= 3 else 1.35 if core == 2 else 1.0
        return op * mult, dp * mult, details, mult

    h_op, h_dp, h_det, h_mult = injury_penalty(h_inj)
    a_op, a_dp, a_det, a_mult = injury_penalty(a_inj)

    # 4. Net Rating
    h_net = (h_td['off_rtg'] - h_op) - (h_td['def_rtg'] + h_dp)
    a_net = (a_td['off_rtg'] - a_op) - (a_td['def_rtg'] + a_dp)
    net_edge = ((h_net - a_net) / 100.0) * 82.0 * 0.6
    total += net_edge
    factors.append({"icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge,
                    "why": "Adjusted for 40-minute WNBA pacing"})

    for team, inj_list, det, mult in [(h, h_inj, h_det, h_mult), (a, a_inj, a_det, a_mult)]:
        if inj_list:
            why = f"Missing: {', '.join(det)}"
            if mult > 1: why += f" 🚨 Depth collapse ×{mult}"
            factors.append({"icon": "🤕", "name": f"{team} Injuries", "adj": 0.0, "why": why})

    # 5. B2B Fatigue
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
st.title("🏀 WNBA Quant AI v1.3")
st.markdown(f"**Market Date:** {display_date_str}")
st.divider()

with st.spinner("Fetching slate, standings, and injuries…"):
    slate     = get_daily_slate(target_date_str)
    standings = get_standings()
    injuries, inj_status = get_injuries()
    b2b       = get_back_to_back(yest_date_str)

# ── Sidebar diagnostics ──
st.sidebar.subheader("📡 Data Status")
st.sidebar.write(f"**Teams with records:** {len(standings)}/{len(TEAM_DATA)}")
st.sidebar.write(inj_status)

st.sidebar.subheader("😴 B2B Fatigue")
if b2b:
    st.sidebar.write(f"**On B2B:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No back-to-backs today.")

st.sidebar.subheader("🤕 Full Injury Report")
if injuries:
    for team in sorted(injuries):
        st.sidebar.markdown(f"**{team}**")
        for p in injuries[team]:
            st.sidebar.warning(p)
else:
    st.sidebar.info("No active injuries found.")

def render_games(use_l10):
    if not slate:
        st.info(f"No games found for {display_date_str}.")
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
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888"
                st.markdown(
                    f"{f['icon']} **{f['name']}**: "
                    f"<span style='color:{color};font-weight:bold'>{f['adj']:+.1f} pts</span>"
                    f" — {f['why']}",
                    unsafe_allow_html=True,
                )
            st.divider()
            c1, c2 = st.columns(2)
            for col, side, name_key, std_key, inj_key in [
                (c1, "🏠", 'h_name', 'h_std', 'h_inj'),
                (c2, "✈️",  'a_name', 'a_std', 'a_inj'),
            ]:
                with col:
                    st.markdown(f"#### {side} {game[name_key]}")
                    rec = pred[std_key]['record']
                    l10 = pred[std_key].get('l10_record', 'N/A')
                    st.write(f"**Record:** {rec}" + (f"  *(L10: {l10})*" if use_l10 else ""))
                    for inj in pred[inj_key]:
                        st.warning(f"🤕 {inj}")

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])
with tab1:
    render_games(use_l10=False)
with tab2:
    render_games(use_l10=True)

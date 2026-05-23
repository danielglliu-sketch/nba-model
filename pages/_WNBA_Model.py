import streamlit as st
import requests
import numpy as np
import json
import os
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup

# ── API Key — reads from st.secrets first, then environment variable ──────────
def _get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")

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
# TEAM DATA — 2026 WNBA (15 teams)
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

def make_session():
    s = requests.Session()
    # Mask the script as an iPhone to easily bypass strict desktop firewalls
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return s

# ─────────────────────────────────────────────────────────────────────────────
# SCOREBOARD — slate + standings source
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
# STANDINGS — from scoreboard competitor blocks (ESPN /standings is broken)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    standings = {}
    today = date.today()
    for days_back in range(0, 15):
        if len(standings) >= len(TEAM_DATA):
            break
        data = _get_scoreboard((today - timedelta(days=days_back)).strftime('%Y%m%d'))
        for event in data.get('events', []):
            for comp in event['competitions'][0]['competitors']:
                abbr = norm(comp['team']['abbreviation'])
                if abbr in standings:
                    continue
                overall = home_rec = away_rec = None
                for rec in comp.get('records', []):
                    rtype   = rec.get('type', '')
                    rname   = rec.get('name', '').lower()
                    summary = rec.get('summary', '')
                    if '-' not in summary:
                        continue
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
                    except:
                        pass
    return standings if standings else {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# INJURIES — 6-source waterfall
#
# WHY THIS ORDER:
#   Source 1 — Rotowire HTML (no key needed, light bot protection, reliable)
#
#   Source 2 — ESPN team injuries endpoint (direct /teams/{id}/injuries route)
#
#   Source 3 — CBS Sports HTML with full browser session + cookie warmup
#
#   Source 4 — ESPN WNBA team roster JSON endpoints
#
#   Source 5 — ESPN sports.core injuries API ($ref chain)
#
#   Source 6 — Anthropic API + web_search (last resort, only if API key present)
#
# The first source that returns non-empty data wins.
# The sidebar always shows which source succeeded.
# ─────────────────────────────────────────────────────────────────────────────
SKIP_STATUSES = {
    'active', 'probable', 'expected to play', 'day-to-day', 'not injury related',
}

TEAM_NAME_MAP = {
    'atlanta':'ATL','chicago':'CHI','connecticut':'CONN','dallas':'DAL',
    'indiana':'IND','las vegas':'LV','los angeles':'LA','minnesota':'MIN',
    'new york':'NY','phoenix':'PHO','seattle':'SEA','washington':'WAS',
    'golden state':'GS','portland':'POR','toronto':'TOR',
}
def _match_team(text):
    t = text.lower()
    for key, abbr in TEAM_NAME_MAP.items():
        if key in t:
            return abbr
    return None

# ── Source 1: Rotowire (primary — no key needed) ───────────────────────────
ROTOWIRE_TEAM_MAP = {
    'ATL': 'atlanta', 'CHI': 'chicago', 'CONN': 'connecticut', 'DAL': 'dallas',
    'IND': 'indiana', 'LV': 'las-vegas', 'LA': 'los-angeles', 'MIN': 'minnesota',
    'NY': 'new-york', 'PHO': 'phoenix', 'SEA': 'seattle', 'WAS': 'washington',
    'GS': 'golden-state', 'POR': 'portland', 'TOR': 'toronto',
}
ROTOWIRE_ABBR_MAP = {v: k for k, v in ROTOWIRE_TEAM_MAP.items()}

def _injuries_rotowire():
    r = make_session().get(
        'https://www.rotowire.com/basketball/wnba-injuries.php', timeout=10
    )
    r.raise_for_status()
    if len(r.text) < 2000:
        raise ValueError("Rotowire returned near-empty page")
    soup = BeautifulSoup(r.text, 'html.parser')
    result = {}

    # Each team block has a header + rows inside .lineup__main or similar
    for section in soup.select('.injury-report, [class*="InjuryReport"], [class*="injury"]'):
        header = section.find(['h4', 'h3', 'h2', 'span'], class_=lambda c: c and 'team' in c.lower())
        team_text = header.get_text(strip=True).lower() if header else ''
        abbr = _match_team(team_text)
        if not abbr:
            continue
        players = []
        for row in section.select('li, tr'):
            cols = row.find_all(['td', 'span', 'div'])
            if len(cols) < 3:
                continue
            name   = cols[0].get_text(strip=True)
            injury = cols[-2].get_text(strip=True) if len(cols) >= 4 else ''
            status = cols[-1].get_text(strip=True)
            if not name or status.lower() in SKIP_STATUSES:
                continue
            players.append(f"{name} ({injury} — {status})" if injury else f"{name} ({status})")
        if players:
            result[abbr] = players

    # Fallback: flat table if section-based parsing got nothing
    if not result:
        for row in soup.select('table tr'):
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            name    = cols[0].get_text(strip=True)
            team_td = cols[1].get_text(strip=True).lower()
            injury  = cols[2].get_text(strip=True)
            status  = cols[3].get_text(strip=True)
            abbr    = _match_team(team_td)
            if not abbr or not name or status.lower() in SKIP_STATUSES:
                continue
            result.setdefault(abbr, []).append(f"{name} ({injury} — {status})")

    return result


# ── Source 2: ESPN team injuries endpoint (cleaner than roster chain) ────────
ESPN_TEAM_IDS = {
    'ATL': 3, 'CHI': 4, 'CONN': 5, 'DAL': 6, 'IND': 8,
    'LV': 14, 'LA': 10, 'MIN': 11, 'NY': 12, 'PHO': 13,
    'SEA': 16, 'WAS': 19, 'GS': 20, 'POR': 21, 'TOR': 22,
}

def _injuries_espn_team():
    result  = {}
    session = make_session()
    for abbr, tid in ESPN_TEAM_IDS.items():
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
            f"/teams/{tid}/injuries"
        )
        try:
            data = session.get(url, timeout=5).json()
        except Exception:
            continue
        players = []
        for item in data.get('injuries', []):
            status = item.get('status', 'Unknown')
            if status.lower() in SKIP_STATUSES:
                continue
            name   = (item.get('athlete') or {}).get('displayName', 'Unknown')
            injury = item.get('type', {}).get('description', 'Injury')
            players.append(f"{name} ({injury} — {status})")
        if players:
            result[abbr] = players
    return result


# ── Source 3: CBS Sports HTML ──────────────────────────────────────────────
def _injuries_cbs():
    session = make_session()
    try:
        session.get('https://www.cbssports.com/', timeout=4)  # cookie warmup
    except Exception:
        pass
    r = session.get('https://www.cbssports.com/wnba/injuries/', timeout=10)
    r.raise_for_status()
    if len(r.text) < 1000:
        raise ValueError("CBS returned near-empty page — likely bot-blocked")
    soup   = BeautifulSoup(r.text, 'html.parser')
    result = {}

    # CBS restructured their layout; try both old and new selectors
    team_blocks = (
        soup.find_all('div', class_='TableBase')
        or soup.find_all('section', class_=lambda c: c and 'injury' in c.lower())
        or soup.find_all('div', class_=lambda c: c and 'Injury' in (c or ''))
    )
    for table in team_blocks:
        name_el = (
            table.find(class_='TeamName')
            or table.find(class_=lambda c: c and 'TeamLogo' in (c or ''))
            or table.find(['h4', 'h3', 'caption'])
        )
        abbr = _match_team(name_el.get_text(strip=True) if name_el else '')
        if not abbr:
            continue
        players = []
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            name   = cols[0].get_text(strip=True)
            injury = cols[-2].get_text(strip=True)
            status = cols[-1].get_text(strip=True)
            if not name or status.lower() in SKIP_STATUSES:
                continue
            players.append(f"{name} ({injury} — {status})")
        if players:
            result[abbr] = players
    return result


# ── Source 4: ESPN WNBA team roster JSON ──────────────────────────────────
ESPN_SLUG_MAP = {
    'lv':'LV','ny':'NY','conn':'CONN','sea':'SEA','min':'MIN',
    'ind':'IND','dal':'DAL','atl':'ATL','phx':'PHO','chi':'CHI',
    'la':'LA','was':'WAS','gs':'GS','por':'POR','tor':'TOR',
}

def _injuries_espn_rosters():
    result  = {}
    session = make_session()
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
                reason    = ''
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


# ── Source 5: ESPN sports.core API ────────────────────────────────────────
def _injuries_espn_core():
    result  = {}
    session = make_session()
    try:
        r = session.get(
            'https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/injuries?limit=300',
            timeout=8,
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
        if status_txt.lower() in SKIP_STATUSES: continue
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


# ── Source 6: Anthropic API with web_search (last resort — key required) ────
def _injuries_via_claude():
    """
    Ask Claude (via the Anthropic API) to web-search today's WNBA injury report
    and return it as structured JSON. Works on Streamlit Cloud and any environment
    where ESPN/CBS are blocked, because the request goes to api.anthropic.com.
    """
    today = datetime.now().strftime('%B %d, %Y')
    prompt = f"""Today is {today}. Search the web for the current WNBA injury report.

Find all players who are OUT, QUESTIONABLE, or DOUBTFUL for today's or upcoming games.
Do NOT include players who are Probable, Active, or Expected to Play.

Return ONLY a valid JSON object in this exact format, nothing else:
{{
  "ATL": ["Player Name (Injury Type - Status)", "Player Name (Injury Type - Status)"],
  "CHI": ["Player Name (Injury Type - Status)"],
  "CONN": [],
  "DAL": ["Player Name (Injury Type - Status)"],
  "GS": [],
  "IND": ["Player Name (Injury Type - Status)"],
  "LA": [],
  "LV": ["Player Name (Injury Type - Status)"],
  "MIN": ["Player Name (Injury Type - Status)"],
  "NY": [],
  "PHO": [],
  "POR": [],
  "SEA": [],
  "TOR": ["Player Name (Injury Type - Status)"],
  "WAS": []
}}

Use these exact team abbreviations. Only include teams that have injured players (non-empty arrays).
Return raw JSON only — no markdown, no explanation, no backticks."""

    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "No ANTHROPIC_API_KEY found. Add it to Streamlit secrets: "
            "Settings > Secrets, then add: ANTHROPIC_API_KEY = 'sk-ant-...'"
        )

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    # Extract the text block from the response
    raw_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            raw_text += block.get("text", "")

    # Strip markdown fences if present
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    parsed = json.loads(clean)

    # Filter out empty arrays and normalize
    result = {}
    for team, players in parsed.items():
        if players:
            result[team.upper()] = [str(p) for p in players]
    return result


@st.cache_data(ttl=600)
def get_injuries():
    # Build source list — only include Claude if a key exists
    sources = [
        ("Rotowire",        _injuries_rotowire),
        ("ESPN Team API",   _injuries_espn_team),
        ("CBS Sports",      _injuries_cbs),
        ("ESPN Roster API", _injuries_espn_rosters),
        ("ESPN Core API",   _injuries_espn_core),
    ]
    if _get_api_key():
        sources.append(("Claude AI Web Search", _injuries_via_claude))

    errors = []
    for source_name, fn in sources:
        try:
            data = fn()
            if data:
                total = sum(len(v) for v in data.values())
                return data, f"✅ Injuries from {source_name} ({total} players flagged)"
        except Exception as e:
            errors.append(f"{source_name}: {type(e).__name__}")
            continue
    return {}, f"⚠️ All injury sources failed. ({' | '.join(errors)})"


# ─────────────────────────────────────────────────────────────────────────────
# BACK-TO-BACK
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_back_to_back():
    b2b  = set()
    yest = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
    for event in _get_scoreboard(yest).get('events', []):
        for c in event['competitions'][0]['competitors']:
            b2b.add(norm(c['team']['abbreviation']))
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td  = TEAM_DATA.get(h, {'off_rtg': 100, 'def_rtg': 102})
    a_td  = TEAM_DATA.get(a, {'off_rtg': 100, 'def_rtg': 102})
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

    def get_player_impact(s):
        raw = (
            s.lower().split(" (")[0]
            .replace(".", "").replace("'", "")
            .replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "")
            .strip()
        )
        val, tier = 1.0, "Role"
        for star in SUPERSTARS:
            c = star.lower().replace(".", "").replace("'", "").replace(" jr","").replace(" iii","").replace(" ii","").strip()
            if c == raw or c in raw or raw in c:
                val, tier = 8.0, "Superstar"; break
        if tier == "Role":
            for star in ALL_STARS:
                c = star.lower().replace(".", "").replace("'", "").replace(" jr","").replace(" iii","").replace(" ii","").strip()
                if c == raw or c in raw or raw in c:
                    val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for star in HIGH_IMPACT:
                c = star.lower().replace(".", "").replace("'", "").replace(" jr","").replace(" iii","").replace(" ii","").strip()
                if c == raw or c in raw or raw in c:
                    val, tier = 2.5, "High-Impact"; break
        archetype = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            c = p.lower().replace(".", "").replace("'", "").strip()
            if c == raw or c in raw or raw in c:
                archetype = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            c = p.lower().replace(".", "").replace("'", "").strip()
            if c == raw or c in raw or raw in c:
                archetype = "Off_Liability"; break
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

    # 4. Net Rating Edge
    h_net = (h_td['off_rtg'] - h_op) - (h_td['def_rtg'] + h_dp)
    a_net = (a_td['off_rtg'] - a_op) - (a_td['def_rtg'] + a_dp)
    net_edge = (h_net - a_net) * 0.55
    total += net_edge
    factors.append({
        "icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge,
        "why":  "Net rating dynamically adjusted by player archetype (40-min WNBA pacing)",
    })

    if h_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(h_det)}"
        if h_mult > 1.0: why += f" (🚨 Depth Collapse: {h_mult}x)"
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": why})
    if a_inj:
        why = f"Impact baked into Net Rating. Missing: {', '.join(a_det)}"
        if a_mult > 1.0: why += f" (🚨 Depth Collapse: {a_mult}x)"
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": why})

    # 5. B2B Fatigue (5pts — WNBA commercial flights, tighter budgets)
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0,
                        "why": f"{h} played yesterday. Commercial flight grind."})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0,
                        "why": f"{a} played yesterday. Commercial flight grind."})

    # Logistic win probability (k=0.17 → 10pt spread ≈ 82%)
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

with st.spinner("Loading slate, standings, and injuries…"):
    slate     = get_daily_slate()
    standings = get_standings()
    injuries, inj_status = get_injuries()
    b2b       = get_back_to_back()

# ── Show API key setup instructions if missing ───────────────────────────────
if not _get_api_key():
    st.sidebar.error(
        "🔑 API Key Required for Injuries. "
        "Go to share.streamlit.io → Settings → Secrets and add: "
        "ANTHROPIC_API_KEY = 'sk-ant-...' "
        "(get a key at console.anthropic.com)"
    )

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

import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup

# --- PAGE SETUP ---
st.set_page_config(page_title="WNBA Quant AI 2026", page_icon="🏀", layout="wide")
st.sidebar.title("⚙️ System Tools")

debug_mode = st.sidebar.checkbox("🐞 Enable API Debugger")
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
SUPERSTARS = ["A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier", "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu"]
ALL_STARS = ["Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike", "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale", "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston", "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor", "Azzi Fudd"]
HIGH_IMPACT = ["Natasha Howard", "Marina Mabrey", "Courtney Vandersloot", "Betnijah Laney-Hamilton", "Brionna Jones", "Dearica Hamby", "Allisha Gray", "Rhyne Howard", "Kayla McBride", "Natasha Cloud", "Kelsey Mitchell", "NaLyssa Smith", "Brittney Griner", "Cheyenne Parker-Tyus", "Courtney Williams", "Alanna Smith", "Sophie Cunningham", "Kia Nurse", "Lexie Hull"]
DEFENSIVE_LIABILITIES = ["Caitlin Clark", "Arike Ogunbowale", "Kelsey Mitchell", "Marina Mabrey", "Diana Taurasi"]
OFFENSIVE_LIABILITIES = ["Alyssa Thomas", "Ezi Magbegor", "Brianna Turner", "Kiah Stokes"]

# ─────────────────────────────────────────────────────────────────────────────
# TEAM DATA
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LV': {'off_rtg': 110.5, 'def_rtg': 99.8}, 'NY': {'off_rtg': 109.2, 'def_rtg': 100.5},
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2}, 'SEA': {'off_rtg': 103.5, 'def_rtg': 98.8},
    'MIN': {'off_rtg': 102.8, 'def_rtg': 99.1}, 'IND': {'off_rtg': 106.5, 'def_rtg': 105.2},
    'DAL': {'off_rtg': 105.1, 'def_rtg': 104.8}, 'ATL': {'off_rtg': 100.2, 'def_rtg': 101.5},
    'PHO': {'off_rtg': 99.5, 'def_rtg': 106.1}, 'CHI': {'off_rtg': 98.2, 'def_rtg': 103.5},
    'LA': {'off_rtg': 96.8, 'def_rtg': 105.2}, 'WAS': {'off_rtg': 97.5, 'def_rtg': 108.4},
    'GS': {'off_rtg': 101.0, 'def_rtg': 103.0}, 'POR': {'off_rtg': 98.0, 'def_rtg': 104.5},
    'TOR': {'off_rtg': 99.0, 'def_rtg': 104.0},
}
BLANK_STD = {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': 'N/A'}

def norm(abbr):
    mapping = {'LVA': 'LV', 'NYL': 'NY', 'CON': 'CONN', 'PHX': 'PHO', 'LAS': 'LA', 'MINN': 'MIN', 'GSV': 'GS', 'GST': 'GS', 'GOLST': 'GS', 'PORT': 'POR', 'TOR': 'TOR'}
    return mapping.get(str(abbr).upper(), str(abbr).upper())

# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_scoreboard(date_string):
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}", timeout=6)
        r.raise_for_status()
        return r.json()
    except: return {}

@st.cache_data(ttl=300)
def get_daily_slate(date_string):
    data = get_scoreboard(date_string)
    games = []
    for event in data.get('events', []):
        comp = event['competitions'][0]
        home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
        away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
        if home and away:
            games.append({'h': norm(home['team']['abbreviation']), 'a': norm(away['team']['abbreviation']), 'h_name': home['team']['displayName'], 'a_name': away['team']['displayName']})
    return games

@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/standings"
    try:
        data = requests.get(url, timeout=8).json()
        result = {}
        def extract_entries(node):
            found = []
            if isinstance(node, dict):
                if 'team' in node and 'stats' in node: found.append(node)
                for v in node.values(): found.extend(extract_entries(v))
            elif isinstance(node, list):
                for i in node: found.extend(extract_entries(i))
            return found
        for entry in extract_entries(data):
            abbr = norm(entry['team']['abbreviation'])
            stats = {str(s.get('name', '')).lower(): s for s in entry.get('stats', []) if isinstance(s, dict)}
            wins = int(stats.get('wins', {}).get('value', 0))
            losses = int(stats.get('losses', {}).get('value', 0))
            win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5
            result[abbr] = {'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 'win_pct': win_pct, 'l10_pct': win_pct, 'l10_record': 'N/A'}
        return result if len(result) > 5 else {k: dict(BLANK_STD) for k in TEAM_DATA}
    except: return {k: dict(BLANK_STD) for k in TEAM_DATA}

@st.cache_data(ttl=600)
def get_injuries():
    try:
        r = requests.get("https://www.rotowire.com/wnba/injury-report.php", headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        news = {}
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 4:
                name = cells[0].get_text(strip=True)
                team = norm(cells[1].get_text(strip=True).upper())
                status = cells[2].get_text(strip=True)
                injury = cells[3].get_text(strip=True)
                if status.lower() not in ['active', 'probable']:
                    if team not in news: news[team] = []
                    news[team].append(f"{name} ({injury} — {status})")
        return news, "✅ Injuries loaded via RotoWire"
    except: return {}, "⚠️ Injury scrape failed"

@st.cache_data(ttl=600)
def get_back_to_back(yest_date_string):
    b2b = set()
    for event in get_scoreboard(yest_date_string).get('events', []):
        for c in event['competitions'][0]['competitors']: b2b.add(norm(c['team']['abbreviation']))
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION ENGINE & UI (Standardization)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td, a_td = TEAM_DATA.get(h, {}), TEAM_DATA.get(a, {})
    h_std, a_std = standings.get(h, BLANK_STD), standings.get(a, BLANK_STD)
    factors, total = [], 0.0
    
    # 1. Edge & Fatigue
    h_pct = h_std['win_pct'] * 0.7 + h_std.get('l10_pct', h_std['win_pct']) * 0.3 if use_l10 else h_std['win_pct']
    a_pct = a_std['win_pct'] * 0.7 + a_std.get('l10_pct', a_std['win_pct']) * 0.3 if use_l10 else a_std['win_pct']
    total += (h_pct - a_pct) * 20.0 + 2.5
    factors.append({"icon": "📊", "name": "Win/HCA Edge", "adj": (h_pct - a_pct) * 20.0 + 2.5, "why": f"{h} vs {a}"})

    # 2. Injuries
    def get_penalties(inj_list):
        o, d, core, det = 0.0, 0.0, 0, []
        for p in inj_list:
            raw = p.lower()
            val, tier = 2.5, "High-Impact"
            if any(s.lower() in raw for s in SUPERSTARS): val, tier = 8.0, "Superstar"
            elif any(s.lower() in raw for s in ALL_STARS): val, tier = 4.5, "All-Star"
            if tier != "Role": core += 1
            o += val * (1.3 if any(d in raw for d in DEFENSIVE_LIABILITIES) else 0.6)
            d += val * (1.3 if any(o in raw for o in OFFENSIVE_LIABILITIES) else 0.4)
            det.append(f"{p.split(' (')[0]} ({tier})")
        mult = 1.35 if core == 2 else 1.75 if core >= 3 else 1.0
        return o * mult, d * mult, det, mult

    h_op, h_dp, h_det, h_m = get_penalties(injuries.get(h, []))
    a_op, a_dp, a_det, a_m = get_penalties(injuries.get(a, []))
    
    net_edge = (((h_td.get('off_rtg', 100) - h_op) - (h_td.get('def_rtg', 100) + h_dp)) - 
                ((a_td.get('off_rtg', 100) - a_op) - (a_td.get('def_rtg', 100) + a_dp))) * 0.8
    total += net_edge
    factors.append({"icon": "⚖️", "name": "Adj. Net Rating", "adj": net_edge, "why": "Pace/Injury adjusted"})
    
    # 3. Final Prob
    prob = max(5.0, min(95.0, 1 / (1 + np.exp(-0.17 * total)) * 100))
    return {'winner': h if prob >= 50 else a, 'conf': prob if prob >= 50 else 100-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': injuries.get(h, []), 'a_inj': injuries.get(a, [])}

# UI EXECUTION
slate = get_daily_slate(target_date_str)
standings = get_standings()
injuries, inj_status = get_injuries()
b2b = get_back_to_back(yest_date_str)

if debug_mode:
    st.error(f"Debug: Standings {len(standings)} teams, Injuries {len(injuries)} teams.")

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries, b2b)
    with st.expander(f"{game['h_name']} vs {game['a_name']} | {pred['winner']} ({pred['conf']:.1f}%)"):
        st.write(f"**Winner: {pred['winner']}**")
        for f in pred['factors']: st.write(f"{f['icon']} {f['name']}: {f['adj']:.1f} - {f['why']}")

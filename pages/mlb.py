import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI 2026", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ Diamond Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Analyzing the slate.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 MLB STAR LIST 2026 (Elite Bats & Arms) 🚨
# ─────────────────────────────────────────────────────────────────────────────
MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Ronald Acuña Jr.", "Yordan Alvarez",
    "Adley Rutschman", "Bryce Harper", "Corey Seager", "Freddie Freeman", "Kyle Tucker",
    "Jose Ramirez", "Vladimir Guerrero Jr.", "Jackson Chourio", "Dylan Crews",
    "Paul Skenes", "Tarik Skubal", "Chris Sale", "Zack Wheeler", "Corbin Burnes",
    "Logan Webb", "Cole Ragans", "Hunter Greene", "Shota Imanaga", "Yoshinobu Yamamoto",
    "Tanner Houck", "George Kirby", "Max Fried", "Framber Valdez", "Luis Castillo"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. FULL 30-TEAM 2026 POWER DATA
# ─────────────────────────────────────────────────────────────────────────────
# Updated with all 30 teams so games are no longer 50/50 by default
TEAM_DATA = {
    'ARI': {'ops': .745, 'era': 4.15, 'park': 1.01}, 'ATL': {'ops': .770, 'era': 3.55, 'park': 1.00},
    'BAL': {'ops': .785, 'era': 3.80, 'park': 0.98}, 'BOS': {'ops': .755, 'era': 4.10, 'park': 1.04},
    'CHC': {'ops': .740, 'era': 3.75, 'park': 1.00}, 'CWS': {'ops': .680, 'era': 4.90, 'park': 0.99},
    'CIN': {'ops': .750, 'era': 4.20, 'park': 1.06}, 'CLE': {'ops': .735, 'era': 3.60, 'park': 0.98},
    'COL': {'ops': .720, 'era': 5.20, 'park': 1.15}, 'DET': {'ops': .740, 'era': 3.65, 'park': 0.97},
    'HOU': {'ops': .765, 'era': 3.75, 'park': 1.00}, 'KC':  {'ops': .755, 'era': 3.85, 'park': 0.99},
    'LAA': {'ops': .710, 'era': 4.50, 'park': 1.00}, 'LAD': {'ops': .798, 'era': 3.40, 'park': 1.02},
    'MIA': {'ops': .700, 'era': 4.30, 'park': 0.96}, 'MIL': {'ops': .745, 'era': 3.70, 'park': 1.01},
    'MIN': {'ops': .750, 'era': 3.90, 'park': 1.00}, 'NYM': {'ops': .760, 'era': 3.85, 'park': 0.97},
    'NYY': {'ops': .785, 'era': 3.70, 'park': 1.05}, 'OAK': {'ops': .690, 'era': 4.80, 'park': 0.95},
    'PHI': {'ops': .770, 'era': 3.45, 'park': 1.02}, 'PIT': {'ops': .725, 'era': 3.80, 'park': 0.98},
    'SD':  {'ops': .760, 'era': 3.55, 'park': 0.94}, 'SF':  {'ops': .730, 'era': 3.70, 'park': 0.93},
    'SEA': {'ops': .720, 'era': 3.35, 'park': 0.91}, 'STL': {'ops': .740, 'era': 4.10, 'park': 0.99},
    'TB':  {'ops': .735, 'era': 3.60, 'park': 0.95}, 'TEX': {'ops': .765, 'era': 4.05, 'park': 1.01},
    'TOR': {'ops': .750, 'era': 3.95, 'park': 1.00}, 'WAS': {'ops': .725, 'era': 4.40, 'park': 1.01}
}

def norm(abbr):
    mapping = {'WSH': 'WAS', 'KC': 'KC', 'SDG': 'SD', 'SFO': 'SF', 'TBR': 'TB', 'CHW': 'CWS', 'KCA': 'KC', 'LAN': 'LAD', 'NYN': 'NYM', 'CHN': 'CHC'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate():
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today_str}"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            h = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            a = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if h and a:
                h_sp = h.get('probables', [{}])[0].get('athlete', {}).get('displayName', 'TBD')
                a_sp = a.get('probables', [{}])[0].get('athlete', {}).get('displayName', 'TBD')
                games.append({
                    'h': norm(h['team']['abbreviation']), 'a': norm(a['team']['abbreviation']),
                    'h_name': h['team']['displayName'], 'a_name': away_team['team']['displayName'] if 'away_team' in locals() else a['team']['displayName'],
                    'h_sp': h_sp, 'a_sp': a_sp
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_mlb_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/standings"
    try:
        data = requests.get(url, timeout=5).json()
        res = {}
        for entry in data.get('children', [{}])[0].get('children', [{}])[0].get('standings', {}).get('entries', []):
            abbr = norm(entry['team']['abbreviation'])
            stats = {s['name']: s['value'] for s in entry['stats']}
            res[abbr] = {'win_pct': stats.get('winPercent', 0.5), 'record': entry['stats'][0]['displayValue']}
        return res
    except: return {}

@st.cache_data(ttl=600)
def get_mlb_injuries():
    url = "https://www.cbssports.com/mlb/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        from bs4 import BeautifulSoup
        html = requests.get(url, headers=headers).text
        soup = BeautifulSoup(html, 'html.parser')
        news = {}
        # Simple MLB Injury Scraper Logic
        for table in soup.find_all('div', class_='TableBase'):
            team_name = table.find('span', class_='TeamName').get_text(strip=True)
            # Shortened team mapping (e.g. "L.A. Dodgers" -> "LAD")
            # Logic here...
            pass 
        return news 
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 3. MLB PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings, injuries):
    h_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10, 'park': 1.0})
    a_td = TEAM_DATA.get(a, {'ops': .740, 'era': 4.10, 'park': 1.0})
    h_std = standings.get(h, {'win_pct': 0.5, 'record': '0-0'})
    a_std = standings.get(a, {'win_pct': 0.5, 'record': '0-0'})

    factors, total = [], 0.0

    # 1. Starting Pitcher Edge (The most important factor)
    def is_star(name):
        return any(s.lower() in name.lower() for s in MLB_STARS)

    if is_star(h_sp):
        total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace Advantage", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if is_star(a_sp):
        total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace Advantage", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # 2. Offensive Edge (OPS Difference)
    ops_diff = (h_td['ops'] - a_td['ops']) * 120.0
    total += ops_diff
    factors.append({"icon": "🎯", "name": "Lineup Strength", "adj": ops_diff, "why": f"OPS Gap: {h_td['ops']} vs {a_td['ops']}"})

    # 3. Bullpen & Defense (ERA Difference)
    era_diff = (a_td['era'] - h_td['era']) * 2.0
    total += era_diff
    factors.append({"icon": "🛡️", "name": "Run Prevention", "adj": era_diff, "why": f"Bullpen ERA Edge"})

    # 4. Standing/Win % Edge
    win_adj = (h_std['win_pct'] - a_std['win_pct']) * 15.0
    total += win_adj
    factors.append({"icon": "📊", "name": "Record Edge", "adj": win_adj, "why": "Seasonal performance"})

    # 5. Home Field Advantage
    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Field", "adj": 2.5, "why": "Stadium advantage"})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
st.markdown(f"**Live Date:** {datetime.utcnow().strftime('%B %d, %Y')}")
st.divider()

slate = get_mlb_slate()
standings = get_mlb_standings()
injuries = get_mlb_injuries()

if not slate:
    st.info("No games scheduled today.")
else:
    for game in slate:
        pred = predict_mlb(game['h'], game['a'], game['h_sp'], game['a_sp'], standings, injuries)
        with st.expander(f"{game['a_name']} vs {game['h_name']} | Winner: {pred['winner']}"):
            st.markdown(f"### 🏆 {pred['winner']} Wins ({pred['conf']:.1f}%)")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                st.write(f"**SP:** {game['h_sp']} | **Rec:** {pred['h_std']['record']}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                st.write(f"**SP:** {game['a_sp']} | **Rec:** {pred['a_std']['record']}")

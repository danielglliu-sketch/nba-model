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
# Equivalent to your >12.5 PPG rule: All-Stars, Top OPS, and Cy Young candidates
MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Ronald Acuña Jr.", "Yordan Alvarez",
    "Adley Rutschman", "Bryce Harper", "Corey Seager", "Freddie Freeman", "Kyle Tucker",
    "Jose Ramirez", "Vladimir Guerrero Jr.", "Jackson Chourio", "Dylan Crews",
    "Paul Skenes", "Tarik Skubal", "Chris Sale", "Zack Wheeler", "Corbin Burnes",
    "Logan Webb", "Cole Ragans", "Hunter Greene", "Shota Imanaga", "Yoshinobu Yamamoto"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. 2026 TEAM EFFICIENCY & PARK FACTORS
# ─────────────────────────────────────────────────────────────────────────────
# Based on 2026 projected Team OPS (Offense) and Team ERA (Defense/Pitching)
TEAM_DATA = {
    'LAD': {'ops': .795, 'era': 3.42, 'park_factor': 1.02}, # Hitter Friendly
    'NYY': {'ops': .780, 'era': 3.65, 'park_factor': 1.05}, # Short Porch
    'ATL': {'ops': .770, 'era': 3.50, 'park_factor': 1.00},
    'BAL': {'ops': .785, 'era': 3.80, 'park_factor': 0.98},
    'PHI': {'ops': .765, 'era': 3.35, 'park_factor': 1.01},
    'HOU': {'ops': .760, 'era': 3.70, 'park_factor': 0.99},
    'SD': {'ops': .750, 'era': 3.45, 'park_factor': 0.94},  # Pitcher Friendly
}

def norm(abbr):
    mapping = {'WSH': 'WAS', 'KC': 'KCR', 'SDG': 'SD', 'SFO': 'SF', 'TBR': 'TB'}
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
                # Attempt to find Starting Pitchers
                h_sp = h.get('probables', [{}])[0].get('athlete', {}).get('displayName', 'TBD')
                a_sp = a.get('probables', [{}])[0].get('athlete', {}).get('displayName', 'TBD')
                games.append({
                    'h': norm(h['team']['abbreviation']), 'a': norm(a['team']['abbreviation']),
                    'h_name': h['team']['displayName'], 'a_name': a['team']['displayName'],
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
        # (Scraping logic similar to NBA but for MLB Teams)
        return news 
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 3. MLB PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings, injuries):
    h_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10, 'park_factor': 1.0})
    a_td = TEAM_DATA.get(a, {'ops': .740, 'era': 4.10, 'park_factor': 1.0})
    h_std = standings.get(h, {'win_pct': 0.5, 'record': '0-0'})
    a_std = standings.get(a, {'win_pct': 0.5, 'record': '0-0'})

    factors, total = [], 0.0

    # 1. Pitching Performance (Starter Edge) - 60% Weight
    # This logic gives 5.0 pts to a Star Starter
    if any(s in h_sp for s in MLB_STARS):
        total += 5.0; factors.append({"icon": "🔥", "name": "Ace Advantage", "adj": 5.0, "why": f"{h_sp} is a Star SP."})
    if any(s in a_sp for s in MLB_STARS):
        total -= 5.0; factors.append({"icon": "🔥", "name": "Ace Penalty", "adj": -5.0, "why": f"{a_sp} is a Star SP."})

    # 2. Offensive Efficiency (OPS Gap)
    ops_adj = (h_td['ops'] - a_td['ops']) * 100.0
    total += ops_adj
    factors.append({"icon": "🎯", "name": "OPS Gap", "adj": ops_adj, "why": f"Team OPS: {h}({h_td['ops']}) vs {a}({a_td['ops']})"})

    # 3. Defensive / Bullpen Reliability (ERA)
    era_adj = (a_td['era'] - h_td['era']) * 1.5
    total += era_adj
    factors.append({"icon": "🛡️", "name": "Run Prevention", "adj": era_adj, "why": f"ERA Edge for {h if era_adj > 0 else a}"})

    # 4. Ballpark Environment
    if h_td['park_factor'] > 1.03:
        factors.append({"icon": "🏟️", "name": "Park Factor", "adj": 0, "why": "High scoring environment (Hitter's Park)."})

    # 5. Injury Impact (Fuzzy Match)
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    def get_tier(name):
        raw = name.lower()
        for star in MLB_STARS:
            if star.lower() in raw: return 4.5, "Star Bat"
        return 1.0, "Role"

    if h_inj:
        p = sum(get_tier(x)[0] for x in h_inj)
        total -= p
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": -p, "why": f"Missing {len(h_inj)} players."})
    if a_inj:
        p = sum(get_tier(x)[0] for x in a_inj)
        total += p
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": p, "why": f"Missing {len(a_inj)} players."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
current_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Season Date:** {current_date}")
st.divider()

slate = get_mlb_slate()
standings = get_mlb_standings()
injuries = get_mlb_injuries()

if not slate:
    st.info("No games scheduled for today.")
else:
    for game in slate:
        pred = predict_mlb(game['h'], game['a'], game['h_sp'], game['a_sp'], standings, injuries)
        
        with st.expander(f"{game['a_name']} ({game['a_sp']}) vs {game['h_name']} ({game['h_sp']}) | Winner: {pred['winner']}"):
            st.markdown(f"### 🏆 {pred['winner']} Wins ({pred['conf']:.1f}%)")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                st.write(f"**SP:** {game['h_sp']} | **Rec:** {pred['h_std']['record']}")
                for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                st.write(f"**SP:** {game['a_sp']} | **Rec:** {pred['a_std']['record']}")
                for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

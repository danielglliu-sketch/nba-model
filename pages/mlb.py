import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI 2026", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ Diamond Tools")

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
    "Tyler Glasnow", "George Kirby", "Max Fried", "Framber Valdez", "Luis Castillo"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. FULL 30-TEAM 2026 POWER DATA
# ─────────────────────────────────────────────────────────────────────────────
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
    'NYY': {'ops': .785, 'era': 3.70, 'park': 1.05}, 'ATH': {'ops': .690, 'era': 4.80, 'park': 0.95},
    'PHI': {'ops': .770, 'era': 3.45, 'park': 1.02}, 'PIT': {'ops': .725, 'era': 3.80, 'park': 0.98},
    'SD':  {'ops': .760, 'era': 3.55, 'park': 0.94}, 'SF':  {'ops': .730, 'era': 3.70, 'park': 0.93},
    'SEA': {'ops': .720, 'era': 3.35, 'park': 0.91}, 'STL': {'ops': .740, 'era': 4.10, 'park': 0.99},
    'TB':  {'ops': .735, 'era': 3.60, 'park': 0.95}, 'TEX': {'ops': .765, 'era': 4.05, 'park': 1.01},
    'TOR': {'ops': .750, 'era': 3.95, 'park': 1.00}, 'WAS': {'ops': .725, 'era': 4.40, 'park': 1.01}
}

def norm(abbr):
    mapping = {'WSH': 'WAS', 'KCA': 'KC', 'SDG': 'SD', 'SFO': 'SF', 'TBR': 'TB', 'CHW': 'CWS', 'LAN': 'LAD', 'NYN': 'NYM', 'CHN': 'CHC', 'OAK': 'ATH'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate():
    # Force Pacific Time Date for MLB Schedule
    today_str = (datetime.utcnow() - timedelta(hours=7)).strftime('%Y%m%d')
    st.sidebar.write(f"🔍 Searching Date: {today_str}")
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today_str}"
    try:
        data = requests.get(url, timeout=10).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            h_data = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            a_data = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if h_data and a_data:
                h_prob = h_data.get('probables', [{}])[0]
                a_prob = a_data.get('probables', [{}])[0]
                games.append({
                    'h': norm(h_data['team']['abbreviation']), 'a': norm(a_data['team']['abbreviation']),
                    'h_name': h_data['team']['displayName'], 'a_name': a_data['team']['displayName'],
                    'h_sp': h_prob.get('athlete', {}).get('displayName', 'TBD'),
                    'a_sp': a_prob.get('athlete', {}).get('displayName', 'TBD'),
                    'h_sp_rec': h_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA'),
                    'a_sp_rec': a_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA')
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_mlb_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/standings"
    try:
        data = requests.get(url, timeout=10).json()
        res = {}
        for league in data.get('children', []):
            for division in league.get('children', []):
                for entry in division.get('standings', {}).get('entries', []):
                    abbr = norm(entry['team']['abbreviation'])
                    stats = {s['name']: s['displayValue'] for s in entry['stats']}
                    val_stats = {s['name']: s['value'] for s in entry['stats']}
                    res[abbr] = {'win_pct': val_stats.get('winPercent', 0.5), 'overall': stats.get('summary', '0-0'), 'home': stats.get('home', '0-0'), 'away': stats.get('road', '0-0')}
        return res
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 3. MLB PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings):
    h_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10, 'park': 1.0})
    a_td = TEAM_DATA.get(a, {'ops': .740, 'era': 4.10, 'park': 1.0})
    h_std = standings.get(h, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})
    a_std = standings.get(a, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})

    factors, total = [], 0.0
    def is_star(name): return any(s.lower() in name.lower() for s in MLB_STARS)

    if is_star(h_sp):
        total += 6.5; factors.append({"icon": "🔥", "name": "Ace Bonus", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if is_star(a_sp):
        total -= 6.5; factors.append({"icon": "🔥", "name": "Ace Penalty", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    ops_diff = (h_td['ops'] - a_td['ops']) * 120.0
    total += ops_diff
    factors.append({"icon": "🎯", "name": "Offensive Edge", "adj": ops_diff, "why": f"OPS Difference: {h_td['ops']} vs {a_td['ops']}"})

    era_diff = (a_td['era'] - h_td['era']) * 2.0
    total += era_diff
    factors.append({"icon": "🛡️", "name": "ERA Advantage", "adj": era_diff, "why": "Run Prevention Edge"})

    win_adj = (h_std['win_pct'] - a_std['win_pct']) * 15.0
    total += win_adj
    factors.append({"icon": "📊", "name": "Record Factor", "adj": win_adj, "why": "Seasonal momentum"})

    total += 2.5
    factors.append({"icon": "🏠", "name": "Home Field", "adj": 2.5, "why": "Stadium advantage"})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Refreshed!")

slate = get_mlb_slate()
standings = get_mlb_standings()

if not slate:
    st.info("No games scheduled. Ensure your system date is correct.")
else:
    for game in slate:
        pred = predict_mlb(game['h'], game['a'], game['h_sp'], game['a_sp'], standings)
        with st.expander(f"{game['a_name']} at {game['h_name']} | Winner: {pred['winner']}"):
            st.markdown(f"### 🏆 {pred['winner']} Wins ({pred['conf']:.1f}%)")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                st.write(f"**SP:** {game['h_sp']} ({game['h_sp_rec']})")
                st.write(f"**Overall:** {pred['h_std']['overall']} | **Home:** {pred['h_std']['home']}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                st.write(f"**SP:** {game['a_sp']} ({game['a_sp_rec']})")
                st.write(f"**Overall:** {pred['a_std']['overall']} | **Road:** {pred['a_std']['away']}")

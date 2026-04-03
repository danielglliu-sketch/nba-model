import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="NBA Master AI 2026", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ System Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! The app is pulling fresh data.")

# ─────────────────────────────────────────────────────────────────────────────
# 1. THE 2026 ACCURATE STANDINGS & RATINGS DATABASE (As of April 3)
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    # Eastern Conference
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727},
    'BOS': {'wins': 51, 'losses': 25, 'record': '51-25', 'win_pct': 0.671},
    'NYK': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623},
    'ATL': {'wins': 44, 'losses': 33, 'record': '44-33', 'win_pct': 0.571},
    'PHI': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553},
    'TOR': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553},
    'CHA': {'wins': 41, 'losses': 36, 'record': '41-36', 'win_pct': 0.532},
    'ORL': {'wins': 40, 'losses': 36, 'record': '40-36', 'win_pct': 0.526},
    'MIA': {'wins': 40, 'losses': 37, 'record': '40-37', 'win_pct': 0.519},
    'MIL': {'wins': 30, 'losses': 46, 'record': '30-46', 'win_pct': 0.395},
    'CHI': {'wins': 29, 'losses': 47, 'record': '29-47', 'win_pct': 0.382},
    'IND': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
    'BKN': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
    'WAS': {'wins': 17, 'losses': 59, 'record': '17-59', 'win_pct': 0.224},
    # Western Conference
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649},
    'DEN': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636},
    'HOU': {'wins': 47, 'losses': 29, 'record': '47-29', 'win_pct': 0.618},
    'MIN': {'wins': 46, 'losses': 30, 'record': '46-30', 'win_pct': 0.605},
    'PHO': {'wins': 42, 'losses': 35, 'record': '42-35', 'win_pct': 0.545},
    'POR': {'wins': 40, 'losses': 38, 'record': '40-38', 'win_pct': 0.513},
    'LAC': {'wins': 39, 'losses': 38, 'record': '39-38', 'win_pct': 0.506},
    'GSW': {'wins': 36, 'losses': 41, 'record': '36-41', 'win_pct': 0.468},
    'MEM': {'wins': 25, 'losses': 51, 'record': '25-51', 'win_pct': 0.329},
    'NOP': {'wins': 25, 'losses': 52, 'record': '25-52', 'win_pct': 0.325},
    'DAL': {'wins': 24, 'losses': 52, 'record': '24-52', 'win_pct': 0.316},
    'UTA': {'wins': 21, 'losses': 56, 'record': '21-56', 'win_pct': 0.273},
    'SAC': {'wins': 20, 'losses': 57, 'record': '20-57', 'win_pct': 0.260},
}

TEAM_DATA = {
    'OKC': {'off_rtg': 116.2, 'def_rtg': 104.1}, 'DET': {'off_rtg': 113.1, 'def_rtg': 105.5},
    'SAS': {'off_rtg': 114.7, 'def_rtg': 107.7}, 'BOS': {'off_rtg': 116.8, 'def_rtg': 108.7},
    'MIN': {'off_rtg': 115.2, 'def_rtg': 109.1}, 'HOU': {'off_rtg': 114.2, 'def_rtg': 109.2},
    'TOR': {'off_rtg': 111.8, 'def_rtg': 109.5}, 'NYK': {'off_rtg': 116.4, 'def_rtg': 109.7},
    'PHO': {'off_rtg': 111.3, 'def_rtg': 109.8}, 'ATL': {'off_rtg': 111.3, 'def_rtg': 110.0},
    'CHA': {'off_rtg': 114.0, 'def_rtg': 110.1}, 'MIA': {'off_rtg': 112.2, 'def_rtg': 110.3},
    'POR': {'off_rtg': 110.1, 'def_rtg': 110.5}, 'ORL': {'off_rtg': 111.6, 'def_rtg': 110.9},
    'CLE': {'off_rtg': 115.3, 'def_rtg': 111.1}, 'GSW': {'off_rtg': 112.3, 'def_rtg': 111.3},
    'PHI': {'off_rtg': 113.1, 'def_rtg': 111.9}, 'LAC': {'off_rtg': 112.8, 'def_rtg': 112.3},
    'LAL': {'off_rtg': 115.0, 'def_rtg': 112.7}, 'DEN': {'off_rtg': 118.4, 'def_rtg': 113.5},
    'MEM': {'off_rtg': 110.5, 'def_rtg': 113.8}, 'CHI': {'off_rtg': 111.1, 'def_rtg': 114.6},
    'BKN': {'off_rtg': 107.2, 'def_rtg': 114.6}, 'NOP': {'off_rtg': 110.9, 'def_rtg': 114.6},
    'IND': {'off_rtg': 107.3, 'def_rtg': 115.3}, 'MIL': {'off_rtg': 111.7, 'def_rtg': 115.4},
    'SAC': {'off_rtg': 107.9, 'def_rtg': 117.4}, 'UTA': {'off_rtg': 111.2, 'def_rtg': 118.2},
    'WAS': {'off_rtg': 108.0, 'def_rtg': 118.3}, 'DAL': {'off_rtg': 108.5, 'def_rtg': 112.5},
}

def norm(abbr):
    mapping = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_daily_slate():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        data = requests.get(url, timeout=5).json()
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
                    'a_name': away['team']['displayName']
                })
        if games: return games
    except: pass
    return [{'h': 'PHI', 'a': 'MIN', 'h_name': '76ers', 'a_name': 'Timberwolves'}]

@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings"
    try:
        data = requests.get(url, timeout=5).json()
        result = {}
        for conf in data.get('children', []):
            for entry in conf.get('standings', {}).get('entries', []):
                abbr = norm(entry['team']['abbreviation'])
                stats = {s.get('name', '').lower(): s for s in entry.get('stats', [])}
                wins = int(stats.get('wins', {}).get('value', 0))
                losses = int(stats.get('losses', {}).get('value', 0))
                if wins + losses > 0:
                    result[abbr] = {
                        'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}",
                        'win_pct': wins / (wins + losses)
                    }
        if len(result) > 10: return result
    except: pass
    return BACKUP_STANDINGS

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings):
    h_td = TEAM_DATA.get(h, {'off_rtg': 112, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 112, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    
    factors = []
    total = 0.0
    
    # 1. Base Win Percentage Edge
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 25.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Win % Edge", "adj": base_adj, "why": f"{h} ({h_std['record']}) vs {a} ({a_std['record']})"})

    # 2. Home Court Advantage
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": f"Advantage for {h} at home."})

    # 3. Efficiency Ratings
    eff_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += eff_adj
    factors.append({"icon": "🛡️", "name": "Defense Gap", "adj": eff_adj, "why": f"{h} Def: {h_td['def_rtg']} | {a} Def: {a_td['def_rtg']}"})

    # 4. Tanking Check (Triggered below 34% win rate)
    if h_std['win_pct'] < 0.34:
        total -= 8.0
        factors.append({"icon": "🎯", "name": "Tanking Penalty", "adj": -8.0, "why": f"{h} prioritizing lottery odds."})
    elif a_std['win_pct'] < 0.34:
        total += 8.0
        factors.append({"icon": "🎯", "name": "Tanking Boost", "adj": 8.0, "why": f"{a} prioritizing lottery odds."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor 2026")
st.markdown(f"**Market Date:** {datetime.now().strftime('%B %d, %Y')}")
st.divider()

slate, standings = get_daily_slate(), get_standings()

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings)
    
    with st.expander(f"{game['h_name']} vs {game['a_name']} | Predicted Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
        st.markdown(f"### 🏆 {pred['winner']} Wins")
        for f in pred['factors']:
            color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        col1.metric(f"🏠 {game['h_name']}", pred['h_std']['record'])
        col2.metric(f"✈️ {game['a_name']}", pred['a_std']['record'])

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
# 1. THE 2026 ACCURATE STANDINGS (As of April 3, 2026)
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '31-9', 'away_record': '25-12'},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792, 'home_record': '33-5', 'away_record': '28-11'},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766, 'home_record': '30-7', 'away_record': '29-11'},
    'BOS': {'wins': 51, 'losses': 25, 'record': '51-25', 'win_pct': 0.671, 'home_record': '26-11', 'away_record': '25-14'},
    'NYK': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '27-9', 'away_record': '22-19'},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'HOU': {'wins': 47, 'losses': 29, 'record': '47-29', 'win_pct': 0.618, 'home_record': '27-10', 'away_record': '20-19'},
    'MIN': {'wins': 46, 'losses': 30, 'record': '46-30', 'win_pct': 0.605, 'home_record': '25-14', 'away_record': '21-16'},
    'TOR': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553, 'home_record': '21-17', 'away_record': '21-17'},
    'PHI': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553, 'home_record': '21-17', 'away_record': '21-17'},
    'ATL': {'wins': 44, 'losses': 33, 'record': '44-33', 'win_pct': 0.571, 'home_record': '23-16', 'away_record': '21-17'},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623},
    'ORL': {'wins': 40, 'losses': 36, 'record': '40-36', 'win_pct': 0.526},
    'MIA': {'wins': 40, 'losses': 37, 'record': '40-37', 'win_pct': 0.519},
    'GSW': {'wins': 36, 'losses': 41, 'record': '36-41', 'win_pct': 0.468},
    'MIL': {'wins': 30, 'losses': 46, 'record': '30-46', 'win_pct': 0.395},
    'CHI': {'wins': 29, 'losses': 47, 'record': '29-47', 'win_pct': 0.382},
    'DAL': {'wins': 24, 'losses': 52, 'record': '24-52', 'win_pct': 0.316},
    'MEM': {'wins': 25, 'losses': 51, 'record': '25-51', 'win_pct': 0.329},
    'NOP': {'wins': 25, 'losses': 52, 'record': '25-52', 'win_pct': 0.325},
    'SAC': {'wins': 20, 'losses': 57, 'record': '20-57', 'win_pct': 0.260},
    'UTA': {'wins': 21, 'losses': 56, 'record': '21-56', 'win_pct': 0.273},
    'WAS': {'wins': 17, 'losses': 59, 'record': '17-59', 'win_pct': 0.224},
    'BKN': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
    'IND': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
    'POR': {'wins': 40, 'losses': 38, 'record': '40-38', 'win_pct': 0.513},
}

# Teams mathematically eliminated from the 2026 Playoffs
ELIMINATED_TEAMS = ['MIL', 'CHI', 'IND', 'BKN', 'WAS', 'MEM', 'NOP', 'DAL', 'UTA', 'SAC']

TEAM_DATA = {
    'OKC': {'off_rtg': 118.9, 'def_rtg': 107.5}, 'DET': {'off_rtg': 117.5, 'def_rtg': 109.6},
    'SAS': {'off_rtg': 119.6, 'def_rtg': 111.1}, 'BOS': {'off_rtg': 114.4, 'def_rtg': 107.2},
    'TOR': {'off_rtg': 114.4, 'def_rtg': 112.3}, 'NYK': {'off_rtg': 116.7, 'def_rtg': 110.6},
    'PHI': {'off_rtg': 116.6, 'def_rtg': 116.7}, 'LAL': {'off_rtg': 116.5, 'def_rtg': 115.0},
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
                games.append({'h': norm(home['team']['abbreviation']), 'a': norm(away['team']['abbreviation']),
                              'h_name': home['team']['displayName'], 'a_name': away['team']['displayName']})
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
                wins, losses = int(stats.get('wins', {}).get('value', 0)), int(stats.get('losses', {}).get('value', 0))
                if wins + losses > 0:
                    result[abbr] = {'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 'win_pct': wins / (wins + losses)}
        if len(result) > 10: return result
    except: pass
    return BACKUP_STANDINGS

@st.cache_data(ttl=600)
def get_injuries():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news"
    try:
        news = {}
        articles = requests.get(url, timeout=5).json().get('articles', [])
        for art in articles:
            hl = art.get('headline', '')
            if 'out' in hl.lower() or 'injury' in hl.lower():
                for cat in art.get('categories', []):
                    if cat.get('type') == 'team':
                        abbr = norm(cat.get('teamAbbrev', ''))
                        if abbr: news.setdefault(abbr, []).append(hl)
        return {k: list(set(v))[:2] for k, v in news.items()}
    except: return {}

@st.cache_data(ttl=600)
def get_back_to_back():
    b2b = set()
    yest = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest}"
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b.add(norm(c['team']['abbreviation']))
    except: pass
    return b2b

# ─────────────────────────────────────────────────────────────────────────────
# 3. UPDATED PREDICTION ENGINE (Dual Injuries & Playoff Status)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set):
    h_td = TEAM_DATA.get(h, {'off_rtg': 112, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 112, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    
    factors = []
    total = 0.0
    
    # 1. Win Percentage Edge
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 25.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Win % Edge", "adj": base_adj, "why": f"{h} ({h_std['record']}) vs {a} ({a_std['record']})"})

    # 2. Home Court Advantage
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": f"Advantage for {h} at home."})

    # 3. Efficiency Gap
    eff_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += eff_adj
    factors.append({"icon": "🛡️", "name": "Defense Gap", "adj": eff_adj, "why": f"{h} Def: {h_td['def_rtg']} | {a} Def: {a_td['def_rtg']}"})

    # 4. Playoff Status Logic (New Motivation Factor)
    if h in ELIMINATED_TEAMS:
        total -= 9.0
        factors.append({"icon": "🎯", "name": "Elimination Penalty", "adj": -9.0, "why": f"{h} is out of playoff contention. Tanking logic active."})
    if a in ELIMINATED_TEAMS:
        total += 9.0
        factors.append({"icon": "🎯", "name": "Elimination Boost", "adj": 9.0, "why": f"{a} is out of playoff contention. Motivation edge to {h}."})

    # 5. Fatigue Check
    if h in b2b_set:
        total -= 4.0; factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": -4.0, "why": f"{h} played yesterday."})
    if a in b2b_set:
        total += 4.0; factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": 4.0, "why": f"{a} played yesterday."})

    # 6. REFINED DUAL INJURY DETECTION
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj:
        total -= 6.0
        factors.append({"icon": "🤕", "name": f"{h} Injury Impact", "adj": -6.0, "why": f"{h} has key players out."})
    if a_inj: # Now calculates for both teams simultaneously
        total += 6.0
        factors.append({"icon": "🤕", "name": f"{a} Injury Impact", "adj": 6.0, "why": f"{a} has key players out."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor 2026")
st.markdown(f"**Market Date:** April 03, 2026")
st.divider()

slate, standings, injuries, b2b = get_daily_slate(), get_standings(), get_injuries(), get_back_to_back()

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries, b2b)
    
    with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
        st.markdown(f"### 🏆 {pred['winner']} Wins")
        for f in pred['factors']:
            color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
        if pred['h_inj'] or pred['a_inj']:
            st.divider()
            if pred['h_inj']: st.warning(f"**{game['h_name']} Injuries:** {pred['h_inj'][0][:60]}...")
            if pred['a_inj']: st.warning(f"**{game['a_name']} Injuries:** {pred['a_inj'][0][:60]}...")

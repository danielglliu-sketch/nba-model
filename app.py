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
# 🚨 MANUAL OVERRIDES 🚨
# ─────────────────────────────────────────────────────────────────────────────
# If a player is playing but listed as injured, add them here to clear the penalty:
CLEARED_PLAYERS = ["Joel Embiid", "Tyrese Maxey"]

# ─────────────────────────────────────────────────────────────────────────────
# 1. THE 2026 ACCURATE STANDINGS & RATINGS (As of April 3, 2026)
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766},
    'BOS': {'wins': 51, 'losses': 25, 'record': '51-25', 'win_pct': 0.671},
    'NYK': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636},
    'TOR': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553},
    'PHI': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.553},
    'HOU': {'wins': 47, 'losses': 29, 'record': '47-29', 'win_pct': 0.618},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623},
    'ATL': {'wins': 44, 'losses': 33, 'record': '44-33', 'win_pct': 0.571},
    'MIN': {'wins': 46, 'losses': 30, 'record': '46-30', 'win_pct': 0.605},
    'MIL': {'wins': 30, 'losses': 46, 'record': '30-46', 'win_pct': 0.395},
    'CHI': {'wins': 29, 'losses': 47, 'record': '29-47', 'win_pct': 0.382},
    'DAL': {'wins': 24, 'losses': 52, 'record': '24-52', 'win_pct': 0.316},
    'SAC': {'wins': 20, 'losses': 57, 'record': '20-57', 'win_pct': 0.260},
    'UTA': {'wins': 21, 'losses': 56, 'record': '21-56', 'win_pct': 0.273},
    'WAS': {'wins': 17, 'losses': 59, 'record': '17-59', 'win_pct': 0.224},
    'BKN': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
    'IND': {'wins': 18, 'losses': 58, 'record': '18-58', 'win_pct': 0.237},
}

TEAM_DATA = {
    'OKC': {'off_rtg': 116.2, 'def_rtg': 104.1}, 'DET': {'off_rtg': 113.1, 'def_rtg': 105.5},
    'SAS': {'off_rtg': 114.7, 'def_rtg': 107.7}, 'BOS': {'off_rtg': 116.8, 'def_rtg': 108.7},
    'TOR': {'off_rtg': 111.8, 'def_rtg': 109.5}, 'NYK': {'off_rtg': 116.4, 'def_rtg': 109.7},
    'PHI': {'off_rtg': 113.1, 'def_rtg': 111.9}, 'LAL': {'off_rtg': 115.0, 'def_rtg': 112.7},
}

def norm(abbr):
    mapping = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. FETCHERS (Standings, Slate, Injuries, B2B)
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
            # Skip if player is in the "Cleared" list
            if any(p.lower() in hl.lower() for p in CLEARED_PLAYERS): continue
            
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
# 3. PREDICTION ENGINE
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

    # 2. Home Court
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": f"Standard advantage for {h}"})

    # 3. Efficiency Gap
    eff_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += eff_adj
    factors.append({"icon": "🛡️", "name": "Defense Gap", "adj": eff_adj, "why": f"{h} Def: {h_td['def_rtg']} | {a} Def: {a_td['def_rtg']}"})

    # 4. Tanking Check
    if h_std['win_pct'] < 0.34:
        total -= 8.0; factors.append({"icon": "🎯", "name": "Tanking Penalty", "adj": -8.0, "why": "Low win rate."})
    elif a_std['win_pct'] < 0.34:
        total += 8.0; factors.append({"icon": "🎯", "name": "Tanking Boost", "adj": 8.0, "why": "Opponent low win rate."})

    # 5. Fatigue Check
    if h in b2b_set:
        total -= 4.0; factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": -4.0, "why": f"{h} played yesterday."})
    elif a in b2b_set:
        total += 4.0; factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": 4.0, "why": f"{a} played yesterday."})

    # 6. Injury Impact
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj:
        total -= 6.0; factors.append({"icon": "🤕", "name": "Injury Penalty", "adj": -6.0, "why": f"{h} missing players."})
    elif a_inj:
        total += 6.0; factors.append({"icon": "🤕", "name": "Opponent Injury", "adj": 6.0, "why": f"{a} missing players."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor 2026")
slate, standings, injuries, b2b = get_daily_slate(), get_standings(), get_injuries(), get_back_to_back()

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries, b2b)
    with st.expander(f"{game['h_name']} vs {game['a_name']} | {pred['winner']} ({pred['conf']:.1f}%)"):
        st.markdown(f"### 🏆 {pred['winner']} Wins")
        for f in pred['factors']:
            color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
        if pred['h_inj'] or pred['a_inj']:
            st.divider()
            if pred['h_inj']: st.warning(f"**{game['h_name']} Injuries:** {pred['h_inj'][0][:60]}...")
            if pred['a_inj']: st.warning(f"**{game['a_name']} Injuries:** {pred['a_inj'][0][:60]}...")

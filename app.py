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
# You rarely need this now, but you can still use it to manually force the AI to ignore a player
CLEARED_PLAYERS = ["Joel Embiid", "Tyrese Maxey"]

# ─────────────────────────────────────────────────────────────────────────────
# 1. THE 2026 ACCURATE STANDINGS & BACKUPS
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '30-9', 'away_record': '26-12'},
    'BOS': {'wins': 52, 'losses': 25, 'record': '52-25', 'win_pct': 0.675, 'home_record': '26-11', 'away_record': '26-14'},
    'NYK': {'wins': 50, 'losses': 28, 'record': '50-28', 'win_pct': 0.641, 'home_record': '28-9', 'away_record': '22-19'},
    'PHI': {'wins': 43, 'losses': 34, 'record': '43-34', 'win_pct': 0.558, 'home_record': '22-17', 'away_record': '21-17'},
    'ATL': {'wins': 45, 'losses': 33, 'record': '45-33', 'win_pct': 0.577, 'home_record': '23-16', 'away_record': '22-17'},
    'CHI': {'wins': 29, 'losses': 48, 'record': '29-48', 'win_pct': 0.377, 'home_record': '18-21', 'away_record': '11-27'},
    'IND': {'wins': 18, 'losses': 59, 'record': '18-59', 'win_pct': 0.234, 'home_record': '11-27', 'away_record': '7-32'},
    'MIL': {'wins': 30, 'losses': 47, 'record': '30-47', 'win_pct': 0.390, 'home_record': '17-22', 'away_record': '13-25'},
    'BKN': {'wins': 18, 'losses': 59, 'record': '18-59', 'win_pct': 0.234, 'home_record': '10-28', 'away_record': '8-31'},
    'CHA': {'wins': 42, 'losses': 36, 'record': '42-36', 'win_pct': 0.538, 'home_record': '21-19', 'away_record': '21-17'},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792, 'home_record': '33-6', 'away_record': '28-9'},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766, 'home_record': '29-7', 'away_record': '29-11'},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'HOU': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623, 'home_record': '28-10', 'away_record': '20-19'},
    'MIN': {'wins': 46, 'losses': 31, 'record': '46-31', 'win_pct': 0.597, 'home_record': '25-14', 'away_record': '21-17'},
    'UTA': {'wins': 21, 'losses': 57, 'record': '21-57', 'win_pct': 0.269, 'home_record': '13-27', 'away_record': '8-30'},
    'DAL': {'wins': 24, 'losses': 53, 'record': '24-53', 'win_pct': 0.312, 'home_record': '14-25', 'away_record': '10-28'},
    'MEM': {'wins': 25, 'losses': 52, 'record': '25-52', 'win_pct': 0.325, 'home_record': '14-26', 'away_record': '11-26'},
    'SAC': {'wins': 21, 'losses': 57, 'record': '21-57', 'win_pct': 0.269, 'home_record': '14-25', 'away_record': '7-32'},
    'NOP': {'wins': 25, 'losses': 53, 'record': '25-53', 'win_pct': 0.321, 'home_record': '16-23', 'away_record': '9-30'},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623},
    'ORL': {'wins': 41, 'losses': 36, 'record': '41-36', 'win_pct': 0.532},
    'MIA': {'wins': 40, 'losses': 37, 'record': '40-37', 'win_pct': 0.519},
    'TOR': {'wins': 43, 'losses': 34, 'record': '43-34', 'win_pct': 0.558},
    'WAS': {'wins': 17, 'losses': 59, 'record': '17-59', 'win_pct': 0.224},
    'DEN': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636},
    'LAC': {'wins': 39, 'losses': 38, 'record': '39-38', 'win_pct': 0.506},
    'PHO': {'wins': 42, 'losses': 35, 'record': '42-35', 'win_pct': 0.545},
    'GSW': {'wins': 36, 'losses': 41, 'record': '36-41', 'win_pct': 0.468},
    'POR': {'wins': 40, 'losses': 38, 'record': '40-38', 'win_pct': 0.513},
}

BACKUP_INJURIES = {
    'MIL': ['Giannis Antetokounmpo (OUT)'], 'LAL': ['Luka Doncic (Questionable)'],
    'DET': ['Cade Cunningham (OUT)'], 'DAL': ['Kyrie Irving (OUT)'],
    'MIN': ['Anthony Edwards (OUT)'], 'PHI': ['Joel Embiid (Doubtful)']
}

ELIMINATED_TEAMS = ['MIL', 'CHI', 'IND', 'BKN', 'WAS', 'MEM', 'NOP', 'DAL', 'UTA', 'SAC']

TEAM_DATA = {
    'OKC': {'off_rtg': 118.8, 'def_rtg': 107.5}, 'DET': {'off_rtg': 117.5, 'def_rtg': 109.6},
    'SAS': {'off_rtg': 119.4, 'def_rtg': 111.0}, 'BOS': {'off_rtg': 120.4, 'def_rtg': 112.7},
    'NYK': {'off_rtg': 119.7, 'def_rtg': 113.5}, 'HOU': {'off_rtg': 118.0, 'def_rtg': 113.4},
    'TOR': {'off_rtg': 115.4, 'def_rtg': 113.6}, 'PHI': {'off_rtg': 116.0, 'def_rtg': 116.0},
    'MIN': {'off_rtg': 116.5, 'def_rtg': 113.1}, 'LAL': {'off_rtg': 118.2, 'def_rtg': 116.8}
}

def norm(abbr):
    mapping = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_daily_slate():
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today_str}"
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
    # Returns an empty list if there are truly no games today, instead of being stuck on April 4th games
    return []

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
                def get_rec(k): return stats.get(k, {}).get('summary') or stats.get(k, {}).get('displayValue', '0-0')
                wins, losses = int(stats.get('wins', {}).get('value', 0)), int(stats.get('losses', {}).get('value', 0))
                if wins + losses > 0:
                    result[abbr] = {
                        'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 
                        'win_pct': wins / (wins + losses),
                        'home_record': get_rec('home'), 'away_record': get_rec('away')
                    }
        if len(result) > 10: return result
    except: pass
    return BACKUP_STANDINGS

# 🚨 THE NEW ADVANCED WEB SCRAPER FOR INJURIES 🚨
@st.cache_data(ttl=600)
def get_injuries():
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        from bs4 import BeautifulSoup
        html = requests.get(url, headers=headers, timeout=5).text
        soup = BeautifulSoup(html, 'html.parser')
        news = {}
        
        # CBS maps injuries by city name, we convert that to our 3-letter codes
        TEAM_MAP = {
            'Atlanta': 'ATL', 'Boston': 'BOS', 'Brooklyn': 'BKN', 'Charlotte': 'CHA',
            'Chicago': 'CHI', 'Cleveland': 'CLE', 'Dallas': 'DAL', 'Denver': 'DEN',
            'Detroit': 'DET', 'Golden State': 'GSW', 'Houston': 'HOU', 'Indiana': 'IND',
            'L.A. Clippers': 'LAC', 'L.A. Lakers': 'LAL', 'Memphis': 'MEM', 'Miami': 'MIA',
            'Milwaukee': 'MIL', 'Minnesota': 'MIN', 'New Orleans': 'NOP', 'New York': 'NYK',
            'Oklahoma City': 'OKC', 'Orlando': 'ORL', 'Philadelphia': 'PHI', 'Phoenix': 'PHO',
            'Portland': 'POR', 'Sacramento': 'SAC', 'San Antonio': 'SAS', 'Toronto': 'TOR',
            'Utah': 'UTA', 'Washington': 'WAS'
        }
        
        for table in soup.find_all('div', class_='TableBase'):
            team_span = table.find('span', class_='TeamName')
            if not team_span: continue
            
            abbr = TEAM_MAP.get(team_span.text.strip())
            if not abbr: continue
            
            players = []
            for row in table.find_all('tr', class_='TableBase-bodyTr'):
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Physically scrape the Player Name and Status columns
                    player = cols[0].get_text(strip=True)
                    status = cols[3].get_text(strip=True)
                    
                    if any(p.lower() in player.lower() for p in CLEARED_PLAYERS):
                        continue
                    
                    # Ignore players who are cleared to play
                    if status.lower() not in ['expected to play', 'probable', 'active']:
                        players.append(f"{player} ({status})")
            
            if players:
                news[abbr] = players[:2] # Grab the top 2 injuries for UI cleanliness
                
        if news: return news
    except: pass
    
    # If the internet drops or you forgot to pip install bs4, it falls back here safely
    return BACKUP_INJURIES

@st.cache_data(ttl=600)
def get_back_to_back():
    b2b = set()
    yest = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
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
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'home_record': '0-0', 'away_record': '0-0'})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'home_record': '0-0', 'away_record': '0-0'})
    
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

    # 4. Playoff Status / Tanking Logic
    if h in ELIMINATED_TEAMS:
        total -= 9.0
        factors.append({"icon": "🎯", "name": "Elimination Penalty", "adj": -9.0, "why": f"{h} is out of playoff contention."})
    if a in ELIMINATED_TEAMS:
        total += 9.0
        factors.append({"icon": "🎯", "name": "Elimination Boost", "adj": 9.0, "why": f"{a} is out of playoff contention."})

    # 5. Fatigue Check (B2B)
    if h in b2b_set:
        total -= 4.0; factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -4.0, "why": f"{h} played yesterday."})
    if a in b2b_set:
        total += 4.0; factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 4.0, "why": f"{a} played yesterday."})

    # 6. DUAL INJURY DETECTION
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj:
        total -= 6.0
        factors.append({"icon": "🤕", "name": f"{h} Injury Impact", "adj": -6.0, "why": f"{h} has key players out."})
    if a_inj: 
        total += 6.0
        factors.append({"icon": "🤕", "name": f"{a} Injury Impact", "adj": 6.0, "why": f"{a} has key players out."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor 2026")

# Dynamic Date Fix: Now it automatically changes at midnight ET!
current_market_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Market Date:** {current_market_date}")
st.divider()

slate, standings, injuries, b2b = get_daily_slate(), get_standings(), get_injuries(), get_back_to_back()

# Fallback in case there are zero games on the schedule today
if not slate:
    st.info("No games scheduled for today, or ESPN hasn't published the slate yet.")
else:
    for game in slate:
        h, a = game['h'], game['a']
        pred = predict_game(h, a, standings, injuries, b2b)
        
        with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {pred['winner']} Wins")
            
            st.markdown("#### 🧠 The Transparent Reasoning Log")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
                
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                st.write(f"**Record:** {pred['h_std']['record']} (Home: {pred['h_std'].get('home_record', '0-0')})")
                for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                st.write(f"**Record:** {pred['a_std']['record']} (Away: {pred['a_std'].get('away_record', '0-0')})")
                for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

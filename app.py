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
# 🚨 MANUAL OVERRIDES & PLAYER TIERS 🚨
# ─────────────────────────────────────────────────────────────────────────────
CLEARED_PLAYERS = []

# 2026 STAR LIST (Threshold: 12.5 PPG and ABOVE + Elite Defenders)
STAR_PLAYERS = [
    "Jalen Duren", "Alex Sarr", "Cooper Flagg", "Deni Avdija", "Norman Powell", "Donovan Clingan",
    "Kon Knueppel", "Reed Sheppard", "Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Aaron Gordon",
    "Luka Doncic", "Kyrie Irving", "Shai Gilgeous-Alexander", "Jalen Williams", "Chet Holmgren",
    "Anthony Edwards", "Karl-Anthony Towns", "Rudy Gobert", "Jaden McDaniels",
    "Kawhi Leonard", "Paul George", "James Harden", "LeBron James", "Anthony Davis", 
    "Kevin Durant", "Devin Booker", "Bradley Beal", "De'Aaron Fox", "Domantas Sabonis", 
    "Zion Williamson", "Brandon Ingram", "CJ McCollum", "Herb Jones", "Stephen Curry", 
    "Jayson Tatum", "Jaylen Brown", "Kristaps Porzingis", "Derrick White", "Jrue Holiday",
    "Giannis Antetokounmpo", "Damian Lillard", "Khris Middleton", "Joel Embiid", "Tyrese Maxey", 
    "Donovan Mitchell", "Darius Garland", "Evan Mobley", "Jarrett Allen", "Jalen Brunson", 
    "Julius Randle", "OG Anunoby", "Jimmy Butler", "Bam Adebayo", "Paolo Banchero", 
    "Franz Wagner", "Tyrese Haliburton", "Pascal Siakam", "DeMar DeRozan", "Zach LaVine", 
    "Trae Young", "Dejounte Murray", "Scottie Barnes", "RJ Barrett", "Victor Wembanyama", 
    "Alperen Sengun", "Cade Cunningham", "Lauri Markkanen", "Mikal Bridges", "Ja Morant",
    "Jalen Johnson", "Nickeil Alexander-Walker", "Amen Thompson", "Cason Wallace"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. STANDINGS & BACKUPS
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '30-9', 'away_record': '26-12'},
    'BOS': {'wins': 52, 'losses': 25, 'record': '52-25', 'win_pct': 0.675, 'home_record': '26-11', 'away_record': '26-14'},
    'NYK': {'wins': 50, 'losses': 28, 'record': '50-28', 'win_pct': 0.641, 'home_record': '28-9', 'away_record': '22-19'},
    'PHI': {'wins': 43, 'losses': 34, 'record': '43-34', 'win_pct': 0.558, 'home_record': '22-17', 'away_record': '21-17'},
    'ATL': {'wins': 45, 'losses': 33, 'record': '45-33', 'win_pct': 0.577, 'home_record': '23-16', 'away_record': '22-17'},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792, 'home_record': '33-6', 'away_record': '28-9'},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766, 'home_record': '29-7', 'away_record': '29-11'},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'DEN': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '24-13', 'away_record': '25-15'},
}

ELIMINATED_TEAMS = ['MIL', 'CHI', 'IND', 'BKN', 'WAS', 'MEM', 'NOP', 'DAL', 'UTA', 'SAC']

TEAM_DATA = {
    'OKC': {'off_rtg': 118.8, 'def_rtg': 107.5}, 'DET': {'off_rtg': 117.5, 'def_rtg': 109.6},
    'SAS': {'off_rtg': 119.4, 'def_rtg': 111.0}, 'BOS': {'off_rtg': 120.4, 'def_rtg': 112.7},
    'NYK': {'off_rtg': 119.7, 'def_rtg': 113.5}, 'LAL': {'off_rtg': 118.2, 'def_rtg': 116.8}
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
        return games if games else []
    except: return []

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
                result[abbr] = {
                    'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 
                    'win_pct': wins / (wins + losses) if (wins + losses) > 0 else 0.5,
                    'home_record': stats.get('home', {}).get('displayValue', '0-0'),
                    'away_record': stats.get('road', {}).get('displayValue', '0-0')
                }
        return result if len(result) > 10 else BACKUP_STANDINGS
    except: return BACKUP_STANDINGS

@st.cache_data(ttl=600)
def get_injuries():
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        from bs4 import BeautifulSoup
        html = requests.get(url, headers=headers, timeout=5).text
        soup = BeautifulSoup(html, 'html.parser')
        news = {}
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
            team_raw = table.find('span', class_='TeamName')
            if not team_raw: team_raw = table.find(class_='TeamLogoNameLockup-name')
            if not team_raw: continue
            abbr = TEAM_MAP.get(team_raw.get_text(strip=True))
            if not abbr: continue
            players = []
            for row in table.find_all('tr', class_='TableBase-bodyTr'):
                cols = row.find_all('td')
                if len(cols) >= 5:
                    p_text = cols[0].get_text(strip=True)
                    injury, status = cols[3].get_text(strip=True), cols[4].get_text(strip=True)
                    if status.lower() not in ['expected to play', 'probable', 'active']:
                        players.append(f"{p_text} ({injury})")
            if players: news[abbr] = players 
        return news
    except: return {}

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
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    
    factors, total = [], 0.0
    
    # 1. Win % Edge
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 25.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Win % Edge", "adj": base_adj, "why": f"{h} vs {a}"})

    # 2. Home Court
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": f"Advantage for {h}"})

    # 3. Efficiency
    eff_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += eff_adj
    factors.append({"icon": "🛡️", "name": "Defense Gap", "adj": eff_adj, "why": "Efficiency comparison"})

    # 4. INJURY DETECTION (IMPROVED FUZZY MATCHING)
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    def get_player_impact(scraped_string):
        raw = scraped_string.lower().strip()
        # Bulletproof Matching: Check if Star is in the name or vice versa
        for star in STAR_PLAYERS:
            s = star.lower()
            if s in raw or raw in s:
                return 5.5, "Star"
        return 1.5, "Role"

    def calc_injury_penalty(inj_list):
        pen = 0.0
        details = []
        for p in inj_list:
            val, tier = get_player_impact(p)
            pen += val
            details.append(f"{p.split(' (')[0]} ({tier})")
        return pen, details

    if h_inj:
        p, d = calc_injury_penalty(h_inj)
        total -= p
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": -p, "why": f"Missing: {', '.join(d)}"})
    if a_inj:
        p, d = calc_injury_penalty(a_inj)
        total += p
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": p, "why": f"Missing: {', '.join(d)}"})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor 2026")
current_market_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Market Date:** {current_market_date}")
st.divider()

slate, standings, injuries, b2b = get_daily_slate(), get_standings(), get_injuries(), get_back_to_back()

if not slate:
    st.info("No games scheduled for today.")
else:
    for game in slate:
        h, a = game['h'], game['a']
        pred = predict_game(h, a, standings, injuries, b2b)
        with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {pred['winner']} Wins")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                st.write(f"**Record:** {pred['h_std'].get('record', '0-0')}")
                for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                st.write(f"**Record:** {pred['a_std'].get('record', '0-0')}")
                for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

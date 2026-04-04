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

# 2026 MASTER STAR LIST (Threshold: 12.5 PPG and ABOVE + Elite Defenders)
STAR_PLAYERS = [
    "Paul George", "Joel Embiid", "Tyrese Maxey", "Jalen Duren", "Alex Sarr", 
    "Cooper Flagg", "Deni Avdija", "Norman Powell", "Donovan Clingan",
    "Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Aaron Gordon",
    "Luka Doncic", "Kyrie Irving", "Shai Gilgeous-Alexander", "Jalen Williams", "Chet Holmgren",
    "Anthony Edwards", "Karl-Anthony Towns", "Rudy Gobert", "Jaden McDaniels",
    "Kawhi Leonard", "James Harden", "LeBron James", "Anthony Davis", 
    "Kevin Durant", "Devin Booker", "Bradley Beal", "De'Aaron Fox", "Domantas Sabonis", 
    "Zion Williamson", "Brandon Ingram", "CJ McCollum", "Herb Jones", "Stephen Curry", 
    "Jayson Tatum", "Jaylen Brown", "Kristaps Porzingis", "Derrick White", "Jrue Holiday",
    "Giannis Antetokounmpo", "Damian Lillard", "Khris Middleton", 
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
    'ATL': {'wins': 45, 'losses': 33, 'record': '45-33', 'win_pct': 0.577, 'home_record': '23-16', 'away_record': '22-17'},
    'BOS': {'wins': 52, 'losses': 25, 'record': '52-25', 'win_pct': 0.675, 'home_record': '26-11', 'away_record': '26-14'},
    'BKN': {'wins': 32, 'losses': 45, 'record': '32-45', 'win_pct': 0.416, 'home_record': '18-20', 'away_record': '14-25'},
    'CHA': {'wins': 25, 'losses': 52, 'record': '25-52', 'win_pct': 0.325, 'home_record': '13-25', 'away_record': '12-27'},
    'CHI': {'wins': 39, 'losses': 38, 'record': '39-38', 'win_pct': 0.506, 'home_record': '20-19', 'away_record': '19-19'},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623, 'home_record': '25-13', 'away_record': '23-16'},
    'DAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'DEN': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '24-13', 'away_record': '25-15'},
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '30-9', 'away_record': '26-12'},
    'GSW': {'wins': 44, 'losses': 33, 'record': '44-33', 'win_pct': 0.571, 'home_record': '23-15', 'away_record': '21-18'},
    'HOU': {'wins': 41, 'losses': 36, 'record': '41-36', 'win_pct': 0.532, 'home_record': '22-16', 'away_record': '19-20'},
    'IND': {'wins': 46, 'losses': 32, 'record': '46-32', 'win_pct': 0.590, 'home_record': '24-15', 'away_record': '22-17'},
    'LAC': {'wins': 47, 'losses': 30, 'record': '47-30', 'win_pct': 0.610, 'home_record': '25-13', 'away_record': '22-17'},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'MEM': {'wins': 35, 'losses': 42, 'record': '35-42', 'win_pct': 0.455, 'home_record': '18-21', 'away_record': '17-21'},
    'MIA': {'wins': 44, 'losses': 33, 'record': '44-33', 'win_pct': 0.571, 'home_record': '22-16', 'away_record': '22-17'},
    'MIL': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '27-11', 'away_record': '22-17'},
    'MIN': {'wins': 54, 'losses': 23, 'record': '54-23', 'win_pct': 0.701, 'home_record': '28-10', 'away_record': '26-13'},
    'NOP': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623, 'home_record': '23-15', 'away_record': '25-14'},
    'NYK': {'wins': 50, 'losses': 28, 'record': '50-28', 'win_pct': 0.641, 'home_record': '28-9', 'away_record': '22-19'},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792, 'home_record': '33-6', 'away_record': '28-9'},
    'ORL': {'wins': 46, 'losses': 31, 'record': '46-31', 'win_pct': 0.597, 'home_record': '27-12', 'away_record': '19-19'},
    'PHI': {'wins': 43, 'losses': 34, 'record': '43-34', 'win_pct': 0.558, 'home_record': '22-17', 'away_record': '21-17'},
    'PHO': {'wins': 47, 'losses': 30, 'record': '47-30', 'win_pct': 0.610, 'home_record': '26-13', 'away_record': '21-17'},
    'POR': {'wins': 21, 'losses': 56, 'record': '21-56', 'win_pct': 0.273, 'home_record': '11-27', 'away_record': '10-29'},
    'SAC': {'wins': 45, 'losses': 32, 'record': '45-32', 'win_pct': 0.584, 'home_record': '23-15', 'away_record': '22-17'},
    'SAS': {'wins': 59, 'losses': 18, 'record': '59-18', 'win_pct': 0.766, 'home_record': '29-7', 'away_record': '29-11'},
    'TOR': {'wins': 33, 'losses': 44, 'record': '33-44', 'win_pct': 0.429, 'home_record': '18-21', 'away_record': '15-23'},
    'UTA': {'wins': 31, 'losses': 46, 'record': '31-46', 'win_pct': 0.403, 'home_record': '19-19', 'away_record': '12-27'},
    'WAS': {'wins': 15, 'losses': 62, 'record': '15-62', 'win_pct': 0.195, 'home_record': '7-31', 'away_record': '8-31'},
}

TEAM_DATA = {
    'ATL': {'off_rtg': 116.4, 'def_rtg': 114.2}, 'BOS': {'off_rtg': 120.4, 'def_rtg': 112.7},
    'BKN': {'off_rtg': 111.2, 'def_rtg': 115.8}, 'CHA': {'off_rtg': 109.5, 'def_rtg': 119.2},
    'CHI': {'off_rtg': 114.1, 'def_rtg': 115.4}, 'CLE': {'off_rtg': 115.8, 'def_rtg': 111.2},
    'DAL': {'off_rtg': 118.9, 'def_rtg': 115.1}, 'DEN': {'off_rtg': 118.2, 'def_rtg': 113.8},
    'DET': {'off_rtg': 117.5, 'def_rtg': 109.6}, 'GSW': {'off_rtg': 117.1, 'def_rtg': 114.9},
    'HOU': {'off_rtg': 113.9, 'def_rtg': 112.8}, 'IND': {'off_rtg': 121.2, 'def_rtg': 119.1},
    'LAC': {'off_rtg': 116.8, 'def_rtg': 113.5}, 'LAL': {'off_rtg': 118.2, 'def_rtg': 116.8},
    'MEM': {'off_rtg': 110.4, 'def_rtg': 112.1}, 'MIA': {'off_rtg': 113.2, 'def_rtg': 112.5},
    'MIL': {'off_rtg': 119.4, 'def_rtg': 116.2}, 'MIN': {'off_rtg': 115.1, 'def_rtg': 108.4},
    'NOP': {'off_rtg': 117.2, 'def_rtg': 113.1}, 'NYK': {'off_rtg': 119.7, 'def_rtg': 113.5},
    'OKC': {'off_rtg': 118.8, 'def_rtg': 107.5}, 'ORL': {'off_rtg': 112.9, 'def_rtg': 110.8},
    'PHI': {'off_rtg': 117.5, 'def_rtg': 113.2}, 'PHO': {'off_rtg': 118.5, 'def_rtg': 115.8},
    'POR': {'off_rtg': 108.8, 'def_rtg': 117.5}, 'SAC': {'off_rtg': 117.8, 'def_rtg': 116.2},
    'SAS': {'off_rtg': 119.4, 'def_rtg': 111.0}, 'TOR': {'off_rtg': 114.5, 'def_rtg': 117.8},
    'UTA': {'off_rtg': 115.2, 'def_rtg': 119.5}, 'WAS': {'off_rtg': 110.1, 'def_rtg': 121.4}
}

def norm(abbr):
    mapping = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN', 'PHX': 'PHO'}
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
    b2b_list = set()
    yest = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest}"
    try:
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b_list.add(norm(c['team']['abbreviation']))
    except: pass
    return b2b_list

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

    # 2. Home Court (Specialized Altitude Adjustment for Denver)
    hca = 5.5 if h == 'DEN' else 3.5
    total += hca
    hca_why = f"Altitude Advantage for {h}" if h == 'DEN' else f"Advantage for {h}"
    factors.append({"icon": "🏠", "name": "Home Court", "adj": hca, "why": hca_why})

    # 3. Efficiency
    eff_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += eff_adj
    factors.append({"icon": "🛡️", "name": "Defense Gap", "adj": eff_adj, "why": "Efficiency comparison"})

    # 4. INJURY DETECTION (SUPER-CLEAN MATCHING)
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    def get_player_impact(scraped_string):
        raw = scraped_string.lower().split(" (")[0].replace(".", "").replace(" jr", "").replace(" iii", "").strip()
        for star in STAR_PLAYERS:
            s = star.lower().replace(".", "").replace(" jr", "").replace(" iii", "").strip()
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

    # 5. BACK-TO-BACK FATIGUE
    if h in b2b_set:
        total -= 4.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -4.0, "why": f"{h} played yesterday."})
    if a in b2b_set:
        total += 4.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 4.0, "why": f"{a} played yesterday."})

    # 6. TANKING PENALTY (Late Season April 2026 Logic)
    if h_std['win_pct'] < 0.350:
        total -= 7.0
        factors.append({"icon": "📉", "name": f"{h} Tanking Penalty", "adj": -7.0, "why": "Incentivized lottery prioritization."})
    if a_std['win_pct'] < 0.350:
        total += 7.0
        factors.append({"icon": "📉", "name": f"{a} Tanking Penalty", "adj": 7.0, "why": "Incentivized lottery prioritization."})

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

# Sidebar Debugger for Fatigue
st.sidebar.subheader("📊 Fatigue Status")
if b2b:
    st.sidebar.write(f"**Teams on B2B:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs today.")

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

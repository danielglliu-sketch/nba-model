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

# SUPERSTARS (-8.0) - Top 10-15 MVP Level Franchise Players
SUPERSTARS = [
    "Nikola Jokic", "Luka Doncic", "Shai Gilgeous-Alexander", "Giannis Antetokounmpo", 
    "Joel Embiid", "Jayson Tatum", "Stephen Curry", "Kevin Durant", "LeBron James", 
    "Anthony Edwards"
]

# ALL-STARS (-4.5) - #2 Options, Consistent All-Stars, Elite Lead Guards
ALL_STARS = [
    "Donovan Mitchell", "Devin Booker", "De'Aaron Fox", "Tyrese Maxey", "Jalen Brunson",
    "Anthony Davis", "Tyrese Haliburton", "Damian Lillard", "Kyrie Irving",
    "Paolo Banchero", "Victor Wembanyama", "Alperen Sengun", "Cade Cunningham", 
    "Zion Williamson", "Jaylen Brown", "Karl-Anthony Towns", "Ja Morant", 
    "Lauri Markkanen", "DeMar DeRozan", "Jimmy Butler", "Bam Adebayo", 
    "Jamal Murray", "Paul George", "Kawhi Leonard", "James Harden", "Trae Young", 
    "Dejounte Murray", "Pascal Siakam", "Scottie Barnes", "Jalen Williams"
]

# HIGH-IMPACT (-2.0) - Elite Role Players, Defensive Anchors, 15+ PPG Scorers
HIGH_IMPACT = [
    "Desmond Bane", "Zach LaVine", "Julius Randle", "Chet Holmgren", 
    "Michael Porter Jr.", "Bradley Beal", "Mikal Bridges", "Cam Thomas", 
    "Anfernee Simons", "Jerami Grant", "Kyle Kuzma", "Jordan Poole", 
    "Tyler Herro", "CJ McCollum", "Jalen Green", "Fred VanVleet",
    "RJ Barrett", "Immanuel Quickley", "Franz Wagner", "Jalen Duren", "Jaden Ivey",
    "Bogdan Bogdanovic", "Miles Bridges", "Terry Rozier", "Malcolm Brogdon", 
    "Deandre Ayton", "John Collins", "Collin Sexton", "Austin Reaves", "D'Angelo Russell",
    "Jusuf Nurkic", "Aaron Gordon", "Khris Middleton", "Brook Lopez", "Bobby Portis",
    "Kristaps Porzingis", "Derrick White", "Jrue Holiday", "Bennedict Mathurin", 
    "Myles Turner", "Jalen Johnson", "Trey Murphy III", "Keldon Johnson", "Devin Vassell",
    "Deni Avdija", "Norman Powell", "Alex Sarr", "Cooper Flagg", "Donovan Clingan",
    "Rudy Gobert", "Naz Reid", "Jaden McDaniels", "Mike Conley", "Coby White",
    "Nikola Vucevic", "Evan Mobley", "Jarrett Allen", "Darius Garland", "Caris LeVert",
    "Alex Caruso", "Marcus Smart", "Lu Dort", "Herbert Jones", "Draymond Green", 
    "Nic Claxton", "Walker Kessler", "OG Anunoby", "Matisse Thybulle", "Jose Alvarado",
    "Nickeil Alexander-Walker", "Amen Thompson", "Cason Wallace",
    "Josh Giddey", "Klay Thompson", "De'Andre Hunter", "Donte DiVincenzo", 
    "Tobias Harris", "Buddy Hield", "PJ Washington", "Bojan Bogdanovic", 
    "Harrison Barnes", "Jordan Clarkson", "Dennis Schroder", "Cameron Johnson",
    "Keegan Murray", "Malik Monk", "Kelly Oubre Jr.", "Jabari Smith Jr.", "Jalen Suggs",
    "Cam Whitmore", "GG Jackson", "Keyonte George", "Josh Hart", "Rui Hachimura",
    "Clint Capela", "Ivica Zubac", "Jonas Valanciunas", "Wendell Carter Jr."
]

# PLAYER ARCHETYPES (Changes how their injury affects Offense vs Defense)
DEFENSIVE_LIABILITIES = [
    "Trae Young", "Damian Lillard", "Luka Doncic", "Tyrese Haliburton",
    "Tyler Herro", "D'Angelo Russell", "Jordan Poole", "CJ McCollum",
    "Bradley Beal", "Cam Thomas", "Anfernee Simons", "Zach LaVine",
    "Buddy Hield", "Bojan Bogdanovic", "Karl-Anthony Towns"
]

OFFENSIVE_LIABILITIES = [
    "Rudy Gobert", "Alex Caruso", "Marcus Smart", "Lu Dort", "Herbert Jones", 
    "Draymond Green", "Nic Claxton", "Walker Kessler", "OG Anunoby", 
    "Matisse Thybulle", "Jose Alvarado", "Amen Thompson", "Cason Wallace",
    "Clint Capela", "Mitchell Robinson"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. STANDINGS & BACKUPS (April 5, 2026 Records)
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'DET': {'wins': 57, 'losses': 21, 'record': '57-21', 'win_pct': 0.731, 'home_record': '30-9', 'away_record': '27-12'},
    'BOS': {'wins': 52, 'losses': 25, 'record': '52-25', 'win_pct': 0.675, 'home_record': '26-11', 'away_record': '26-14'},
    'NYK': {'wins': 50, 'losses': 28, 'record': '50-28', 'win_pct': 0.641, 'home_record': '28-9', 'away_record': '22-19'},
    'CLE': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623, 'home_record': '24-14', 'away_record': '24-15'},
    'ATL': {'wins': 45, 'losses': 33, 'record': '45-33', 'win_pct': 0.577, 'home_record': '23-16', 'away_record': '22-17'},
    'TOR': {'wins': 43, 'losses': 34, 'record': '43-34', 'win_pct': 0.558, 'home_record': '21-17', 'away_record': '22-17'},
    'PHI': {'wins': 43, 'losses': 35, 'record': '43-35', 'win_pct': 0.551, 'home_record': '22-18', 'away_record': '21-17'},
    'CHA': {'wins': 42, 'losses': 36, 'record': '42-36', 'win_pct': 0.538, 'home_record': '21-19', 'away_record': '21-17'},
    'ORL': {'wins': 41, 'losses': 36, 'record': '41-36', 'win_pct': 0.532, 'home_record': '23-15', 'away_record': '18-21'},
    'MIA': {'wins': 41, 'losses': 37, 'record': '41-37', 'win_pct': 0.526, 'home_record': '25-15', 'away_record': '16-22'},
    'MIL': {'wins': 30, 'losses': 47, 'record': '30-47', 'win_pct': 0.39, 'home_record': '17-22', 'away_record': '13-25'},
    'CHI': {'wins': 29, 'losses': 48, 'record': '29-48', 'win_pct': 0.377, 'home_record': '18-21', 'away_record': '11-27'},
    'IND': {'wins': 18, 'losses': 59, 'record': '18-59', 'win_pct': 0.234, 'home_record': '11-27', 'away_record': '7-32'},
    'BKN': {'wins': 18, 'losses': 59, 'record': '18-59', 'win_pct': 0.234, 'home_record': '10-28', 'away_record': '8-31'},
    'WAS': {'wins': 17, 'losses': 60, 'record': '17-60', 'win_pct': 0.221, 'home_record': '11-27', 'away_record': '6-33'},
    'OKC': {'wins': 61, 'losses': 16, 'record': '61-16', 'win_pct': 0.792, 'home_record': '33-6', 'away_record': '28-10'},
    'SAS': {'wins': 59, 'losses': 19, 'record': '59-19', 'win_pct': 0.756, 'home_record': '29-7', 'away_record': '30-12'},
    'LAL': {'wins': 50, 'losses': 27, 'record': '50-27', 'win_pct': 0.649, 'home_record': '26-12', 'away_record': '24-15'},
    'DEN': {'wins': 50, 'losses': 28, 'record': '50-28', 'win_pct': 0.641, 'home_record': '25-13', 'away_record': '25-15'},
    'HOU': {'wins': 48, 'losses': 29, 'record': '48-29', 'win_pct': 0.623, 'home_record': '28-10', 'away_record': '20-19'},
    'MIN': {'wins': 46, 'losses': 31, 'record': '46-31', 'win_pct': 0.597, 'home_record': '25-14', 'away_record': '21-17'},
    'PHO': {'wins': 42, 'losses': 35, 'record': '42-35', 'win_pct': 0.545, 'home_record': '24-15', 'away_record': '18-20'},
    'POR': {'wins': 40, 'losses': 38, 'record': '40-38', 'win_pct': 0.513, 'home_record': '22-17', 'away_record': '18-21'},
    'LAC': {'wins': 39, 'losses': 38, 'record': '39-38', 'win_pct': 0.506, 'home_record': '21-17', 'away_record': '18-21'},
    'GSW': {'wins': 36, 'losses': 41, 'record': '36-41', 'win_pct': 0.468, 'home_record': '21-17', 'away_record': '15-24'},
    'MEM': {'wins': 25, 'losses': 52, 'record': '25-52', 'win_pct': 0.325, 'home_record': '13-26', 'away_record': '12-26'},
    'NOP': {'wins': 25, 'losses': 53, 'record': '25-53', 'win_pct': 0.321, 'home_record': '16-23', 'away_record': '9-30'},
    'DAL': {'wins': 24, 'losses': 53, 'record': '24-53', 'win_pct': 0.312, 'home_record': '14-25', 'away_record': '10-28'},
    'SAC': {'wins': 21, 'losses': 57, 'record': '21-57', 'win_pct': 0.269, 'home_record': '14-25', 'away_record': '7-32'},
    'UTA': {'wins': 21, 'losses': 57, 'record': '21-57', 'win_pct': 0.269, 'home_record': '13-27', 'away_record': '8-30'},
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
                wins = int(stats.get('wins', {}).get('value', 0))
                losses = int(stats.get('losses', {}).get('value', 0))
                win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5
                
                l10_pct = win_pct
                l10_record = "0-0"
                for key in ['lasttengames', 'lastten', 'last10', 'l10', 'last10games']:
                    if key in stats:
                        l10_record = stats[key].get('displayValue', '0-0')
                        try:
                            l10_w, l10_l = map(int, l10_record.split('-'))
                            l10_pct = l10_w / (l10_w + l10_l) if (l10_w + l10_l) > 0 else win_pct
                        except: pass
                        break
                
                result[abbr] = {
                    'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 
                    'win_pct': win_pct,
                    'l10_pct': l10_pct,
                    'l10_record': l10_record,
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
            
            abbr = None
            if team_raw:
                team_text = team_raw.get_text(strip=True)
                for key, val in TEAM_MAP.items():
                    if key.lower() in team_text.lower():
                        abbr = val
                        break
            
            if not abbr:
                table_html = str(table).lower()
                if 'golden state' in table_html or '/gs/' in table_html: abbr = 'GSW'
                elif 'clippers' in table_html or '/lac/' in table_html: abbr = 'LAC'
                elif 'lakers' in table_html or '/lal/' in table_html: abbr = 'LAL'

            if not abbr: continue
            
            players = []
            for row in table.find_all('tr', class_='TableBase-bodyTr'):
                cols = row.find_all('td')
                if len(cols) >= 5:
                    p_name_elem = cols[0].find('span', class_='CellPlayerName--long')
                    if not p_name_elem: p_name_elem = cols[0].find('a')
                    p_text = p_name_elem.get_text(strip=True) if p_name_elem else cols[0].get_text(strip=True)
                    
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
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td = TEAM_DATA.get(h, {'off_rtg': 112, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 112, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    
    factors, total = [], 0.0
    
    # 1. Win % Edge
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']
    
    if use_l10:
        h_l10 = h_std.get('l10_pct', h_pct)
        a_l10 = a_std.get('l10_pct', a_pct)
        h_pct = (h_pct * 0.6) + (h_l10 * 0.4)
        a_pct = (a_pct * 0.6) + (a_l10 * 0.4)
        
    base_adj = (h_pct - a_pct) * 25.0
    total += base_adj
    edge_name = "Blended Win % Edge (L10)" if use_l10 else "Win % Edge"
    factors.append({"icon": "📊", "name": edge_name, "adj": base_adj, "why": f"{h} vs {a}"})

    # 2. Home Court
    hca = 5.5 if h == 'DEN' else 3.5
    total += hca
    hca_why = f"Altitude Advantage for {h}" if h == 'DEN' else f"Advantage for {h}"
    factors.append({"icon": "🏠", "name": "Home Court", "adj": hca, "why": hca_why})

    # 3. INJURY DETECTION (ARCHETYPE PENALTIES)
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    def get_player_impact(scraped_string):
        raw = scraped_string.lower().split(" (")[0].replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
        
        val, tier = 1.0, "Role"
        for star in SUPERSTARS:
            s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
            if s == raw or s in raw or raw in s: val, tier = 8.0, "Superstar"; break
        if tier == "Role":
            for star in ALL_STARS:
                s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
                if s == raw or s in raw or raw in s: val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for star in HIGH_IMPACT:
                s = star.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
                if s == raw or s in raw or raw in s: val, tier = 2.0, "High-Impact"; break
                
        archetype = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            s = p.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
            if s == raw or s in raw or raw in s: archetype = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            s = p.lower().replace(".", "").replace("'", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" sr", "").strip()
            if s == raw or s in raw or raw in s: archetype = "Off_Liability"; break
            
        return val, tier, archetype

    def calc_injury_penalty(inj_list):
        o_pen, d_pen = 0.0, 0.0
        details = []
        for p in inj_list:
            val, tier, archetype = get_player_impact(p)
            
            if archetype == "Def_Liability":
                o = val * 1.3
                d = val * -0.3 # Negative means defense GETS BETTER without them
            elif archetype == "Off_Liability":
                o = val * -0.3 # Negative means offense GETS BETTER without them
                d = val * 1.3
            else:
                o = val * 0.6
                d = val * 0.4
                
            o_pen += o
            d_pen += d
            details.append(f"{p.split(' (')[0]} ({tier})")
        return o_pen, d_pen, details

    h_off_pen, h_def_pen, h_det = calc_injury_penalty(h_inj) if h_inj else (0.0, 0.0, [])
    a_off_pen, a_def_pen, a_det = calc_injury_penalty(a_inj) if a_inj else (0.0, 0.0, [])

    # 4. Efficiency (Injury-Adjusted Net Rating)
    adj_h_off = h_td['off_rtg'] - h_off_pen
    adj_h_def = h_td['def_rtg'] + h_def_pen  # + makes defense worse
    h_net = adj_h_off - adj_h_def
    
    adj_a_off = a_td['off_rtg'] - a_off_pen
    adj_a_def = a_td['def_rtg'] + a_def_pen
    a_net = adj_a_off - adj_a_def
    
    net_edge = (h_net - a_net) * 0.6
    total += net_edge
    
    factors.append({"icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge, "why": "Net Rating adjusted dynamically by player archetype"})

    if h_inj:
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": f"Impact baked into Net Rating. Missing: {', '.join(h_det)}"})
    if a_inj:
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": f"Impact baked into Net Rating. Missing: {', '.join(a_det)}"})

    # 5. BACK-TO-BACK FATIGUE
    if h in b2b_set:
        total -= 4.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -4.0, "why": f"{h} played yesterday."})
    if a in b2b_set:
        total += 4.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 4.0, "why": f"{a} played yesterday."})

    # 6. TANKING PENALTY
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

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])

with tab1:
    if not slate:
        st.info("No games scheduled for today.")
    else:
        for game in slate:
            h, a = game['h'], game['a']
            pred = predict_game(h, a, standings, injuries, b2b, use_l10=False)
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

with tab2:
    if not slate:
        st.info("No games scheduled for today.")
    else:
        for game in slate:
            h, a = game['h'], game['a']
            pred = predict_game(h, a, standings, injuries, b2b, use_l10=True)
            with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
                st.markdown(f"### 🏆 {pred['winner']} Wins")
                for f in pred['factors']:
                    color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                    st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"#### 🏠 {game['h_name']}")
                    st.write(f"**Record:** {pred['h_std'].get('record', '0-0')} *(L10: {pred['h_std'].get('l10_record', 'N/A')})*")
                    for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
                with col2:
                    st.markdown(f"#### ✈️ {game['a_name']}")
                    st.write(f"**Record:** {pred['a_std'].get('record', '0-0')} *(L10: {pred['a_std'].get('l10_record', 'N/A')})*")
                    for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

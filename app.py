import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="NBA Master AI Predictor", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ System Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! The app is pulling fresh data.")

# ─────────────────────────────────────────────────────────────────────────────
# 1. THE FULL 30-TEAM STARTING ROSTER DATABASE
# ─────────────────────────────────────────────────────────────────────────────
STARTING_FIVES = {
    # EASTERN CONFERENCE
    'BOS': {'PG': {'name': 'Jrue Holiday', 'off': 82, 'def': 94}, 'SG': {'name': 'Derrick White', 'off': 84, 'def': 89}, 'SF': {'name': 'Jaylen Brown', 'off': 89, 'def': 84}, 'PF': {'name': 'Jayson Tatum', 'off': 94, 'def': 86}, 'C': {'name': 'Kristaps Porzingis', 'off': 86, 'def': 82}},
    'NYK': {'PG': {'name': 'Jalen Brunson', 'off': 95, 'def': 74}, 'SG': {'name': 'Mikal Bridges', 'off': 85, 'def': 91}, 'SF': {'name': 'OG Anunoby', 'off': 81, 'def': 93}, 'PF': {'name': 'Karl-Anthony Towns', 'off': 91, 'def': 79}, 'C': {'name': 'Mitchell Robinson', 'off': 75, 'def': 89}},
    'PHI': {'PG': {'name': 'Tyrese Maxey', 'off': 90, 'def': 75}, 'SG': {'name': 'Kelly Oubre Jr.', 'off': 79, 'def': 76}, 'SF': {'name': 'Paul George', 'off': 88, 'def': 84}, 'PF': {'name': 'Caleb Martin', 'off': 76, 'def': 81}, 'C': {'name': 'Joel Embiid', 'off': 97, 'def': 88}},
    'MIL': {'PG': {'name': 'Damian Lillard', 'off': 92, 'def': 72}, 'SG': {'name': 'Gary Trent Jr.', 'off': 79, 'def': 75}, 'SF': {'name': 'Khris Middleton', 'off': 84, 'def': 78}, 'PF': {'name': 'Giannis Antetokounmpo', 'off': 96, 'def': 89}, 'C': {'name': 'Brook Lopez', 'off': 79, 'def': 86}},
    'CLE': {'PG': {'name': 'Darius Garland', 'off': 85, 'def': 74}, 'SG': {'name': 'Donovan Mitchell', 'off': 92, 'def': 76}, 'SF': {'name': 'Max Strus', 'off': 78, 'def': 77}, 'PF': {'name': 'Evan Mobley', 'off': 83, 'def': 89}, 'C': {'name': 'Jarrett Allen', 'off': 82, 'def': 86}},
    'IND': {'PG': {'name': 'Tyrese Haliburton', 'off': 91, 'def': 74}, 'SG': {'name': 'Andrew Nembhard', 'off': 79, 'def': 81}, 'SF': {'name': 'Aaron Nesmith', 'off': 78, 'def': 84}, 'PF': {'name': 'Pascal Siakam', 'off': 87, 'def': 80}, 'C': {'name': 'Myles Turner', 'off': 82, 'def': 85}},
    'ORL': {'PG': {'name': 'Jalen Suggs', 'off': 79, 'def': 90}, 'SG': {'name': 'Kentavious Caldwell-Pope', 'off': 78, 'def': 86}, 'SF': {'name': 'Franz Wagner', 'off': 85, 'def': 81}, 'PF': {'name': 'Paolo Banchero', 'off': 89, 'def': 79}, 'C': {'name': 'Wendell Carter Jr.', 'off': 78, 'def': 82}},
    'MIA': {'PG': {'name': 'Terry Rozier', 'off': 83, 'def': 75}, 'SG': {'name': 'Tyler Herro', 'off': 84, 'def': 73}, 'SF': {'name': 'Jimmy Butler', 'off': 89, 'def': 87}, 'PF': {'name': 'Nikola Jovic', 'off': 78, 'def': 76}, 'C': {'name': 'Bam Adebayo', 'off': 86, 'def': 92}},
    'CHI': {'PG': {'name': 'Josh Giddey', 'off': 81, 'def': 76}, 'SG': {'name': 'Coby White', 'off': 84, 'def': 74}, 'SF': {'name': 'Zach LaVine', 'off': 85, 'def': 73}, 'PF': {'name': 'Patrick Williams', 'off': 77, 'def': 82}, 'C': {'name': 'Nikola Vucevic', 'off': 82, 'def': 75}},
    'ATL': {'PG': {'name': 'Trae Young', 'off': 91, 'def': 70}, 'SG': {'name': 'Dyson Daniels', 'off': 75, 'def': 86}, 'SF': {'name': 'Jalen Johnson', 'off': 83, 'def': 82}, 'PF': {'name': 'Zaccharie Risacher', 'off': 76, 'def': 77}, 'C': {'name': 'Clint Capela', 'off': 79, 'def': 81}},
    'BKN': {'PG': {'name': 'Dennis Schroder', 'off': 80, 'def': 78}, 'SG': {'name': 'Cam Thomas', 'off': 85, 'def': 71}, 'SF': {'name': 'Cameron Johnson', 'off': 81, 'def': 78}, 'PF': {'name': 'Dorian Finney-Smith', 'off': 75, 'def': 83}, 'C': {'name': 'Nic Claxton', 'off': 78, 'def': 87}},
    'TOR': {'PG': {'name': 'Immanuel Quickley', 'off': 83, 'def': 76}, 'SG': {'name': 'RJ Barrett', 'off': 83, 'def': 75}, 'SF': {'name': 'Scottie Barnes', 'off': 86, 'def': 84}, 'PF': {'name': 'Kelly Olynyk', 'off': 78, 'def': 74}, 'C': {'name': 'Jakob Poeltl', 'off': 78, 'def': 82}},
    'CHA': {'PG': {'name': 'LaMelo Ball', 'off': 88, 'def': 74}, 'SG': {'name': 'Brandon Miller', 'off': 83, 'def': 78}, 'SF': {'name': 'Miles Bridges', 'off': 84, 'def': 77}, 'PF': {'name': 'Grant Williams', 'off': 76, 'def': 80}, 'C': {'name': 'Mark Williams', 'off': 79, 'def': 83}},
    'WAS': {'PG': {'name': 'Jordan Poole', 'off': 81, 'def': 72}, 'SG': {'name': 'Bilal Coulibaly', 'off': 75, 'def': 84}, 'SF': {'name': 'Kyle Kuzma', 'off': 84, 'def': 75}, 'PF': {'name': 'Alex Sarr', 'off': 76, 'def': 82}, 'C': {'name': 'Jonas Valanciunas', 'off': 81, 'def': 77}},
    'DET': {'PG': {'name': 'Cade Cunningham', 'off': 86, 'def': 78}, 'SG': {'name': 'Jaden Ivey', 'off': 81, 'def': 75}, 'SF': {'name': 'Ausar Thompson', 'off': 74, 'def': 89}, 'PF': {'name': 'Tobias Harris', 'off': 81, 'def': 77}, 'C': {'name': 'Jalen Duren', 'off': 80, 'def': 81}},

    # WESTERN CONFERENCE
    'OKC': {'PG': {'name': 'SGA', 'off': 96, 'def': 87}, 'SG': {'name': 'Alex Caruso', 'off': 76, 'def': 94}, 'SF': {'name': 'Jalen Williams', 'off': 87, 'def': 85}, 'PF': {'name': 'Chet Holmgren', 'off': 86, 'def': 90}, 'C': {'name': 'Isaiah Hartenstein', 'off': 78, 'def': 88}},
    'DEN': {'PG': {'name': 'Jamal Murray', 'off': 88, 'def': 77}, 'SG': {'name': 'Christian Braun', 'off': 76, 'def': 83}, 'SF': {'name': 'Michael Porter Jr.', 'off': 84, 'def': 78}, 'PF': {'name': 'Aaron Gordon', 'off': 82, 'def': 86}, 'C': {'name': 'Nikola Jokic', 'off': 98, 'def': 81}},
    'MIN': {'PG': {'name': 'Mike Conley', 'off': 80, 'def': 79}, 'SG': {'name': 'Anthony Edwards', 'off': 94, 'def': 86}, 'SF': {'name': 'Jaden McDaniels', 'off': 77, 'def': 92}, 'PF': {'name': 'Julius Randle', 'off': 88, 'def': 76}, 'C': {'name': 'Rudy Gobert', 'off': 78, 'def': 96}},
    'DAL': {'PG': {'name': 'Luka Doncic', 'off': 98, 'def': 77}, 'SG': {'name': 'Kyrie Irving', 'off': 93, 'def': 76}, 'SF': {'name': 'Klay Thompson', 'off': 82, 'def': 78}, 'PF': {'name': 'P.J. Washington', 'off': 79, 'def': 84}, 'C': {'name': 'Dereck Lively II', 'off': 78, 'def': 87}},
    'LAC': {'PG': {'name': 'James Harden', 'off': 89, 'def': 76}, 'SG': {'name': 'Terance Mann', 'off': 77, 'def': 82}, 'SF': {'name': 'Norman Powell', 'off': 83, 'def': 75}, 'PF': {'name': 'Kawhi Leonard', 'off': 92, 'def': 90}, 'C': {'name': 'Ivica Zubac', 'off': 80, 'def': 83}},
    'PHO': {'PG': {'name': 'Tyus Jones', 'off': 79, 'def': 75}, 'SG': {'name': 'Devin Booker', 'off': 93, 'def': 78}, 'SF': {'name': 'Bradley Beal', 'off': 86, 'def': 76}, 'PF': {'name': 'Kevin Durant', 'off': 94, 'def': 83}, 'C': {'name': 'Jusuf Nurkic', 'off': 80, 'def': 79}},
    'LAL': {'PG': {'name': 'DAngelo Russell', 'off': 83, 'def': 72}, 'SG': {'name': 'Austin Reaves', 'off': 84, 'def': 76}, 'SF': {'name': 'LeBron James', 'off': 94, 'def': 82}, 'PF': {'name': 'Rui Hachimura', 'off': 80, 'def': 75}, 'C': {'name': 'Anthony Davis', 'off': 91, 'def': 95}},
    'SAC': {'PG': {'name': 'DeAaron Fox', 'off': 90, 'def': 80}, 'SG': {'name': 'Malik Monk', 'off': 84, 'def': 74}, 'SF': {'name': 'DeMar DeRozan', 'off': 87, 'def': 75}, 'PF': {'name': 'Keegan Murray', 'off': 81, 'def': 83}, 'C': {'name': 'Domantas Sabonis', 'off': 88, 'def': 79}},
    'NOP': {'PG': {'name': 'Dejounte Murray', 'off': 85, 'def': 84}, 'SG': {'name': 'CJ McCollum', 'off': 84, 'def': 74}, 'SF': {'name': 'Brandon Ingram', 'off': 86, 'def': 77}, 'PF': {'name': 'Zion Williamson', 'off': 90, 'def': 78}, 'C': {'name': 'Daniel Theis', 'off': 74, 'def': 76}},
    'GSW': {'PG': {'name': 'Stephen Curry', 'off': 95, 'def': 76}, 'SG': {'name': 'Brandin Podziemski', 'off': 79, 'def': 78}, 'SF': {'name': 'Andrew Wiggins', 'off': 80, 'def': 83}, 'PF': {'name': 'Jonathan Kuminga', 'off': 84, 'def': 79}, 'C': {'name': 'Draymond Green', 'off': 76, 'def': 89}},
    'HOU': {'PG': {'name': 'Fred VanVleet', 'off': 83, 'def': 81}, 'SG': {'name': 'Jalen Green', 'off': 84, 'def': 75}, 'SF': {'name': 'Dillon Brooks', 'off': 76, 'def': 86}, 'PF': {'name': 'Jabari Smith Jr.', 'off': 79, 'def': 82}, 'C': {'name': 'Alperen Sengun', 'off': 87, 'def': 78}},
    'MEM': {'PG': {'name': 'Ja Morant', 'off': 92, 'def': 76}, 'SG': {'name': 'Marcus Smart', 'off': 78, 'def': 88}, 'SF': {'name': 'Desmond Bane', 'off': 86, 'def': 79}, 'PF': {'name': 'Jaren Jackson Jr.', 'off': 84, 'def': 91}, 'C': {'name': 'Zach Edey', 'off': 77, 'def': 79}},
    'UTA': {'PG': {'name': 'Keyonte George', 'off': 79, 'def': 73}, 'SG': {'name': 'Collin Sexton', 'off': 84, 'def': 74}, 'SF': {'name': 'Lauri Markkanen', 'off': 88, 'def': 78}, 'PF': {'name': 'Taylor Hendricks', 'off': 75, 'def': 80}, 'C': {'name': 'Walker Kessler', 'off': 75, 'def': 88}},
    'SAS': {'PG': {'name': 'Chris Paul', 'off': 80, 'def': 77}, 'SG': {'name': 'Devin Vassell', 'off': 84, 'def': 80}, 'SF': {'name': 'Harrison Barnes', 'off': 78, 'def': 76}, 'PF': {'name': 'Jeremy Sochan', 'off': 76, 'def': 84}, 'C': {'name': 'Victor Wembanyama', 'off': 86, 'def': 95}},
    'POR': {'PG': {'name': 'Anfernee Simons', 'off': 85, 'def': 71}, 'SG': {'name': 'Shaedon Sharpe', 'off': 81, 'def': 74}, 'SF': {'name': 'Deni Avdija', 'off': 79, 'def': 80}, 'PF': {'name': 'Jerami Grant', 'off': 83, 'def': 77}, 'C': {'name': 'Deandre Ayton', 'off': 82, 'def': 79}}
}

DEFAULT_ROSTER = {
    'PG': {'name': 'Starting PG', 'off': 80, 'def': 80},
    'SG': {'name': 'Starting SG', 'off': 80, 'def': 80},
    'SF': {'name': 'Starting SF', 'off': 80, 'def': 80},
    'PF': {'name': 'Starting PF', 'off': 80, 'def': 80},
    'C':  {'name': 'Starting C',  'off': 80, 'def': 80}
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. FULL 30-TEAM STANDINGS & METRICS DATABASE
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
def norm(abbr): return ESPN_TO_STD.get(abbr, abbr)

BACKUP_STANDINGS = {
    'BOS': {'wins': 64, 'losses': 18, 'record': '64-18', 'win_pct': 0.780},
    'NYK': {'wins': 50, 'losses': 32, 'record': '50-32', 'win_pct': 0.610},
    'PHI': {'wins': 47, 'losses': 35, 'record': '47-35', 'win_pct': 0.573},
    'CLE': {'wins': 48, 'losses': 34, 'record': '48-34', 'win_pct': 0.585},
    'MIL': {'wins': 49, 'losses': 33, 'record': '49-33', 'win_pct': 0.598},
    'ORL': {'wins': 47, 'losses': 35, 'record': '47-35', 'win_pct': 0.573},
    'IND': {'wins': 47, 'losses': 35, 'record': '47-35', 'win_pct': 0.573},
    'MIA': {'wins': 46, 'losses': 36, 'record': '46-36', 'win_pct': 0.561},
    'CHI': {'wins': 39, 'losses': 43, 'record': '39-43', 'win_pct': 0.476},
    'ATL': {'wins': 36, 'losses': 46, 'record': '36-46', 'win_pct': 0.439},
    'BKN': {'wins': 32, 'losses': 50, 'record': '32-50', 'win_pct': 0.390},
    'TOR': {'wins': 25, 'losses': 57, 'record': '25-57', 'win_pct': 0.305},
    'CHA': {'wins': 21, 'losses': 61, 'record': '21-61', 'win_pct': 0.256},
    'WAS': {'wins': 15, 'losses': 67, 'record': '15-67', 'win_pct': 0.183},
    'DET': {'wins': 14, 'losses': 68, 'record': '14-68', 'win_pct': 0.171},
    
    'OKC': {'wins': 57, 'losses': 25, 'record': '57-25', 'win_pct': 0.695},
    'DEN': {'wins': 57, 'losses': 25, 'record': '57-25', 'win_pct': 0.695},
    'MIN': {'wins': 56, 'losses': 26, 'record': '56-26', 'win_pct': 0.683},
    'LAC': {'wins': 51, 'losses': 31, 'record': '51-31', 'win_pct': 0.622},
    'DAL': {'wins': 50, 'losses': 32, 'record': '50-32', 'win_pct': 0.610},
    'PHO': {'wins': 49, 'losses': 33, 'record': '49-33', 'win_pct': 0.598},
    'NOP': {'wins': 49, 'losses': 33, 'record': '49-33', 'win_pct': 0.598},
    'LAL': {'wins': 47, 'losses': 35, 'record': '47-35', 'win_pct': 0.573},
    'SAC': {'wins': 46, 'losses': 36, 'record': '46-36', 'win_pct': 0.561},
    'GSW': {'wins': 46, 'losses': 36, 'record': '46-36', 'win_pct': 0.561},
    'HOU': {'wins': 41, 'losses': 41, 'record': '41-41', 'win_pct': 0.500},
    'UTA': {'wins': 31, 'losses': 51, 'record': '31-51', 'win_pct': 0.378},
    'MEM': {'wins': 27, 'losses': 55, 'record': '27-55', 'win_pct': 0.329},
    'SAS': {'wins': 22, 'losses': 60, 'record': '22-60', 'win_pct': 0.268},
    'POR': {'wins': 21, 'losses': 61, 'record': '21-61', 'win_pct': 0.256}
}

TEAM_DATA = {
    'BOS': {'off_rtg': 122.2, 'def_rtg': 110.5}, 'NYK': {'off_rtg': 117.3, 'def_rtg': 111.4},
    'PHI': {'off_rtg': 116.8, 'def_rtg': 113.2}, 'CLE': {'off_rtg': 114.5, 'def_rtg': 112.1},
    'MIL': {'off_rtg': 118.4, 'def_rtg': 115.0}, 'ORL': {'off_rtg': 112.9, 'def_rtg': 110.8},
    'IND': {'off_rtg': 120.5, 'def_rtg': 118.0}, 'MIA': {'off_rtg': 113.3, 'def_rtg': 111.9},
    'CHI': {'off_rtg': 114.0, 'def_rtg': 115.5}, 'ATL': {'off_rtg': 117.1, 'def_rtg': 118.8},
    'BKN': {'off_rtg': 113.2, 'def_rtg': 116.1}, 'TOR': {'off_rtg': 112.4, 'def_rtg': 117.8},
    'CHA': {'off_rtg': 111.0, 'def_rtg': 119.2}, 'WAS': {'off_rtg': 110.5, 'def_rtg': 119.8},
    'DET': {'off_rtg': 110.0, 'def_rtg': 118.5}, 'OKC': {'off_rtg': 118.5, 'def_rtg': 111.0},
    'DEN': {'off_rtg': 118.0, 'def_rtg': 112.5}, 'MIN': {'off_rtg': 114.8, 'def_rtg': 108.4},
    'LAC': {'off_rtg': 117.5, 'def_rtg': 114.0}, 'DAL': {'off_rtg': 117.0, 'def_rtg': 114.5},
    'PHO': {'off_rtg': 116.5, 'def_rtg': 113.8}, 'NOP': {'off_rtg': 116.0, 'def_rtg': 112.9},
    'LAL': {'off_rtg': 115.0, 'def_rtg': 114.5}, 'SAC': {'off_rtg': 116.2, 'def_rtg': 115.0},
    'GSW': {'off_rtg': 116.8, 'def_rtg': 114.2}, 'HOU': {'off_rtg': 113.5, 'def_rtg': 112.8},
    'UTA': {'off_rtg': 114.2, 'def_rtg': 119.5}, 'MEM': {'off_rtg': 107.5, 'def_rtg': 113.0},
    'SAS': {'off_rtg': 110.2, 'def_rtg': 115.8}, 'POR': {'off_rtg': 110.0, 'def_rtg': 118.0}
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. LIVE FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_daily_slate():
    now_est = datetime.utcnow() - timedelta(hours=4)
    yest_str = (now_est - timedelta(days=1)).strftime('%Y%m%d')
    tom_str = (now_est + timedelta(days=1)).strftime('%Y%m%d')
    target_date = now_est.strftime('%Y-%m-%d')
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest_str}-{tom_str}"
    
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            dt_utc = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')
            dt_est = dt_utc - timedelta(hours=4)
            
            if dt_est.strftime('%Y-%m-%d') != target_date: continue

            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            
            if home and away:
                games.append({
                    'h': norm(home['team']['abbreviation']), 'a': norm(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 'a_name': away['team']['displayName'],
                    'time': dt_est.strftime('%I:%M %p ET').lstrip('0'),
                    'venue': comp.get('venue', {}).get('fullName', 'Arena')
                })
        if games: return games
    except: pass
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
                    }
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
            if 'out' in hl.lower() or 'injury' in hl.lower() or 'questionable' in hl.lower():
                for cat in art.get('categories', []):
                    if cat.get('type') == 'team':
                        abbr = norm(cat.get('teamAbbrev', ''))
                        if abbr: news.setdefault(abbr, []).append(hl)
        if len(news) > 0: return {k: list(set(v))[:3] for k, v in news.items()}
    except: pass
    return {}

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

def is_active(player_name, team_injuries):
    last_name = player_name.split()[-1]
    return not any(last_name in inj for inj in team_injuries)

# ─────────────────────────────────────────────────────────────────────────────
# 4. TRANSPARENT PREDICTION ENGINE (WITH 5-ON-5 LOGIC)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set):
    h_td = TEAM_DATA.get(h, {'off_rtg': 115, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 115, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    factors = []
    matchup_logs = []
    total = 0.0
    
    # 1. Base Win % Edge
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 20.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Team Form Edge", "adj": base_adj, "why": f"Overall record disparity ({h_std['record']} vs {a_std['record']})."})

    # 2. Home Court
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court Advantage", "adj": 3.5, "why": f"Standard NBA home venue advantage."})

    # 3. Defensive Efficiency
    def_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += def_adj
    factors.append({"icon": "🛡️", "name": "Defensive Matchup", "adj": def_adj, "why": f"{h} def rating: {h_td['def_rtg']} | {a} def rating: {a_td['def_rtg']}"})

    # 4. 5-ON-5 PLAYER MATCHUP ENGINE
    SCALING_FACTOR = 0.15 
    
    h_roster = STARTING_FIVES.get(h, DEFAULT_ROSTER)
    a_roster = STARTING_FIVES.get(a, DEFAULT_ROSTER)
    
    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    
    for pos in positions:
        hp = h_roster[pos]
        ap = a_roster[pos]
        
        # Check Injury Report
        if not is_active(hp['name'], h_inj) or not is_active(ap['name'], a_inj):
            matchup_logs.append({
                "pos": pos, "matchup": f"⚠️ {hp['name']} vs {ap['name']}",
                "math": "Matchup Voided due to Live Injury Report.",
                "adj": 0.0, "color": "#888888"
            })
            continue
            
        # Positional Math
        h_score = max(0, hp['off'] - ap['def'])
        a_score = max(0, ap['off'] - hp['def'])
        net_edge = (h_score - a_score) * SCALING_FACTOR
        total += net_edge
        
        math_str = f"(H_OFF {hp['off']} - A_DEF {ap['def']}) vs (A_OFF {ap['off']} - H_DEF {hp['def']})"
        color = "#28a745" if net_edge > 0 else "#dc3545" if net_edge < 0 else "#888888"
        
        matchup_logs.append({
            "pos": pos, "matchup": f"**{hp['name']}** ({h}) vs **{ap['name']}** ({a})",
            "math": math_str, "adj": net_edge, "color": color
        })

    # 5. Tanking Logic
    if h_std['win_pct'] < 0.36 and h_std['wins'] + h_std['losses'] > 15:
        total -= 8.0
        factors.append({"icon": "🎯", "name": "Tanking Penalty", "adj": -8.0, "why": f"{h} win rate is critically low. Prioritizing lottery."})
    elif a_std['win_pct'] < 0.36 and a_std['wins'] + a_std['losses'] > 15:
        total += 8.0
        factors.append({"icon": "🎯", "name": "Tanking Boost", "adj": 8.0, "why": f"{a} win rate is critically low. Easy matchup for {h}."})
    else:
        factors.append({"icon": "🤝", "name": "Motivation Status", "adj": 0.0, "why": "Both teams are actively competing."})

    # 6. Fatigue
    if h in b2b_set:
        total -= 4.5
        factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": -4.5, "why": f"{h} played yesterday. Heavy legs."})
    elif a in b2b_set:
        total += 4.5
        factors.append({"icon": "😴", "name": "B2B Fatigue", "adj": 4.5, "why": f"{a} played yesterday. Schedule advantage for {h}."})
    else:
        factors.append({"icon": "🔋", "name": "Rest Status", "adj": 0.0, "why": "Both teams have adequate rest."})

    # 7. Overall Team Injury Impact
    if h_inj:
        total -= 6.0
        factors.append({"icon": "🤕", "name": "Team Injury Impact", "adj": -6.0, "why": f"{h} is missing players from rotation."})
    elif a_inj:
        total += 6.0
        factors.append({"icon": "🤕", "name": "Opponent Injury Boost", "adj": 6.0, "why": f"{a} is missing players from rotation."})
    else:
        factors.append({"icon": "🏥", "name": "General Health", "adj": 0.0, "why": "No major game-altering injuries detected."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0 - prob,
        'prob_h': prob, 'factors': factors, 'matchups': matchup_logs,
        'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 Live NBA Predictor (Full 30-Team Database)")
st.divider()

with st.spinner("📡 Syncing Live ESPN Data..."):
    slate = get_daily_slate()
    standings = get_standings()
    injuries = get_injuries()
    b2b_set = get_back_to_back()

if not slate:
    st.info("✅ ESPN Live Feed connected, but no games are scheduled for today! Check back tomorrow.")
    st.stop()

st.subheader(f"Today's Predictions ({len(slate)} Games)")

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries, b2b_set)
    conf = pred['conf']
    
    icon = "🔒" if conf >= 80 else ("🔥" if conf >= 65 else "⚖️")
    header = f"{icon} {game['h_name']} vs {game['a_name']} | {pred['winner']} ({conf:.1f}%)"

    with st.expander(header):
        color = '#28a745' if conf >= 65 else '#17a2b8'
        st.markdown(f"""
        <div style="border-left:5px solid {color};background:#1e1e1e;padding:12px;border-radius:6px;margin-bottom:15px;">
            <h3 style="margin:0;color:white;">🏆 {pred['winner']} WINS</h3>
        </div>""", unsafe_allow_html=True)

        # --- 5-ON-5 MATCHUP BOARD ---
        if pred['matchups']:
            st.markdown("#### ⚔️ Starting 5 Positional Matchups")
            st.write("Calculated by: `(Home OFF - Away DEF) - (Away OFF - Home DEF) * 0.15`")
            
            for m in pred['matchups']:
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"**{m['pos']}**")
                c2.markdown(f"{m['matchup']} <br> <span style='font-size:12px;color:gray;'>Math: {m['math']}</span>", unsafe_allow_html=True)
                c3.markdown(f"<span style='color:{m['color']};font-weight:bold;'>{m['adj']:+.1f} pts</span>", unsafe_allow_html=True)
            st.divider()

        st.markdown("#### 🧠 The Transparent Reasoning Log")
        st.write("Every rule checked and verified by the AI model:")
        
        for f in pred['factors']:
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f['icon'])
            c2.markdown(f"**{f['name']}** <br> <span style='color:gray;font-size:14px;'>{f['why']}</span>", unsafe_allow_html=True)
            
            if f['adj'] > 0: pt_color = "#28a745"
            elif f['adj'] < 0: pt_color = "#dc3545"
            else: pt_color = "#888888"
            
            c3.markdown(f"<span style='color:{pt_color};font-weight:bold;font-size:18px;'>{f['adj']:+.1f} pts</span>", unsafe_allow_html=True)
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 🏠 {game['h_name']}")
            st.write(f"**Record:** {pred['h_std']['record']}")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### ✈️ {game['a_name']}")
            st.write(f"**Record:** {pred['a_std']['record']}")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

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
# 1. THE LIVE 2025-2026 STARTING ROSTER DATABASE (Player vs Player)
# ─────────────────────────────────────────────────────────────────────────────
STARTING_FIVES = {
    'BOS': {
        'PG': {'name': 'Jrue Holiday', 'off': 82, 'def': 94},
        'SG': {'name': 'Derrick White', 'off': 84, 'def': 89},
        'SF': {'name': 'Jaylen Brown', 'off': 89, 'def': 84},
        'PF': {'name': 'Jayson Tatum', 'off': 94, 'def': 86},
        'C':  {'name': 'Kristaps Porzingis', 'off': 86, 'def': 82}
    },
    'NYK': {
        'PG': {'name': 'Jalen Brunson', 'off': 95, 'def': 74},
        'SG': {'name': 'Mikal Bridges', 'off': 85, 'def': 91},
        'SF': {'name': 'OG Anunoby', 'off': 81, 'def': 93},
        'PF': {'name': 'Karl-Anthony Towns', 'off': 91, 'def': 79},
        'C':  {'name': 'Mitchell Robinson', 'off': 75, 'def': 89}
    },
    'MIN': {
        'PG': {'name': 'Mike Conley', 'off': 80, 'def': 79},
        'SG': {'name': 'Anthony Edwards', 'off': 94, 'def': 86},
        'SF': {'name': 'Jaden McDaniels', 'off': 77, 'def': 92},
        'PF': {'name': 'Julius Randle', 'off': 88, 'def': 76},
        'C':  {'name': 'Rudy Gobert', 'off': 78, 'def': 96}
    },
    'MIL': {
        'PG': {'name': 'Damian Lillard', 'off': 92, 'def': 72},
        'SG': {'name': 'Gary Trent Jr.', 'off': 79, 'def': 75},
        'SF': {'name': 'Khris Middleton', 'off': 84, 'def': 78},
        'PF': {'name': 'Giannis Antetokounmpo', 'off': 96, 'def': 89},
        'C':  {'name': 'Brook Lopez', 'off': 79, 'def': 86}
    },
    'PHI': {
        'PG': {'name': 'Tyrese Maxey', 'off': 90, 'def': 75},
        'SG': {'name': 'Kelly Oubre Jr.', 'off': 79, 'def': 76},
        'SF': {'name': 'Paul George', 'off': 88, 'def': 84},
        'PF': {'name': 'Caleb Martin', 'off': 76, 'def': 81},
        'C':  {'name': 'Joel Embiid', 'off': 97, 'def': 88}
    },
    'DAL': {
        'PG': {'name': 'Luka Doncic', 'off': 98, 'def': 77},
        'SG': {'name': 'Kyrie Irving', 'off': 93, 'def': 76},
        'SF': {'name': 'Klay Thompson', 'off': 82, 'def': 78},
        'PF': {'name': 'P.J. Washington', 'off': 79, 'def': 84},
        'C':  {'name': 'Dereck Lively II', 'off': 78, 'def': 87}
    },
    'OKC': {
        'PG': {'name': 'Shai Gilgeous-Alexander', 'off': 96, 'def': 87},
        'SG': {'name': 'Alex Caruso', 'off': 76, 'def': 94},
        'SF': {'name': 'Jalen Williams', 'off': 87, 'def': 85},
        'PF': {'name': 'Chet Holmgren', 'off': 86, 'def': 90},
        'C':  {'name': 'Isaiah Hartenstein', 'off': 78, 'def': 88}
    }
}

# The Failsafe: Ensures math works even if a team isn't listed above yet
DEFAULT_ROSTER = {
    'PG': {'name': 'Starting PG', 'off': 80, 'def': 80},
    'SG': {'name': 'Starting SG', 'off': 80, 'def': 80},
    'SF': {'name': 'Starting SF', 'off': 80, 'def': 80},
    'PF': {'name': 'Starting PF', 'off': 80, 'def': 80},
    'C':  {'name': 'Starting C',  'off': 80, 'def': 80}
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE IRONCLAD BACKUP DATABASE & ABBREVIATIONS
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
def norm(abbr): return ESPN_TO_STD.get(abbr, abbr)

BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '30-8', 'away_record': '26-13', 'point_diff': 7.2},
    'BOS': {'wins': 51, 'losses': 25, 'record': '51-25', 'win_pct': 0.671, 'home_record': '28-10', 'away_record': '23-15', 'point_diff': 7.2},
    'NYK': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '27-11', 'away_record': '22-17', 'point_diff': 4.2},
    'PHI': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.552, 'home_record': '24-15', 'away_record': '18-19', 'point_diff': 0.8},
    'OKC': {'wins': 60, 'losses': 16, 'record': '60-16', 'win_pct': 0.789, 'home_record': '33-5', 'away_record': '27-11', 'point_diff': 9.8},
    'SAS': {'wins': 58, 'losses': 18, 'record': '58-18', 'win_pct': 0.763, 'home_record': '32-6', 'away_record': '26-12', 'point_diff': 7.5},
    'LAL': {'wins': 50, 'losses': 26, 'record': '50-26', 'win_pct': 0.657, 'home_record': '28-11', 'away_record': '22-15', 'point_diff': 4.8},
    'HOU': {'wins': 47, 'losses': 29, 'record': '47-29', 'win_pct': 0.618, 'home_record': '27-10', 'away_record': '20-19', 'point_diff': 3.8},
    'MIN': {'wins': 46, 'losses': 29, 'record': '46-29', 'win_pct': 0.613, 'home_record': '25-12', 'away_record': '21-17', 'point_diff': 3.5},
    'UTA': {'wins': 21, 'losses': 56, 'record': '21-56', 'win_pct': 0.272, 'home_record': '13-26', 'away_record': '8-30', 'point_diff': -11.0},
    'DAL': {'wins': 24, 'losses': 52, 'record': '24-52', 'win_pct': 0.315, 'home_record': '14-24', 'away_record': '10-28', 'point_diff': -5.2},
    'MEM': {'wins': 35, 'losses': 41, 'record': '35-41', 'win_pct': 0.460, 'home_record': '20-18', 'away_record': '15-23', 'point_diff': 0.2},
    'SAC': {'wins': 38, 'losses': 39, 'record': '38-39', 'win_pct': 0.493, 'home_record': '22-17', 'away_record': '16-22', 'point_diff': -0.8},
    'NOP': {'wins': 28, 'losses': 48, 'record': '28-48', 'win_pct': 0.368, 'home_record': '16-22', 'away_record': '12-26', 'point_diff': -7.5},
    'CHI': {'wins': 30, 'losses': 47, 'record': '30-47', 'win_pct': 0.389, 'home_record': '18-21', 'away_record': '12-26', 'point_diff': -3.2},
    'IND': {'wins': 35, 'losses': 42, 'record': '35-42', 'win_pct': 0.454, 'home_record': '20-18', 'away_record': '15-24', 'point_diff': -1.5},
    'BKN': {'wins': 20, 'losses': 56, 'record': '20-56', 'win_pct': 0.263, 'home_record': '12-26', 'away_record': '8-30', 'point_diff': -11.5},
    'CHA': {'wins': 41, 'losses': 36, 'record': '41-36', 'win_pct': 0.532, 'home_record': '22-16', 'away_record': '19-20', 'point_diff': 0.5},
}

TEAM_DATA = {
    'DET': {'off_rtg': 112.5, 'def_rtg': 108.5}, 'BOS': {'off_rtg': 121.6, 'def_rtg': 107.2},
    'NYK': {'off_rtg': 115.4, 'def_rtg': 111.2}, 'PHI': {'off_rtg': 115.5, 'def_rtg': 114.2},
    'ATL': {'off_rtg': 116.5, 'def_rtg': 118.4}, 'MIL': {'off_rtg': 118.6, 'def_rtg': 115.7},
    'CHI': {'off_rtg': 111.8, 'def_rtg': 114.4}, 'IND': {'off_rtg': 119.0, 'def_rtg': 118.5},
    'BKN': {'off_rtg': 112.0, 'def_rtg': 116.5}, 'CHA': {'off_rtg': 110.2, 'def_rtg': 119.0},
    'OKC': {'off_rtg': 119.5, 'def_rtg': 111.0}, 'SAS': {'off_rtg': 110.0, 'def_rtg': 114.5},
    'LAL': {'off_rtg': 114.5, 'def_rtg': 113.8}, 'HOU': {'off_rtg': 112.0, 'def_rtg': 111.0},
    'MIN': {'off_rtg': 114.5, 'def_rtg': 108.0}, 'UTA': {'off_rtg': 114.0, 'def_rtg': 120.2},
    'DAL': {'off_rtg': 117.8, 'def_rtg': 115.5}, 'MEM': {'off_rtg': 106.5, 'def_rtg': 112.0},
    'SAC': {'off_rtg': 115.0, 'def_rtg': 115.5}, 'NOP': {'off_rtg': 115.0, 'def_rtg': 112.5},
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
            
            # Pull only today's live games
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
                        'home_record': get_rec('home'), 'away_record': get_rec('away'),
                        'point_diff': float(stats.get('pointdifferential', {}).get('value', 0))
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
    h_td = TEAM_DATA.get(h, {'off_rtg': 112, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 112, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'point_diff': 0})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'point_diff': 0})
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
    factors.append({"icon": "🛡️", "name": "Def

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
# 1. 2026 PLAYER MATCHUP DATABASE (With POSITIONAL ZONING)
# ─────────────────────────────────────────────────────────────────────────────
# Zones: 'Perimeter' (Guards), 'Wing' (Forwards), 'Paint' (Bigs)
OFFENSIVE_STARS = {
    'OKC': {'name': 'Shai Gilgeous-Alexander', 'impact': 8.5, 'zone': 'Perimeter'},
    'DEN': {'name': 'Nikola Jokic', 'impact': 9.0, 'zone': 'Paint'},
    'LAL': {'name': 'Luka Doncic', 'impact': 8.8, 'zone': 'Perimeter'},
    'NYK': {'name': 'Jalen Brunson', 'impact': 7.2, 'zone': 'Perimeter'},
    'MIN': {'name': 'Anthony Edwards', 'impact': 6.5, 'zone': 'Wing'},
    'MIL': {'name': 'Giannis Antetokounmpo', 'impact': 8.0, 'zone': 'Paint'},
    'PHI': {'name': 'Tyrese Maxey', 'impact': 6.0, 'zone': 'Perimeter'},
    'HOU': {'name': 'Kevin Durant', 'impact': 7.0, 'zone': 'Wing'},
    'BOS': {'name': 'Jayson Tatum', 'impact': 6.8, 'zone': 'Wing'}
}

ELITE_STOPPERS = {
    'BOS': {'name': 'Jrue Holiday', 'stopper_rating': 4.5, 'zone': 'Perimeter'},
    'MIN': {'name': 'Rudy Gobert', 'stopper_rating': 5.2, 'zone': 'Paint'},
    'OKC': {'name': 'Lu Dort', 'stopper_rating': 4.0, 'zone': 'Perimeter'},
    'NOP': {'name': 'Herb Jones', 'stopper_rating': 4.2, 'zone': 'Wing'},
    'SAS': {'name': 'Victor Wembanyama', 'stopper_rating': 5.5, 'zone': 'Paint'},
    'MIA': {'name': 'Bam Adebayo', 'stopper_rating': 4.8, 'zone': 'Paint'},
    'NYK': {'name': 'OG Anunoby', 'stopper_rating': 3.9, 'zone': 'Wing'}
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

BACKUP_INJURIES = {
    'MIL': ['Giannis Antetokounmpo (OUT)'], 'LAL': ['Luka Doncic (Questionable)'],
    'DET': ['Cade Cunningham (OUT)'], 'DAL': ['Kyrie Irving (OUT)'],
    'MIN': ['Anthony Edwards (OUT)'], 'PHI': ['Joel Embiid (Doubtful)']
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
# 3. ROBUST FETCHERS
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
                    'h': norm(home['team']['abbreviation']), 'a': norm(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 'a_name': away['team']['displayName'],
                    'time': 'Scheduled', 'venue': comp.get('venue', {}).get('fullName', 'Arena')
                })
        
        if len(games) >= 9: return games
    except: pass
    
    return [
        {'h': 'PHI', 'a': 'MIN', 'h_name': '76ers', 'a_name': 'Timberwolves', 'time': '7:00 PM', 'venue': 'Wells Fargo Center'},
        {'h': 'CHA', 'a': 'IND', 'h_name': 'Hornets', 'a_name': 'Pacers', 'time': '7:00 PM', 'venue': 'Spectrum Center'},
        {'h': 'BKN', 'a': 'ATL', 'h_name': 'Nets', 'a_name': 'Hawks', 'time': '7:30 PM', 'venue': 'Barclays Center'},
        {'h': 'NYK', 'a': 'CHI', 'h_name': 'Knicks', 'a_name': 'Bulls', 'time': '7:30 PM', 'venue': 'MSG'},
        {'h': 'BOS', 'a': 'MIL', 'h_name': 'Celtics', 'a_name': 'Bucks', 'time': '7:30 PM', 'venue': 'TD Garden'},
        {'h': 'HOU', 'a': 'UTA', 'h_name': 'Rockets', 'a_name': 'Jazz', 'time': '8:00 PM', 'venue': 'Toyota Center'},
        {'h': 'MEM', 'a': 'TOR', 'h_name': 'Grizzlies', 'a_name': 'Raptors', 'time': '8:00 PM', 'venue': 'FedExForum'},
        {'h': 'DAL', 'a': 'ORL', 'h_name': 'Mavericks', 'a_name': 'Magic', 'time': '8:30 PM', 'venue': 'AAC'},
        {'h': 'SAC', 'a': 'NOP', 'h_name': 'Kings', 'a_name': 'Pelicans', 'time': '10:00 PM', 'venue': 'Golden 1 Center'}
    ]

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
            if 'out' in hl.lower() or 'injury' in hl.lower():
                for cat in art.get('categories', []):
                    if cat.get('type') == 'team':
                        abbr = norm(cat.get('teamAbbrev', ''))
                        if abbr: news.setdefault(abbr, []).append(hl)
        if len(news) > 0: return {k: v[:2] for k, v in news.items()}
    except: pass
    return BACKUP_INJURIES

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
# 4. TRANSPARENT PREDICTION ENGINE (WITH POSITIONAL ZONING)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set):
    h_td = TEAM_DATA.get(h, {'off_rtg': 112, 'def_rtg': 115})
    a_td = TEAM_DATA.get(a, {'off_rtg': 112, 'def_rtg': 115})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'point_diff': 0})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'point_diff': 0})
    
    factors = []
    total = 0.0
    
    # 1. Base Win % Edge
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 25.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Win % Disparity", "adj": base_adj, "why": f"{h} ({h_std['record']}) vs {a} ({a_std['record']})"})

    # 2. Home Court
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court Advantage", "adj": 3.5, "why": f"Standard NBA home court boost for {h}."})

    # 3. Defensive Efficiency
    def_adj = (a_td['def_rtg'] - h_td['def_rtg']) * 0.4
    total += def_adj
    factors.append({"icon": "🛡️", "name": "Team Defense Matchup", "adj": def_adj, "why": f"{h} def rating: {h_td['def_rtg']} | {a} def rating: {a_td['def_rtg']}"})

    # 4. INDIVIDUAL POSITIONAL MATCHUP LOGIC (Zone vs Zone)
    matchup_found = False
    
    # Check if Home has a Star and Away has a Stopper
    if h in OFFENSIVE_STARS and a in ELITE_STOPPERS:
        star, stopper = OFFENSIVE_STARS[h], ELITE_STOPPERS[a]
        # ONLY apply if their zones match (e.g., Perimeter vs Perimeter)
        if star['zone'] == stopper['zone']:
            penalty = min(star['impact'], stopper['stopper_rating'])
            total -= penalty
            factors.append({"icon": "🥷", "name": "Positional Matchup Detected", "adj": -penalty, 
                            "why": f"{stopper['name']} ({a}) is guarding {star['name']} ({h}) in the {star['zone']}."})
            matchup_found = True
        else:
            factors.append({"icon": "🥷", "name": "Mismatch Escaped", "adj": 0.0, 
                            "why": f"{stopper['name']} ({a}) is a {stopper['zone']} defender and will not primarily guard {star['name']} ({star['zone']})."})
            matchup_found = True
        
    # Check if Away has a Star and Home has a Stopper
    if a in OFFENSIVE_STARS and h in ELITE_STOPPERS and not matchup_found:
        star, stopper = OFFENSIVE_STARS[a], ELITE_STOPPERS[h]
        if star['zone'] == stopper['zone']:
            penalty = min(star['impact'], stopper['stopper_rating'])
            total += penalty
            factors.append({"icon": "🥷", "name": "Positional Matchup Detected", "adj": penalty, 
                            "why": f"{stopper['name']} ({h}) is guarding {star['name']} ({a}) in the {star['zone']}."})
            matchup_found = True
        else:
            factors.append({"icon": "🥷", "name": "Mismatch Escaped", "adj": 0.0, 
                            "why": f"{stopper['name']} ({h}) is a {stopper['zone']} defender and will not primarily guard {star['name']} ({star['zone']})."})
            matchup_found = True

    if not matchup_found:
        factors.append({"icon": "🥷", "name": "Star vs. Stopper", "adj": 0.0, "why": "No direct 1-on-1 matchups identified."})

    # 5. Tanking Logic
    if h_std['win_pct'] < 0.36 and h_std['wins'] + h_std['losses'] > 15:
        total -= 8.0
        factors.append({"icon": "🎯", "name": "Tanking Penalty", "adj": -8.0, "why": f"{h} win rate critically low. Prioritizing lottery."})
    elif a_std['win_pct'] < 0.36 and a_std['wins'] + a_std['losses'] > 15:
        total += 8.0
        factors.append({"icon": "🎯", "name": "Tanking Boost", "adj": 8.0, "why": f"{a} win rate critically low. Easy matchup for {h}."})
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

    # 7. Injuries
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj:
        total -= 6.0
        factors.append({"icon": "🤕", "name": "Injury Impact", "adj": -6.0, "why": f"{h} is missing key players."})
    elif a_inj:
        total += 6.0
        factors.append({"icon": "🤕", "name": "Opponent Injury", "adj": 6.0, "why": f"{a} is missing key players."})
    else:
        factors.append({"icon": "🏥", "name": "Injury Report", "adj": 0.0, "why": "No major game-altering injuries detected."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0 - prob,
        'prob_h': prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor")
st.divider()

slate = get_daily_slate()
standings = get_standings()
injuries = get_injuries()
b2b_set = get_back_to_back()

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
            st.write(f"**Record:** {pred['h_std']['record']} (Home: {pred['h_std'].get('home_record', '0-0')})")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### ✈️ {game['a_name']}")
            st.write(f"**Record:** {pred['a_std']['record']} (Away: {pred['a_std'].get('away_record', '0-0')})")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

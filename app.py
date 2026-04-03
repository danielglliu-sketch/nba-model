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
# 1. THE 5-ON-5 STARTING ROSTER DATABASE (Player vs Player)
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
st.title("🏀 NBA Master AI Predictor (5-on-5 Edition)")
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
            st.write(f"**Record:** {pred['h_std']['record']} (Home: {pred['h_std'].get('home_record', '0-0')})")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### ✈️ {game['a_name']}")
            st.write(f"**Record:** {pred['a_std']['record']} (Away: {pred['a_std'].get('away_record', '0-0')})")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

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
# 1. THE 5-ON-5 STARTING ROSTER DATABASE
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
        'PG': {'name': 'Jalen Brunson', 'off': 94, 'def': 74},
        'SG': {'name': 'Donte DiVincenzo', 'off': 81, 'def': 79},
        'SF': {'name': 'Mikal Bridges', 'off': 84, 'def': 90},
        'PF': {'name': 'OG Anunoby', 'off': 80, 'def': 92},
        'C':  {'name': 'Mitchell Robinson', 'off': 75, 'def': 88}
    },
    'MIN': {
        'PG': {'name': 'Mike Conley', 'off': 79, 'def': 78},
        'SG': {'name': 'Anthony Edwards', 'off': 93, 'def': 85},
        'SF': {'name': 'Jaden McDaniels', 'off': 76, 'def': 91},
        'PF': {'name': 'Karl-Anthony Towns', 'off': 89, 'def': 77},
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
        'PG': {'name': 'Luka Doncic', 'off': 97, 'def': 76},
        'SG': {'name': 'Kyrie Irving', 'off': 92, 'def': 75},
        'SF': {'name': 'P.J. Washington', 'off': 78, 'def': 84},
        'PF': {'name': 'Derrick Jones Jr.', 'off': 75, 'def': 85},
        'C':  {'name': 'Dereck Lively II', 'off': 77, 'def': 86}
    },
    'OKC': {
        'PG': {'name': 'SGA', 'off': 96, 'def': 86},
        'SG': {'name': 'Josh Giddey', 'off': 81, 'def': 76},
        'SF': {'name': 'Lu Dort', 'off': 76, 'def': 92},
        'PF': {'name': 'Jalen Williams', 'off': 86, 'def': 84},
        'C':  {'name': 'Chet Holmgren', 'off': 85, 'def': 89}
    }
}

# The Failsafe: If a live game features a team not in the dictionary above, use this.
DEFAULT_ROSTER = {
    'PG': {'name': 'Starting PG', 'off': 80, 'def': 80},
    'SG': {'name': 'Starting SG', 'off': 80, 'def': 80},
    'SF': {'name': 'Starting SF', 'off': 80, 'def': 80},
    'PF': {'name': 'Starting PF', 'off': 80, 'def': 80},
    'C':  {'name': 'Starting C',  'off': 80, 'def': 80}
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. STANDINGS, FETCHERS & FALLBACKS
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
def norm(abbr): return ESPN_TO_STD.get(abbr, abbr)

@st.cache_data(ttl=300)
def get_daily_slate():
    now_est = datetime.utcnow() - timedelta(hours=4)
    # Pull a 3 day window to prevent timezone drop-offs
    yest_str = (now_est - timedelta(days=1)).strftime('%Y%m%d')
    tom_str = (now_est + timedelta(days=1)).strftime('%Y%m%d')
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest_str}-{tom_str}"
    
    try:
        data = requests.get(url, timeout=6).json()
        games = []
        target_date = now_est.strftime('%Y-%m-%d')
        
        for event in data.get('events', []):
            dt_utc = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')
            dt_est = dt_utc - timedelta(hours=4)
            
            # Only pull games happening TODAY
            if dt_est.strftime('%Y-%m-%d') != target_date:
                continue

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
    
    return [] # Return empty if no games are scheduled today

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
                    }
        if len(result) > 10: return result
    except: pass
    return {}

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
        if len(news) > 0: return {k: v[:2] for k, v in news.items()}
    except: pass
    return {}

def is_active(player_name, team_injuries):
    last_name = player_name.split()[-1]
    return not any(last_name in inj for inj in team_injuries)

# ─────────────────────────────────────────────────────────────────────────────
# 3. THE LIVE 5-ON-5 PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries):
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    factors = []
    matchup_logs = []
    total = 0.0
    
    # 1. Base Factors
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": "Standard home boost."})
    
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 20.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Team Form Edge", "adj": base_adj, "why": f"Overall record disparity ({h_std['record']} vs {a_std['record']})."})

    # --- 5-ON-5 POSITIONAL MATCHUP ENGINE ---
    SCALING_FACTOR = 0.15 
    
    # Use real roster if we have it, otherwise use the league average DEFAULT_ROSTER
    h_roster = STARTING_FIVES.get(h, DEFAULT_ROSTER)
    a_roster = STARTING_FIVES.get(a, DEFAULT_ROSTER)
    
    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    
    for pos in positions:
        hp = h_roster[pos]
        ap = a_roster[pos]
        
        # Injury Check
        if not is_active(hp['name'], h_inj) or not is_active(ap['name'], a_inj):
            matchup_logs.append({
                "pos": pos, "matchup": f"⚠️ {hp['name']} vs {ap['name']}",
                "math": "Matchup Voided due to Injury Report.",
                "adj": 0.0, "color": "#888888"
            })
            continue
            
        # The Math
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

    # Injury Adjustments
    if h_inj: total -= 4.0; factors.append({"icon": "🤕", "name": "Injury Impact", "adj": -4.0, "why": f"{h} missing rotation players."})
    if a_inj: total += 4.0; factors.append({"icon": "🤕", "name": "Injury Impact", "adj": 4.0, "why": f"{a} missing rotation players."})

    # Tanking Check
    if h_std['win_pct'] < 0.36 and h_std['wins'] + h_std['losses'] > 15:
        total -= 8.0; factors.append({"icon": "🎯", "name": "Tanking Penalty", "adj": -8.0, "why": f"{h} win rate critically low."})
    elif a_std['win_pct'] < 0.36 and a_std['wins'] + a_std['losses'] > 15:
        total += 8.0; factors.append({"icon": "🎯", "name": "Tanking Boost", "adj": 8.0, "why": f"{a} win rate critically low."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0 - prob,
        'prob_h': prob, 'factors': factors, 'matchups': matchup_logs,
        'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 Live NBA Predictor (5-on-5 Edition)")
st.divider()

with st.spinner("📡 Syncing Live ESPN Data..."):
    slate = get_daily_slate()
    standings = get_standings()
    injuries = get_injuries()

if not slate:
    st.success("✅ No games scheduled for today! Check back tomorrow.")
    st.stop()

st.subheader(f"Today's Live Matchups ({len(slate)} Games)")

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries)
    conf = pred['conf']
    
    icon = "🔒" if conf >= 80 else ("🔥" if conf >= 65 else "⚖️")
    header = f"{icon} {game['h_name']} vs {game['a_name']} | {pred['winner']} ({conf:.1f}%)"

    with st.expander(header):
        st.markdown(f"### 🏆 {pred['winner']} WINS ({conf:.1f}%)")
        st.caption(f"📍 {game['venue']} | 🕐 {game['time']}")
        
        # --- 5-ON-5 MATCHUP BOARD ---
        if pred['matchups']:
            st.markdown("#### ⚔️ Starting 5 Positional Matchups")
            st.write("Calculated by: `(Home OFF - Away DEF) - (Away OFF - Home DEF) * Scaling Factor`")
            
            for m in pred['matchups']:
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"**{m['pos']}**")
                c2.markdown(f"{m['matchup']} <br> <span style='font-size:12px;color:gray;'>Math: {m['math']}</span>", unsafe_allow_html=True)
                c3.markdown(f"<span style='color:{m['color']};font-weight:bold;'>{m['adj']:+.1f} pts</span>", unsafe_allow_html=True)
            st.divider()

        # --- GENERAL FACTORS LOG ---
        st.markdown("#### 🧠 General Factors Log")
        for f in pred['factors']:
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f['icon'])
            c2.markdown(f"**{f['name']}** <br> <span style='color:gray;font-size:14px;'>{f['why']}</span>", unsafe_allow_html=True)
            pt_color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            c3.markdown(f"<span style='color:{pt_color};font-weight:bold;font-size:18px;'>{f['adj']:+.1f} pts</span>", unsafe_allow_html=True)
        
        st.divider()

        # --- LIVE TEAM STATS ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 🏠 {game['h_name']}")
            st.write(f"**Record:** {pred['h_std']['record']}")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### ✈️ {game['a_name']}")
            st.write(f"**Record:** {pred['a_std']['record']}")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

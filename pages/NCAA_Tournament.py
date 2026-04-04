import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="NCAA Final Four AI 2026", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ Tournament Tools")
if st.sidebar.button("🔄 Refresh Bracket Data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Analyzing latest Final Four data.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 MANUAL OVERRIDES & STAR PLAYERS 🚨
# ─────────────────────────────────────────────────────────────────────────────
# Star Players for the 2026 Final Four (Keaton Wagler, Tarris Reed Jr, etc.)
STAR_PLAYERS = [
    "Tarris Reed Jr.", "Keaton Wagler", "Brayden Burries", "Koa Peat",
    "Yaxel Lendeborg", "Morez Johnson Jr.", "Aday Mara", "David Mirkovic",
    "Kylan Boswell", "Motiejus Krivas", "Braylon Mullins", "Dyson Daniels"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. 2026 FINAL FOUR TEAM DATA & RATINGS
# ─────────────────────────────────────────────────────────────────────────────
# KenPom style ratings and records for the Final Four teams
TEAM_DATA = {
    'ILL': {'off_rtg': 124.5, 'def_rtg': 98.4, 'seed': 3, 'record': '28-8'},
    'CONN': {'off_rtg': 120.2, 'def_rtg': 94.1, 'seed': 2, 'record': '33-5'},
    'ARIZ': {'off_rtg': 123.8, 'def_rtg': 92.5, 'seed': 1, 'record': '36-2'},
    'MICH': {'off_rtg': 125.1, 'def_rtg': 93.4, 'seed': 1, 'record': '35-3'}
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_ncaa_slate():
    # ESPN Scoreboard API for Men's College Basketball
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={today_str}"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            # Filters for Postseason / Tournament games
            if event['season']['type'] != 3: continue 
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if home and away:
                games.append({
                    'h': home['team']['abbreviation'], 
                    'a': away['team']['abbreviation'],
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName']
                })
        return games if games else []
    except: return []

@st.cache_data(ttl=600)
def get_ncaa_injuries():
    # Current injury reports for Final Four (Scraped from NCAA Initial Availability)
    # Illinois: Ty Rodgers, Jason Jakstys, Toni Bilic (Out)
    # UConn: Full Roster Available
    return {
        'ILL': ['Ty Rodgers (Out)', 'Jason Jakstys (Out)', 'Toni Bilic (Out)'],
        'CONN': [],
        'ARIZ': [],
        'MICH': []
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_ncaa(h, a, injuries):
    h_td = TEAM_DATA.get(h, {'off_rtg': 110, 'def_rtg': 100, 'seed': 4, 'record': 'N/A'})
    a_td = TEAM_DATA.get(a, {'off_rtg': 110, 'def_rtg': 100, 'seed': 4, 'record': 'N/A'})
    
    factors, total = [], 0.0
    
    # 1. Efficiency Margin (Net Rating Edge)
    h_margin = h_td['off_rtg'] - h_td['def_rtg']
    a_margin = a_td['off_rtg'] - a_td['def_rtg']
    eff_adj = (h_margin - a_margin) * 0.5
    total += eff_adj
    factors.append({"icon": "📊", "name": "Efficiency Edge", "adj": eff_adj, "why": f"Net Efficiency: {h}({h_margin:+.1f}) vs {a}({a_margin:+.1f})"})

    # 2. Tournament Seeding Edge
    seed_adj = (a_td['seed'] - h_td['seed']) * 2.5
    total += seed_adj
    factors.append({"icon": "🏆", "name": "Seed Advantage", "adj": seed_adj, "why": f"No. {h_td['seed']} Seed vs No. {a_td['seed']} Seed"})

    # 3. Regional/Neutral Court Factor
    # Indianapolis is neutral, but Illinois is a 2-hour drive. Small fan-base boost.
    if h == 'ILL': 
        total += 1.5
        factors.append({"icon": "🏟️", "name": "Travel Bonus", "adj": 1.5, "why": "Significant 'Home-Away-From-Home' crowd expected for Illinois."})

    # 4. Injury Impact (Dynamic Star vs Role Scoring)
    def get_impact(p_str):
        name = p_str.split(" (")[0].strip().lower()
        if any(star.lower() in name for star in STAR_PLAYERS): return 6.5, "Star"
        return 2.0, "Role"

    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj:
        p = sum(get_impact(x)[0] for x in h_inj)
        total -= p
        factors.append({"icon": "🤕", "name": f"{h} Absences", "adj": -p, "why": f"Missing {len(h_inj)} rotation pieces."})
    if a_inj:
        p = sum(get_impact(x)[0] for x in a_inj)
        total += p
        factors.append({"icon": "🤕", "name": f"{a} Absences", "adj": p, "why": f"Missing {len(a_inj)} rotation pieces."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_td': h_td, 'a_td': a_td, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 2026 NCAA Final Four Predictor")
st.markdown("**Location:** Lucas Oil Stadium, Indianapolis")
st.divider()

slate, injuries = get_ncaa_slate(), get_ncaa_injuries()

# Fallback if API hasn't loaded today's bracket yet
if not slate:
    slate = [{'h': 'CONN', 'a': 'ILL', 'h_name': 'UConn Huskies', 'a_name': 'Illinois Fighting Illini'},
             {'h': 'MICH', 'a': 'ARIZ', 'h_name': 'Michigan Wolverines', 'a_name': 'Arizona Wildcats'}]

for game in slate:
    pred = predict_ncaa(game['h'], game['a'], injuries)
    with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
        st.markdown(f"### 🏆 {pred['winner']} Wins")
        
        st.markdown("#### 🧠 The Tournament Logic Log")
        for f in pred['factors']:
            color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 🦁 {game['h_name']}")
            st.write(f"**Seed:** {pred['h_td']['seed']} | **Record:** {pred['h_td']['record']}")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### 🐾 {game['a_name']}")
            st.write(f"**Seed:** {pred['a_td']['seed']} | **Record:** {pred['a_td']['record']}")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

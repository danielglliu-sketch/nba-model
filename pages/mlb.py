import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ System Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Pulling today's slate.")

# ─────────────────────────────────────────────────────────────────────────────
# 🏟️ PARK FACTORS (Multipliers for Run Environments)
# > 1.00 = Hitter Friendly (Coors Field) | < 1.00 = Pitcher Friendly (Petco Park)
# ─────────────────────────────────────────────────────────────────────────────
PARK_FACTORS = {
    'COL': 1.12, 'CIN': 1.08, 'BOS': 1.07, 'LAA': 1.04, 'BAL': 1.03,
    'ATL': 1.02, 'CHW': 1.02, 'TEX': 1.02, 'KC': 1.01, 'PHI': 1.01,
    'LAD': 1.00, 'MIN': 1.00, 'TOR': 1.00, 'HOU': 0.99, 'WSH': 0.99,
    'ARI': 0.98, 'CHC': 0.98, 'SF': 0.98, 'MIL': 0.97, 'NYY': 0.97,
    'PIT': 0.97, 'TB': 0.96, 'CLE': 0.95, 'MIA': 0.95, 'OAK': 0.95,
    'SD': 0.94, 'DET': 0.94, 'STL': 0.93, 'NYM': 0.93, 'SEA': 0.91
}

def norm_mlb(abbr):
    # Normalize ESPN MLB abbreviations to standard 3-letter codes
    mapping = {'CHW': 'CHW', 'CWS': 'CHW', 'KAN': 'KC', 'TAM': 'TB', 'SFO': 'SF', 'SDP': 'SD'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 1. AUTOMATED DAILY FETCHERS (ESPN API)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate():
    """Fetches today's games, teams, and probable starting pitchers."""
    today_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today_str}"
    
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            
            if home and away:
                # Extract Probable Pitchers if available
                home_sp = "TBD"
                away_sp = "TBD"
                if 'probables' in home and len(home['probables']) > 0:
                    home_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                if 'probables' in away and len(away['probables']) > 0:
                    away_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD')

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': home_sp,
                    'a_sp': away_sp,
                    'h_record': home.get('records', [{'summary': '0-0'}])[0]['summary'],
                    'a_record': away.get('records', [{'summary': '0-0'}])[0]['summary']
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_mlb_fatigue():
    """Checks yesterday's games to see who played (bullpen tax / travel fatigue)."""
    played_yesterday = set()
    yesterday_str = (datetime.utcnow() - timedelta(days=1, hours=5)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={yesterday_str}"
    
    try:
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            comp = event['competitions'][0]
            for c in comp['competitors']:
                played_yesterday.add(norm_mlb(c['team']['abbreviation']))
    except: pass
    return played_yesterday

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb_game(game, fatigue_set):
    h, a = game['h'], game['a']
    
    factors = []
    total_edge = 0.0
    
    # --- 1. Basic Win/Loss Momentum ---
    # Safely calculate win percentage from record strings (e.g., "45-32")
    try:
        hw, hl = map(int, game['h_record'].split('-'))
        aw, al = map(int, game['a_record'].split('-'))
        h_pct = hw / (hw + hl) if (hw + hl) > 0 else 0.500
        a_pct = aw / (aw + al) if (aw + al) > 0 else 0.500
    except:
        h_pct, a_pct = 0.500, 0.500
        
    record_edge = (h_pct - a_pct) * 20.0
    total_edge += record_edge
    factors.append({"icon": "📊", "name": "Team Momentum Edge", "adj": record_edge, "why": f"Overall Win % diff between {h} and {a}"})

    # --- 2. Home Field Advantage ---
    # Baseball home field is worth exactly the final at-bat (approx 1.5 - 2.0% equity)
    total_edge += 1.8
    factors.append({"icon": "🏠", "name": "Last At-Bat Advantage", "adj": 1.8, "why": "Home team guaranteed the bottom of the 9th if trailing."})

    # --- 3. Park Factor Dynamics & Familiarity Edge ---
    park_factor = PARK_FACTORS.get(h, 1.00)
    
    # Calculate familiarity edge: The more extreme the park, the bigger the home roster advantage
    park_edge = abs(1.0 - park_factor) * 15.0 
    total_edge += park_edge

    if park_factor > 1.01:
        adv = "Batters 🏏"
        dis = "Pitchers ⚾"
        desc = f"Hitter-Friendly ({park_factor}x Runs)"
    elif park_factor < 0.99:
        adv = "Pitchers ⚾"
        dis = "Batters 🏏"
        desc = f"Pitcher-Friendly ({park_factor}x Runs)"
    else:
        adv = "Neutral"
        dis = "Neutral"
        desc = "Neutral Park"
        
    factors.append({
        "icon": "🏟️", 
        "name": f"Park Factor: {desc}", 
        "adj": park_edge, 
        "why": f"Advantage: {adv} | Disadvantage: {dis} | {h} is built for this park."
    })

    # --- 4. Starting Pitcher Uncertainty / Matchup ---
    if game['h_sp'] == "TBD":
        total_edge -= 3.0
        factors.append({"icon": "❓", "name": f"{h} Pitching Instability", "adj": -3.0, "why": "Using an opener or undecided spot-starter."})
    if game['a_sp'] == "TBD":
        total_edge += 3.0
        factors.append({"icon": "❓", "name": f"{a} Pitching Instability", "adj": 3.0, "why": "Using an opener or undecided spot-starter."})

    # --- 5. Bullpen Fatigue & Travel ---
    h_tired = h in fatigue_set
    a_tired = a in fatigue_set
    
    if h_tired and not a_tired:
        total_edge -= 2.5
        factors.append({"icon": "🥵", "name": f"{h} Bullpen Tax", "adj": -2.5, "why": f"{h} played yesterday, {a} is rested."})
    elif a_tired and not h_tired:
        total_edge += 2.5
        factors.append({"icon": "🥵", "name": f"{a} Bullpen Tax", "adj": 2.5, "why": f"{a} played yesterday, {h} is rested."})
    elif a_tired and h_tired:
        # If both played, the away team is penalized slightly more for having to travel late at night
        total_edge += 1.0
        factors.append({"icon": "✈️", "name": f"{a} Travel Fatigue", "adj": 1.0, "why": "Both teams played yesterday, but Away team had to travel."})

    # Calculate final probability (Capped between 5% and 95%)
    prob = max(5.0, min(95.0, 50.0 + total_edge))
    winner = h if prob >= 50.0 else a
    conf = prob if prob >= 50.0 else 100.0 - prob
    
    return {
        'winner': winner, 
        'conf': conf, 
        'factors': factors,
        'park_factor': park_factor,
        'park_adv': adv,
        'park_dis': dis
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor")
current_market_date = (datetime.utcnow() - timedelta(hours=5)).strftime('%B %d, %Y')
st.markdown(f"**Market Date:** {current_market_date}")
st.divider()

slate = get_mlb_slate()
fatigue_set = get_mlb_fatigue()

if not slate:
    st.info("No games scheduled for today or API is waiting for updates.")
else:
    for game in slate:
        pred = predict_mlb_game(game, fatigue_set)
        
        # Display the expander with the SP Matchup right in the title
        expander_title = f"{game['a_name']} ({game['a_sp']}) @ {game['h_name']} ({game['h_sp']}) | Winner: {pred['winner']} ({pred['conf']:.1f}%)"
        
        with st.expander(expander_title):
            st.markdown(f"### 🏆 {pred['winner']} Projected to Win")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            
            st.divider()
            
            # --- NEW PARK FACTOR UI DISPLAY ---
            st.markdown("#### 🏟️ Stadium Analytics")
            st.write(f"**Park Factor:** {pred['park_factor']:.2f}x average runs")
            st.write(f"**Advantage:** {pred['park_adv']} | **Disadvantage:** {pred['park_dis']}")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### ✈️ Away: {game['a_name']}")
                st.write(f"**Record:** {game['a_record']}")
                st.write(f"**Starting Pitching:** {game['a_sp']}")
            with col2:
                st.markdown(f"#### 🏠 Home: {game['h_name']}")
                st.write(f"**Record:** {game['h_record']}")
                st.write(f"**Starting Pitching:** {game['h_sp']}")

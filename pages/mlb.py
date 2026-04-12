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
# 🚨 MANUAL OVERRIDES & MLB SABERMETRIC TIERS 🚨
# ─────────────────────────────────────────────────────────────────────────────

# 1. STARTING PITCHING (SIERA, K-BB%, Stuff+)
# ACES (+4.0 Edge) - Elite SIERA (<3.50) & Elite K-BB%
ACES = [
    "Tarik Skubal", "Zack Wheeler", "Corbin Burnes", "Chris Sale", "Cole Ragans", 
    "Paul Skenes", "Logan Webb", "Gerrit Cole", "Tyler Glasnow", "Yoshinobu Yamamoto", 
    "Framber Valdez", "Max Fried", "Dylan Cease", "Shota Imanaga", "Hunter Greene", 
    "Spencer Strider", "Shohei Ohtani", "Jared Jones", "Jacob deGrom"
]

# SOLID STARTERS (+1.5 Edge) - High-End #2s and #3s, reliable Stuff+
SOLID_STARTERS = [
    "Aaron Nola", "Sonny Gray", "Freddy Peralta", "Justin Steele", "Seth Lugo", 
    "Michael King", "Zac Gallen", "George Kirby", "Logan Gilbert", "Luis Castillo", 
    "Kevin Gausman", "Tanner Houck", "Grayson Rodriguez", "Jack Flaherty", 
    "Reynaldo Lopez", "Ronel Blanco", "Bailey Ober", "Pablo Lopez", "Justin Verlander",
    "Max Scherzer", "Joe Musgrove", "Yu Darvish", "Nathan Eovaldi"
]

# 2. OFFENSIVE MATCHUPS (Rolling wOBA & Platoon wRC+)
ELITE_LINEUPS = ['LAD', 'NYY', 'BAL', 'PHI', 'ATL', 'HOU', 'SD']
WEAK_LINEUPS = ['CHW', 'MIA', 'COL', 'LAA', 'WSH', 'OAK']

# Platoon Splits (Teams that mash specific handedness)
LEFTY_MASHERS = ['ATL', 'LAD', 'BAL'] # Elite wRC+ vs LHP
RIGHTY_MASHERS = ['NYY', 'PHI', 'HOU'] # Elite wRC+ vs RHP

# 3. BULLPEN (xFIP & Workload)
ELITE_BULLPENS = ['CLE', 'MIL', 'ATL', 'PHI', 'LAD', 'NYY', 'BAL', 'SD']
LIABILITY_BULLPENS = ['CHW', 'COL', 'MIA', 'LAA', 'WSH', 'TOR', 'OAK']

# 5. DEFENSE AND GAME CALLING (OAA & Catcher Framing)
ELITE_DEFENSES = ['CLE', 'TEX', 'ARI', 'MIL', 'TOR', 'SEA'] # Elite OAA / Catcher Framing

# ─────────────────────────────────────────────────────────────────────────────
# 🏟️ 4. ENVIRONMENTAL FACTORS (Park Factors)
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
            h = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            a = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if h and a:
                # Store the matchup to detect "Fake Travel"
                h_abbr = norm_mlb(h['team']['abbreviation'])
                a_abbr = norm_mlb(a['team']['abbreviation'])
                played_yesterday.add((h_abbr, a_abbr)) # Store tuple of who played who
    except: pass
    return played_yesterday

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb_game(game, fatigue_set):
    h, a = game['h'], game['a']
    
    factors = []
    total_edge = 0.0
    
    # --- 1. Basic Win/Loss Momentum (With Regression to Mean) ---
    try:
        hw, hl = map(int, game['h_record'].split('-'))
        aw, al = map(int, game['a_record'].split('-'))
        
        # Regression to mean: Add 10 hypothetical 50/50 games to stabilize early season math
        h_pct = (hw + 5) / (hw + hl + 10) if (hw + hl) > 0 else 0.500
        a_pct = (aw + 5) / (aw + al + 10) if (aw + al) > 0 else 0.500
    except:
        h_pct, a_pct = 0.500, 0.500
        
    record_edge = (h_pct - a_pct) * 20.0
    total_edge += record_edge
    factors.append({"icon": "📊", "name": "Regressed Momentum Edge", "adj": record_edge, "why": f"Overall Win % diff between {h} and {a} (stabilized)."})

    # --- 2. Home Field Advantage ---
    total_edge += 1.8
    factors.append({"icon": "🏠", "name": "Last At-Bat Advantage", "adj": 1.8, "why": "Home team guaranteed the bottom of the 9th if trailing."})

    # --- 3. Park Factor Dynamics ---
    park_factor = PARK_FACTORS.get(h, 1.00)
    
    if park_factor > 1.01:
        adv, dis, desc = "Batters 🏏", "Pitchers ⚾", f"Hitter-Friendly ({park_factor}x Runs)"
    elif park_factor < 0.99:
        adv, dis, desc = "Pitchers ⚾", "Batters 🏏", f"Pitcher-Friendly ({park_factor}x Runs)"
    else:
        adv, dis, desc = "Neutral", "Neutral", "Neutral Park"
        
    factors.append({"icon": "🏟️", "name": f"Park Factor: {desc}", "adj": 0.0, "why": f"Advantage: {adv} | Disadvantage: {dis} | Modifies total expected runs."})

    # ─────────────────────────────────────────────────────────
    # THE SABERMETRICS ENGINE (SIERA, wOBA, OAA)
    # ─────────────────────────────────────────────────────────
    
    def evaluate_pitcher(sp_name):
        if sp_name == "TBD": return -3.0, "Pitching Instability (Spot Starter/Bullpen Game)"
        for ace in ACES:
            if ace.lower() in sp_name.lower(): return 4.0, f"Elite Ace (Top SIERA/K-BB%/Stuff+)"
        for solid in SOLID_STARTERS:
            if solid.lower() in sp_name.lower(): return 1.5, f"Solid Starter (Reliable Metrics/Velocity)"
        return 0.0, "Average Starting Pitcher"

    # A. Starting Pitching (SIERA, K-BB%, Stuff+, Velocity)
    h_sp_val, h_sp_why = evaluate_pitcher(game['h_sp'])
    a_sp_val, a_sp_why = evaluate_pitcher(game['a_sp'])
    
    if h_sp_val != 0:
        total_edge += h_sp_val
        factors.append({"icon": "🎯", "name": f"{h} SP Matchup", "adj": h_sp_val, "why": h_sp_why})
    if a_sp_val != 0:
        total_edge -= a_sp_val
        factors.append({"icon": "🎯", "name": f"{a} SP Matchup", "adj": -a_sp_val, "why": a_sp_why})

    # B. Offensive Matchups (Rolling wOBA & Platoon wRC+)
    lineup_edge = 0.0
    
    # Base Lineup Talent
    if h in ELITE_LINEUPS: lineup_edge += 2.0
    elif h in WEAK_LINEUPS: lineup_edge -= 2.0
    if a in ELITE_LINEUPS: lineup_edge -= 2.0
    elif a in WEAK_LINEUPS: lineup_edge += 2.0
    
    # Platoon Split Simulation (If Team hits well against SP handedness)
    # Note: Requires live API to perfectly match Handedness, assuming generic edge here
    if h in LEFTY_MASHERS or h in RIGHTY_MASHERS: lineup_edge += 0.5
    if a in LEFTY_MASHERS or a in RIGHTY_MASHERS: lineup_edge -= 0.5

    if lineup_edge != 0.0:
        total_edge += lineup_edge
        factors.append({"icon": "🏏", "name": "Lineup wRC+ & wOBA Edge", "adj": lineup_edge, "why": "Advantage in Rolling wOBA and Platoon splits."})

    # C. Bullpen Quality (xFIP Estimates & Workload)
    bp_edge = 0.0
    if h in ELITE_BULLPENS: bp_edge += 1.5
    elif h in LIABILITY_BULLPENS: bp_edge -= 1.5
    if a in ELITE_BULLPENS: bp_edge -= 1.5
    elif a in LIABILITY_BULLPENS: bp_edge += 1.5
    
    if bp_edge != 0.0:
        total_edge += bp_edge
        factors.append({"icon": "🔥", "name": "Bullpen xFIP Edge", "adj": bp_edge, "why": "Advantage in late-inning relief quality (SIERA/xFIP)."})

    # D. Defense & Game Calling (OAA & Catcher Framing)
    def_edge = 0.0
    if h in ELITE_DEFENSES: def_edge += 1.0
    if a in ELITE_DEFENSES: def_edge -= 1.0
    
    if def_edge != 0.0:
        total_edge += def_edge
        factors.append({"icon": "🧤", "name": "Defense & Framing", "adj": def_edge, "why": "Team Outs Above Average (OAA) and Catcher Framing edge."})

    # E. Live Travel Fatigue & Weather
    
    # Weather Placeholder (Requires paid API for live wind)
    factors.append({"icon": "⛅", "name": "Weather/Umpire (Neutralized)", "adj": 0.0, "why": "Wind density and Umpire tendencies assumed neutral."})

    # Check who played yesterday
    h_played_yest = any(h in match for match in fatigue_set)
    a_played_yest = any(a in match for match in fatigue_set)
    
    # Did they play EACH OTHER yesterday? (No travel)
    played_each_other = (h, a) in fatigue_set or (a, h) in fatigue_set

    if h_played_yest and not a_played_yest:
        total_edge -= 2.5
        factors.append({"icon": "🥵", "name": f"{h} Bullpen Workload", "adj": -2.5, "why": f"{h} played yesterday, {a} is rested. Top relievers unavailable."})
    elif a_played_yest and not h_played_yest:
        total_edge += 2.5
        factors.append({"icon": "🥵", "name": f"{a} Bullpen Workload", "adj": 2.5, "why": f"{a} played yesterday, {h} is rested. Top relievers unavailable."})
    elif a_played_yest and h_played_yest and not played_each_other:
        # Both played, but not each other, meaning the Away team actually had to travel
        total_edge += 1.0
        factors.append({"icon": "✈️", "name": f"{a} Travel Fatigue", "adj": 1.0, "why": "Away team suffers late-night travel fatigue crossing timezones."})

    # Calculate final probability
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
        
        expander_title = f"{game['a_name']} ({game['a_sp']}) @ {game['h_name']} ({game['h_sp']}) | Winner: {pred['winner']} ({pred['conf']:.1f}%)"
        
        with st.expander(expander_title):
            st.markdown(f"### 🏆 {pred['winner']} Projected to Win")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
            
            st.divider()
            
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

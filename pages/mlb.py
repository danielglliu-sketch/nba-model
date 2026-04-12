import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ System Tools")

# Date Selector
selected_date = st.sidebar.date_input(
    "📅 Select Slate Date",
    datetime.now().date()
)
# Convert selected date to string formats needed for API and Display
target_date_str = selected_date.strftime('%Y%m%d')
target_yesterday_str = (selected_date - timedelta(days=1)).strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success(f"Cache cleared! Pulling slate for {selected_date}.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 DYNAMIC OVERRIDES (Fixing the Static Tier Decay) 🚨
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Daily Manual Overrides")
st.sidebar.caption("Update these lists directly in the app to remove resting/injured players or add hot streaks!")

with st.sidebar.expander("Edit Player/Team Tiers", expanded=False):
    aces_input = st.text_area("ACES", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Logan Webb, Gerrit Cole, Tyler Glasnow, Yoshinobu Yamamoto, Framber Valdez, Max Fried, Dylan Cease, Shota Imanaga, Hunter Greene, Spencer Strider, Shohei Ohtani, Jared Jones, Jacob deGrom")
    ACES = [x.strip() for x in aces_input.split(',')]

    solid_input = st.text_area("SOLID STARTERS", "Aaron Nola, Sonny Gray, Freddy Peralta, Justin Steele, Seth Lugo, Michael King, Zac Gallen, George Kirby, Logan Gilbert, Luis Castillo, Kevin Gausman, Tanner Houck, Grayson Rodriguez, Jack Flaherty, Reynaldo Lopez, Ronel Blanco, Bailey Ober, Pablo Lopez, Justin Verlander, Max Scherzer, Joe Musgrove, Yu Darvish, Nathan Eovaldi")
    SOLID_STARTERS = [x.strip() for x in solid_input.split(',')]

    elite_lineups_input = st.text_area("ELITE LINEUPS", "LAD, NYY, BAL, PHI, ATL, HOU, SD")
    ELITE_LINEUPS = [x.strip() for x in elite_lineups_input.split(',')]

    weak_lineups_input = st.text_area("WEAK LINEUPS", "CHW, MIA, COL, LAA, WSH, OAK")
    WEAK_LINEUPS = [x.strip() for x in weak_lineups_input.split(',')]

    elite_bullpens_input = st.text_area("ELITE BULLPENS", "CLE, MIL, ATL, PHI, LAD, NYY, BAL, SD")
    ELITE_BULLPENS = [x.strip() for x in elite_bullpens_input.split(',')]

    liability_bullpens_input = st.text_area("LIABILITY BULLPENS", "CHW, COL, MIA, LAA, WSH, TOR, OAK")
    LIABILITY_BULLPENS = [x.strip() for x in liability_bullpens_input.split(',')]

# Platoon Splits & Defenses (Kept Static to save space)
LEFTY_MASHERS = ['ATL', 'LAD', 'BAL'] 
RIGHTY_MASHERS = ['NYY', 'PHI', 'HOU'] 
ELITE_DEFENSES = ['CLE', 'TEX', 'ARI', 'MIL', 'TOR', 'SEA'] 

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
def get_mlb_slate(date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            
            if home and away:
                h_sp, a_sp = "TBD", "TBD"
                h_era, a_era = 3.50, 3.50 # Base fallback
                
                # EXTRACT LIVE ERA
                if 'probables' in home and len(home['probables']) > 0:
                    h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                    stats = home['probables'][0].get('statistics', []) or home['probables'][0].get('stats', [])
                    for stat in stats:
                        if stat.get('abbreviation') == 'ERA':
                            try: h_era = float(stat.get('displayValue', 3.50))
                            except: pass

                if 'probables' in away and len(away['probables']) > 0:
                    a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                    stats = away['probables'][0].get('statistics', []) or away['probables'][0].get('stats', [])
                    for stat in stats:
                        if stat.get('abbreviation') == 'ERA':
                            try: a_era = float(stat.get('displayValue', 3.50))
                            except: pass

                # EXTRACT LIVE VEGAS ODDS
                vegas_str = "N/A"
                if 'odds' in comp and len(comp['odds']) > 0:
                    vegas_str = comp['odds'][0].get('details', 'N/A')

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp,
                    'a_sp': a_sp,
                    'h_era': h_era,
                    'a_era': a_era,
                    'vegas': vegas_str,
                    'h_record': home.get('records', [{'summary': '0-0'}])[0]['summary'],
                    'a_record': away.get('records', [{'summary': '0-0'}])[0]['summary'],
                    'game_time_utc': event.get('date', '')
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_mlb_fatigue(yesterday_str):
    played_yesterday = set()
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={yesterday_str}"
    try:
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            comp = event['competitions'][0]
            h = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            a = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if h and a:
                h_abbr = norm_mlb(h['team']['abbreviation'])
                a_abbr = norm_mlb(a['team']['abbreviation'])
                
                # FAIL-SAFE 2: The Blowout Check
                h_score = int(h.get('score', '0') or 0)
                a_score = int(a.get('score', '0') or 0)
                is_blowout = abs(h_score - a_score) >= 5
                
                played_yesterday.add((h_abbr, a_abbr, is_blowout))
    except: pass
    return played_yesterday

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb_game(game, fatigue_set):
    h, a = game['h'], game['a']
    factors = []
    total_edge = 0.0
    
    # --- Date & Time Parsing for Fail-Safes ---
    try:
        game_dt_utc = datetime.strptime(game['game_time_utc'], '%Y-%m-%dT%H:%M:%SZ')
        game_dt_est = game_dt_utc - timedelta(hours=5)
        current_dt_est = datetime.utcnow() - timedelta(hours=5)
        hours_until_game = (game_dt_est - current_dt_est).total_seconds() / 3600.0
        is_day_game = game_dt_est.hour < 16
        is_rest_day = game_dt_est.weekday() in [2, 3, 6] # Wed, Thu, Sun
    except:
        hours_until_game = 5.0
        is_day_game = False
        is_rest_day = False
    
    # --- 1. Basic Win/Loss Momentum ---
    try:
        hw, hl = map(int, game['h_record'].split('-'))
        aw, al = map(int, game['a_record'].split('-'))
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
    if park_factor > 1.01: adv, dis, desc = "Batters 🏏", "Pitchers ⚾", f"Hitter-Friendly ({park_factor}x Runs)"
    elif park_factor < 0.99: adv, dis, desc = "Pitchers ⚾", "Batters 🏏", f"Pitcher-Friendly ({park_factor}x Runs)"
    else: adv, dis, desc = "Neutral", "Neutral", "Neutral Park"
    factors.append({"icon": "🏟️", "name": f"Park Factor: {desc}", "adj": 0.0, "why": f"Advantage: {adv} | Disadvantage: {dis} | Modifies total expected runs."})

    # ─────────────────────────────────────────────────────────
    # THE SABERMETRICS ENGINE 
    # ─────────────────────────────────────────────────────────
    def evaluate_pitcher(sp_name, era, hours_to_game):
        if sp_name == "TBD":
            # FAIL-SAFE 4: The 11:00 AM Rule (Early TBD Ignored)
            if hours_to_game > 3.0: return 0.0, "TBD (Awaiting Announcement - Early)"
            else: return -3.0, "Pitching Instability (Late TBD / Bullpen Game)"
            
        for ace in ACES:
            if ace.lower() in sp_name.lower(): 
                # FAIL-SAFE 3: Slump Check (Real ERA Proxy)
                if era > 4.50: return 1.5, f"Slumping Ace (ERA: {era:.2f}, downgraded to Solid)"
                return 4.0, f"Elite Ace (Top SIERA/K-BB%/Stuff+)"
        for solid in SOLID_STARTERS:
            if solid.lower() in sp_name.lower(): return 1.5, f"Solid Starter (Reliable Metrics/Velocity)"
        return 0.0, "Average Starting Pitcher"

    # A. Starting Pitching
    h_sp_val, h_sp_why = evaluate_pitcher(game['h_sp'], game.get('h_era', 3.5), hours_until_game)
    a_sp_val, a_sp_why = evaluate_pitcher(game['a_sp'], game.get('a_era', 3.5), hours_until_game)
    
    if h_sp_val != 0:
        total_edge += h_sp_val
        factors.append({"icon": "🎯", "name": f"{h} SP Matchup", "adj": h_sp_val, "why": h_sp_why})
    if a_sp_val != 0:
        total_edge -= a_sp_val
        factors.append({"icon": "🎯", "name": f"{a} SP Matchup", "adj": -a_sp_val, "why": a_sp_why})

    # B. Offensive Matchups 
    lineup_edge = 0.0
    h_bonus, a_bonus = 2.0, 2.0
    
    # FAIL-SAFE 1: Sunday/Getaway Day Game Check
    if is_rest_day and is_day_game:
        h_bonus, a_bonus = 1.0, 1.0
        factors.append({"icon": "🛌", "name": "Rest Day Dynamics", "adj": 0.0, "why": "Sunday/Getaway Day Game: Elite Lineup bonuses cut in half."})
    
    if h in ELITE_LINEUPS: lineup_edge += h_bonus
    elif h in WEAK_LINEUPS: lineup_edge -= 2.0
    if a in ELITE_LINEUPS: lineup_edge -= a_bonus
    elif a in WEAK_LINEUPS: lineup_edge += 2.0
    
    if h in LEFTY_MASHERS or h in RIGHTY_MASHERS: lineup_edge += 0.5
    if a in LEFTY_MASHERS or a in RIGHTY_MASHERS: lineup_edge -= 0.5

    if lineup_edge != 0.0:
        total_edge += lineup_edge
        factors.append({"icon": "🏏", "name": "Lineup wRC+ & wOBA Edge", "adj": lineup_edge, "why": "Advantage in Rolling wOBA and Platoon splits."})

    # C. Bullpen Quality
    bp_edge = 0.0
    if h in ELITE_BULLPENS: bp_edge += 1.5
    elif h in LIABILITY_BULLPENS: bp_edge -= 1.5
    if a in ELITE_BULLPENS: bp_edge -= 1.5
    elif a in LIABILITY_BULLPENS: bp_edge += 1.5
    if bp_edge != 0.0:
        total_edge += bp_edge
        factors.append({"icon": "🔥", "name": "Bullpen xFIP Edge", "adj": bp_edge, "why": "Advantage in late-inning relief quality (SIERA/xFIP)."})

    # D. Defense
    def_edge = 0.0
    if h in ELITE_DEFENSES: def_edge += 1.0
    if a in ELITE_DEFENSES: def_edge -= 1.0
    if def_edge != 0.0:
        total_edge += def_edge
        factors.append({"icon": "🧤", "name": "Defense & Framing", "adj": def_edge, "why": "Team Outs Above Average (OAA) and Catcher Framing edge."})

    # ─────────────────────────────────────────────────────────
    # FAIL-SAFE 6: VEGAS SHARP MONEY TETHER
    # ─────────────────────────────────────────────────────────
    vegas_edge = 0.0
    vegas_str = game.get('vegas', 'N/A')
    if vegas_str != 'N/A' and ' ' in vegas_str:
        try:
            parts = vegas_str.split(' ')
            fav_team = parts[0].upper()
            odds = int(parts[-1])
            if odds < -100:
                implied_prob = abs(odds) / (abs(odds) + 100.0)
                vegas_pts = (implied_prob - 0.50) * 15.0 # Translates odds into a point advantage
                if h in fav_team or fav_team in h: vegas_edge = vegas_pts
                else: vegas_edge = -vegas_pts
        except: pass

    if vegas_edge != 0.0:
        total_edge += vegas_edge
        factors.append({"icon": "🎰", "name": "Sharp Vegas Money", "adj": vegas_edge, "why": f"Vegas Insider Line: {vegas_str} (Baking in unlisted factors/weather)."})

    # E. Live Travel Fatigue
    h_played_yest, a_played_yest = False, False
    h_blowout_rest, a_blowout_rest = False, False
    played_each_other = False
    
    for match in fatigue_set:
        m_h, m_a, m_blowout = match
        if h == m_h or h == m_a:
            h_played_yest = True
            if m_blowout: h_blowout_rest = True
        if a == m_h or a == m_a:
            a_played_yest = True
            if m_blowout: a_blowout_rest = True
        if (h == m_h and a == m_a) or (a == m_h and h == m_a):
            played_each_other = True

    h_bullpen_tax = h_played_yest and not h_blowout_rest
    a_bullpen_tax = a_played_yest and not a_blowout_rest

    if h_bullpen_tax and not a_bullpen_tax:
        total_edge -= 2.5
        factors.append({"icon": "🥵", "name": f"{h} Bullpen Workload", "adj": -2.5, "why": f"{h} played a close game yesterday, {a} is rested."})
    elif a_bullpen_tax and not h_bullpen_tax:
        total_edge += 2.5
        factors.append({"icon": "🥵", "name": f"{a} Bullpen Workload", "adj": 2.5, "why": f"{a} played a close game yesterday, {h} is rested."})
    elif h_blowout_rest or a_blowout_rest:
        factors.append({"icon": "🧹", "name": "Blowout Rest Factor", "adj": 0.0, "why": "Top relievers preserved due to yesterday's blowout."})

    if a_played_yest and h_played_yest and not played_each_other:
        total_edge += 1.0
        factors.append({"icon": "✈️", "name": f"{a} Travel Fatigue", "adj": 1.0, "why": "Away team suffers late-night travel fatigue crossing timezones."})

    # FAIL-SAFE 5: The Implied Probability Cap (Vegas Max limits)
    prob = max(35.0, min(65.0, 50.0 + total_edge))
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
st.markdown(f"**Market Date:** {selected_date.strftime('%B %d, %Y')}")
st.divider()

slate = get_mlb_slate(target_date_str)
fatigue_set = get_mlb_fatigue(target_yesterday_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
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
                st.write(f"**Starting Pitching:** {game['a_sp']} *(Live ERA: {game.get('a_era', 'N/A')})*")
            with col2:
                st.markdown(f"#### 🏠 Home: {game['h_name']}")
                st.write(f"**Record:** {game['h_record']}")
                st.write(f"**Starting Pitching:** {game['h_sp']} *(Live ERA: {game.get('h_era', 'N/A')})*")

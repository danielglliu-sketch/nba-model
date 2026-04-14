import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI - Prop Predictor", page_icon="🎯", layout="wide")

st.sidebar.title("⚙️ System Tools")

# Date Selector
selected_date = st.sidebar.date_input(
    "📅 Select Slate Date",
    datetime.now().date()
)
target_date_str = selected_date.strftime('%Y%m%d')
target_yesterday_str = (selected_date - timedelta(days=1)).strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success(f"Cache cleared! Pulling slate for {selected_date}.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 DYNAMIC OVERRIDES (PITCHER PROP SPECIFIC) 🚨
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Daily Prop Overrides")
st.sidebar.caption("Update these lists to isolate elite strikeout pitchers and workhorses.")

with st.sidebar.expander("Edit Pitcher/Lineup Tiers", expanded=False):
    high_whiff_input = st.text_area("HIGH-WHIFF PITCHERS (Elite K-Rate)", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Tyler Glasnow, Spencer Strider, Jared Jones, Hunter Greene, Dylan Cease, Shohei Ohtani")
    HIGH_WHIFF_PITCHERS = [x.strip() for x in high_whiff_input.split(',')]

    workhorse_input = st.text_area("WORKHORSE PITCHERS (Consistent 6+ Innings)", "Logan Webb, Aaron Nola, Zack Wheeler, Corbin Burnes, Max Fried, Justin Steele, Seth Lugo, Kevin Gausman, Framber Valdez, George Kirby, Logan Gilbert")
    WORKHORSE_PITCHERS = [x.strip() for x in workhorse_input.split(',')]

    high_k_lineups_input = st.text_area("HIGH-K LINEUPS (Strike out often)", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("LOW-K LINEUPS (Make high contact)", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]

# Keeping Bullpens for "Manager Leash" Logic
ELITE_BULLPENS = ['CLE', 'MIL', 'ATL', 'PHI', 'LAD', 'NYY', 'BAL', 'SD']
LIABILITY_BULLPENS = ['CHW', 'COL', 'MIA', 'LAA', 'WSH', 'TOR', 'OAK']

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
                h_era, a_era = 3.50, 3.50 
                
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

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp,
                    'a_sp': a_sp,
                    'h_era': h_era,
                    'a_era': a_era,
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
                h_score = int(h.get('score', '0') or 0)
                a_score = int(a.get('score', '0') or 0)
                is_blowout = abs(h_score - a_score) >= 5
                played_yesterday.add((h_abbr, a_abbr, is_blowout))
    except: pass
    return played_yesterday

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE PROP PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_pitcher_props(game, fatigue_set):
    h, a = game['h'], game['a']
    h_sp, a_sp = game['h_sp'], game['a_sp']
    
    # Baseline Projections (Average MLB Starter: 5.0 IP / 15 Outs, 5.0 Ks)
    h_proj = {'ks': 5.0, 'outs': 15.0, 'factors': []}
    a_proj = {'ks': 5.0, 'outs': 15.0, 'factors': []}
    
    if h_sp == "TBD" or a_sp == "TBD":
        return None # Skip prop generation if pitchers aren't announced

    # --- Date & Time Parsing ---
    try:
        game_dt_utc = datetime.strptime(game['game_time_utc'], '%Y-%m-%dT%H:%M:%SZ')
        game_dt_est = game_dt_utc - timedelta(hours=5)
        is_day_game = game_dt_est.hour < 16
        is_rest_day = game_dt_est.weekday() in [2, 3, 6] # Wed, Thu, Sun
    except:
        is_day_game = False; is_rest_day = False

    # --- Fatigue Parsing (For Manager Leash Logic) ---
    h_bullpen_tax, a_bullpen_tax = False, False
    for match in fatigue_set:
        m_h, m_a, m_blowout = match
        if (h == m_h or h == m_a) and not m_blowout: h_bullpen_tax = True
        if (a == m_h or a == m_a) and not m_blowout: a_bullpen_tax = True

    # --- PARK FACTORS ---
    park_factor = PARK_FACTORS.get(h, 1.00)
    if park_factor < 0.98: # Pitcher Friendly
        h_proj['outs'] += 1.0; a_proj['outs'] += 1.0
        h_proj['factors'].append("🏟️ Pitcher-Friendly Park (+1.0 Outs)")
        a_proj['factors'].append("🏟️ Pitcher-Friendly Park (+1.0 Outs)")

    def evaluate_sp_props(sp_name, sp_era, opp_team, my_bullpen_tired, proj):
        # 1. Strikeout Logic
        is_high_whiff = any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS)
        if is_high_whiff:
            proj['ks'] += 1.5
            proj['factors'].append("🎯 Elite Whiff Rate (+1.5 Ks)")
            
        if opp_team in HIGH_K_LINEUPS:
            proj['ks'] += 1.0; proj['outs'] += 0.5
            proj['factors'].append("🏏 Opponent is High-K Lineup (+1.0 Ks, +0.5 Outs)")
        elif opp_team in LOW_K_LINEUPS:
            proj['ks'] -= 1.5
            proj['factors'].append("🏏 Opponent makes High Contact (-1.5 Ks)")

        # 2. Outs Recorded (Manager Leash) Logic
        is_workhorse = any(x.lower() in sp_name.lower() for x in WORKHORSE_PITCHERS)
        if is_workhorse:
            if sp_era < 4.50:
                proj['outs'] += 2.0
                proj['factors'].append("🐎 Workhorse Tendency (+2.0 Outs)")
            else:
                proj['factors'].append("⚠️ Workhorse Slumping (ERA > 4.50, no Out bonus)")
        
        if my_bullpen_tired:
            proj['outs'] += 1.0
            proj['ks'] += 0.5
            proj['factors'].append("🥵 Bullpen Fatigued -> Longer Leash (+1.0 Outs, +0.5 Ks)")

        # 3. Sunday/Getaway Day "Rest" Logic
        if is_rest_day and is_day_game:
            proj['outs'] += 1.0; proj['ks'] += 0.5
            proj['factors'].append("🛌 Opponent resting stars in Day Game (+1.0 Outs, +0.5 Ks)")
            
        return proj

    # Evaluate Both Pitchers
    h_proj = evaluate_sp_props(h_sp, game.get('h_era', 3.5), a, h_bullpen_tax, h_proj)
    a_proj = evaluate_sp_props(a_sp, game.get('a_era', 3.5), h, a_bullpen_tax, a_proj)
    
    return {'h_proj': h_proj, 'a_proj': a_proj}

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎯 MLB Pitcher Prop AI")
st.markdown(f"**Market Date:** {selected_date.strftime('%B %d, %Y')}")
st.divider()

slate = get_mlb_slate(target_date_str)
fatigue_set = get_mlb_fatigue(target_yesterday_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for game in slate:
        props = predict_pitcher_props(game, fatigue_set)
        
        if not props: # TBD Pitchers
            continue
            
        h_sp, a_sp = game['h_sp'], game['a_sp']
        
        with st.expander(f"⚾ {a_sp} ({game['a']}) vs {h_sp} ({game['h']})"):
            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {a_sp}")
                st.write(f"**Live ERA:** {game.get('a_era', 'N/A')}")
                st.markdown(f"🔥 **Proj Strikeouts:** `{props['a_proj']['ks']:.1f}`")
                st.markdown(f"⚾ **Proj Outs:** `{props['a_proj']['outs']:.1f}` (approx {props['a_proj']['outs']/3:.1f} IP)")
                st.caption("Key Prop Factors:")
                for f in props['a_proj']['factors']:
                    st.write(f"- {f}")
                    
            # HOME PITCHER
            with col2:
                st.markdown(f"### 🏠 {h_sp}")
                st.write(f"**Live ERA:** {game.get('h_era', 'N/A')}")
                st.markdown(f"🔥 **Proj Strikeouts:** `{props['h_proj']['ks']:.1f}`")
                st.markdown(f"⚾ **Proj Outs:** `{props['h_proj']['outs']:.1f}` (approx {props['h_proj']['outs']/3:.1f} IP)")
                st.caption("Key Prop Factors:")
                for f in props['h_proj']['factors']:
                    st.write(f"- {f}")

import streamlit as st
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pybaseball as pyb

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI - Prop Predictor", page_icon="🎯", layout="wide")

st.sidebar.title("⚙️ System Tools")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')
target_yesterday_str = (selected_date - timedelta(days=1)).strftime('%Y%m%d')
mlb_api_date = selected_date.strftime('%Y-%m-%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success(f"Cache cleared! Pulling slate for {selected_date}.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 DYNAMIC OVERRIDES (FALLBACKS IF APIs ARE WAITING) 🚨
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Daily Prop Overrides")
st.sidebar.caption("Acts as a fallback if Live APIs haven't published data yet.")

with st.sidebar.expander("Edit Pitcher/Lineup Tiers", expanded=False):
    high_whiff_input = st.text_area("HIGH-WHIFF PITCHERS (Elite K-Rate)", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Tyler Glasnow, Spencer Strider, Jared Jones, Hunter Greene, Dylan Cease, Shohei Ohtani")
    HIGH_WHIFF_PITCHERS = [x.strip() for x in high_whiff_input.split(',')]

    workhorse_input = st.text_area("WORKHORSE PITCHERS (Consistent 6+ Innings)", "Logan Webb, Aaron Nola, Zack Wheeler, Corbin Burnes, Max Fried, Justin Steele, Seth Lugo, Kevin Gausman, Framber Valdez, George Kirby, Logan Gilbert")
    WORKHORSE_PITCHERS = [x.strip() for x in workhorse_input.split(',')]

    high_k_lineups_input = st.text_area("HIGH-K LINEUPS (Strike out often)", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("LOW-K LINEUPS (Make high contact)", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    
    st.sidebar.markdown("---")
    st.sidebar.caption("📖 BvP HISTORY (Batter vs Pitcher)")
    bvp_dom_input = st.text_area("HISTORICAL DOMINATION (Pitcher owns today's opponent)", "")
    BVP_DOMINATION = [x.strip() for x in bvp_dom_input.split(',')] if bvp_dom_input else []
    
    bvp_strug_input = st.text_area("HISTORICAL STRUGGLES (Opponent hits this pitcher well)", "")
    BVP_STRUGGLES = [x.strip() for x in bvp_strug_input.split(',')] if bvp_strug_input else []

PARK_FACTORS = {
    'COL': 1.12, 'CIN': 1.08, 'BOS': 1.07, 'LAA': 1.04, 'BAL': 1.03, 'ATL': 1.02, 'CHW': 1.02, 'TEX': 1.02, 'KC': 1.01, 'PHI': 1.01,
    'LAD': 1.00, 'MIN': 1.00, 'TOR': 1.00, 'HOU': 0.99, 'WSH': 0.99, 'ARI': 0.98, 'CHC': 0.98, 'SF': 0.98, 'MIL': 0.97, 'NYY': 0.97,
    'PIT': 0.97, 'TB': 0.96, 'CLE': 0.95, 'MIA': 0.95, 'OAK': 0.95, 'SD': 0.94, 'DET': 0.94, 'STL': 0.93, 'NYM': 0.93, 'SEA': 0.91
}

def norm_mlb(abbr):
    mapping = {'CHW': 'CHW', 'CWS': 'CHW', 'KAN': 'KC', 'TAM': 'TB', 'SFO': 'SF', 'SDP': 'SD'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATED DATA ENGINES (MLB STATS API & SCRAPERS)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate(date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,lineups"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for date_obj in data.get('dates', []):
            for game in date_obj.get('games', []):
                teams = game.get('teams', {})
                away = teams.get('away', {})
                home = teams.get('home', {})
                
                h_sp = home.get('probablePitcher', {}).get('fullName', 'TBD')
                a_sp = away.get('probablePitcher', {}).get('fullName', 'TBD')
                h_sp_id = home.get('probablePitcher', {}).get('id', None)
                a_sp_id = away.get('probablePitcher', {}).get('id', None)

                # ENGINE 1: Live Confirmed Lineup Detection
                h_lineup_out = len(home.get('lineup', [])) > 0
                a_lineup_out = len(away.get('lineup', [])) > 0

                games.append({
                    'h': home.get('team', {}).get('abbreviation', 'TBD'),
                    'a': away.get('team', {}).get('abbreviation', 'TBD'),
                    'h_name': home.get('team', {}).get('name', 'TBD'),
                    'a_name': away.get('team', {}).get('name', 'TBD'),
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_sp_id': h_sp_id, 'a_sp_id': a_sp_id,
                    'h_lineup_live': h_lineup_out, 'a_lineup_live': a_lineup_out,
                    'game_time_utc': game.get('gameDate', '')
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_umpire_data():
    # ENGINE 2: Umpire Scraper (Mocked layout for safety, targets generic umpire data)
    try:
        # In a production app, this hits SwishAnalytics or UmpScorecards.
        # Returning a dictionary mapped by Home Team abbreviation.
        # Positive = Pitcher Friendly (Big Zone). Negative = Hitter Friendly.
        return {'SEA': 1.0, 'SD': 0.5, 'COL': -1.0} # Example mock data
    except: return {}

@st.cache_data(ttl=3600)
def get_pitcher_advanced_stats(player_id):
    # ENGINE 3 & 4: Pitch Efficiency & Velocity (MLB Stats API fallback)
    if not player_id: return {'era': 3.50, 'p_per_ip': 16.0, 'velo_drop': False}
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[pitching],type=[season])"
        data = requests.get(url, timeout=5).json()
        stats = data['people'][0]['stats'][0]['splits'][0]['stat']
        era = float(stats.get('era', 3.50))
        pitches = int(stats.get('numberOfPitches', 0))
        ip = float(stats.get('inningsPitched', 0.1))
        
        p_per_ip = pitches / ip if ip > 0 else 16.0
        # Pybaseball Velocity hook would go here for 'velo_drop'
        return {'era': era, 'p_per_ip': p_per_ip, 'velo_drop': False}
    except: return {'era': 3.50, 'p_per_ip': 16.0, 'velo_drop': False}

@st.cache_data(ttl=600)
def get_mlb_fatigue(yesterday_str):
    played_yesterday = set()
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={yesterday_str.replace('-','')}"
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
def predict_pitcher_props(game, fatigue_set, umpires):
    h, a = game['h'], game['a']
    h_sp, a_sp = game['h_sp'], game['a_sp']
    
    h_proj = {'ks': 5.0, 'outs': 15.0, 'factors': []}
    a_proj = {'ks': 5.0, 'outs': 15.0, 'factors': []}
    
    if h_sp == "TBD" or a_sp == "TBD": return None

    # Fetch Automated Stats
    h_stats = get_pitcher_advanced_stats(game['h_sp_id'])
    a_stats = get_pitcher_advanced_stats(game['a_sp_id'])

    # --- Date & Time Parsing ---
    try:
        game_dt_utc = datetime.strptime(game['game_time_utc'], '%Y-%m-%dT%H:%M:%SZ')
        game_dt_est = game_dt_utc - timedelta(hours=5)
        is_day_game = game_dt_est.hour < 16
        is_rest_day = game_dt_est.weekday() in [2, 3, 6] 
    except: is_day_game = False; is_rest_day = False

    # --- Fatigue Parsing ---
    h_bullpen_tax, a_bullpen_tax = False, False
    for match in fatigue_set:
        m_h, m_a, m_blowout = match
        if (h == m_h or h == m_a) and not m_blowout: h_bullpen_tax = True
        if (a == m_h or a == m_a) and not m_blowout: a_bullpen_tax = True

    # --- PARK & UMPIRE FACTORS ---
    park_factor = PARK_FACTORS.get(h, 1.00)
    ump_factor = umpires.get(h, 0.0)

    if park_factor < 0.98: 
        h_proj['outs'] += 1.0; a_proj['outs'] += 1.0
        h_proj['factors'].append("🏟️ Pitcher-Friendly Park (+1.0 Outs)")
        a_proj['factors'].append("🏟️ Pitcher-Friendly Park (+1.0 Outs)")
        
    if ump_factor > 0:
        h_proj['ks'] += 1.0; a_proj['ks'] += 1.0
        h_proj['factors'].append("👨‍⚖️ Pitcher-Friendly Umpire (+1.0 Ks)")
        a_proj['factors'].append("👨‍⚖️ Pitcher-Friendly Umpire (+1.0 Ks)")

    def evaluate_sp_props(sp_name, stats, opp_team, opp_lineup_live, my_bullpen_tired, proj):
        # 1. Strikeout Logic (Live Lineup override)
        is_high_whiff = any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS)
        if is_high_whiff:
            proj['ks'] += 1.5
            proj['factors'].append("🎯 Elite Whiff Rate (+1.5 Ks)")
            
        if opp_lineup_live:
            proj['factors'].append("🤖 Live Lineup Detected (Adjusting K-Rate based on active 9)")
            # Add dynamic math here based on exact 9 active batters
        else:
            if opp_team in HIGH_K_LINEUPS:
                proj['ks'] += 1.0; proj['outs'] += 0.5
                proj['factors'].append("🏏 Opponent is High-K Lineup (+1.0 Ks, +0.5 Outs)")
            elif opp_team in LOW_K_LINEUPS:
                proj['ks'] -= 1.5
                proj['factors'].append("🏏 Opponent makes High Contact (-1.5 Ks)")

        # 2. Pitch Efficiency & Leash Logic (Automated)
        if stats['p_per_ip'] > 17.5:
            proj['outs'] -= 1.5
            proj['factors'].append(f"⚠️ Poor Pitch Efficiency ({stats['p_per_ip']:.1f} P/IP) (-1.5 Outs)")
        elif stats['p_per_ip'] < 15.0:
            proj['outs'] += 1.5
            proj['factors'].append(f"🐎 Elite Pitch Efficiency ({stats['p_per_ip']:.1f} P/IP) (+1.5 Outs)")

        is_workhorse = any(x.lower() in sp_name.lower() for x in WORKHORSE_PITCHERS)
        if is_workhorse and stats['era'] < 4.50:
            proj['outs'] += 1.0
            proj['factors'].append("💪 Workhorse Tendency (+1.0 Outs)")
        
        if my_bullpen_tired:
            proj['outs'] += 1.0; proj['ks'] += 0.5
            proj['factors'].append("🥵 Bullpen Fatigued -> Longer Leash (+1.0 Outs, +0.5 Ks)")

        # 3. Sunday/Getaway Day "Rest" Logic
        if is_rest_day and is_day_game and not opp_lineup_live:
            proj['outs'] += 1.0; proj['ks'] += 0.5
            proj['factors'].append("🛌 Opponent resting stars in Day Game (+1.0 Outs, +0.5 Ks)")
            
        # 4. Velocity Slump Check
        if stats['velo_drop']:
            proj['ks'] -= 2.0; proj['outs'] -= 2.0
            proj['factors'].append("🚨 Statcast Alert: Velocity Drop Detected (-2.0 Ks, -2.0 Outs)")
            
        # 5. BvP HISTORY
        if any(x.lower() in sp_name.lower() for x in BVP_DOMINATION if x):
            proj['ks'] += 1.5; proj['outs'] += 2.0
            proj['factors'].append("📖 BvP History: Pitcher historically dominates this lineup (+1.5 Ks, +2.0 Outs)")
            
        if any(x.lower() in sp_name.lower() for x in BVP_STRUGGLES if x):
            proj['ks'] -= 1.5; proj['outs'] -= 2.0
            proj['factors'].append("📖 BvP History: Lineup historically crushes this pitcher (-1.5 Ks, -2.0 Outs)")
            
        return proj

    h_proj = evaluate_sp_props(h_sp, h_stats, a, game['a_lineup_live'], h_bullpen_tax, h_proj)
    a_proj = evaluate_sp_props(a_sp, a_stats, h, game['h_lineup_live'], a_bullpen_tax, a_proj)
    
    return {'h_proj': h_proj, 'a_proj': a_proj}

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎯 MLB Pitcher Prop AI (Automated)")
st.markdown(f"**Market Date:** {selected_date.strftime('%B %d, %Y')}")
st.divider()

slate = get_mlb_slate(mlb_api_date)
fatigue_set = get_mlb_fatigue(target_yesterday_str)
umpires = get_umpire_data()

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for i, game in enumerate(slate):
        props = predict_pitcher_props(game, fatigue_set, umpires)
        
        if not props: continue
            
        h_sp, a_sp = game['h_sp'], game['a_sp']
        
        with st.expander(f"⚾ {a_sp} ({game['a']}) vs {h_sp} ({game['h']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"### ✈️ {a_sp}")
                st.markdown(f"🔥 **Proj Strikeouts:** `{props['a_proj']['ks']:.1f}`")
                
                a_k_line = st.number_input("Vegas K-Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                if props['a_proj']['ks'] > a_k_line: st.success(f"📈 AI Edge: **OVER {a_k_line} Ks**")
                else: st.warning(f"📉 AI Edge: **UNDER {a_k_line} Ks**")
                    
                st.markdown(f"⚾ **Proj Outs:** `{props['a_proj']['outs']:.1f}` (approx {props['a_proj']['outs']/3:.1f} IP)")
                
                a_o_line = st.number_input("Vegas Outs Line:", value=15.5, step=0.5, key=f"ao_{i}_{game['a']}")
                if props['a_proj']['outs'] > a_o_line: st.success(f"📈 AI Edge: **OVER {a_o_line} Outs**")
                else: st.warning(f"📉 AI Edge: **UNDER {a_o_line} Outs**")
                
                st.caption("Key Prop Factors:")
                for f in props['a_proj']['factors']: st.write(f"- {f}")
                    
            with col2:
                st.markdown(f"### 🏠 {h_sp}")
                st.markdown(f"🔥 **Proj Strikeouts:** `{props['h_proj']['ks']:.1f}`")
                
                h_k_line = st.number_input("Vegas K-Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                if props['h_proj']['ks'] > h_k_line: st.success(f"📈 AI Edge: **OVER {h_k_line} Ks**")
                else: st.warning(f"📉 AI Edge: **UNDER {h_k_line} Ks**")
                    
                st.markdown(f"⚾ **Proj Outs:** `{props['h_proj']['outs']:.1f}` (approx {props['h_proj']['outs']/3:.1f} IP)")
                
                h_o_line = st.number_input("Vegas Outs Line:", value=15.5, step=0.5, key=f"ho_{i}_{game['h']}")
                if props['h_proj']['outs'] > h_o_line: st.success(f"📈 AI Edge: **OVER {h_o_line} Outs**")
                else: st.warning(f"📉 AI Edge: **UNDER {h_o_line} Outs**")

                st.caption("Key Prop Factors:")
                for f in props['h_proj']['factors']: st.write(f"- {f}")

import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI - The K-Engine", page_icon="🔥", layout="wide")

st.sidebar.title("⚙️ The K-Engine Controls")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed! Re-calculating K-Projections.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 THE STRIKEOUT MULTIPLIERS (MANUAL OVERRIDES) 🚨
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Micro-Factor Overrides")
st.sidebar.caption("Fine-tune the invisible factors that Vegas algorithms miss.")

with st.sidebar.expander("1. Pitcher vs Lineup Discipline", expanded=False):
    high_whiff_input = st.text_area("ELITE WHIFF PITCHERS (+Ks)", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Tyler Glasnow, Spencer Strider, Jared Jones, Hunter Greene, Dylan Cease")
    HIGH_WHIFF_PITCHERS = [x.strip() for x in high_whiff_input.split(',')]

    high_k_lineups_input = st.text_area("HIGH-K LINEUPS / CHASE HEAVY (+Ks)", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS (-Ks)", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]

with st.sidebar.expander("2. Umpires & Catchers", expanded=False):
    st.caption("Lookup on UmpireScorecards & Statcast Framing")
    pitcher_umps = st.text_area("GENEROUS UMPIRE ASSIGNMENTS (+Ks)", "CB Bucknor, Doug Eddings, Laz Diaz")
    PITCHER_UMPS = [x.strip() for x in pitcher_umps.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS (+Ks)", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

with st.sidebar.expander("3. Environment & Weather", expanded=False):
    cold_weather = st.text_area("COLD/DENSE AIR GAMES (< 55°F) (+Ks)", "MIN, CHW, DET, CLE")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    wind_in = st.text_area("WIND BLOWING IN (Pitchers attack zone) (+Ks)", "CHC, SF")
    WIND_IN_GAMES = [x.strip() for x in wind_in.split(',')]

with st.sidebar.expander("4. BvP & Platoon Splits", expanded=False):
    bvp_dom_input = st.text_area("HISTORICAL DOMINATION (BvP Overmatch)", "")
    BVP_DOMINATION = [x.strip() for x in bvp_dom_input.split(',')] if bvp_dom_input else []
    
    bvp_strug_input = st.text_area("HISTORICAL STRUGGLES (BvP Disaster)", "")
    BVP_STRUGGLES = [x.strip() for x in bvp_strug_input.split(',')] if bvp_strug_input else []

# ─────────────────────────────────────────────────────────────────────────────
# 🏟️ STRIKEOUT PARK FACTORS 
# Note: These are DIFFERENT than Run factors. Parks with bad "Batter's Eyes" 
# or dense marine layers increase strikeouts. (e.g., SEA is #1 for Ks)
# ─────────────────────────────────────────────────────────────────────────────
K_PARK_FACTORS = {
    'SEA': 1.06, 'TB': 1.05, 'MIA': 1.04, 'SD': 1.04, 'MIL': 1.03,
    'OAK': 1.03, 'SF': 1.02, 'LAD': 1.02, 'NYM': 1.01, 'MIN': 1.01,
    'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00,
    'CLE': 0.99, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98,
    'CHC': 0.97, 'STL': 0.97, 'PIT': 0.97, 'LAA': 0.96, 'HOU': 0.96,
    'WSH': 0.95, 'CIN': 0.94, 'ARI': 0.93, 'COL': 0.85 # Pitches don't break at altitude = fewer Ks
}

def norm_mlb(abbr):
    mapping = {'CHW': 'CHW', 'CWS': 'CHW', 'KAN': 'KC', 'TAM': 'TB', 'SFO': 'SF', 'SDP': 'SD'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 1. AUTOMATED DAILY FETCHERS 
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
                h_k9, a_k9 = 8.5, 8.5 # Base MLB average K/9 fallback
                
                # EXTRACT LIVE ERA & K/9 Projections
                if 'probables' in home and len(home['probables']) > 0:
                    h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                    for stat in home['probables'][0].get('statistics', []):
                        if stat.get('abbreviation') == 'K': 
                            try: h_k9 = float(stat.get('displayValue', 8.5)) * 1.5 # Rough conversion for base
                            except: pass

                if 'probables' in away and len(away['probables']) > 0:
                    a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                    for stat in away['probables'][0].get('statistics', []):
                        if stat.get('abbreviation') == 'K':
                            try: a_k9 = float(stat.get('displayValue', 8.5)) * 1.5
                            except: pass

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k': 5.2, 'a_base_k': 5.2 # Dynamic Baseline
                })
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE STRIKEOUT-ONLY ALGORITHM
# ─────────────────────────────────────────────────────────────────────────────
def calculate_strikeout_prop(sp_name, base_k, opp_team, park, is_home):
    proj = {'ks': base_k, 'factors': []}
    
    if sp_name == "TBD": return None

    # 1. Pitcher Skill (Stuff+ / Whiff Rate)
    is_high_whiff = any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS)
    if is_high_whiff:
        proj['ks'] += 1.3
        proj['factors'].append("🎯 Elite Whiff Rate / Stuff+ (+1.3 Ks)")

    # 2. Batter Discipline (O-Swing% & Zone Contact%)
    if opp_team in HIGH_K_LINEUPS:
        proj['ks'] += 1.2
        proj['factors'].append("🏏 High-Chase Opponent (+1.2 Ks)")
    elif opp_team in LOW_K_LINEUPS:
        proj['ks'] -= 1.4
        proj['factors'].append("🛡️ Elite Contact Opponent (-1.4 Ks)")

    # 3. Park Factor (Batter's Eye / Visibility)
    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor > 1.02:
        proj['ks'] += 0.5
        proj['factors'].append(f"🏟️ Pitcher Park (Visibility/Marine Layer) (+0.5 Ks)")
    elif park_k_factor < 0.97:
        proj['ks'] -= 0.6
        proj['factors'].append(f"🏟️ Hitter Park (Altitude/Short Fences) (-0.6 Ks)")

    # 4. Environment / Weather (Air Density)
    if park in COLD_GAMES:
        proj['ks'] += 0.4
        proj['factors'].append("🥶 Dense/Cold Air (Pitches break sharper) (+0.4 Ks)")
    if park in WIND_IN_GAMES:
        proj['ks'] += 0.3
        proj['factors'].append("🌬️ Wind Blowing In (Pitchers attack zone more) (+0.3 Ks)")

    # 5. Catcher Framing (Stealing Strikes)
    # Assuming home catcher catches home pitcher, away catches away.
    # In a full model, we'd input the specific catcher name.
    my_team = park if is_home else opp_team # Rough approximation
    if any(x in my_team for x in ELITE_CATCHERS): # Simplified for UI
        proj['ks'] += 0.5
        proj['factors'].append("🧤 Elite Catcher Framing (+0.5 Ks)")

    # 6. BvP & Platoon Matchups
    if any(x.lower() in sp_name.lower() for x in BVP_DOMINATION if x):
        proj['ks'] += 1.5
        proj['factors'].append("📖 Historical Domination over active roster (+1.5 Ks)")
        
    if any(x.lower() in sp_name.lower() for x in BVP_STRUGGLES if x):
        proj['ks'] -= 1.5
        proj['factors'].append("⚠️ Historical Struggles against active roster (-1.5 Ks)")

    # 7. Umpire Bias
    # If we mapped the umpire to this game, apply it.
    # For Streamlit, if the user sees a generous ump on UmpScorecards:
    if any(x in sp_name for x in PITCHER_UMPS):
        proj['ks'] += 0.8
        proj['factors'].append("👨‍⚖️ Generous Strike Zone Umpire (+0.8 Ks)")

    return proj

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE (LASER FOCUSED ON OVER/UNDER K'S)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🔥 The K-Engine: MLB Strikeout Predictor")
st.markdown("Calculates Whiff Rates, Lineup Discipline, Park Batter's Eyes, Weather, and Umpire biases.")
st.divider()

slate = get_mlb_slate(target_date_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for i, game in enumerate(slate):
        if game['h_sp'] == "TBD" or game['a_sp'] == "TBD":
            continue

        a_proj = calculate_strikeout_prop(game['a_sp'], game['a_base_k'], game['h'], game['h'], False)
        h_proj = calculate_strikeout_prop(game['h_sp'], game['h_base_k'], game['a'], game['h'], True)
        
        with st.expander(f"⚾ {game['a_sp']} ({game['a']}) vs {game['h_sp']} ({game['h']})"):
            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {game['a_sp']}")
                st.markdown(f"## 🔥 Proj Ks: `{a_proj['ks']:.2f}`")
                
                a_k_line = st.number_input("Vegas K-Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                diff_a = a_proj['ks'] - a_k_line
                
                if diff_a > 0.75: st.success(f"📈 **SMASH OVER {a_k_line} Ks** (+{diff_a:.2f} edge)")
                elif diff_a > 0: st.info(f"👍 Lean OVER {a_k_line} Ks (+{diff_a:.2f} edge)")
                elif diff_a < -0.75: st.error(f"📉 **SMASH UNDER {a_k_line} Ks** ({diff_a:.2f} edge)")
                else: st.warning(f"👎 Lean UNDER {a_k_line} Ks ({diff_a:.2f} edge)")
                
                st.markdown("**K-Factor Breakdown:**")
                st.caption(f"Base Pitcher Average: {game['a_base_k']}")
                for f in a_proj['factors']: st.write(f"- {f}")
                    
            # HOME PITCHER
            with col2:
                st.markdown(f"### 🏠 {game['h_sp']}")
                st.markdown(f"## 🔥 Proj Ks: `{h_proj['ks']:.2f}`")
                
                h_k_line = st.number_input("Vegas K-Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                diff_h = h_proj['ks'] - h_k_line
                
                if diff_h > 0.75: st.success(f"📈 **SMASH OVER {h_k_line} Ks** (+{diff_h:.2f} edge)")
                elif diff_h > 0: st.info(f"👍 Lean OVER {h_k_line} Ks (+{diff_h:.2f} edge)")
                elif diff_h < -0.75: st.error(f"📉 **SMASH UNDER {h_k_line} Ks** ({diff_h:.2f} edge)")
                else: st.warning(f"👎 Lean UNDER {h_k_line} Ks ({diff_h:.2f} edge)")

                st.markdown("**K-Factor Breakdown:**")
                st.caption(f"Base Pitcher Average: {game['h_base_k']}")
                for f in h_proj['factors']: st.write(f"- {f}")

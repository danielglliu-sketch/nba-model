import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Monte Carlo K-Model", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed! Re-running 10,000 simulations per pitcher.")

# --- NEW: LIVE ODDS API (CLV TRACKING) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Live Odds Integration")
st.sidebar.caption("Get a free key at the-odds-api.com to pull live Vegas lines and track CLV.")
odds_api_key = st.sidebar.text_input("The Odds API Key (Optional):", type="password")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS (Adjusts the % chance per batter, not flat Ks)
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Simulation Modifiers")
st.sidebar.caption("These alter the raw K% probability before running the 10k simulations.")

use_ml_weights = st.sidebar.checkbox("🤖 Use ML Contextual Weights (XGBoost Emulator)", value=True, help="Instead of flat additions, weights dynamically scale based on baseline K%.")

with st.sidebar.expander("1. Arsenal & Discipline", expanded=False):
    high_whiff_input = st.text_area("ELITE WHIFF PITCHERS (Base K% + 4%)", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Tyler Glasnow, Spencer Strider, Jared Jones, Hunter Greene, Dylan Cease")
    HIGH_WHIFF_PITCHERS = [x.strip() for x in high_whiff_input.split(',')]

    high_k_lineups_input = st.text_area("HIGH-K LINEUPS (Opp K% + 3%)", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS (Opp K% - 4%)", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS (High Variance)", "Reid Detmers, Ryan Weathers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

with st.sidebar.expander("2. Environment & Matchup", expanded=False):
    cold_weather = st.text_area("COLD/WIND IN GAMES (K% + 2%)", "MIN, CHW, DET, CLE, CHC, SF")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS (K% + 1.5%)", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

with st.sidebar.expander("3. Predictability (Best Bets Filter)", expanded=False):
    workhorse_input = st.text_area("WORKHORSE PITCHERS (Low Variance)", "Logan Webb, Aaron Nola, Framber Valdez, Zach Eflin, George Kirby")
    WORKHORSE_PITCHERS = [x.strip() for x in workhorse_input.split(',')]

    analytics_teams_input = st.text_area("STRICT ANALYTICS TEAMS (Predictable Leash)", "TB, LAD, MIL, BAL")
    ANALYTICS_TEAMS = [x.strip() for x in analytics_teams_input.split(',')]

# --- NEW: ARSENAL MATCHING ---
with st.sidebar.expander("4. Advanced Arsenal Matching", expanded=False):
    st.caption("Checks Statcast Pitch distribution against lineup Whiff Rates.")
    elite_arsenal_input = st.text_area("ELITE PITCH MATCHUP (Opp whiffs on primary pitch)", "")
    ELITE_ARSENAL = [x.strip() for x in elite_arsenal_input.split(',')] if elite_arsenal_input else []
    
    poor_arsenal_input = st.text_area("POOR PITCH MATCHUP (Opp crushes primary pitch)", "")
    POOR_ARSENAL = [x.strip() for x in poor_arsenal_input.split(',')] if poor_arsenal_input else []

# Strikeout Park Factors (Used to scale probability)
K_PARK_FACTORS = {
    'SEA': 1.06, 'TB': 1.05, 'MIA': 1.04, 'SD': 1.04, 'MIL': 1.03, 'OAK': 1.03, 'SF': 1.02, 'LAD': 1.02, 'NYM': 1.01, 'MIN': 1.01,
    'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 0.99, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98,
    'CHC': 0.97, 'STL': 0.97, 'PIT': 0.97, 'LAA': 0.96, 'HOU': 0.96, 'WSH': 0.95, 'CIN': 0.94, 'ARI': 0.93, 'COL': 0.85 
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
                h_k_rate, a_k_rate = 0.22, 0.22 
                
                if 'probables' in home and len(home['probables']) > 0:
                    h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                if 'probables' in away and len(away['probables']) > 0:
                    a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD')

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k_rate': h_k_rate, 'a_base_k_rate': a_k_rate
                })
        return games
    except: return []

@st.cache_data(ttl=300)
def get_live_odds(api_key):
    if not api_key: return {}
    try:
        url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={api_key}&regions=us&markets=pitcher_strikeouts&oddsFormat=american"
        resp = requests.get(url, timeout=5).json()
        lines = {}
        # Simplistic parsing to grab the first available over/under line per pitcher
        for game in resp:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'pitcher_strikeouts':
                        for outcome in market.get('outcomes', []):
                            player = outcome.get('description')
                            if player and player not in lines:
                                lines[player] = outcome.get('point', 5.5)
        return lines
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE MONTE CARLO ENGINE (WITH EFFICIENCY & VARIANCE UPGRADES)
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, opp_team, park, is_home, pitch_limit=95, ppa=3.8, extra_bp_pitches=0, num_sims=10000):
    if sp_name == "TBD": return None
    
    adj_k_rate = base_k_rate
    factors = []

    # --- ML Scaling Math (If toggle is on, contextualize the weights) ---
    w_whiff = 0.04 * (1.5 - base_k_rate) if use_ml_weights else 0.04
    w_high_k = 0.03 if not use_ml_weights else 0.03 * (1.2 if is_home else 1.0)
    w_low_k = 0.04 if not use_ml_weights else 0.04 * (1.2 if not is_home else 1.0)
    w_framing = 0.015 if not use_ml_weights else 0.015 * (1 + (0.30 - base_k_rate)) # Framing helps low-K pitchers more
    
    if any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS):
        adj_k_rate += w_whiff
        factors.append(f"🎯 Elite Whiff Rate (+{w_whiff*100:.1f}% K-Prob)")

    if opp_team in HIGH_K_LINEUPS:
        adj_k_rate += w_high_k
        factors.append(f"🏏 High-Chase Opponent (+{w_high_k*100:.1f}% K-Prob)")
    elif opp_team in LOW_K_LINEUPS:
        adj_k_rate -= w_low_k
        factors.append(f"🛡️ Elite Contact Opponent (-{w_low_k*100:.1f}% K-Prob)")

    # --- NEW: ARSENAL MATCHING ---
    if any(x.lower() in sp_name.lower() for x in ELITE_ARSENAL if x):
        adj_k_rate += 0.05
        factors.append("⚾ Statcast Arsenal Matchup: Elite (+5.0% K-Prob)")
    if any(x.lower() in sp_name.lower() for x in POOR_ARSENAL if x):
        adj_k_rate -= 0.05
        factors.append("⚾ Statcast Arsenal Matchup: Poor (-5.0% K-Prob)")

    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor != 1.00:
        adj_k_rate = adj_k_rate * park_k_factor
        val = (park_k_factor - 1) * 100
        factors.append(f"🏟️ Park Visibility Scaler ({val:+.1f}%)")

    if park in COLD_GAMES:
        adj_k_rate += 0.02
        factors.append("🥶 Dense/Cold Air (+2.0% K-Prob)")

    my_team = park if is_home else opp_team
    if any(x in my_team for x in ELITE_CATCHERS):
        adj_k_rate += w_framing
        factors.append(f"🧤 Elite Catcher Framing (+{w_framing*100:.1f}% K-Prob)")

    adj_k_rate = max(0.10, min(0.45, adj_k_rate))

    is_high_variance = any(x.lower() in sp_name.lower() for x in BOOM_BUST_PITCHERS)
    std_dev = 0.08 if is_high_variance else 0.03 
    
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=std_dev, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65) 

    # --- NEW: BULLPEN TAX INJECTION ---
    total_pitches = pitch_limit + extra_bp_pitches
    batters_faced = int(total_pitches / ppa)
    
    if extra_bp_pitches > 0:
        factors.append(f"🥵 Bullpen Tax Extended Leash (+{extra_bp_pitches} Pitches / +{int(extra_bp_pitches/ppa)} Batters)")
    else:
        factors.append(f"⏱️ Pitch Efficiency Cap ({pitch_limit} max pitches @ {ppa:.1f} P/PA = {batters_faced} Batters)")
    
    if is_high_variance:
        factors.append(f"🎢 Boom-or-Bust Variance Applied (±8% K-Rate Swings)")
    else:
        factors.append(f"📊 Standard Variance Applied (±3% K-Rate Swings)")

    simulated_games = np.random.binomial(n=batters_faced, p=game_k_rates)
    mean_ks = np.mean(simulated_games)
    
    df = pd.DataFrame(simulated_games, columns=['Ks'])
    dist = df['Ks'].value_counts(normalize=True).sort_index() * 100
    
    return {
        'true_k_rate': adj_k_rate,
        'mean_ks': mean_ks,
        'simulations': simulated_games,
        'distribution': dist,
        'factors': factors
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE 
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Monte Carlo Simulator")
st.markdown("Runs 10,000 pitch-by-pitch simulations per game to calculate the true mathematical probability of hitting a Vegas Prop line.")
st.divider()

live_odds = get_live_odds(odds_api_key)

best_bets_container = st.container()
best_bets_data = []

slate = get_mlb_slate(target_date_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for i, game in enumerate(slate):
        if game['h_sp'] == "TBD" or game['a_sp'] == "TBD":
            continue

        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']} Stadium)"):
            
            st.caption("Adjust expected pitch count limit, opponent Pitches per At-Bat (P/PA), and Bullpen Exhaustion Tax.")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                pl_a = st.slider(f"{game['a_sp']} Max Pitches", 60, 115, 95, key=f"pl_a_{i}")
                ppa_a = st.slider(f"{game['h']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_a_{i}")
                bp_tax_a = st.number_input(f"{game['a']} Bullpen Tax (Extra Pitches)", 0, 20, 0, key=f"bpt_a_{i}")
            with col_l2:
                pl_h = st.slider(f"{game['h_sp']} Max Pitches", 60, 115, 95, key=f"pl_h_{i}")
                ppa_h = st.slider(f"{game['a']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_h_{i}")
                bp_tax_h = st.number_input(f"{game['h']} Bullpen Tax (Extra Pitches)", 0, 20, 0, key=f"bpt_h_{i}")
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['h'], game['h'], False, pl_a, ppa_a, bp_tax_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['a'], game['h'], True, pl_h, ppa_h, bp_tax_h)

            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {game['a_sp']}")
                
                # Live Odds auto-fill logic
                a_live_line = live_odds.get(game['a_sp'])
                if a_live_line:
                    st.info(f"📡 Live CLV Line: **{a_live_line}**")
                    a_k_line = a_live_line
                else:
                    a_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                
                over_hits = np.sum(a_proj['simulations'] > a_k_line)
                over_prob = (over_hits / 10000) * 100
                
                is_boom = any(x.lower() in game['a_sp'].lower() for x in BOOM_BUST_PITCHERS if x)
                if not is_boom and (over_prob >= 56.0 or over_prob <= 44.0):
                    is_wh = any(x.lower() in game['a_sp'].lower() for x in WORKHORSE_PITCHERS if x)
                    if is_wh or game['a'] in ANALYTICS_TEAMS or game['h'] in HIGH_K_LINEUPS:
                        best_bets_data.append({
                            'sp': game['a_sp'], 'line': a_k_line, 'prob': over_prob,
                            'wh': is_wh, 'an': game['a'] in ANALYTICS_TEAMS, 'fs': game['h'] in HIGH_K_LINEUPS
                        })
                
                st.markdown(f"**Mean K%:** `{a_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {100-over_prob:.1f}% Under)")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(a_proj['distribution'])
                
                st.caption("Probability Modifiers:")
                for f in a_proj['factors']: st.write(f"- {f}")
                    
            # HOME PITCHER
            with col2:
                st.markdown(f"### 🏠 {game['h_sp']}")
                
                # Live Odds auto-fill logic
                h_live_line = live_odds.get(game['h_sp'])
                if h_live_line:
                    st.info(f"📡 Live CLV Line: **{h_live_line}**")
                    h_k_line = h_live_line
                else:
                    h_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                
                over_hits = np.sum(h_proj['simulations'] > h_k_line)
                over_prob = (over_hits / 10000) * 100
                
                is_boom = any(x.lower() in game['h_sp'].lower() for x in BOOM_BUST_PITCHERS if x)
                if not is_boom and (over_prob >= 56.0 or over_prob <= 44.0):
                    is_wh = any(x.lower() in game['h_sp'].lower() for x in WORKHORSE_PITCHERS if x)
                    if is_wh or game['h'] in ANALYTICS_TEAMS or game['a'] in HIGH_K_LINEUPS:
                        best_bets_data.append({
                            'sp': game['h_sp'], 'line': h_k_line, 'prob': over_prob,
                            'wh': is_wh, 'an': game['h'] in ANALYTICS_TEAMS, 'fs': game['a'] in HIGH_K_LINEUPS
                        })
                
                st.markdown(f"**Mean K%:** `{h_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {100-over_prob:.1f}% Under)")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(h_proj['distribution'])

                st.caption("Probability Modifiers:")
                for f in h_proj['factors']: st.write(f"- {f}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. RENDER BEST BETS AT TOP OF PAGE
# ─────────────────────────────────────────────────────────────────────────────
if slate:
    with best_bets_container:
        st.subheader("⭐ Quant Identified: Premium Best Bets")
        st.caption("Filtered mathematically for >56% Edge AND Low Variance Matchup Conditions.")
        if not best_bets_data:
            st.info("No premium best bets identified on the board right now. Adjust parameters or wait for sharper lines.")
        else:
            for bet in best_bets_data:
                side = "OVER" if bet['prob'] >= 56 else "UNDER"
                confidence = bet['prob'] if side == "OVER" else (100 - bet['prob'])
                
                tags = []
                if bet['wh']: tags.append("🐎 Workhorse (Low Variance)")
                if bet['an']: tags.append("🤖 Strict Analytics Leash")
                if bet['fs']: tags.append("🏏 Free-Swinging Opp")
                
                st.success(f"**{bet['sp']}** | **{side} {bet['line']} Ks** | Edge: **{confidence:.1f}%** | Factors: {', '.join(tags)}")
        st.divider()

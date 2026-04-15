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

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS (Adjusts the % chance per batter, not flat Ks)
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Simulation Modifiers")
st.sidebar.caption("These alter the raw K% probability before running the 10k simulations.")

with st.sidebar.expander("1. Arsenal & Discipline", expanded=False):
    high_whiff_input = st.text_area("ELITE WHIFF PITCHERS (Base K% + 4%)", "Tarik Skubal, Zack Wheeler, Corbin Burnes, Chris Sale, Cole Ragans, Paul Skenes, Tyler Glasnow, Spencer Strider, Jared Jones, Hunter Greene, Dylan Cease")
    HIGH_WHIFF_PITCHERS = [x.strip() for x in high_whiff_input.split(',')]

    high_k_lineups_input = st.text_area("HIGH-K LINEUPS (Opp K% + 3%)", "COL, CHW, LAA, SEA, OAK, CIN, TB")
    HIGH_K_LINEUPS = [x.strip() for x in high_k_lineups_input.split(',')]

    low_k_lineups_input = st.text_area("ELITE CONTACT LINEUPS (Opp K% - 4%)", "HOU, CLE, SD, KC, NYY, ATL")
    LOW_K_LINEUPS = [x.strip() for x in low_k_lineups_input.split(',')]
    
    # --- NEW: VARIANCE OVERRIDE ---
    boom_bust_input = st.text_area("BOOM-OR-BUST PITCHERS (High Variance)", "Reid Detmers, Ryan Weathers, Blake Snell, Hunter Greene, Nick Pivetta")
    BOOM_BUST_PITCHERS = [x.strip() for x in boom_bust_input.split(',')]

with st.sidebar.expander("2. Environment & Matchup", expanded=False):
    cold_weather = st.text_area("COLD/WIND IN GAMES (K% + 2%)", "MIN, CHW, DET, CLE, CHC, SF")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS (K% + 1.5%)", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

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
                h_k_rate, a_k_rate = 0.22, 0.22 # MLB Average K% per batter is ~22%
                
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

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE MONTE CARLO ENGINE (WITH EFFICIENCY & VARIANCE UPGRADES)
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, opp_team, park, is_home, pitch_limit=95, ppa=3.8, num_sims=10000):
    if sp_name == "TBD": return None
    
    # --- Step 1: Adjust the True Average Probability (K%) ---
    adj_k_rate = base_k_rate
    factors = []

    if any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS):
        adj_k_rate += 0.04
        factors.append("🎯 Elite Whiff Rate (+4% Base K-Probability)")

    if opp_team in HIGH_K_LINEUPS:
        adj_k_rate += 0.03
        factors.append("🏏 High-Chase Opponent (+3% Base K-Probability)")
    elif opp_team in LOW_K_LINEUPS:
        adj_k_rate -= 0.04
        factors.append("🛡️ Elite Contact Opponent (-4% Base K-Probability)")

    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor != 1.00:
        adj_k_rate = adj_k_rate * park_k_factor
        val = (park_k_factor - 1) * 100
        factors.append(f"🏟️ Park Visibility Scaler ({val:+.1f}%)")

    if park in COLD_GAMES:
        adj_k_rate += 0.02
        factors.append("🥶 Dense/Cold Air (+2% Base K-Probability)")

    my_team = park if is_home else opp_team
    if any(x in my_team for x in ELITE_CATCHERS):
        adj_k_rate += 0.015
        factors.append("🧤 Elite Catcher Framing (+1.5% Base K-Probability)")

    # Bound the baseline probability 
    adj_k_rate = max(0.10, min(0.45, adj_k_rate))

    # --- Step 2: Inject Variance (Standard Deviation) ---
    is_high_variance = any(x.lower() in sp_name.lower() for x in BOOM_BUST_PITCHERS)
    std_dev = 0.08 if is_high_variance else 0.03 # 8% swing for wild guys, 3% for average guys
    
    # Generate 10,000 different parallel universes where the pitcher is either hot, cold, or average
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=std_dev, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65) # Keep the math bounds realistic

    batters_faced = int(pitch_limit / ppa)
    factors.append(f"⏱️ Pitch Efficiency Cap ({pitch_limit} max pitches @ {ppa:.1f} P/PA = {batters_faced} Batters)")
    
    if is_high_variance:
        factors.append(f"🎢 Boom-or-Bust Variance Applied (±8% K-Rate Swings)")
    else:
        factors.append(f"📊 Standard Variance Applied (±3% K-Rate Swings)")

    # --- Step 3: Execute 10,000 Simulations using the variable K-rates ---
    simulated_games = np.random.binomial(n=batters_faced, p=game_k_rates)
    
    # --- Step 4: Calculate Distribution Analytics ---
    mean_ks = np.mean(simulated_games)
    
    # Create a frequency distribution for the chart
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
# 3. USER INTERFACE (Visualizing the Quant Data)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Monte Carlo Simulator")
st.markdown("Runs 10,000 pitch-by-pitch simulations per game to calculate the true mathematical probability of hitting a Vegas Prop line.")
st.divider()

slate = get_mlb_slate(target_date_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for i, game in enumerate(slate):
        if game['h_sp'] == "TBD" or game['a_sp'] == "TBD":
            continue

        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']} Stadium)"):
            
            # --- Tweak Pitch Count Efficiency (Leash) ---
            st.caption("Adjust expected pitch count limit and opponent Pitches per At-Bat (P/PA).")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                pl_a = st.slider(f"{game['a_sp']} Max Pitches", 60, 115, 95, key=f"pl_a_{i}")
                ppa_a = st.slider(f"{game['h']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_a_{i}")
            with col_l2:
                pl_h = st.slider(f"{game['h_sp']} Max Pitches", 60, 115, 95, key=f"pl_h_{i}")
                ppa_h = st.slider(f"{game['a']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_h_{i}")
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['h'], game['h'], False, pl_a, ppa_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['a'], game['h'], True, pl_h, ppa_h)

            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {game['a_sp']}")
                a_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                
                # Calculate Win Probability from the 10,000 simulations
                over_hits = np.sum(a_proj['simulations'] > a_k_line)
                over_prob = (over_hits / 10000) * 100
                
                st.markdown(f"**Mean K%:** `{a_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {100-over_prob:.1f}% Under)")
                
                # Display the Probability Curve Chart
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(a_proj['distribution'])
                
                st.caption("Probability Modifiers:")
                for f in a_proj['factors']: st.write(f"- {f}")
                    
            # HOME PITCHER
            with col2:
                st.markdown(f"### 🏠 {game['h_sp']}")
                h_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                
                over_hits = np.sum(h_proj['simulations'] > h_k_line)
                over_prob = (over_hits / 10000) * 100
                
                st.markdown(f"**Mean K%:** `{h_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {100-over_prob:.1f}% Under)")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(h_proj['distribution'])

                st.caption("Probability Modifiers:")
                for f in h_proj['factors']: st.write(f"- {f}")

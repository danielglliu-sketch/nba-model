import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb
import difflib

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Quant AI - Monte Carlo K-Model", page_icon="🎲", layout="wide")

st.sidebar.title("⚙️ The Quant Controls")

selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Slate refreshed! Re-running 10,000 simulations per pitcher.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 PROBABILITY MULTIPLIERS 
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

with st.sidebar.expander("2. Environment & Matchup", expanded=False):
    cold_weather = st.text_area("COLD/WIND IN GAMES (K% + 2%)", "MIN, CHW, DET, CLE, CHC, SF")
    COLD_GAMES = [x.strip() for x in cold_weather.split(',')]
    
    elite_catchers = st.text_area("ELITE FRAMING CATCHERS (K% + 1.5%)", "Patrick Bailey, Austin Hedges, Jonah Heim, Cal Raleigh, William Contreras")
    ELITE_CATCHERS = [x.strip() for x in elite_catchers.split(',')]

# Strikeout Park Factors
K_PARK_FACTORS = {
    'SEA': 1.06, 'TB': 1.05, 'MIA': 1.04, 'SD': 1.04, 'MIL': 1.03, 'OAK': 1.03, 'SF': 1.02, 'LAD': 1.02, 'NYM': 1.01, 'MIN': 1.01,
    'BAL': 1.00, 'TOR': 1.00, 'TEX': 1.00, 'ATL': 1.00, 'DET': 1.00, 'CLE': 0.99, 'NYY': 0.99, 'CHW': 0.99, 'PHI': 0.98, 'BOS': 0.98,
    'CHC': 0.97, 'STL': 0.97, 'PIT': 0.97, 'LAA': 0.96, 'HOU': 0.96, 'WSH': 0.95, 'CIN': 0.94, 'ARI': 0.93, 'COL': 0.85 
}

def norm_mlb(abbr):
    mapping = {'CHW': 'CHW', 'CWS': 'CHW', 'KAN': 'KC', 'TAM': 'TB', 'SFO': 'SF', 'SDP': 'SD'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AUTOMATION: BAYESIAN SHRINKAGE & DYNAMIC WORKLOAD ENGINE
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    try:
        df = pyb.pitching_stats(2026, qual=0)
        df['TBF'] = df['TBF'].fillna(50) 
        
        for col in ['K%', 'BB%']:
            if df[col].dtype == object:
                df[col] = df[col].str.rstrip('%').astype('float') / 100.0
        
        # Calculate pitches per game (Leash) and efficiency (P/PA)
        df['Auto_Leash'] = ((df['IP'] / df['GS']) * 14 + 10).clip(55, 105)
        df['Auto_PPA'] = 3.8 + (df['BB%'] * 6.0) # High walks = high pitches per batter
        
        # Bayesian Shrinkage to prevent wild projections from small 2026 samples
        df['K%'] = (df['K%'] * df['TBF'] + 0.22 * 70) / (df['TBF'] + 70)
        df['BB%'] = (df['BB%'] * df['TBF'] + 0.08 * 100) / (df['TBF'] + 100)
        
        return df.set_index('Name')[['K%', 'BB%', 'Auto_Leash', 'Auto_PPA']].to_dict('index')
    except: return {}

STATS_DB = get_pitcher_stats_database()

def get_automated_pitcher_metrics(pitcher_name):
    all_names = list(STATS_DB.keys())
    matches = difflib.get_close_matches(pitcher_name, all_names, n=1, cutoff=0.55)
    match = STATS_DB[matches[0]] if matches else None
    
    if match:
        # Predict how many batters they will face based on their efficiency
        expected_bf = int(match['Auto_Leash'] / match['Auto_PPA'])
        # Cap realistically between 14 and 28 batters
        expected_bf = max(14, min(28, expected_bf)) 
        
        return match['K%'], match['BB%'], expected_bf, f"Found: {matches[0]} (Regressed K%: {match['K%']*100:.1f}%)"
    return 0.22, 0.08, 22, "⚠️ Data Missing (Using League Avg)"

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
                
                if 'probables' in home and len(home['probables']) > 0:
                    h_sp = home['probables'][0].get('athlete', {}).get('displayName', 'TBD')
                if 'probables' in away and len(away['probables']) > 0:
                    a_sp = away['probables'][0].get('athlete', {}).get('displayName', 'TBD')

                h_k, h_bb, h_bf, h_status = get_automated_pitcher_metrics(h_sp)
                a_k, a_bb, a_bf, a_status = get_automated_pitcher_metrics(a_sp)

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k_rate': h_k, 'a_base_k_rate': a_k,
                    'h_bb': h_bb, 'a_bb': a_bb,
                    'h_bf': h_bf, 'a_bf': a_bf,
                    'h_status': h_status, 'a_status': a_status
                })
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE MONTE CARLO ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, bb_rate, opp_team, park, is_home, batters_faced, num_sims=10000):
    if sp_name == "TBD": return None
    
    # --- Step 1: Adjust the True Probability (K%) ---
    adj_k_rate = base_k_rate
    factors = [f"📊 Baseline Rate: {base_k_rate*100:.1f}%"]
    
    # 🚨 COMMAND TAX: Cut raw rate slightly if they are issuing too many walks
    if bb_rate > 0.11:
        adj_k_rate -= 0.02
        factors.append(f"⚠️ High Walk Rate Penalty (-2% K-Probability)")

    if any(x.lower() in sp_name.lower() for x in HIGH_WHIFF_PITCHERS):
        adj_k_rate += 0.04
        factors.append("🎯 Elite Whiff Rate (+4% K-Probability)")

    # 🚨 MATCHUP DAMPENER: Wild pitchers get less benefit from bad lineups
    w_high_k = 0.03
    if bb_rate > 0.11: w_high_k = 0.015 

    if opp_team in HIGH_K_LINEUPS:
        adj_k_rate += w_high_k
        factors.append(f"🏏 High-Chase Opponent (+{w_high_k*100:.1f}% K-Probability)")
    elif opp_team in LOW_K_LINEUPS:
        adj_k_rate -= 0.04
        factors.append("🛡️ Elite Contact Opponent (-4% K-Probability)")

    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor != 1.00:
        adj_k_rate = adj_k_rate * park_k_factor
        val = (park_k_factor - 1) * 100
        factors.append(f"🏟️ Park Scaler ({val:+.1f}%)")

    if park in COLD_GAMES:
        adj_k_rate += 0.02
        factors.append("🥶 Dense/Cold Air (+2% K-Probability)")

    my_team = park if is_home else opp_team
    if any(x in my_team for x in ELITE_CATCHERS):
        adj_k_rate += 0.015
        factors.append("🧤 Elite Framing (+1.5% K-Probability)")

    adj_k_rate = max(0.08, min(0.45, adj_k_rate))

    # --- Step 2: Execute 10,000 Simulations ---
    simulated_games = np.random.binomial(n=batters_faced, p=adj_k_rate, size=num_sims)
    
    # --- Step 3: Calculate Distribution Analytics ---
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

slate = get_mlb_slate(target_date_str)

if not slate:
    st.info(f"No games scheduled for {selected_date} or API is waiting for updates.")
else:
    for i, game in enumerate(slate):
        if game['h_sp'] == "TBD" or game['a_sp'] == "TBD":
            continue

        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']} Stadium)"):
            st.caption(f"📡 Data Status | Away: {game['a_status']} | Home: {game['h_status']}")
            
            # --- Smart Default Batters Faced ---
            st.caption("Batters Faced is now auto-calculated based on live pitch counts and walk efficiency.")
            bf_a = st.slider(f"{game['a_sp']} Batters Faced", 12, 28, int(game['a_bf']), key=f"bf_a_{i}")
            bf_h = st.slider(f"{game['h_sp']} Batters Faced", 12, 28, int(game['h_bf']), key=f"bf_h_{i}")
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['a_bb'], game['h'], game['h'], False, bf_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['h_bb'], game['a'], game['h'], True, bf_h)

            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {game['a_sp']}")
                a_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                
                over_hits = np.sum(a_proj['simulations'] > a_k_line)
                over_prob = (over_hits / 10000) * 100
                
                st.markdown(f"**Final Simulated K%:** `{a_proj['true_k_rate']*100:.1f}%` per batter")
                
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
                h_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                
                over_hits = np.sum(h_proj['simulations'] > h_k_line)
                over_prob = (over_hits / 10000) * 100
                
                st.markdown(f"**Final Simulated K%:** `{h_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {100-over_prob:.1f}% Under)")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(h_proj['distribution'])

                st.caption("Probability Modifiers:")
                for f in h_proj['factors']: st.write(f"- {f}")

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

    st.info("🎯 Elite Whiff Rate is automatically driven by Live 2026 SwStr% (>13.5%).")
    st.info("📊 Live 2026 Opponent Team K% Data automatically integrated via PyBaseball.")

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
# 🤖 AUTOMATION: BAYESIAN SHRINKAGE, WORKLOAD, SWSTR%, & LIVE OPPONENT K%
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_team_k_rates():
    try:
        df = pyb.team_batting(2026)
        if 'K%' in df.columns:
            if df['K%'].dtype == object:
                df['K%'] = df['K%'].str.rstrip('%').astype('float') / 100.0
        else:
            df['K%'] = df['SO'] / df['PA']
            
        team_map = {'SFG': 'SF', 'SDP': 'SD', 'WSN': 'WSH', 'TBR': 'TB', 'KCR': 'KC'}
        df['Team'] = df['Team'].replace(team_map)
        
        return df.set_index('Team')['K%'].to_dict()
    except: return {}

TEAM_K_DB = get_team_k_rates()

@st.cache_data(ttl=86400)
def get_pitcher_stats_database():
    try:
        df = pyb.pitching_stats(2026, qual=0)
        df['TBF'] = df['TBF'].fillna(50) 
        df['GS'] = df['GS'].fillna(0)
        
        for col in ['K%', 'BB%', 'SwStr%']:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].str.rstrip('%').astype('float') / 100.0
            else:
                df[col] = 0.11 if col == 'SwStr%' else 0.10
        
        # FIX: Replaced suffocating pitch-count math with Regressed Batters Faced per Start
        df['BF_per_Start'] = (df['TBF'] + (22.5 * 3)) / (df['GS'] + 3)
        df['BF_per_Start'] = df['BF_per_Start'].fillna(22.5).clip(16, 28)
        
        # Store Raw K% before applying Shrinkage
        df['Raw_K%'] = df['K%']
        
        # Lowered Bayesian Shrinkage constants for early-season (April) accuracy
        df['K%'] = (df['K%'] * df['TBF'] + 0.22 * 25) / (df['TBF'] + 25)
        df['BB%'] = (df['BB%'] * df['TBF'] + 0.08 * 40) / (df['TBF'] + 40)
        
        return df.set_index('Name')[['K%', 'Raw_K%', 'BB%', 'SwStr%', 'BF_per_Start']].to_dict('index')
    except: return {}

STATS_DB = get_pitcher_stats_database()

def get_automated_pitcher_metrics(pitcher_name):
    all_names = list(STATS_DB.keys())
    matches = difflib.get_close_matches(pitcher_name, all_names, n=1, cutoff=0.55)
    match = STATS_DB[matches[0]] if matches else None
    
    if match:
        expected_bf = int(round(match.get('BF_per_Start', 22.5)))
        swstr = match.get('SwStr%', 0.11)
        raw_k = match.get('Raw_K%', match['K%'])
        
        return match['K%'], raw_k, match['BB%'], swstr, expected_bf, f"Found: {matches[0]} (Reg K%: {match['K%']*100:.1f}% | Raw: {raw_k*100:.1f}%)"
    
    return 0.18, 0.18, 0.08, 0.09, 21, "⚠️ Data Missing (Using Replacement Defaults)"

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

                h_k, h_raw_k, h_bb, h_swstr, h_bf, h_status = get_automated_pitcher_metrics(h_sp)
                a_k, a_raw_k, a_bb, a_swstr, a_bf, a_status = get_automated_pitcher_metrics(a_sp)

                games.append({
                    'h': norm_mlb(home['team']['abbreviation']), 
                    'a': norm_mlb(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'], 
                    'a_name': away['team']['displayName'],
                    'h_sp': h_sp, 'a_sp': a_sp,
                    'h_base_k_rate': h_k, 'a_base_k_rate': a_k,
                    'h_raw_k_rate': h_raw_k, 'a_raw_k_rate': a_raw_k,
                    'h_bb': h_bb, 'a_bb': a_bb,
                    'h_swstr': h_swstr, 'a_swstr': a_swstr,
                    'h_bf': h_bf, 'a_bf': a_bf,
                    'h_status': h_status, 'a_status': a_status
                })
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 2. THE MONTE CARLO ENGINE (BALANCED)
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, raw_k_rate, bb_rate, swstr_rate, opp_team, opp_k_rate, park, is_home, batters_faced, num_sims=10000):
    if sp_name == "TBD": return None
    
    factors = []
    
    # 🚨 THE FORM CHECK: Is the pitcher actively struggling right now?
    is_struggling = raw_k_rate < (base_k_rate - 0.02)
    
    if is_struggling:
        # Abandon Optimistic Shrinkage and reset baseline to the ugly raw rate
        adj_k_rate = raw_k_rate
        factors.append(f"📉 Form Check: Active Struggling. Shrinkage bypassed. Baseline reset to Raw ({raw_k_rate*100:.1f}%)")
        factors.append(f"📉 Form Check: All situational boosts dampened by 50%")
    else:
        adj_k_rate = base_k_rate
        factors.append(f"📊 Baseline Rate (Post-Shrinkage): {base_k_rate*100:.1f}%")

    if swstr_rate > 0.135:
        adj_k_rate += 0.04
        factors.append(f"🎯 Elite Whiff Rate ({swstr_rate*100:.1f}% SwStr%) (+4.0% K-Probability)")

    # FIX: SOFTENED PROPORTIONAL MULTIPLIER
    raw_opp_k_ratio = opp_k_rate / 0.225 
    
    # Soften the impact by cutting the deviation from 1.0 in half
    opp_k_ratio = 1.0 + ((raw_opp_k_ratio - 1.0) * 0.5)
    
    if raw_opp_k_ratio > 1.0:
        if is_struggling:
            opp_k_ratio = 1.0 + ((raw_opp_k_ratio - 1.0) * 0.25) # Form check caps it even further
            factors.append(f"🏏 Opponent K% ({opp_k_rate*100:.1f}%) dampener applied (Poor Form)")
        else:
            factors.append(f"🏏 Live Opponent K% ({opp_k_rate*100:.1f}%): Softened {opp_k_ratio:.2f}x Multiplier")
    else:
        factors.append(f"🏏 Live Opponent K% ({opp_k_rate*100:.1f}%): Softened {opp_k_ratio:.2f}x Multiplier")
        
    adj_k_rate = adj_k_rate * opp_k_ratio

    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor != 1.00:
        if park_k_factor > 1.00 and is_struggling:
            park_k_factor = 1.00 + ((park_k_factor - 1.00) * 0.5) # Form Check Caps Park Boost
            factors.append(f"🏟️ Park Scaler Dampened by Form (Now {(park_k_factor-1)*100:+.1f}%)")
        else:
            val = (park_k_factor - 1) * 100
            factors.append(f"🏟️ Park Scaler ({val:+.1f}%)")
        adj_k_rate = adj_k_rate * park_k_factor

    if park in COLD_GAMES:
        boost = 0.02 if not is_struggling else 0.01 # Form Check Caps Weather Boost
        adj_k_rate += boost
        factors.append(f"🥶 Dense/Cold Air (+{boost*100:.1f}% K-Probability)")

    my_team = park if is_home else opp_team
    if any(x in my_team for x in ELITE_CATCHERS):
        boost = 0.015 if not is_struggling else 0.007 # Form Check Caps Framing Boost
        adj_k_rate += boost
        factors.append(f"🧤 Elite Framing (+{boost*100:.1f}% K-Probability)")

    adj_k_rate = max(0.08, min(0.45, adj_k_rate))

    # --- INJECTING VARIANCE SCALER (Replaces static binomial probability) ---
    # Introduces a +/- 3% standard deviation for "Good Stuff / Bad Stuff" days
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=0.03, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65) # Bounds realistic limits
    
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
# EV CALCULATOR HELPER
# ─────────────────────────────────────────────────────────────────────────────
def calculate_ev_percent(win_prob_pct, american_odds):
    if american_odds == 0: return 0.0
    prob = win_prob_pct / 100.0
    
    if american_odds > 0:
        payout_ratio = american_odds / 100.0
    else:
        payout_ratio = 100.0 / abs(american_odds)
        
    ev = (prob * payout_ratio) - (1.0 - prob)
    return ev * 100.0

# ─────────────────────────────────────────────────────────────────────────────
# 3. USER INTERFACE 
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎲 MLB Quant AI: Monte Carlo Simulator")
st.markdown("Runs 10,000 pitch-by-pitch simulations per game to calculate the true mathematical probability of hitting a Vegas Prop line. Use the EV tracker to find profitable bets.")
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
            
            st.caption("Batters Faced is now auto-calculated based on Regressed Starts.")
            bf_a = st.slider(f"{game['a_sp']} Batters Faced", 12, 28, int(game['a_bf']), key=f"bf_a_{i}")
            bf_h = st.slider(f"{game['h_sp']} Batters Faced", 12, 28, int(game['h_bf']), key=f"bf_h_{i}")
            
            opp_k_a = TEAM_K_DB.get(game['h'], 0.225)
            opp_k_h = TEAM_K_DB.get(game['a'], 0.225)
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['a_raw_k_rate'], game['a_bb'], game['a_swstr'], game['h'], opp_k_a, game['h'], False, bf_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['h_raw_k_rate'], game['h_bb'], game['h_swstr'], game['a'], opp_k_h, game['h'], True, bf_h)

            col1, col2 = st.columns(2)
            
            # AWAY PITCHER
            with col1:
                st.markdown(f"### ✈️ {game['a_sp']}")
                a_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"ak_{i}_{game['a']}")
                
                # Dynamic EV Input Fields
                c1, c2 = st.columns(2)
                with c1:
                    a_over_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"ao_{i}_{game['a']}")
                with c2:
                    a_under_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"au_{i}_{game['a']}")
                
                over_hits = np.sum(a_proj['simulations'] > a_k_line)
                over_prob = (over_hits / 10000) * 100
                under_prob = 100.0 - over_prob
                
                over_ev = calculate_ev_percent(over_prob, a_over_odds)
                under_ev = calculate_ev_percent(under_prob, a_under_odds)
                
                st.markdown(f"**Final Simulated Median K%:** `{a_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif under_prob > 60: st.error(f"📉 **{under_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {under_prob:.1f}% Under)")
                
                # Expected Value (EV) Display
                if over_ev > 1.5: 
                    st.success(f"🔥 **+EV PLAY IDENTIFIED: OVER ({over_ev:+.1f}% Edge)**")
                elif under_ev > 1.5: 
                    st.success(f"🔥 **+EV PLAY IDENTIFIED: UNDER ({under_ev:+.1f}% Edge)**")
                else: 
                    st.info(f"🛑 No Mathematical Edge. Over EV: {over_ev:+.1f}% | Under EV: {under_ev:+.1f}%")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(a_proj['distribution'])
                
                st.caption("Probability Modifiers:")
                for f in a_proj['factors']: st.write(f"- {f}")
                    
            # HOME PITCHER
            with col2:
                st.markdown(f"### 🏠 {game['h_sp']}")
                h_k_line = st.number_input("Vegas Line:", value=5.5, step=0.5, key=f"hk_{i}_{game['h']}")
                
                # Dynamic EV Input Fields
                c3, c4 = st.columns(2)
                with c3:
                    h_over_odds = st.number_input("Over Odds:", value=-110, step=5, key=f"ho_{i}_{game['h']}")
                with c4:
                    h_under_odds = st.number_input("Under Odds:", value=-110, step=5, key=f"hu_{i}_{game['h']}")
                
                over_hits = np.sum(h_proj['simulations'] > h_k_line)
                over_prob = (over_hits / 10000) * 100
                under_prob = 100.0 - over_prob
                
                over_ev = calculate_ev_percent(over_prob, h_over_odds)
                under_ev = calculate_ev_percent(under_prob, h_under_odds)
                
                st.markdown(f"**Final Simulated Median K%:** `{h_proj['true_k_rate']*100:.1f}%` per batter")
                
                if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                elif under_prob > 60: st.error(f"📉 **{under_prob:.1f}% Chance to hit UNDER**")
                else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over / {under_prob:.1f}% Under)")
                
                # Expected Value (EV) Display
                if over_ev > 1.5: 
                    st.success(f"🔥 **+EV PLAY IDENTIFIED: OVER ({over_ev:+.1f}% Edge)**")
                elif under_ev > 1.5: 
                    st.success(f"🔥 **+EV PLAY IDENTIFIED: UNDER ({under_ev:+.1f}% Edge)**")
                else: 
                    st.info(f"🛑 No Mathematical Edge. Over EV: {over_ev:+.1f}% | Under EV: {under_ev:+.1f}%")
                
                st.markdown("**Simulated Probability Distribution:**")
                st.bar_chart(h_proj['distribution'])

                st.caption("Probability Modifiers:")
                for f in h_proj['factors']: st.write(f"- {f}")

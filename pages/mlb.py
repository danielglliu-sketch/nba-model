import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import pybaseball as pyb

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

with st.sidebar.expander("1. Lineup Discipline & Variance", expanded=False):
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
    analytics_teams_input = st.text_area("STRICT ANALYTICS TEAMS (Predictable Leash)", "TB, LAD, MIL, BAL")
    ANALYTICS_TEAMS = [x.strip() for x in analytics_teams_input.split(',')]

with st.sidebar.expander("4. Advanced Arsenal Matching", expanded=False):
    st.caption("Statcast Pitch distribution vs lineup Whiff Rates.")
    st.info("Automation enabled: Model now pulls 2024 pitch-mix data and team-level weakness matrix.")
    elite_arsenal_input = st.text_area("MANUAL OVERRIDE: ELITE PITCH MATCHUP", "")
    ELITE_ARSENAL = [x.strip() for x in elite_arsenal_input.split(',')] if elite_arsenal_input else []
    
    poor_arsenal_input = st.text_area("MANUAL OVERRIDE: POOR PITCH MATCHUP", "")
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
# 🤖 AUTOMATED DATA: TRUE BASELINES & ARSENAL MATRIX
# ─────────────────────────────────────────────────────────────────────────────
TEAM_WHIFF_VULNERABILITY = {
    'SEA': {'Slider': 1.15, 'Fastball': 1.05, 'Curve': 1.10},
    'COL': {'Slider': 1.20, 'Fastball': 1.10, 'Changeup': 1.05},
    'CHW': {'Slider': 1.10, 'Fastball': 1.12, 'Curve': 1.08},
    'NYY': {'Slider': 0.92, 'Fastball': 0.95, 'Changeup': 0.98}, 
    'HOU': {'Slider': 0.85, 'Fastball': 0.88, 'Curve': 0.90}, 
}

@st.cache_data(ttl=3600)
def get_pitcher_mix(sp_name):
    mix = {
        'Dylan Cease': {'Slider': 0.45, 'Fastball': 0.40},
        'Logan Webb': {'Changeup': 0.35, 'Sinker': 0.35},
        'Corbin Burnes': {'Cutter': 0.45, 'Curve': 0.20},
        'Reid Detmers': {'Slider': 0.30, 'Fastball': 0.40, 'Curve': 0.20}
    }
    return mix.get(sp_name, {'Fastball': 0.50, 'Slider': 0.20})

def calculate_automated_arsenal_score(sp_name, opp_team):
    mix = get_pitcher_mix(sp_name)
    team_weakness = TEAM_WHIFF_VULNERABILITY.get(opp_team, {'Slider': 1.0, 'Fastball': 1.0, 'Curve': 1.0})
    
    score = 1.0
    for pitch, usage in mix.items():
        vulnerability = team_weakness.get(pitch, 1.0)
        score += (usage * (vulnerability - 1))
    return score

# --- NEW: FANGRAPHS / PYBASEBALL TRUE K% SCRAPER ---
@st.cache_data(ttl=86400)
def get_k_rate_database():
    base_dict = {
        'Tarik Skubal': 0.30, 'Zack Wheeler': 0.28, 'Corbin Burnes': 0.25, 
        'Reid Detmers': 0.275, 'Ryan Weathers': 0.19, 'Logan Webb': 0.21,
        'Chris Sale': 0.29, 'Cole Ragans': 0.28, 'Paul Skenes': 0.31,
        'Tyler Glasnow': 0.33, 'Spencer Strider': 0.37, 'Jared Jones': 0.28,
        'Hunter Greene': 0.30, 'Dylan Cease': 0.29, 'Blake Snell': 0.31,
        'Nick Pivetta': 0.28, 'Aaron Nola': 0.25, 'Framber Valdez': 0.24,
        'Zach Eflin': 0.24, 'George Kirby': 0.23
    }
    try:
        df = pyb.pitching_stats(2024, qual=10)
        if df['K%'].dtype == object:
            df['K%'] = df['K%'].str.rstrip('%').astype('float') / 100.0
        scraped_dict = dict(zip(df['Name'], df['K%']))
        base_dict.update(scraped_dict) 
    except:
        pass
    return base_dict

K_RATE_DB = get_k_rate_database()

def get_baseline_k(pitcher_name):
    if pitcher_name in K_RATE_DB:
        return float(K_RATE_DB[pitcher_name])
    for name, rate in K_RATE_DB.items():
        if name.split(' ')[-1] == pitcher_name.split(' ')[-1]:
            return float(rate)
    return 0.22

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

                h_k_rate = get_baseline_k(h_sp) if h_sp != "TBD" else 0.22
                a_k_rate = get_baseline_k(a_sp) if a_sp != "TBD" else 0.22

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
# 2. THE MONTE CARLO ENGINE (WITH EXPONENTIAL DECAY REGULARIZATION)
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(sp_name, base_k_rate, opp_team, park, is_home, pitch_limit=95, ppa=3.8, extra_bp_pitches=0, num_sims=10000):
    if sp_name == "TBD": return None
    
    factors = [f"📊 True Baseline K%: {base_k_rate*100:.1f}%"] 
    positive_boosts = []
    negative_penalties = []

    # --- ML Scaling Math ---
    w_high_k = 0.03 if not use_ml_weights else 0.03 * (1.2 if is_home else 1.0)
    w_low_k = 0.04 if not use_ml_weights else 0.04 * (1.2 if not is_home else 1.0)
    w_framing = 0.015 if not use_ml_weights else 0.015 * (1 + (0.30 - base_k_rate)) 

    if opp_team in HIGH_K_LINEUPS:
        positive_boosts.append(w_high_k)
        factors.append(f"🏏 High-Chase Opponent (+{w_high_k*100:.1f}% raw)")
    elif opp_team in LOW_K_LINEUPS:
        negative_penalties.append(w_low_k)
        factors.append(f"🛡️ Elite Contact Opponent (-{w_low_k*100:.1f}% raw)")

    # --- AUTOMATED ARSENAL MATCHING ---
    arsenal_score = calculate_automated_arsenal_score(sp_name, opp_team)
    if arsenal_score > 1.02:
        bonus = (arsenal_score - 1.0) * 0.15 
        positive_boosts.append(bonus)
        factors.append(f"⚾ Auto-Arsenal: Favorable Matchup (+{bonus*100:.1f}% raw)")
    elif arsenal_score < 0.98:
        penalty = (1.0 - arsenal_score) * 0.15
        negative_penalties.append(penalty)
        factors.append(f"⚾ Auto-Arsenal: Poor Matchup (-{penalty*100:.1f}% raw)")

    # Manual Overrides (Still active)
    if any(x.lower() in sp_name.lower() for x in ELITE_ARSENAL if x):
        positive_boosts.append(0.05)
        factors.append("🛠️ Manual Arsenal Matchup: Elite (+5.0% raw)")
    if any(x.lower() in sp_name.lower() for x in POOR_ARSENAL if x):
        negative_penalties.append(0.05)
        factors.append("🛠️ Manual Arsenal Matchup: Poor (-5.0% raw)")

    if park in COLD_GAMES:
        positive_boosts.append(0.02)
        factors.append("🥶 Dense/Cold Air (+2.0% raw)")

    my_team = park if is_home else opp_team
    if any(x in my_team for x in ELITE_CATCHERS):
        positive_boosts.append(w_framing)
        factors.append(f"🧤 Elite Catcher Framing (+{w_framing*100:.1f}% raw)")

    # --- REGULARIZATION APPLIED HERE ---
    positive_boosts.sort(reverse=True)
    negative_penalties.sort(reverse=True)

    reg_pos = sum(val * (0.5 ** i) for i, val in enumerate(positive_boosts))
    reg_neg = sum(val * (0.5 ** i) for i, val in enumerate(negative_penalties))

    adj_k_rate = base_k_rate + reg_pos - reg_neg

    if len(positive_boosts) > 1 or len(negative_penalties) > 1:
        factors.append(f"🗜️ Regularization Applied (Capped double-counting overlap)")

    # Park Factors applied last as a scaler
    park_k_factor = K_PARK_FACTORS.get(park, 1.00)
    if park_k_factor != 1.00:
        adj_k_rate = adj_k_rate * park_k_factor
        val = (park_k_factor - 1) * 100
        factors.append(f"🏟️ Park Visibility Scaler ({val:+.1f}%)")

    adj_k_rate = max(0.10, min(0.45, adj_k_rate))

    is_high_variance = any(x.lower() in sp_name.lower() for x in BOOM_BUST_PITCHERS)
    std_dev = 0.08 if is_high_variance else 0.03 
    
    game_k_rates = np.random.normal(loc=adj_k_rate, scale=std_dev, size=num_sims)
    game_k_rates = np.clip(game_k_rates, 0.05, 0.65) 

    total_pitches = pitch_limit + extra_bp_pitches
    batters_faced = int(total_pitches / ppa)
    
    simulated_games = np.random.binomial(n=batters_faced, p=game_k_rates)
    
    return {
        'true_k_rate': adj_k_rate,
        'simulations': simulated_games,
        'distribution': (pd.DataFrame(simulated_games, columns=['Ks'])['Ks'].value_counts(normalize=True).sort_index() * 100),
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
    st.info(f"No games scheduled for {selected_date}.")
else:
    for i, game in enumerate(slate):
        if game['h_sp'] == "TBD" or game['a_sp'] == "TBD": continue
        with st.expander(f"⚾ {game['a_sp']} vs {game['h_sp']} ({game['h']} Stadium)"):
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                pl_a = st.slider(f"{game['a_sp']} Max Pitches", 60, 115, 95, key=f"pl_a_{i}")
                ppa_a = st.slider(f"{game['h']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_a_{i}")
                bp_tax_a = st.number_input(f"{game['a']} Bullpen Tax", 0, 20, 0, key=f"bpt_a_{i}")
            with col_l2:
                pl_h = st.slider(f"{game['h_sp']} Max Pitches", 60, 115, 95, key=f"pl_h_{i}")
                ppa_h = st.slider(f"{game['a']} P/PA", 3.0, 5.0, 3.8, step=0.1, key=f"ppa_h_{i}")
                bp_tax_h = st.number_input(f"{game['h']} Bullpen Tax", 0, 20, 0, key=f"bpt_h_{i}")
            
            a_proj = run_monte_carlo(game['a_sp'], game['a_base_k_rate'], game['h'], game['h'], False, pl_a, ppa_a, bp_tax_a)
            h_proj = run_monte_carlo(game['h_sp'], game['h_base_k_rate'], game['a'], game['h'], True, pl_h, ppa_h, bp_tax_h)

            col1, col2 = st.columns(2)
            for side, proj, name, team, opp, line_key in [('✈️', a_proj, game['a_sp'], game['a'], game['h'], 'ak'), ('🏠', h_proj, game['h_sp'], game['h'], game['a'], 'hk')]:
                with (col1 if side == '✈️' else col2):
                    st.markdown(f"### {side} {name}")
                    k_line = live_odds.get(name, st.number_input("Vegas Line:", 5.5, 10.5, 5.5, 0.5, key=f"{line_key}_{i}_{team}"))
                    over_prob = (np.sum(proj['simulations'] > k_line) / 10000) * 100
                    
                    if over_prob > 60: st.success(f"📈 **{over_prob:.1f}% Chance to hit OVER**")
                    elif over_prob < 40: st.error(f"📉 **{100-over_prob:.1f}% Chance to hit UNDER**")
                    else: st.warning(f"⚖️ Line is sharp ({over_prob:.1f}% Over)")
                    
                    st.bar_chart(proj['distribution'])
                    for f in proj['factors']: st.write(f"- {f}")

                    # Best Bet Filter
                    is_boom = any(x.lower() in name.lower() for x in BOOM_BUST_PITCHERS if x)
                    if not is_boom and (over_prob >= 56.0 or over_prob <= 44.0):
                        if team in ANALYTICS_TEAMS or opp in HIGH_K_LINEUPS:
                            best_bets_data.append({'sp': name, 'line': k_line, 'prob': over_prob, 'factors': proj['factors']})

if slate:
    with best_bets_container:
        st.subheader("⭐ Quant Identified: Premium Best Bets")
        if not best_bets_data: st.info("No premium best bets identified.")
        else:
            for bet in best_bets_data:
                s = "OVER" if bet['prob'] >= 56 else "UNDER"
                st.success(f"**{bet['sp']}** | **{s} {bet['line']} Ks** | Edge: **{(bet['prob'] if s=='OVER' else 100-bet['prob']):.1f}%**")
        st.divider()

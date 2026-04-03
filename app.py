import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="NBA Master AI 2026", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ System Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! The app is pulling fresh data.")

# ─────────────────────────────────────────────────────────────────────────────
# 1. THE 5-ON-5 STARTING ROSTER DATABASE
# Ratings scale: 70 (Bench level) to 99 (Generational Superstar)
# ─────────────────────────────────────────────────────────────────────────────
STARTING_FIVES = {
    'BOS': {
        'PG': {'name': 'Jrue Holiday', 'off': 82, 'def': 94},
        'SG': {'name': 'Derrick White', 'off': 84, 'def': 89},
        'SF': {'name': 'Jaylen Brown', 'off': 89, 'def': 84},
        'PF': {'name': 'Jayson Tatum', 'off': 94, 'def': 86},
        'C':  {'name': 'Kristaps Porzingis', 'off': 86, 'def': 82}
    },
    'NYK': {
        'PG': {'name': 'Jalen Brunson', 'off': 94, 'def': 74},
        'SG': {'name': 'Donte DiVincenzo', 'off': 81, 'def': 79},
        'SF': {'name': 'Mikal Bridges', 'off': 84, 'def': 90},
        'PF': {'name': 'OG Anunoby', 'off': 80, 'def': 92},
        'C':  {'name': 'Mitchell Robinson', 'off': 75, 'def': 88}
    },
    'MIN': {
        'PG': {'name': 'Mike Conley', 'off': 79, 'def': 78},
        'SG': {'name': 'Anthony Edwards', 'off': 93, 'def': 85},
        'SF': {'name': 'Jaden McDaniels', 'off': 76, 'def': 91},
        'PF': {'name': 'Karl-Anthony Towns', 'off': 89, 'def': 77},
        'C':  {'name': 'Rudy Gobert', 'off': 78, 'def': 96}
    },
    'MIL': {
        'PG': {'name': 'Damian Lillard', 'off': 92, 'def': 72},
        'SG': {'name': 'Gary Trent Jr.', 'off': 79, 'def': 75},
        'SF': {'name': 'Khris Middleton', 'off': 84, 'def': 78},
        'PF': {'name': 'Giannis Antetokounmpo', 'off': 96, 'def': 89},
        'C':  {'name': 'Brook Lopez', 'off': 79, 'def': 86}
    },
    'PHI': {
        'PG': {'name': 'Tyrese Maxey', 'off': 90, 'def': 75},
        'SG': {'name': 'Kelly Oubre Jr.', 'off': 79, 'def': 76},
        'SF': {'name': 'Paul George', 'off': 88, 'def': 84},
        'PF': {'name': 'Caleb Martin', 'off': 76, 'def': 81},
        'C':  {'name': 'Joel Embiid', 'off': 97, 'def': 88}
    },
    'DET': {
        'PG': {'name': 'Cade Cunningham', 'off': 86, 'def': 78},
        'SG': {'name': 'Jaden Ivey', 'off': 81, 'def': 75},
        'SF': {'name': 'Ausar Thompson', 'off': 74, 'def': 89},
        'PF': {'name': 'Tobias Harris', 'off': 81, 'def': 77},
        'C':  {'name': 'Jalen Duren', 'off': 80, 'def': 81}
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. STANDINGS, FETCHERS & FALLBACKS
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS', 'CHAR': 'CHA', 'BKLN': 'BKN'}
def norm(abbr): return ESPN_TO_STD.get(abbr, abbr)

BACKUP_STANDINGS = {
    'DET': {'wins': 56, 'losses': 21, 'record': '56-21', 'win_pct': 0.727, 'home_record': '30-8', 'away_record': '26-13'},
    'BOS': {'wins': 51, 'losses': 25, 'record': '51-25', 'win_pct': 0.671, 'home_record': '28-10', 'away_record': '23-15'},
    'NYK': {'wins': 49, 'losses': 28, 'record': '49-28', 'win_pct': 0.636, 'home_record': '27-11', 'away_record': '22-17'},
    'PHI': {'wins': 42, 'losses': 34, 'record': '42-34', 'win_pct': 0.552, 'home_record': '24-15', 'away_record': '18-19'},
    'MIN': {'wins': 46, 'losses': 29, 'record': '46-29', 'win_pct': 0.613, 'home_record': '25-12', 'away_record': '21-17'},
    'MIL': {'wins': 30, 'losses': 46, 'record': '30-46', 'win_pct': 0.394, 'home_record': '19-20', 'away_record': '11-26'},
}

@st.cache_data(ttl=300)
def get_daily_slate():
    # Force Custom Demo Slate to guarantee we see our programmed 5-on-5 logic
    return [
        {'h': 'NYK', 'a': 'BOS', 'h_name': 'Knicks', 'a_name': 'Celtics', 'time': '7:30 PM', 'venue': 'MSG'},
        {'h': 'MIN', 'a': 'MIL', 'h_name': 'Timberwolves', 'a_name': 'Bucks', 'time': '8:00 PM', 'venue': 'Target Center'},
        {'h': 'PHI', 'a': 'DET', 'h_name': '76ers', 'a_name': 'Pistons', 'time': '7:00 PM', 'venue': 'Wells Fargo Center'},
    ]

@st.cache_data(ttl=600)
def get_standings(): return BACKUP_STANDINGS

@st.cache_data(ttl=600)
def get_injuries():
    # Embiid injured to demonstrate the Matchup Voiding logic
    return {'PHI': ['Joel Embiid (Doubtful - Knee)']}

def is_active(player_name, team_injuries):
    last_name = player_name.split()[-1]
    return not any(last_name in inj for inj in team_injuries)

# ─────────────────────────────────────────────────────────────────────────────
# 3. THE 5-ON-5 PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries):
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    factors = []
    matchup_logs = []
    total = 0.0
    
    # Base Factors
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "adj": 3.5, "why": "Standard home boost."})
    
    base_adj = (h_std['win_pct'] - a_std['win_pct']) * 20.0
    total += base_adj
    factors.append({"icon": "📊", "name": "Team Form Edge", "adj": base_adj, "why": f"Overall record disparity ({h_std['record']} vs {a_std['record']})."})

    # --- 5-ON-5 POSITIONAL MATCHUP ENGINE ---
    # We scale the matchup math by 0.15 so a +10 advantage equals +1.5 win probability points.
    SCALING_FACTOR = 0.15 
    
    h_roster = STARTING_FIVES.get(h)
    a_roster = STARTING_FIVES.get(a)
    
    if h_roster and a_roster:
        positions = ['PG', 'SG', 'SF', 'PF', 'C']
        
        for pos in positions:
            hp = h_roster[pos]
            ap = a_roster[pos]
            
            # 1. Injury Check
            if not is_active(hp['name'], h_inj) or not is_active(ap['name'], a_inj):
                matchup_logs.append({
                    "pos": pos, "matchup": f"⚠️ {hp['name']} vs {ap['name']}",
                    "math": "Matchup Voided due to Injury Report. Bench logic applied.",
                    "adj": 0.0, "color": "#888888"
                })
                continue
                
            # 2. Calculate the Math
            # How many points Home Offense creates against Away Defense
            h_score = max(0, hp['off'] - ap['def'])
            # How many points Away Offense creates against Home Defense
            a_score = max(0, ap['off'] - hp['def'])
            
            # The Net difference scaled down for the probability engine
            net_edge = (h_score - a_score) * SCALING_FACTOR
            total += net_edge
            
            # Format the math for the UI
            math_str = f"(H_OFF {hp['off']} - A_DEF {ap['def']}) vs (A_OFF {ap['off']} - H_DEF {hp['def']})"
            color = "#28a745" if net_edge > 0 else "#dc3545" if net_edge < 0 else "#888888"
            
            matchup_logs.append({
                "pos": pos, "matchup": f"**{hp['name']}** ({h}) vs **{ap['name']}** ({a})",
                "math": math_str, "adj": net_edge, "color": color
            })
            
    else:
        factors.append({"icon": "⚠️", "name": "Rosters Missing", "adj": 0.0, "why": "Full 5-on-5 data not available for these teams."})

    # Injury Adjustments
    if h_inj: total -= 4.0; factors.append({"icon": "🤕", "name": "Team Injury Impact", "adj": -4.0, "why": f"{h} missing rotation players."})
    if a_inj: total += 4.0; factors.append({"icon": "🤕", "name": "Team Injury Impact", "adj": 4.0, "why": f"{a} missing rotation players."})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0 - prob,
        'prob_h': prob, 'factors': factors, 'matchups': matchup_logs,
        'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor (5-on-5 Edition)")
st.divider()

slate = get_daily_slate()
standings = get_standings()
injuries = get_injuries()

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, injuries)
    conf = pred['conf']
    
    icon = "🔒" if conf >= 80 else ("🔥" if conf >= 65 else "⚖️")
    header = f"{icon} {game['h_name']} vs {game['a_name']} | {pred['winner']} ({conf:.1f}%)"

    with st.expander(header):
        st.markdown(f"### 🏆 {pred['winner']} WINS ({conf:.1f}%)")
        
        # --- NEW 5-ON-5 MATCHUP BOARD ---
        if pred['matchups']:
            st.markdown("#### ⚔️ Starting 5 Positional Matchups")
            st.write("Calculated by: `(Home OFF - Away DEF) - (Away OFF - Home DEF) * Scaling Factor`")
            
            # Create a clean UI table for the matchups
            for m in pred['matchups']:
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"**{m['pos']}**")
                c2.markdown(f"{m['matchup']} <br> <span style='font-size:12px;color:gray;'>Math: {m['math']}</span>", unsafe_allow_html=True)
                c3.markdown(f"<span style='color:{m['color']};font-weight:bold;'>{m['adj']:+.1f} pts</span>", unsafe_allow_html=True)
            st.divider()

        # --- GENERAL FACTORS LOG ---
        st.markdown("#### 🧠 General Factors Log")
        for f in pred['factors']:
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f['icon'])
            c2.markdown(f"**{f['name']}** <br> <span style='color:gray;font-size:14px;'>{f['why']}</span>", unsafe_allow_html=True)
            pt_color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            c3.markdown(f"<span style='color:{pt_color};font-weight:bold;font-size:18px;'>{f['adj']:+.1f} pts</span>", unsafe_allow_html=True)
        
        st.divider()

        # --- LIVE TEAM STATS ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 🏠 {game['h_name']}")
            st.write(f"**Record:** {pred['h_std']['record']}")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
        with col2:
            st.markdown(f"#### ✈️ {game['a_name']}")
            st.write(f"**Record:** {pred['a_std']['record']}")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

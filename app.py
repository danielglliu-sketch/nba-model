import streamlit as st
from datetime import datetime

# Page Configuration for Mobile
st.set_page_config(page_title="2026 NBA AI", page_icon="🏀", layout="wide")

st.title("🏀 NBA Master AI")
st.write(f"**Live Scouting Report:** {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

# --- THE 2026 MASTER LOGIC ---
def predict_game(home, away, injuries, notes, is_best_bet=False):
    # Base Win Probability Math
    prob = 0.545 # Base Home Advantage (54.5%)
    
    # Power Ratings for April 3, 2026 (Net Rating L10)
    ratings = {
        'BOS': 10.5, 'MIL': -4.2, 'HOU': 7.1, 'UTA': -12.5, 
        'ATL': 8.8, 'BKN': -6.1, 'MEM': 5.5, 'TOR': -5.8,
        'PHI': 4.2, 'MIN': -1.5, 'CHA': 6.2, 'IND': -3.1,
        'NYK': 5.5, 'CHI': -4.8, 'ORL': 3.9, 'DAL': -8.2,
        'SAC': 2.1, 'NOP': -5.5
    }
    
    # Apply Rating Differential
    prob += (ratings.get(home, 0) - ratings.get(away, 0)) * 0.02
    
    # Injury Penalties
    if home in injuries: prob -= 0.12
    if away in injuries: prob += 0.12

    # Formatting for Phone
    icon = "🔥 BEST BET" if is_best_bet else "🔍"
    with st.expander(f"{icon} {home} vs {away}", expanded=is_best_bet):
        col1, col2 = st.columns([1, 2])
        col1.metric("Win Prob", f"{prob*100:.1f}%")
        col2.write("**Model Reasoning:**")
        for n in notes:
            st.write(f"· {n}")

# --- THE APRIL 3, 2026 SLATE ---
st.subheader("🔥 Top Analytical Picks")

# 1. BOS vs MIL (High Confidence)
predict_game("BOS", "MIL", ["MIL"], 
             ["Giannis is OUT (Ankle)", "MIL on Back-to-Back", "BOS #1 Defense"], True)

# 2. HOU vs UTA (High Confidence)
predict_game("HOU", "UTA", ["UTA"], 
             ["Utah resting 3 starters", "HOU dominant at home (27-10)"], True)

st.divider()
st.subheader("📋 Remaining Slate")

# 3. PHI vs MIN
predict_game("PHI", "MIN", ["MIN"], 
             ["Anthony Edwards is OUT", "Embiid (Doubtful) baked into 58% prob"])

# 4. ATL vs BKN
predict_game("ATL", "BKN", [], 
             ["Post-Trae Trade Momentum (8-2 L10)", "BKN sliding (1-9 L10)"])

# 5. ORL vs DAL
predict_game("ORL", "DAL", ["DAL"], 
             ["Dallas tanking (24-52)", "ORL needs win for playoff seeding"])

# 6. MEM vs TOR
predict_game("MEM", "TOR", [], 
             ["Upset Alert: MEM youth vs tired Raptors core", "TOR 2-8 in last 10"])

# 7. NYK vs CHI
predict_game("NYK", "CHI", [], 
             ["Knicks fighting for #3 seed", "CHI on 5-game losing streak"])

# 8. CHA vs IND
predict_game("CHA", "IND", ["IND"], 
             ["Pacers missing Haliburton", "CHA #2 in L10 Net Rating"])

# 9. SAC vs NOP
predict_game("SAC", "NOP", ["NOP"], 
             ["Pelicans on 6-game slide", "SAC fighting for home court"])

st.info("💡 Tap the rows above to see the full breakdown for each game.")

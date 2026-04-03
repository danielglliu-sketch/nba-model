import streamlit as st
import pandas as pd
from datetime import datetime

# --- APP UI ---
st.set_page_config(page_title="2026 NBA Predictor", layout="centered")
st.title("🏀 NBA Master Model")
st.subheader(f"Daily Scouting Report: {datetime.now().strftime('%B %d, %Y')}")

class NBAMobileModel:
    def __init__(self):
        # Your current 2026 data
        self.team_ratings = {'SAS': 14.6, 'OKC': 12.2, 'BOS': 9.5, 'ATL': 8.1, 'HOU': 6.8}
        self.home_court_adv = 0.045

    def get_prediction(self, home, away, injuries):
        # (Insert the Logic & Reasoning Engine we built earlier here)
        prob = 0.50 + self.home_court_adv + ((self.team_ratings.get(home, 0) - self.team_ratings.get(away, 0)) * 0.02)
        
        reasons = [f"Base Home Court Advantage (+4.5%)"]
        if home == 'BOS' and 'MIL' in injuries:
            prob += 0.08
            reasons.append("Injury Advantage: Milwaukee missing Giannis (+8.0%)")
            
        return prob, reasons

# --- MOBILE DASHBOARD ---
model = NBAMobileModel()

# Example for today's big game
st.header("Today's Top Pick")
prob, insights = model.get_prediction('BOS', 'MIL', ['MIL'])

with st.container():
    col1, col2 = st.columns(2)
    col1.metric("Matchup", "BOS vs MIL")
    col2.metric("Win Prob", f"{prob*100:.1f}%")

st.write("### 🧠 Why the Model favors this:")
for note in insights:
    st.info(note)

st.divider()
st.write("Check this every morning before the 3:30 PM injury updates!")

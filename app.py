import streamlit as st
from datetime import datetime

# Safe Page Setup
st.set_page_config(page_title="NBA AI 2026", layout="centered")

st.title("🏀 NBA Master AI")
# Get current date from server
curr_date = datetime.now().strftime('%Y-%m-%d')
st.write(f"Logged in: {curr_date}")

# --- FULL 9-GAME SLATE FOR APRIL 3 ---
schedule = {
    '2026-04-03': [
        {'h': 'BOS', 'a': 'MIL', 'prob': 94, 'notes': ['Giannis OUT', 'MIL on B2B']},
        {'h': 'HOU', 'a': 'UTA', 'prob': 91, 'notes': ['Utah Tanking', 'HOU Home Edge']},
        {'h': 'ATL', 'a': 'BKN', 'prob': 74, 'notes': ['Post-Trae Momentum', 'ATL #1 Def']},
        {'h': 'MEM', 'a': 'TOR', 'prob': 61, 'notes': ['Upset Alert', 'TOR sliding']},
        {'h': 'PHI', 'a': 'MIN', 'prob': 58, 'notes': ['Ant Edwards Rest', 'Embiid (Doubtful)']},
        {'h': 'CHA', 'a': 'IND', 'prob': 54, 'notes': ['CHA Momentum', 'IND missing Hali']},
        {'h': 'NYK', 'a': 'CHI', 'prob': 79, 'notes': ['NYK #3 Seed chase', 'Bulls L5 slide']},
        {'h': 'DAL', 'a': 'ORL', 'prob': 83, 'notes': ['Dallas Tanking', 'ORL Seeding']},
        {'h': 'SAC', 'a': 'NOP', 'prob': 72, 'notes': ['NOP 6-game slide', 'SAC Home court']}
    ],
    '2026-04-04': [
        {'h': 'SAS', 'a': 'DEN', 'prob': 52, 'notes': ['Wemby vs Jokic']},
        {'h': 'GSW', 'a': 'LAL', 'prob': 48, 'notes': ['Lakers 6th seed chase']},
        {'h': 'PHX', 'a': 'MIN', 'prob': 66, 'notes': ['Suns Perimeter D']}
    ]
}

st.divider()

# Logic to find and display games
if curr_date in schedule:
    st.subheader("Today's Predictions")
    for g in schedule[curr_date]:
        with st.expander(f"{g['h']} vs {g['a']} — {g['prob']}%"):
            for note in g['notes']:
                st.write(f"· {note}")
else:
    st.warning("No games found for today's date in the database.")
    st.write("Check your computer's date vs the server date!")

st.divider()
st.caption("2026 Master Model v1.2")

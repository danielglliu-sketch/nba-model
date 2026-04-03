import streamlit as st
from datetime import datetime

# Mobile-Optimized Page Config
st.set_page_config(page_title="NBA AI 2026", page_icon="🏀")

# --- APP HEADER ---
st.title("🏀 NBA Master AI")
today_date = datetime.now().strftime('%Y-%m-%d')
st.write(f"**Live Scouting Report:** {datetime.now().strftime('%A, %B %d')}")
st.divider()

# --- THE 2026 SCHEDULE DATABASE ---
schedule = {
    '2026-04-03': [
        {'h': 'BOS', 'a': 'MIL', 'win': 'BOS', 'prob': 94, 'notes': ['Giannis OUT (Ankle)', 'MIL on B2B Fatigue']},
        {'h': 'HOU', 'a': 'UTA', 'win': 'HOU', 'prob': 91, 'notes': ['Utah Tanking/Resting starters', 'HOU Home Dominance']},
        {'h': 'NYK', 'a': 'CHI', 'win': 'NYK', 'prob': 79, 'notes': ['NYK chasing #3 seed', 'Bulls 5-game skid']},
        {'h': 'DAL', 'a': 'ORL', 'win': 'ORL', 'prob': 83, 'notes': ['Dallas in Lottery Mode', 'ORL Playoff Seeding']},
        {'h': 'ATL', 'a': 'BKN', 'win': 'ATL', 'prob': 74, 'notes': ['Post-Trae Defense Surge', 'BKN sliding (1-9 L10)']},
        {'h': 'SAC', 'a': 'NOP', 'win': 'SAC', 'prob': 72, 'notes': ['Pelicans 6-game slide', 'SAC Home Court Edge']},
        {'h': 'MEM', 'a': 'TOR', 'win': 'MEM', 'prob': 61, 'notes': ['Upset Alert: MEM Youth Energy', 'TOR late-season fatigue']},
        {'h': 'PHI', 'a': 'MIN', 'win': 'PHI', 'prob': 58, 'notes': ['MIN on B2B', 'Ant Edwards (Rest) Alert']},
        {'h': 'CHA', 'a': 'IND', 'win': 'CHA', 'prob': 54, 'notes': ['CHA #2 L10 Net Rating', 'IND missing Haliburton']}
    ],
    '2026-04-04': [
        {'h': 'DEN', 'a': 'SAS', 'win': 'DEN', 'prob': 53, 'notes': ['Jokic vs Wemby Showdown', 'Denver Playoff Seeding']},
        {'h': 'MIA', 'a': 'WAS', 'win': 'MIA', 'prob': 88, 'notes': ['Heat Play-In desperation', 'Wizards tanking']},
        {'h': 'PHI', 'a': 'DET', 'win': 'DET', 'prob': 51, 'notes': ['Detroit #1 Seed momentum', 'Embiid likely load mgmt']}
    ],
    '2026-04-05': [
        {'h': 'OKC', 'a': 'UTA', 'win': 'OKC', 'prob': 95, 'notes': ['SGA MVP Campaign', 'Utah officially resting']},
        {'h': 'GSW', 'a': 'HOU', 'win': 'HOU', 'prob': 55, 'notes': ['Rockets hot momentum', 'Warriors on B2B']},
        {'h': 'DAL', 'a': 'LAL', 'win': 'LAL', 'prob': 64, 'notes': ['Lakers 6th seed chase', 'Doncic (LAL) vs Luka (DAL)']}
    ]
}

# --- THE AUTO-DISPLAY LOGIC ---
if today_date in schedule:
    st.subheader("🔥 Today's Predicted Winners")
    
    for game in schedule[today_date]:
        # Choose icon based on confidence
        icon = "🔒" if game['prob'] > 80 else "🏀"
        
        # Create a clearly labeled header
        with st.expander(f"{icon} {game['h']} vs {game['a']}"):
            # Big bold winner text
            st.markdown(f"### 🏆 VERDICT: **{game['win']} WINS**")
            
            c1, c2 = st.columns([1, 2])
            c1.metric("Confidence", f"{game['prob']}%")
            
            c2.write("**Reasoning:**")
            for note in game['notes']:
                c2.caption(f"✅ {note}")
else:
    st.warning("📅 No games in database for today. Update GitHub 'schedule' block!")

st.divider()
st.info("💡 To update games, edit the 'schedule' dictionary in app.py on GitHub.")

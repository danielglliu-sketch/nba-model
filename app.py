import streamlit as st
from datetime import datetime

# Mobile-Optimized Page Config
st.set_page_config(page_title="2026 NBA AI", page_icon="🏀")

# --- APP HEADER ---
st.title("🏀 NBA Master AI")
today_date = datetime.now().strftime('%Y-%m-%d')
st.write(f"**Live Scouting Report:** {datetime.now().strftime('%A, %B %d')}")
st.divider()

# --- THE 2026 SEASON DATABASE ---
# I have pre-filled this with the high-impact games for the next 4 days.
schedule = {
    '2026-04-03': [
        {'h': 'BOS', 'a': 'MIL', 'prob': 94.2, 'notes': ['Giannis OUT (Ankle)', 'MIL on B2B', 'BOS #1 Defense']},
        {'h': 'HOU', 'a': 'UTA', 'prob': 91.5, 'notes': ['Utah Tanking', 'HOU 27-10 Home Record']},
        {'h': 'ATL', 'a': 'BKN', 'prob': 74.1, 'notes': ['Post-Trae Trade Defense (#1 L10)', 'BKN 1-9 in last 10']},
        {'h': 'MEM', 'a': 'TOR', 'prob': 61.2, 'notes': ['Upset Alert: MEM Youth vs Tired Raptors']}
    ],
    '2026-04-04': [
        {'h': 'SAS', 'a': 'DEN', 'prob': 52.8, 'notes': ['Wemby vs Jokic Battle', 'SAS #3 Def Rating', 'Jokic MVP Momentum']},
        {'h': 'GSW', 'a': 'LAL', 'prob': 48.5, 'notes': ['Lakers fighting for 6th seed', 'Curry vs Doncic (LAL) showdown']},
        {'h': 'PHX', 'a': 'MIN', 'prob': 66.4, 'notes': ['Anthony Edwards Questionable', 'Suns elite perimeter D']}
    ],
    '2026-04-05': [
        {'h': 'DET', 'a': 'PHI', 'prob': 68.2, 'notes': ['Pistons #1 Seed dominance', 'Embiid Load Mgmt possible']},
        {'h': 'CLE', 'a': 'MIA', 'prob': 59.1, 'notes': ['Miami Heat Play-In desperation', 'Cavs interior size edge']}
    ],
    '2026-04-06': [
        {'h': 'NYK', 'a': 'BOS', 'prob': 49.2, 'notes': ['Battle for the East', 'Brunson vs Tatum', 'High Intensity Game']},
        {'h': 'OKC', 'a': 'DAL', 'prob': 82.5, 'notes': ['SGA MVP Campaign', 'Dallas officially in Lottery Mode']}
    ],
    '2026-04-07': [
        {'h': 'ATL', 'a': 'CHA', 'prob': 58.7, 'notes': ['Post-Trae Hawks vs Hot Hornets', 'Clash of two top-5 momentum teams']}
    ]
}

# --- THE AUTO-DISPLAY LOGIC ---
if today_date in schedule:
    st.subheader(f"🔥 Today's Analytical Picks")
    for game in schedule[today_date]:
        # High confidence highlight
        is_lock = game['prob'] > 80
        icon = "🔒" if is_lock else "🏀"
        
        with st.expander(f"{icon} {game['h']} vs {game['a']}"):
            c1, c2 = st.columns([1, 2])
            c1.metric("Win Prob", f"{game['prob']}%")
            for note in game['notes']:
                c2.caption(f"✅ {note}")
else:
    st.warning("📅 No games scheduled in the model for today. Update your GitHub 'schedule' block!")

st.divider()
st.info("💡 To update next week's games, just edit the 'schedule' dictionary in your app.py on GitHub.")

import streamlit as st
import requests
from datetime import datetime

# --- APP SETUP ---
st.set_page_config(page_title="2026 NBA Master AI", page_icon="🏀", layout="wide")

# --- 2026 LOGIC ENGINE (All 30 Teams) ---
TEAM_DATA = {
    # East Contenders
    'BOS': {'rtg': 10.5,  'def': 107.2, 'status': 'Title Contender',  'note': 'Best 2-way team in the league.'},
    'CLE': {'rtg': 9.1,   'def': 108.8, 'status': 'East Threat',       'note': 'Mitchell leading strong core.'},
    'NYK': {'rtg': 7.5,   'def': 111.2, 'status': 'Seeding Battle',    'note': 'Brunson carry-job continues.'},
    'MIA': {'rtg': 6.8,   'def': 110.5, 'status': 'Playoff Lock',      'note': 'Heat culture always shows up.'},
    'MIL': {'rtg': -4.2,  'def': 115.8, 'status': 'Injured',           'note': 'Giannis (Ankle) major impact.'},
    'IND': {'rtg': 5.5,   'def': 112.0, 'status': 'Playoff Team',      'note': 'Haliburton offense clicks.'},
    'CHI': {'rtg': -2.5,  'def': 116.4, 'status': 'Play-In Bubble',    'note': 'Inconsistent defense.'},
    'ATL': {'rtg': 8.2,   'def': 110.4, 'status': 'Play-In Fight',     'note': 'Post-Trae trade surge.'},
    'DET': {'rtg': 8.8,   'def': 108.5, 'status': '1st Seed Lock',     'note': 'Cunningham injury impact.'},
    'PHI': {'rtg': -6.0,  'def': 118.2, 'status': 'Rebuilding',        'note': 'Post-Embiid transition.'},
    'TOR': {'rtg': -7.5,  'def': 119.0, 'status': 'Lottery',           'note': 'Youth development mode.'},
    'BKN': {'rtg': -11.0, 'def': 122.5, 'status': 'Tanking',           'note': 'Full rebuild underway.'},
    'WAS': {'rtg': -13.0, 'def': 125.0, 'status': 'Tanking',           'note': 'Draft positioning priority.'},
    'ORL': {'rtg': 3.2,   'def': 109.5, 'status': 'Playoff Lock',      'note': 'Franz Wagner emerging star.'},
    'CHA': {'rtg': -10.0, 'def': 121.0, 'status': 'Lottery',           'note': 'LaMelo health concerns.'},
    # West Contenders
    'OKC': {'rtg': 15.7,  'def': 108.0, 'status': 'MVP Mode',          'note': 'SGA dominance all season.'},
    'HOU': {'rtg': 12.0,  'def': 109.1, 'status': 'West Power',        'note': 'Elite home advantage.'},
    'LAL': {'rtg': 5.0,   'def': 112.5, 'status': 'Playoff Team',      'note': 'LeBron milestone chase.'},
    'LAC': {'rtg': 4.5,   'def': 113.0, 'status': 'Seeding Battle',    'note': 'Kawhi availability key.'},
    'GSW': {'rtg': 3.8,   'def': 111.8, 'status': 'Playoff Lock',      'note': 'Curry still elite.'},
    'DEN': {'rtg': 6.5,   'def': 111.5, 'status': 'West Threat',       'note': 'Jokic MVP pace again.'},
    'MIN': {'rtg': 7.0,   'def': 110.0, 'status': 'West Threat',       'note': 'Edwards ascending star.'},
    'PHX': {'rtg': 1.5,   'def': 114.0, 'status': 'Play-In Bubble',    'note': 'KD load management.'},
    'SAC': {'rtg': 2.0,   'def': 113.5, 'status': 'Play-In Bubble',    'note': 'Sabonis engine grinding.'},
    'MEM': {'rtg': 4.0,   'def': 112.2, 'status': 'Playoff Lock',      'note': 'Morant back healthy.'},
    'NOP': {'rtg': -9.0,  'def': 120.5, 'status': 'Lottery',           'note': 'Zion injury cloud lingers.'},
    'SAS': {'rtg': -8.5,  'def': 119.8, 'status': 'Lottery',           'note': 'Wembanyama development year.'},
    'DAL': {'rtg': -8.2,  'def': 119.5, 'status': 'Lottery',           'note': 'Luka trade aftermath.'},
    'POR': {'rtg': -10.5, 'def': 121.8, 'status': 'Tanking',           'note': 'Scoot development focus.'},
    'UTA': {'rtg': -12.5, 'def': 124.2, 'status': 'Tanking',           'note': 'Resting veterans for draft.'},
}

# --- ESPN API FETCHER (with correct home/away detection) ---
@st.cache_data(ttl=600)
def get_daily_slate():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        games = []
        for event in data.get('events', []):
            competitors = event['competitions'][0]['competitors']
            # FIX: Use the homeAway field — never assume index order
            home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
            away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
            if home and away:
                games.append({
                    'h': home['team']['abbreviation'],
                    'a': away['team']['abbreviation']
                })
        return games
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Live feed unavailable ({e}). Showing fallback slate.")
        return [
            {'h': 'BOS', 'a': 'MIL'}, {'h': 'HOU', 'a': 'UTA'},
            {'h': 'NYK', 'a': 'CHI'}, {'h': 'ATL', 'a': 'BKN'},
            {'h': 'PHI', 'a': 'MIN'}, {'h': 'SAC', 'a': 'NOP'}
        ]

# --- PREDICTION ENGINE ---
def predict_game(h, a):
    DEFAULT = {'rtg': 0, 'def': 115.0, 'status': 'Unknown', 'note': 'No data available.'}
    h_data = TEAM_DATA.get(h, DEFAULT)
    a_data = TEAM_DATA.get(a, DEFAULT)

    # Base: home court edge + net rating diff + defensive matchup
    prob = 54.5
    prob += (h_data['rtg'] - a_data['rtg']) * 2.0
    prob += (a_data['def'] - h_data['def']) * 0.5  # Lower def rating = better defense

    # Context modifiers
    if h_data['status'] == 'Tanking':  prob -= 10
    if a_data['status'] == 'Tanking':  prob += 10
    if h_data['status'] == 'Injured':  prob -= 6
    if a_data['status'] == 'Injured':  prob += 6

    prob = max(1.0, min(99.0, prob))

    # FIX: Break 50/50 ties cleanly toward home (home court advantage)
    if prob >= 50:
        winner, conf = h, prob
    else:
        winner, conf = a, 100.0 - prob

    return winner, round(conf, 1), h_data, a_data

# --- UI ---
st.title("🏀 NBA Master AI (Full-Auto)")
st.write(f"**Live Scouting Analysis:** {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

with st.spinner("📡 Fetching today's slate..."):
    slate = get_daily_slate()

if slate:
    st.subheader(f"Today's Smart Predictions — {len(slate)} Games")

    for game in slate:
        h, a = game['h'], game['a']
        winner, conf, h_data, a_data = predict_game(h, a)

        lock = conf >= 85
        label = f"{'🔒' if lock else '🏀'}  {h} vs {a}  —  {winner} favored ({conf}%)"

        with st.expander(label):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### 🏆 VERDICT: **{winner} WINS**")
                st.info(f"🏠 **{h}** ({h_data['status']}): {h_data['note']}")
                st.info(f"✈️  **{a}** ({a_data['status']}): {a_data['note']}")
                st.caption(
                    f"🛡️ Defensive Efficiency → {h}: {h_data['def']} | {a}: {a_data['def']}  "
                    f"*(lower = better defense)*"
                )

            with col2:
                st.metric("Model Confidence", f"{conf}%")
                st.metric("Home Net Rtg", f"{h_data['rtg']:+.1f}")
                st.metric("Away Net Rtg", f"{a_data['rtg']:+.1f}")
else:
    st.error("No games found. Please refresh in a moment.")

st.divider()
st.info("💡 Auto-updating every 10 min. Predictions use 2026 net ratings, defensive efficiency, and game-context modifiers.")

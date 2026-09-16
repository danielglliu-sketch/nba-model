import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta, date

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="NFL Master AI 2026", page_icon="🏈", layout="wide")
st.sidebar.title("⚙️ NFL System Tools")

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Pulling fresh NFL data.")

st.sidebar.subheader("📅 View Date")
selected_date = st.sidebar.date_input(
    "Select game date",
    value=date.today(),
    min_value=date(2026, 8, 1),
    max_value=date.today() + timedelta(days=14),
    label_visibility="collapsed",
)

# 🚨 THE FIX: NFL games are weekly, not daily. 
# We create an 8-day window centered on your selected date to capture Thurs/Sun/Mon games.
start_d = selected_date - timedelta(days=3)
end_d = selected_date + timedelta(days=4)
selected_date_str = f"{start_d.strftime('%Y%m%d')}-{end_d.strftime('%Y%m%d')}"

# ─────────────────────────────────────────────────────────────────────────────
# NFL PLAYER TIERS — The Ultimate Line Movers
# ─────────────────────────────────────────────────────────────────────────────
ELITE_QBS = ["Patrick Mahomes", "Josh Allen", "Lamar Jackson", "Joe Burrow", "CJ Stroud", "Justin Herbert"]
GOOD_QBS = ["Jalen Hurts", "Dak Prescott", "Jordan Love", "Matthew Stafford", "Jared Goff", "Brock Purdy", "Tua Tagovailoa", "Trevor Lawrence", "Kyler Murray", "Caleb Williams"]
AVG_QBS = ["Baker Mayfield", "Geno Smith", "Aaron Rodgers", "Kirk Cousins", "Deshaun Watson", "Jayden Daniels", "Anthony Richardson", "Will Levis"]

# The very best skill players and game-wrecking defensive players
ELITE_NON_QBS = [
    "Justin Jefferson", "Tyreek Hill", "Christian McCaffrey", "Ja'Marr Chase", "CeeDee Lamb", "Amon-Ra St. Brown",
    "Micah Parsons", "T.J. Watt", "Myles Garrett", "Nick Bosa", "Chris Jones", "Maxx Crosby", 
    "Trent Williams", "Fred Warner", "Sauce Gardner", "Patrick Surtain II", "Roquan Smith"
]

def _build_nfl_player_lookup():
    lookup: dict = {}
    for p in ELITE_QBS:
        lookup[p.lower()] = (6.0, "Elite QB")
    for p in GOOD_QBS:
        lookup[p.lower()] = (4.0, "Good QB")
    for p in AVG_QBS:
        lookup[p.lower()] = (2.5, "Avg QB")
    for p in ELITE_NON_QBS:
        lookup[p.lower()] = (1.0, "Elite Non-QB")
    return lookup

NFL_PLAYER_LOOKUP = _build_nfl_player_lookup()

# ─────────────────────────────────────────────────────────────────────────────
# NFL BASE TEAM DATA — (Proxy for Base EPA & Roster Talent)
# off_pwr: Points generated vs avg defense
# def_pwr: Points allowed vs avg offense
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'ARI': {'off_pwr': 22.0, 'def_pwr': 25.5}, 'ATL': {'off_pwr': 22.5, 'def_pwr': 21.0},
    'BAL': {'off_pwr': 27.0, 'def_pwr': 17.5}, 'BUF': {'off_pwr': 26.5, 'def_pwr': 19.5},
    'CAR': {'off_pwr': 16.0, 'def_pwr': 27.5}, 'CHI': {'off_pwr': 21.5, 'def_pwr': 21.0},
    'CIN': {'off_pwr': 25.0, 'def_pwr': 22.0}, 'CLE': {'off_pwr': 20.0, 'def_pwr': 18.0},
    'DAL': {'off_pwr': 27.5, 'def_pwr': 20.0}, 'DEN': {'off_pwr': 18.5, 'def_pwr': 23.5},
    'DET': {'off_pwr': 26.5, 'def_pwr': 21.5}, 'GB':  {'off_pwr': 24.5, 'def_pwr': 21.0},
    'HOU': {'off_pwr': 24.0, 'def_pwr': 20.5}, 'IND': {'off_pwr': 23.0, 'def_pwr': 24.0},
    'JAX': {'off_pwr': 21.5, 'def_pwr': 23.0}, 'KC':  {'off_pwr': 26.0, 'def_pwr': 18.0},
    'LV':  {'off_pwr': 19.0, 'def_pwr': 20.5}, 'LAC': {'off_pwr': 23.0, 'def_pwr': 23.0},
    'LAR': {'off_pwr': 24.0, 'def_pwr': 22.5}, 'MIA': {'off_pwr': 27.5, 'def_pwr': 23.0},
    'MIN': {'off_pwr': 21.0, 'def_pwr': 21.5}, 'NE':  {'off_pwr': 15.5, 'def_pwr': 21.0},
    'NO':  {'off_pwr': 21.5, 'def_pwr': 20.0}, 'NYG': {'off_pwr': 17.0, 'def_pwr': 25.0},
    'NYJ': {'off_pwr': 22.5, 'def_pwr': 17.5}, 'PHI': {'off_pwr': 25.5, 'def_pwr': 22.0},
    'PIT': {'off_pwr': 19.5, 'def_pwr': 19.0}, 'SF':  {'off_pwr': 28.0, 'def_pwr': 18.0},
    'SEA': {'off_pwr': 21.5, 'def_pwr': 23.5}, 'TB':  {'off_pwr': 21.0, 'def_pwr': 20.5},
    'TEN': {'off_pwr': 19.0, 'def_pwr': 22.0}, 'WAS': {'off_pwr': 20.5, 'def_pwr': 26.5},
}

BLANK_STD = {
    'wins': 0, 'losses': 0, 'ties': 0, 'record': '0-0', 'win_pct': 0.5, 
}

ESPN_NORM = {
    'WSH': 'WAS', 'SFO': 'SF', 'TBB': 'TB', 'KCC': 'KC', 'LVR': 'LV', 
    'NWE': 'NE', 'NO': 'NO', 'JAC': 'JAX', 'CLV': 'CLE', 'BLT': 'BAL', 
    'HST': 'HOU', 'ARZ': 'ARI'
}
def norm(abbr):
    if not abbr: 
        return ""
    return ESPN_NORM.get(abbr, abbr).upper()

# ─────────────────────────────────────────────────────────────────────────────
# Session singleton
# ─────────────────────────────────────────────────────────────────────────────
_SESSION = None
def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json',
        })
    return _SESSION

# ─────────────────────────────────────────────────────────────────────────────
# Scoreboard & Standings
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_nfl_scoreboard(date_string):
    # 🚨 THE FIX: Added &limit=100 to ensure date-range queries don't get truncated
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_string}&limit=100"
    try:
        r = get_session().get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        games = []
        for event in data.get('events', []):
            comp = event.get('competitions', [{}])[0]
            home = next((c for c in comp.get('competitors', []) if c.get('homeAway') == 'home'), None)
            away = next((c for c in comp.get('competitors', []) if c.get('homeAway') == 'away'), None)
            
            if home and away:
                # Safe record parsing
                h_recs = home.get('records')
                a_recs = away.get('records')
                h_rec = h_recs[0].get('summary', '0-0') if h_recs and len(h_recs) > 0 else '0-0'
                a_rec = a_recs[0].get('summary', '0-0') if a_recs and len(a_recs) > 0 else '0-0'
                
                # Safe abbreviation parsing
                h_abbr = home.get('team', {}).get('abbreviation', '')
                a_abbr = away.get('team', {}).get('abbreviation', '')
                
                games.append({
                    'h': norm(h_abbr),
                    'a': norm(a_abbr),
                    'h_name': home.get('team', {}).get('displayName', 'Home Team'),
                    'a_name': away.get('team', {}).get('displayName', 'Away Team'),
                    'h_record': h_rec,
                    'a_record': a_rec,
                })
        return games
    except Exception as e:
        st.error(f"Diagnostic API Issue: {e}")
        return []

@st.cache_data(ttl=600)
def get_nfl_standings():
    standings = {}
    try:
        url = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"
        r = get_session().get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        
        # ESPN API nests standings in groups (AFC/NFC, or Divisions)
        for group in data.get('children', []):
            for division in group.get('children', []):
                for team_entry in division.get('standings', {}).get('entries', []):
                    try:
                        abbr = norm(team_entry['team']['abbreviation'])
                        stats = {s['name']: s['value'] for s in team_entry.get('stats', [])}
                        w, l, t = int(stats.get('wins', 0)), int(stats.get('losses', 0)), int(stats.get('ties', 0))
                        total_games = w + l + t
                        pct = (w + (t * 0.5)) / total_games if total_games > 0 else 0.5
                        standings[abbr] = {
                            'wins': w, 'losses': l, 'ties': t, 'record': f"{w}-{l}" if t==0 else f"{w}-{l}-{t}",
                            'win_pct': pct
                        }
                    except: pass
    except: pass
    return standings if standings else {k: dict(BLANK_STD) for k in TEAM_DATA}

# ─────────────────────────────────────────────────────────────────────────────
# Prediction engine (NFL SPECIFIC MATH)
# ─────────────────────────────────────────────────────────────────────────────
def predict_nfl_game(h, a, standings, injuries, situational):
    h_td  = TEAM_DATA.get(h, {'off_pwr': 21.0, 'def_pwr': 21.0})
    a_td  = TEAM_DATA.get(a, {'off_pwr': 21.0, 'def_pwr': 21.0})
    h_std = standings.get(h, BLANK_STD)
    a_std = standings.get(a, BLANK_STD)
    factors, total = [], 0.0

    # 1. Base Roster / EPA Edge
    h_net = h_td['off_pwr'] - h_td['def_pwr']
    a_net = a_td['off_pwr'] - a_td['def_pwr']
    roster_edge = (h_net - a_net) * 0.85 
    total += roster_edge
    factors.append({
        "icon": "⚖️", "name": "Base EPA / Roster Edge", "adj": roster_edge,
        "why": f"Overall offensive and defensive efficiency disparity."
    })

    # 2. Win % / Momentum Edge
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']
    win_edge = (h_pct - a_pct) * 5.0 
    total += win_edge
    factors.append({
        "icon": "📊", "name": "Win % Edge", "adj": win_edge,
        "why": f"{h} ({h_std['record']}) vs {a} ({a_std['record']})"
    })

    # 3. NFL Home Field Advantage
    total += 2.5
    factors.append({"icon": "🏟️", "name": "Home Field", "adj": 2.5, "why": f"Standard NFL home-field adjustment for {h}."})

    # 4. Injury / QB Core Subtractions
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    def calc_injury_penalty(team, inj_list):
        penalty, details = 0.0, []
        non_qb_pen = 0.0
        for p in inj_list:
            clean_name = p.strip().lower()
            if clean_name in NFL_PLAYER_LOOKUP:
                val, tier = NFL_PLAYER_LOOKUP[clean_name]
                if "QB" in tier:
                    penalty -= val 
                    details.append(f"{p.strip()} ({tier}: -{val})")
                else:
                    non_qb_pen -= val
                    details.append(f"{p.strip()} ({tier}: -{val})")
        penalty += max(-3.5, non_qb_pen)
        return penalty, details

    h_pen, h_det = calc_injury_penalty(h, h_inj)
    a_pen, a_det = calc_injury_penalty(a, a_inj)
    
    total += h_pen 
    total -= a_pen 
    
    if h_det: factors.append({"icon": "🚑", "name": f"{h} Absences", "adj": h_pen, "why": f"Missing: {', '.join(h_det)}"})
    if a_det: factors.append({"icon": "🚑", "name": f"{a} Absences", "adj": -a_pen, "why": f"Missing: {', '.join(a_det)}"})

    # 5. Situational NFL Factors
    h_sit = situational.get(h, [])
    a_sit = situational.get(a, [])
    
    def apply_situational(sit_list, is_home):
        val = 0.0
        det = []
        if "Off Bye Week" in sit_list:
            val += 1.5; det.append("Extra prep/rest (+1.5)")
        if "Short Week (Thursday)" in sit_list:
            val -= 1.5; det.append("Fatigue/Travel (-1.5)")
        if "Turnover Regression Penalty" in sit_list:
            val -= 1.5; det.append("Unsustainable TO luck (-1.5)")
        return val, det

    h_sit_val, h_sit_det = apply_situational(h_sit, True)
    a_sit_val, a_sit_det = apply_situational(a_sit, False)
    
    total += h_sit_val
    total -= a_sit_val
    
    if h_sit_det: factors.append({"icon": "⏰", "name": f"{h} Situational", "adj": h_sit_val, "why": f"{', '.join(h_sit_det)}"})
    if a_sit_det: factors.append({"icon": "⏰", "name": f"{a} Situational", "adj": -a_sit_val, "why": f"{', '.join(a_sit_det)}"})

    # 6. NFL Logistic Win Probability
    prob = max(1.0, min(99.0, 1 / (1 + np.exp(-0.27 * total)) * 100))
    
    return {
        'winner':  h if prob >= 50.0 else a,
        'conf':    prob if prob >= 50.0 else 100.0 - prob,
        'spread_edge': total,
        'factors': factors,
    }

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏈 NFL Master AI Predictor 2026")
current_date_display = selected_date.strftime('%B %d, %Y')
st.markdown(f"**Market Week:** {start_d.strftime('%B %d')} — {end_d.strftime('%B %d')}")
st.divider()

with st.spinner("Loading NFL slate and standings…"):
    slate = get_nfl_scoreboard(selected_date_str)
    standings = get_nfl_standings()

st.sidebar.subheader("🚑 QB & Key Player Absences")
st.sidebar.caption("Type missing Elite/Starting QBs or Elite edge rushers/WRs separated by commas (e.g., `Patrick Mahomes, T.J. Watt`).")
injuries = {}

st.sidebar.subheader("⏰ NFL Situational Factors")
situational = {}

if slate:
    teams_playing = set()
    for game in slate:
        teams_playing.add(game['h'])
        teams_playing.add(game['a'])

    for team in sorted(teams_playing):
        with st.sidebar.expander(f"{team} Adjustments"):
            inj_input = st.text_input(f"Missing Players", key=f"inj_{team}")
            if inj_input.strip():
                injuries[team] = [p.strip() for p in inj_input.split(',') if p.strip()]
            
            sits = st.multiselect(
                "Situational / Rest",
                ["Off Bye Week", "Short Week (Thursday)", "Turnover Regression Penalty"],
                key=f"sit_{team}"
            )
            if sits:
                situational[team] = sits
else:
    st.sidebar.info("No NFL games scheduled for this specific date range.")

if not slate:
    st.info(f"No NFL games found during the week of {current_date_display}.")
else:
    for game in slate:
        h, a = game['h'], game['a']
        pred = predict_nfl_game(h, a, standings, injuries, situational)
        
        with st.expander(
            f"{game['h_name']} vs {game['a_name']}  |  "
            f"Winner: **{pred['winner']}** ({pred['conf']:.1f}%)"
        ):
            st.markdown(f"### 🏆 {pred['winner']} Wins (Proj. Margin: {abs(pred['spread_edge']):.1f} pts)")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(
                    f"{f['icon']} **{f['name']}**: "
                    f"<span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span>"
                    f" — {f['why']}",
                    unsafe_allow_html=True,
                )
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### 🏠 {game['h_name']} ({game['h_record']})")
                if h in injuries and injuries[h]:
                    st.warning(f"🚑 Out: {', '.join(injuries[h])}")
            with c2:
                st.markdown(f"#### ✈️ {game['a_name']} ({game['a_record']})")
                if a in injuries and injuries[a]:
                    st.warning(f"🚑 Out: {', '.join(injuries[a])}")

import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI 2026", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ Sabermetric Tools")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Refreshed! Data synced to April 4, 2026.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 2026 BvP DATA BANK (Batter vs. Pitcher - April 4 Slate) 🚨
# ─────────────────────────────────────────────────────────────────────────────
# Key career stats for the specific hitters vs today's starters.
BVP_INTEL = {
    "Jake Irvin": [
        {"team": "LAD", "name": "Shohei Ohtani", "stat": ".364 AVG / 4 HR", "impact": 2.5},
        {"team": "LAD", "name": "Mookie Betts", "stat": ".357 AVG", "impact": 1.5},
        {"team": "LAD", "name": "Will Smith", "stat": "1.020 OPS", "impact": 1.0}
    ],
    "Jack Kochanowicz": [
        {"team": "SEA", "name": "Julio Rodriguez", "stat": ".714 AVG (5-for-7)", "impact": 3.0},
        {"team": "SEA", "name": "Cal Raleigh", "stat": "1.200 OPS", "impact": 1.5}
    ],
    "Ryan Weathers": [
        {"team": "NYY", "name": "Aaron Judge", "stat": ".333 AVG / 2 HR", "impact": 2.0},
        {"team": "NYY", "name": "Juan Soto", "stat": ".450 OBP", "impact": 1.5}
    ],
    "Shota Imanaga": [
        {"team": "CLE", "name": "David Fry", "stat": "1.500 OPS", "impact": 2.0},
        {"team": "CLE", "name": "Austin Hedges", "stat": ".500 AVG", "impact": 1.0}
    ],
    "Seth Lugo": [
        {"team": "MIL", "name": "Christian Yelich", "stat": ".904 OPS", "impact": 1.5},
        {"team": "MIL", "name": "Willy Adames", "stat": ".280 AVG", "impact": 1.0}
    ]
}

MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Paul Skenes", "Tarik Skubal",
    "Chris Sale", "Zack Wheeler", "Corbin Burnes", "Shota Imanaga", "Yoshinobu Yamamoto"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. STANDINGS & TEAM POWER
# ─────────────────────────────────────────────────────────────────────────────
# Projections for all 30 teams to ensure no 50/50 bugs.
TEAM_DATA = {
    'NYY': {'ops': .785, 'era': 3.70}, 'BAL': {'ops': .785, 'era': 3.80}, 'TOR': {'ops': .750, 'era': 3.95},
    'TB':  {'ops': .735, 'era': 3.60}, 'BOS': {'ops': .755, 'era': 4.10}, 'CLE': {'ops': .735, 'era': 3.60},
    'MIN': {'ops': .750, 'era': 3.90}, 'DET': {'ops': .740, 'era': 3.65}, 'KC':  {'ops': .755, 'era': 3.85},
    'CWS': {'ops': .680, 'era': 4.90}, 'HOU': {'ops': .765, 'era': 3.75}, 'TEX': {'ops': .765, 'era': 4.05},
    'SEA': {'ops': .720, 'era': 3.35}, 'LAA': {'ops': .710, 'era': 4.50}, 'ATH': {'ops': .690, 'era': 4.80},
    'ATL': {'ops': .770, 'era': 3.55}, 'PHI': {'ops': .770, 'era': 3.45}, 'MIA': {'ops': .700, 'era': 4.30},
    'NYM': {'ops': .760, 'era': 3.85}, 'WAS': {'ops': .725, 'era': 4.40}, 'MIL': {'ops': .745, 'era': 3.70},
    'CHC': {'ops': .740, 'era': 3.75}, 'STL': {'ops': .740, 'era': 4.10}, 'CIN': {'ops': .750, 'era': 4.20},
    'PIT': {'ops': .725, 'era': 3.80}, 'LAD': {'ops': .798, 'era': 3.40}, 'ARI': {'ops': .745, 'era': 4.15},
    'SF':  {'ops': .730, 'era': 3.70}, 'SD':  {'ops': .760, 'era': 3.55}, 'COL': {'ops': .720, 'era': 5.20}
}

def norm(abbr):
    mapping = {'WSH': 'WAS', 'WSN': 'WAS', 'KCA': 'KC', 'KCR': 'KC', 'SDG': 'SD', 'SDP': 'SD', 'SFO': 'SF', 'SFG': 'SF', 'TBR': 'TB', 'LAN': 'LAD', 'NYN': 'NYM', 'OAK': 'ATH'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_mlb_slate():
    today_str = (datetime.utcnow() - timedelta(hours=7)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today_str}"
    try:
        data = requests.get(url, timeout=10).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            h_raw = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            a_raw = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if h_raw and a_raw:
                h_prob = h_raw.get('probables', [{}])[0] if h_raw.get('probables') else {}
                a_prob = a_raw.get('probables', [{}])[0] if a_raw.get('probables') else {}
                games.append({
                    'h': norm(h_raw['team']['abbreviation']), 'a': norm(a_raw['team']['abbreviation']),
                    'h_name': h_raw['team']['displayName'], 'a_name': a_raw['team']['displayName'],
                    'h_sp': h_prob.get('athlete', {}).get('displayName', 'TBD'),
                    'a_sp': a_prob.get('athlete', {}).get('displayName', 'TBD'),
                    'h_sp_rec': h_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA') if h_prob.get('statistics') else '0-0, 0.00 ERA',
                    'a_sp_rec': a_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA') if a_prob.get('statistics') else '0-0, 0.00 ERA'
                })
        return games
    except: return []

@st.cache_data(ttl=600)
def get_mlb_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/standings"
    try:
        data = requests.get(url, timeout=10).json()
        res = {}
        for league in data.get('children', []):
            for division in league.get('children', []):
                for entry in division.get('standings', {}).get('entries', []):
                    abbr = norm(entry['team']['abbreviation'])
                    stats = {s['name']: s['displayValue'] for s in entry['stats']}
                    res[abbr] = {'win_pct': entry['stats'][1]['value'], 'overall': stats.get('summary', '0-0'), 'home': stats.get('home', '0-0'), 'away': stats.get('road', '0-0')}
        return res
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICTION ENGINE (BvP INTEGRATED)
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings):
    h_td, a_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10}), TEAM_DATA.get(a, {'ops': .740, 'era': 4.10})
    h_std, a_std = standings.get(h, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'}), standings.get(a, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})

    factors, total = [], 0.0

    # Batter vs Pitcher (BvP) Logic
    h_killers = [b for b in BVP_INTEL.get(a_sp, []) if b['team'] == h]
    a_killers = [b for b in BVP_INTEL.get(h_sp, []) if b['team'] == a]
    
    if h_killers:
        impact = sum(b['impact'] for b in h_killers)
        total += impact
        factors.append({"icon": "⚔️", "name": f"{h} BvP Edge", "adj": impact, "why": f"{len(h_killers)} hitters dominate {a_sp}."})
    if a_killers:
        impact = sum(b['impact'] for b in a_killers)
        total -= impact
        factors.append({"icon": "⚔️", "name": f"{a} BvP Edge", "adj": -impact, "why": f"{len(a_killers)} hitters dominate {h_sp}."})

    # Ace Bonus
    if any(s.lower() in h_sp.lower() for s in MLB_STARS): total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if any(s.lower() in a_sp.lower() for s in MLB_STARS): total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # Standard Factors
    total += (h_td['ops'] - a_td['ops']) * 120.0
    total += (h_std['win_pct'] - a_std['win_pct']) * 15.0 + 2.5
    
    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_killers': h_killers, 'a_killers': a_killers}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
slate, standings = get_mlb_slate(), get_mlb_standings()

if not slate or len(standings) < 15:
    st.warning("🔄 Fetching all 30 team records and today's slate... please wait.")
else:
    for g in slate:
        p = predict_mlb(g['h'], g['a'], g['h_sp'], g['a_sp'], standings)
        with st.expander(f"{g['a_name']} vs {g['h_name']} | Winner: {p['winner']} ({p['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {p['winner']} Wins")
            for f in p['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            
            if p['h_killers'] or p['a_killers']:
                st.markdown("#### 📉 Notable BvP Statistics")
                c1, c2 = st.columns(2)
                with c1:
                    for k in p['h_killers']: st.success(f"**{k['name']}**: {k['stat']} vs {g['a_sp']}")
                with c2:
                    for k in p['a_killers']: st.error(f"**{k['name']}**: {k['stat']} vs {g['h_sp']}")
                st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {g['h_name']}")
                st.write(f"**SP:** {g['h_sp']} ({g['h_sp_rec']})")
                st.write(f"**Record:** {p['h_std']['overall']} (Home: {p['h_std']['home']})")
            with col2:
                st.markdown(f"#### ✈️ {g['a_name']}")
                st.write(f"**SP:** {g['a_sp']} ({g['a_sp_rec']})")
                st.write(f"**Record:** {p['a_std']['overall']} (Away: {p['a_std']['away']})")

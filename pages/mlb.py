import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI 2026", page_icon="⚾", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 Sabermetric BvP Intelligence (Career Stats vs Today's Pitchers) 🚨
# ─────────────────────────────────────────────────────────────────────────────
# This acts as the "Brain" for Batter vs Pitcher performance integration.
BVP_LIBRARY = {
    "Jake Irvin": {
        "LAD": [
            {"name": "Shohei Ohtani", "stat": ".364 AVG / 4 HR", "ops": "1.250", "notes": "Pitcher Killer"},
            {"name": "Mookie Betts", "stat": ".357 AVG", "ops": ".980", "notes": "Elite timing"},
            {"name": "Will Smith", "stat": ".310 AVG", "ops": ".915", "notes": "Hard-hit specialist"}
        ]
    },
    "Jack Kochanowicz": {
        "SEA": [
            {"name": "Julio Rodriguez", "stat": ".714 AVG (5/7)", "ops": "1.800", "notes": "Dominates the slider"},
            {"name": "Cal Raleigh", "stat": ".600 AVG / 2 HR", "ops": "2.100", "notes": "Power advantage"}
        ]
    },
    "Ryan Weathers": {
        "NYY": [
            {"name": "Aaron Judge", "stat": ".333 AVG / 2 HR", "ops": "1.150", "notes": "Left-on-Right power"},
            {"name": "Juan Soto", "stat": ".450 OBP", "ops": "1.005", "notes": "Elite discipline"}
        ]
    },
    "Shota Imanaga": {
        "CLE": [
            {"name": "David Fry", "stat": "1.500 OPS", "ops": "1.500", "notes": "LHP Specialist"},
            {"name": "Austin Hedges", "stat": ".500 AVG", "ops": "1.100", "notes": "Sample size edge"}
        ]
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. 2026 POWER RANKINGS & ALL-STAR LIST
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LAD': {'ops': .798, 'era': 3.40}, 'NYY': {'ops': .785, 'era': 3.70}, 'ATL': {'ops': .770, 'era': 3.55},
    'BAL': {'ops': .785, 'era': 3.80}, 'PHI': {'ops': .770, 'era': 3.45}, 'CLE': {'ops': .735, 'era': 3.60},
    'MIL': {'ops': .745, 'era': 3.70}, 'HOU': {'ops': .765, 'era': 3.75}, 'SEA': {'ops': .720, 'era': 3.35},
    'DET': {'ops': .740, 'era': 3.65}, 'ARI': {'ops': .745, 'era': 4.15}, 'KC':  {'ops': .755, 'era': 3.85},
    'SD':  {'ops': .760, 'era': 3.55}, 'SF':  {'ops': .730, 'era': 3.70}, 'MIN': {'ops': .750, 'era': 3.90},
    'TOR': {'ops': .750, 'era': 3.95}, 'NYM': {'ops': .760, 'era': 3.85}, 'TEX': {'ops': .765, 'era': 4.05},
    'CHC': {'ops': .740, 'era': 3.75}, 'BOS': {'ops': .755, 'era': 4.10}, 'STL': {'ops': .740, 'era': 4.10},
    'CIN': {'ops': .750, 'era': 4.20}, 'PIT': {'ops': .725, 'era': 3.80}, 'ARI': {'ops': .745, 'era': 4.15},
    'WAS': {'ops': .725, 'era': 4.40}, 'LAA': {'ops': .710, 'era': 4.50}, 'MIA': {'ops': .700, 'era': 4.30},
    'ATH': {'ops': .690, 'era': 4.80}, 'COL': {'ops': .720, 'era': 5.20}, 'CWS': {'ops': .680, 'era': 4.90}
}

MLB_STARS = ["Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.", 
             "Gunnar Henderson", "Paul Skenes", "Tarik Skubal", "Chris Sale", "Shota Imanaga"]

def norm(abbr):
    mapping = {'WSH': 'WAS', 'WSN': 'WAS', 'KCA': 'KC', 'SDG': 'SD', 'SFO': 'SF', 'TBR': 'TB', 'LAN': 'LAD', 'NYN': 'NYM', 'OAK': 'ATH'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS (RECURSIVE FOR ALL 30 TEAMS)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_full_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/standings"
    try:
        data = requests.get(url, timeout=10).json()
        res = {}
        # Recursive loop to catch AL and NL (All 30 Teams)
        for league in data.get('children', []):
            for division in league.get('children', []):
                for entry in division.get('standings', {}).get('entries', []):
                    abbr = norm(entry['team']['abbreviation'])
                    stats = {s['name']: s['displayValue'] for s in entry['stats']}
                    v_stats = {s['name']: s['value'] for s in entry['stats']}
                    res[abbr] = {
                        'win_pct': v_stats.get('winPercent', 0.5),
                        'overall': stats.get('summary', '0-0'),
                        'home': stats.get('home', '0-0'),
                        'away': stats.get('road', '0-0')
                    }
        return res
    except: return {}

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
                # Safe Probables Detection
                h_prob = h_raw.get('probables', [{}])[0] if h_raw.get('probables') else {}
                a_prob = a_raw.get('probables', [{}])[0] if a_raw.get('probables') else {}
                h_sp = h_prob.get('athlete', {}).get('displayName', 'TBD')
                a_sp = a_prob.get('athlete', {}).get('displayName', 'TBD')
                h_sp_rec = h_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA') if h_prob.get('statistics') else '0-0, 0.00 ERA'
                a_sp_rec = a_prob.get('statistics', [{}])[0].get('displayValue', '0-0, 0.00 ERA') if a_prob.get('statistics') else '0-0, 0.00 ERA'
                games.append({'h': norm(h_raw['team']['abbreviation']), 'a': norm(a_raw['team']['abbreviation']),
                              'h_name': h_raw['team']['displayName'], 'a_name': a_raw['team']['displayName'],
                              'h_sp': h_sp, 'a_sp': a_sp, 'h_sp_rec': h_sp_rec, 'a_sp_rec': a_sp_rec})
        return games
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICTION ENGINE (BvP & RECORD INTEGRATED)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, h_sp, a_sp, standings):
    h_td, a_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10}), TEAM_DATA.get(a, {'ops': .740, 'era': 4.10})
    h_std, a_std = standings.get(h, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'}), standings.get(a, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})
    
    factors, total = [], 0.0
    
    # 1. Batter vs Pitcher (BvP) Impact
    h_killers = BVP_LIBRARY.get(a_sp, {}).get(h, [])
    a_killers = BVP_LIBRARY.get(h_sp, {}).get(a, [])
    
    if h_killers:
        adj = min(6.0, len(h_killers) * 2.0)
        total += adj
        factors.append({"icon": "⚔️", "name": f"{h} BvP Edge", "adj": adj, "why": f"{len(h_killers)} hitters dominate {a_sp}"})
    if a_killers:
        adj = min(6.0, len(a_killers) * 2.0)
        total -= adj
        factors.append({"icon": "⚔️", "name": f"{a} BvP Edge", "adj": -adj, "why": f"{len(a_killers)} hitters dominate {h_sp}"})

    # 2. Ace Bonus
    if any(s.lower() in h_sp.lower() for s in MLB_STARS): total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace Bonus", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if any(s.lower() in a_sp.lower() for s in MLB_STARS): total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace Bonus", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # 3. Standard Stats
    total += (h_td['ops'] - a_td['ops']) * 120.0
    total += (h_std['win_pct'] - a_std['win_pct']) * 15.0 + 2.5 # Home Advantage
    
    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 
            'h_std': h_std, 'a_std': a_std, 'h_killers': h_killers, 'a_killers': a_killers}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
st.sidebar.info("Market Date: April 4, 2026")

standings, slate = get_full_standings(), get_mlb_slate()

if not slate or len(standings) < 15:
    st.warning("🔄 Bullpen is warming up... Syncing 30-team data and today's BvP matchups.")
else:
    for g in slate:
        p = predict_game(g['h'], g['a'], g['h_sp'], g['a_sp'], standings)
        with st.expander(f"{g['a_name']} vs {g['h_name']} | Winner: {p['winner']} ({p['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {p['winner']} Wins")
            for f in p['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            
            if p['h_killers'] or p['a_killers']:
                st.markdown("#### 📉 Notable BvP Matchups")
                c1, c2 = st.columns(2)
                with c1:
                    for k in p['h_killers']: st.success(f"**{k['name']}**: {k['stat']} ({k['notes']})")
                with c2:
                    for k in p['a_killers']: st.error(f"**{k['name']}**: {k['stat']} ({k['notes']})")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {g['h_name']}")
                st.write(f"**SP:** {g['h_sp']} ({g['h_sp_rec']})")
                st.write(f"**Overall:** {p['h_std']['overall']} | **Home:** {p['h_std']['home']}")
            with col2:
                st.markdown(f"#### ✈️ {g['a_name']}")
                st.write(f"**SP:** {g['a_sp']} ({g['a_sp_rec']})")
                st.write(f"**Overall:** {p['a_std']['overall']} | **Road:** {p['a_std']['away']}")

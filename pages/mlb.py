import streamlit as st
import requests
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="MLB Master AI 2026", page_icon="⚾", layout="wide")

st.sidebar.title("⚙️ Diamond Intelligence")
if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Refreshed! Syncing to April 4, 2026.")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 2026 BvP DATA BANK (Batter vs. Pitcher - April 4 Slate) 🚨
# ─────────────────────────────────────────────────────────────────────────────
# Data includes career career slash lines for hitters vs today's SP.
BVP_INTEL = {
    ("LAD", "Jake Irvin"): [
        {"name": "Mookie Betts", "stat": ".357 AVG", "desc": "Elite timing"},
        {"name": "Shohei Ohtani", "stat": ".364 AVG / 4 HR", "desc": "Pitcher Killer"},
        {"name": "Will Smith", "stat": "1.020 OPS", "desc": "Consistently hits hard"}
    ],
    ("SEA", "Jack Kochanowicz"): [
        {"name": "Julio Rodriguez", "stat": ".714 AVG (5-for-7)", "desc": "Dominates the slider"},
        {"name": "Cal Raleigh", "stat": ".600 AVG / 2 HR", "desc": "High power matchup"}
    ],
    ("NYY", "Ryan Weathers"): [
        {"name": "Aaron Judge", "stat": ".333 AVG / 2 HR", "desc": "Power edge"},
        {"name": "Juan Soto", "stat": ".450 OBP", "desc": "Plate discipline edge"}
    ],
    ("CLE", "Shota Imanaga"): [
        {"name": "David Fry", "stat": "1.500 OPS", "desc": "Left-handed specialist"},
        {"name": "Austin Hedges", "stat": ".500 AVG", "desc": "Small sample dominance"}
    ],
    ("ATL", "Michael Soroka"): [
        {"name": "Marcell Ozuna", "stat": ".412 AVG", "desc": "Historical success"},
        {"name": "Ozzie Albies", "stat": ".305 AVG", "desc": "Line drive threat"}
    ]
}

MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Ronald Acuña Jr.", "Yordan Alvarez",
    "Paul Skenes", "Tarik Skubal", "Chris Sale", "Zack Wheeler", "Corbin Burnes",
    "Logan Webb", "Shota Imanaga", "Yoshinobu Yamamoto", "Tyler Glasnow"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. FULL 30-TEAM 2026 POWER DATA
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    # AL East
    'NYY': {'ops': .785, 'era': 3.70}, 'BAL': {'ops': .785, 'era': 3.80},
    'TOR': {'ops': .750, 'era': 3.95}, 'TB':  {'ops': .735, 'era': 3.60}, 'BOS': {'ops': .755, 'era': 4.10},
    # AL Central
    'CLE': {'ops': .735, 'era': 3.60}, 'MIN': {'ops': .750, 'era': 3.90}, 
    'DET': {'ops': .740, 'era': 3.65}, 'KC':  {'ops': .755, 'era': 3.85}, 'CWS': {'ops': .680, 'era': 4.90},
    # AL West
    'HOU': {'ops': .765, 'era': 3.75}, 'TEX': {'ops': .765, 'era': 4.05}, 
    'SEA': {'ops': .720, 'era': 3.35}, 'LAA': {'ops': .710, 'era': 4.50}, 'ATH': {'ops': .690, 'era': 4.80},
    # NL East
    'ATL': {'ops': .770, 'era': 3.55}, 'PHI': {'ops': .770, 'era': 3.45}, 
    'MIA': {'ops': .700, 'era': 4.30}, 'NYM': {'ops': .760, 'era': 3.85}, 'WAS': {'ops': .725, 'era': 4.40},
    # NL Central
    'MIL': {'ops': .745, 'era': 3.70}, 'CHC': {'ops': .740, 'era': 3.75}, 
    'STL': {'ops': .740, 'era': 4.10}, 'CIN': {'ops': .750, 'era': 4.20}, 'PIT': {'ops': .725, 'era': 3.80},
    # NL West
    'LAD': {'ops': .798, 'era': 3.40}, 'ARI': {'ops': .745, 'era': 4.15}, 
    'SF':  {'ops': .730, 'era': 3.70}, 'SD':  {'ops': .760, 'era': 3.55}, 'COL': {'ops': .720, 'era': 5.20}
}

def norm(abbr):
    mapping = {
        'WSH': 'WAS', 'WSN': 'WAS', 'KCA': 'KC', 'KCR': 'KC', 'SDG': 'SD', 'SDP': 'SD',
        'SFO': 'SF', 'SFG': 'SF', 'TBR': 'TB', 'TBA': 'TB', 'CHW': 'CWS', 'LAN': 'LAD', 
        'NYN': 'NYM', 'CHN': 'CHC', 'OAK': 'ATH', 'SAC': 'ATH'
    }
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
        # Robust 30-team crawler
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

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICTION ENGINE (BvP INTEGRATED)
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings):
    h_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10})
    a_td = TEAM_DATA.get(a, {'ops': .740, 'era': 4.10})
    h_std = standings.get(h, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})
    a_std = standings.get(a, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})

    factors, total = [], 0.0
    def is_star(name): return any(s.lower() in name.lower() for s in MLB_STARS)

    # 1. Batter vs. Pitcher Matchups
    h_bvp_list = BVP_INTEL.get((h, a_sp), [])
    a_bvp_list = BVP_INTEL.get((a, h_sp), [])
    
    if h_bvp_list:
        edge = min(5.5, len(h_bvp_list) * 1.8) # Cap BvP impact
        total += edge
        b_summary = ", ".join([f"{b['name']} ({b['stat']})" for b in h_bvp_list])
        factors.append({"icon": "⚔️", "name": f"{h} BvP Edge", "adj": edge, "why": f"Key Matchups vs {a_sp}: {b_summary}"})
    if a_bvp_list:
        edge = min(5.5, len(a_bvp_list) * 1.8)
        total -= edge
        b_summary = ", ".join([f"{b['name']} ({b['stat']})" for b in a_bvp_list])
        factors.append({"icon": "⚔️", "name": f"{a} BvP Edge", "adj": -edge, "why": f"Key Matchups vs {h_sp}: {b_summary}"})

    # 2. Starting Pitcher Star Status
    if is_star(h_sp): total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace Bonus", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if is_star(a_sp): total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace Bonus", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # 3. OPS & ERA Differentials
    ops_diff = (h_td['ops'] - a_td['ops']) * 120.0
    total += ops_diff
    win_adj = (h_std['win_pct'] - a_std['win_pct']) * 15.0
    total += win_adj + 2.5 # Base Home Field
    
    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_bvp': h_bvp_list, 'a_bvp': a_bvp_list}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
slate, standings = get_mlb_slate(), get_mlb_standings()

if not slate or len(standings) < 10:
    st.warning("Fetching data from the bullpen... Please wait or refresh.")
else:
    for g in slate:
        p = predict_mlb(g['h'], g['a'], g['h_sp'], g['a_sp'], standings)
        with st.expander(f"{g['a_name']} at {g['h_name']} | Winner: {p['winner']} ({p['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {p['winner']} Wins")
            for f in p['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            st.divider()
            
            # Batter vs Pitcher Section
            if p['h_bvp'] or p['a_bvp']:
                st.markdown("#### 📉 Notable Batter vs Pitcher Stats")
                b1, b2 = st.columns(2)
                with b1:
                    for b in p['h_bvp']: st.success(f"**{b['name']}**: {b['stat']} — {b['desc']}")
                with b2:
                    for b in p['a_bvp']: st.error(f"**{b['name']}**: {b['stat']} — {b['desc']}")
                st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {g['h_name']}")
                st.write(f"**SP:** {g['h_sp']} ({g['h_sp_rec']})")
                st.write(f"**Overall Record:** {p['h_std']['overall']} | **Home:** {p['h_std']['home']}")
            with col2:
                st.markdown(f"#### ✈️ {g['a_name']}")
                st.write(f"**SP:** {g['a_sp']} ({g['a_sp_rec']})")
                st.write(f"**Overall Record:** {p['a_std']['overall']} | **Road:** {p['a_std']['away']}")

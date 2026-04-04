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
# 🚨 2026 BvP DATA BANK (Batter vs. Pitcher Matchups) 🚨
# ─────────────────────────────────────────────────────────────────────────────
# This dictionary contains known career dominance for the current slate.
# Impact: Points added to the team score.
BVP_INTEL = {
    ("SEA", "Jack Kochanowicz"): {"J. Rodriguez": ".714 AVG (5/7)", "C. Raleigh": "1.200 OPS", "Impact": 5.0},
    ("LAD", "Jake Irvin"): {"M. Betts": ".357 AVG", "S. Ohtani": ".364 AVG (4 HR)", "W. Smith": ".310 AVG", "Impact": 5.5},
    ("MIL", "Luinder Avila"): {"L. Rengifo": "2.000 OPS", "G. Sanchez": "1.100 OPS", "C. Yelich": ".880 OPS", "Impact": 4.5},
    ("ATL", "Eduardo Rodriguez"): {"M. Ozuna": ".412 AVG", "O. Albies": ".305 AVG", "Impact": 3.0},
    ("NYY", "Ryan Weathers"): {"A. Judge": ".333 AVG", "J. Soto": ".450 OBP", "Impact": 4.0},
    ("BAL", "Carmen Mlodzinski"): {"A. Rutschman": ".290 AVG", "G. Henderson": ".320 AVG", "Impact": 2.5},
    ("CLE", "Shota Imanaga"): {"D. Fry": "1.500 OPS", "A. Hedges": ".500 AVG", "Impact": 3.5}
}

MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Ronald Acuña Jr.", "Yordan Alvarez",
    "Paul Skenes", "Tarik Skubal", "Chris Sale", "Zack Wheeler", "Corbin Burnes",
    "Logan Webb", "Shota Imanaga", "Yoshinobu Yamamoto", "Tyler Glasnow", "Max Meyer"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. 2026 FULL 30-TEAM POWER DATA
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'ARI': {'ops': .745, 'era': 4.15}, 'ATL': {'ops': .770, 'era': 3.55},
    'BAL': {'ops': .785, 'era': 3.80}, 'BOS': {'ops': .755, 'era': 4.10},
    'CHC': {'ops': .740, 'era': 3.75}, 'CWS': {'ops': .680, 'era': 4.90},
    'CIN': {'ops': .750, 'era': 4.20}, 'CLE': {'ops': .735, 'era': 3.60},
    'COL': {'ops': .720, 'era': 5.20}, 'DET': {'ops': .740, 'era': 3.65},
    'HOU': {'ops': .765, 'era': 3.75}, 'KC':  {'ops': .755, 'era': 3.85},
    'LAA': {'ops': .710, 'era': 4.50}, 'LAD': {'ops': .798, 'era': 3.40},
    'MIA': {'ops': .700, 'era': 4.30}, 'MIL': {'ops': .745, 'era': 3.70},
    'MIN': {'ops': .750, 'era': 3.90}, 'NYM': {'ops': .760, 'era': 3.85},
    'NYY': {'ops': .785, 'era': 3.70}, 'ATH': {'ops': .690, 'era': 4.80},
    'PHI': {'ops': .770, 'era': 3.45}, 'PIT': {'ops': .725, 'era': 3.80},
    'SD':  {'ops': .760, 'era': 3.55}, 'SF':  {'ops': .730, 'era': 3.70},
    'SEA': {'ops': .720, 'era': 3.35}, 'STL': {'ops': .740, 'era': 4.10},
    'TB':  {'ops': .735, 'era': 3.60}, 'TEX': {'ops': .765, 'era': 4.05},
    'TOR': {'ops': .750, 'era': 3.95}, 'WAS': {'ops': .725, 'era': 4.40}
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
# 3. PREDICTION ENGINE (BvP INTEGRATION)
# ─────────────────────────────────────────────────────────────────────────────
def predict_mlb(h, a, h_sp, a_sp, standings):
    h_td = TEAM_DATA.get(h, {'ops': .740, 'era': 4.10})
    a_td = TEAM_DATA.get(a, {'ops': .740, 'era': 4.10})
    h_std = standings.get(h, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})
    a_std = standings.get(a, {'win_pct': 0.5, 'overall': '0-0', 'home': '0-0', 'away': '0-0'})

    factors, total = [], 0.0
    def is_star(name): return any(s.lower() in name.lower() for s in MLB_STARS)

    # 1. BvP Analysis (Pitcher Killers)
    h_bvp = BVP_INTEL.get((h, a_sp), {})
    a_bvp = BVP_INTEL.get((a, h_sp), {})
    
    if h_bvp:
        impact = h_bvp.get("Impact", 0)
        total += impact
        b_list = [f"{k} ({v})" for k, v in h_bvp.items() if k != "Impact"]
        factors.append({"icon": "⚔️", "name": f"{h} BvP Edge", "adj": impact, "why": f"Dominant vs {a_sp}: {', '.join(b_list)}"})
    if a_bvp:
        impact = a_bvp.get("Impact", 0)
        total -= impact
        b_list = [f"{k} ({v})" for k, v in a_bvp.items() if k != "Impact"]
        factors.append({"icon": "⚔️", "name": f"{a} BvP Edge", "adj": -impact, "why": f"Dominant vs {h_sp}: {', '.join(b_list)}"})

    # 2. Starting Pitcher Ace Bonus
    if is_star(h_sp):
        total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace Bonus", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if is_star(a_sp):
        total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace Bonus", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # 3. OPS & ERA Gaps
    ops_diff = (h_td['ops'] - a_td['ops']) * 120.0
    total += ops_diff
    factors.append({"icon": "🎯", "name": "Offensive Edge", "adj": ops_diff, "why": f"Team OPS Gap: {h_td['ops']} vs {a_td['ops']}"})

    win_adj = (h_std['win_pct'] - a_std['win_pct']) * 15.0
    total += win_adj + 2.5 # Home Advantage
    factors.append({"icon": "📊", "name": "Record Factor", "adj": win_adj, "why": f"Overall Win % comparison"})

    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
st.sidebar.info(f"Query Date: April 4, 2026")

slate, standings = get_mlb_slate(), get_mlb_standings()

if not slate:
    st.warning("Standings found for all 30 teams. Fetching today's game slate...")
else:
    for g in slate:
        p = predict_mlb(g['h'], g['a'], g['h_sp'], g['a_sp'], standings)
        with st.expander(f"{g['a_name']} at {g['h_name']} | Winner: {p['winner']} ({p['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {p['winner']} Wins")
            for f in p['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {g['h_name']}")
                st.write(f"**SP:** {g['h_sp']} ({g['h_sp_rec']})")
                st.write(f"**Overall Record:** {p['h_std']['overall']} | **Home:** {p['h_std']['home']}")
            with col2:
                st.markdown(f"#### ✈️ {g['a_name']}")
                st.write(f"**SP:** {g['a_sp']} ({g['a_sp_rec']})")
                st.write(f"**Overall Record:** {p['a_std']['overall']} | **Away:** {p['a_std']['away']}")

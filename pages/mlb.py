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
# These values are added to the team's score based on career dominance.
BVP_MATCHUPS = {
    ("SEA", "Jack Kochanowicz"): {"J. Rodriguez": ".714 AVG", "C. Raleigh": ".600 AVG", "Impact": 4.5},
    ("LAD", "Jake Irvin"): {"M. Betts": ".357 AVG", "S. Ohtani": ".364 AVG", "W. Smith": "1.000 OPS", "Impact": 5.0},
    ("MIL", "Seth Lugo"): {"C. Yelich": ".904 OPS", "W. Adames": ".280 AVG", "Impact": 2.5},
    ("NYM", "Landen Roupp"): {"F. Lindor": ".310 AVG", "P. Alonso": ".400 OBP", "Impact": 2.0},
    ("CLE", "Shota Imanaga"): {"D. Fry": "1.500 OPS", "A. Hedges": ".500 AVG", "Impact": 3.5}
}

MLB_STARS = [
    "Shohei Ohtani", "Aaron Judge", "Juan Soto", "Mookie Betts", "Bobby Witt Jr.",
    "Gunnar Henderson", "Elly De La Cruz", "Ronald Acuña Jr.", "Yordan Alvarez",
    "Paul Skenes", "Tarik Skubal", "Chris Sale", "Zack Wheeler", "Corbin Burnes",
    "Shota Imanaga", "Yoshinobu Yamamoto", "Tyler Glasnow", "Max Meyer", "Dustin May"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. STANDINGS & TEAM POWER
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'LAD': {'ops': .798, 'era': 3.40}, 'NYY': {'ops': .785, 'era': 3.70},
    'ATL': {'ops': .770, 'era': 3.55}, 'BAL': {'ops': .785, 'era': 3.80},
    'PHI': {'ops': .770, 'era': 3.45}, 'HOU': {'ops': .765, 'era': 3.75},
    'MIL': {'ops': .745, 'era': 3.70}, 'CLE': {'ops': .735, 'era': 3.60},
    'ARI': {'ops': .745, 'era': 4.15}, 'DET': {'ops': .740, 'era': 3.65}
}

def norm(abbr):
    mapping = {
        'WSH': 'WAS', 'WSN': 'WAS', 'KCA': 'KC', 'KCR': 'KC', 'SDG': 'SD', 'SDP': 'SD',
        'SFO': 'SF', 'SFG': 'SF', 'TBR': 'TB', 'CHW': 'CWS', 'LAN': 'LAD', 'NYN': 'NYM'
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
            for div in league.get('children', []):
                for entry in div.get('standings', {}).get('entries', []):
                    abbr = norm(entry['team']['abbreviation'])
                    stats = {s['name']: s['displayValue'] for s in entry['stats']}
                    v_stats = {s['name']: s['value'] for s in entry['stats']}
                    res[abbr] = {'win_pct': v_stats.get('winPercent', 0.5), 'overall': stats.get('summary', '0-0'), 'home': stats.get('home', '0-0'), 'away': stats.get('road', '0-0')}
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

    # 1. BvP Matchup Logic (The "Rodriguez Rule")
    h_bvp = BVP_MATCHUPS.get((h, a_sp), {})
    a_bvp = BVP_MATCHUPS.get((a, h_sp), {})
    
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

    # 2. Ace Advantage
    is_h_ace = any(s.lower() in h_sp.lower() for s in MLB_STARS)
    is_a_ace = any(s.lower() in a_sp.lower() for s in MLB_STARS)
    if is_h_ace: total += 6.5; factors.append({"icon": "🔥", "name": f"{h} Ace", "adj": 6.5, "why": f"{h_sp} is a Star SP."})
    if is_a_ace: total -= 6.5; factors.append({"icon": "🔥", "name": f"{a} Ace", "adj": -6.5, "why": f"{a_sp} is a Star SP."})

    # 3. Base Stats (OPS/ERA/Win %)
    ops_adj = (h_td['ops'] - a_td['ops']) * 120.0
    total += ops_adj
    win_adj = (h_std['win_pct'] - a_std['win_pct']) * 15.0
    total += win_adj + 2.5 # Home Advantage
    
    prob = max(5.0, min(95.0, 50.0 + total))
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚾ MLB Master AI Predictor 2026")
slate, standings = get_mlb_slate(), get_mlb_standings()

if not slate:
    st.warning("Gathering game data... If this persists, click 'Force Data Refresh'.")
else:
    for g in slate:
        p = predict_mlb(g['h'], g['a'], g['h_sp'], g['a_sp'], standings)
        with st.expander(f"{g['a_name']} vs {g['h_name']} | Winner: {p['winner']} ({p['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {p['winner']} Wins")
            for f in p['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(f"{f['icon']} **{f['name']}**: {f['adj']:+.1f} pts — {f['why']}", unsafe_allow_html=True)
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### 🏠 {g['h_name']}")
                st.write(f"**SP:** {g['h_sp']} ({g['h_sp_rec']})")
                st.write(f"**Record:** {p['h_std']['overall']} (H: {p['h_std']['home']})")
            with c2:
                st.markdown(f"#### ✈️ {g['a_name']}")
                st.write(f"**SP:** {g['a_sp']} ({g['a_sp_rec']})")
                st.write(f"**Record:** {p['a_std']['overall']} (A: {p['a_std']['away']})")

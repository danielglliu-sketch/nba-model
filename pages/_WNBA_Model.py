import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="WNBA Quant AI 2026", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ System Tools")

debug_mode = st.sidebar.checkbox("🐞 Enable API Debugger")

# --- DATE SELECTOR ---
selected_date = st.sidebar.date_input("📅 Select Slate Date", datetime.now().date())
target_date_str = selected_date.strftime('%Y%m%d')
yest_date_str = (selected_date - timedelta(days=1)).strftime('%Y%m%d')
display_date_str = selected_date.strftime('%B %d, %Y')

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! The app is pulling fresh WNBA data.")

st.sidebar.markdown("---")
st.sidebar.caption("WNBA v1.1 | 40-Min Recalibration | Historical Backtesting Active")

# ─────────────────────────────────────────────────────────────────────────────
# 🚨 MANUAL OVERRIDES & WNBA PLAYER TIERS (2026) 🚨
# ─────────────────────────────────────────────────────────────────────────────

# SUPERSTARS (-8.0) - The MVP Level Game-Changers
SUPERSTARS = [
    "A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier", 
    "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu"
]

# ALL-STARS (-4.5) - #2 Options, Consistent Elite Players
ALL_STARS = [
    "Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike", 
    "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale", 
    "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston", 
    "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor"
]

# HIGH-IMPACT (-2.5) - Crucial Starters & Defensive Anchors
HIGH_IMPACT = [
    "Natasha Howard", "Marina Mabrey", "Courtney Vandersloot", "Betnijah Laney-Hamilton",
    "Brionna Jones", "Dearica Hamby", "Allisha Gray", "Rhyne Howard", "Kayla McBride",
    "Natasha Cloud", "Kelsey Mitchell", "NaLyssa Smith", "Brittney Griner",
    "Cheyenne Parker-Tyus", "Courtney Williams", "Alanna Smith", "Sophie Cunningham"
]

# WNBA ARCHETYPES
DEFENSIVE_LIABILITIES = [
    "Caitlin Clark", "Arike Ogunbowale", "Kelsey Mitchell", "Marina Mabrey", "Diana Taurasi"
]

OFFENSIVE_LIABILITIES = [
    "Alyssa Thomas", "Ezi Magbegor", "Brianna Turner", "Kiah Stokes"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. STANDINGS & BACKUPS (12 Teams)
# ─────────────────────────────────────────────────────────────────────────────
BACKUP_STANDINGS = {
    'LV': {'wins': 34, 'losses': 6, 'record': '34-6', 'win_pct': 0.850, 'l10_pct': 0.8},
    'NY': {'wins': 32, 'losses': 8, 'record': '32-8', 'win_pct': 0.800, 'l10_pct': 0.7},
    'CONN': {'wins': 27, 'losses': 13, 'record': '27-13', 'win_pct': 0.675, 'l10_pct': 0.6},
    'SEA': {'wins': 25, 'losses': 15, 'record': '25-15', 'win_pct': 0.625, 'l10_pct': 0.6},
    'MIN': {'wins': 24, 'losses': 16, 'record': '24-16', 'win_pct': 0.600, 'l10_pct': 0.5},
    'IND': {'wins': 22, 'losses': 18, 'record': '22-18', 'win_pct': 0.550, 'l10_pct': 0.6},
    'DAL': {'wins': 20, 'losses': 20, 'record': '20-20', 'win_pct': 0.500, 'l10_pct': 0.5},
    'ATL': {'wins': 19, 'losses': 21, 'record': '19-21', 'win_pct': 0.475, 'l10_pct': 0.4},
    'PHO': {'wins': 16, 'losses': 24, 'record': '16-24', 'win_pct': 0.400, 'l10_pct': 0.4},
    'CHI': {'wins': 14, 'losses': 26, 'record': '14-26', 'win_pct': 0.350, 'l10_pct': 0.3},
    'LA': {'wins': 11, 'losses': 29, 'record': '11-29', 'win_pct': 0.275, 'l10_pct': 0.2},
    'WAS': {'wins': 9, 'losses': 31, 'record': '9-31', 'win_pct': 0.225, 'l10_pct': 0.2},
}

# Projected Baseline Net Ratings for 2026 (Adjusted for 40-minute pacing)
TEAM_DATA = {
    'LV': {'off_rtg': 110.5, 'def_rtg': 99.8}, 
    'NY': {'off_rtg': 109.2, 'def_rtg': 100.5},
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2}, 
    'SEA': {'off_rtg': 103.5, 'def_rtg': 98.8},
    'MIN': {'off_rtg': 102.8, 'def_rtg': 99.1}, 
    'IND': {'off_rtg': 106.5, 'def_rtg': 105.2},
    'DAL': {'off_rtg': 105.1, 'def_rtg': 104.8}, 
    'ATL': {'off_rtg': 100.2, 'def_rtg': 101.5},
    'PHO': {'off_rtg': 99.5, 'def_rtg': 106.1}, 
    'CHI': {'off_rtg': 98.2, 'def_rtg': 103.5},
    'LA': {'off_rtg': 96.8, 'def_rtg': 105.2}, 
    'WAS': {'off_rtg': 97.5, 'def_rtg': 108.4}
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS (Brute-Force Fix)
# ─────────────────────────────────────────────────────────────────────────────
def norm(abbr):
    mapping = {'LVA': 'LV', 'NYL': 'NY', 'CON': 'CONN', 'PHX': 'PHO', 'LAS': 'LA', 'MINN': 'MIN', 'WSH': 'WAS'}
    return mapping.get(str(abbr).upper(), str(abbr).upper())

@st.cache_data(ttl=300)
def get_daily_slate(date_string):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_string}"
    try:
        data = requests.get(url, timeout=5).json()
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)
            if home and away:
                games.append({'h': norm(home['team']['abbreviation']), 'a': norm(away['team']['abbreviation']),
                              'h_name': home['team']['displayName'], 'a_name': away['team']['displayName']})
        return games if games else []
    except: return []

@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/standings"
    try:
        data = requests.get(url, timeout=8).json()
        result = {}
        
        # BRUTE FORCE JSON SEARCH
        def extract_entries(node):
            found = []
            if isinstance(node, dict):
                if 'team' in node and 'stats' in node:
                    found.append(node)
                for key, val in node.items():
                    found.extend(extract_entries(val))
            elif isinstance(node, list):
                for item in node:
                    found.extend(extract_entries(item))
            return found

        entries = extract_entries(data)
        
        for entry in entries:
            abbr = norm(entry['team']['abbreviation'])
            stats = {str(s.get('name', '')).lower(): s for s in entry.get('stats', []) if isinstance(s, dict)}
            
            wins = int(stats.get('wins', {}).get('value', 0))
            losses = int(stats.get('losses', {}).get('value', 0))
            win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.500
            
            l10_record = "0-0"
            for key in ['lasttengames', 'lastten', 'last10', 'l10', 'last10games']:
                if key in stats:
                    l10_record = stats[key].get('displayValue', '0-0')
                    break
                    
            if l10_record == "0-0" and 'records' in entry:
                for rec in entry['records']:
                    if isinstance(rec, dict) and rec.get('name') == 'lastTen':
                        l10_record = rec.get('summary', '0-0')
                        break
                        
            try:
                l10_w, l10_l = map(int, l10_record.split('-'))
                l10_pct = l10_w / (l10_w + l10_l) if (l10_w + l10_l) > 0 else win_pct
            except: 
                l10_pct = win_pct
            
            result[abbr] = {
                'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}", 
                'win_pct': win_pct, 'l10_pct': l10_pct, 'l10_record': l10_record
            }
        return result if len(result) > 5 else BACKUP_STANDINGS
    except Exception as e: 
        return BACKUP_STANDINGS

@st.cache_data(ttl=600)
def get_injuries():
    url = "https://www.cbssports.com/wnba/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        from bs4 import BeautifulSoup
        html = requests.get(url, headers=headers, timeout=8).text
        soup = BeautifulSoup(html, 'html.parser')
        news = {}
        
        TEAM_MAP = {
            'atlanta': 'ATL', 'chicago': 'CHI', 'connecticut': 'CONN', 'dallas': 'DAL',
            'indiana': 'IND', 'las vegas': 'LV', 'los angeles': 'LA', 'minnesota': 'MIN',
            'new york': 'NY', 'phoenix': 'PHO', 'seattle': 'SEA', 'washington': 'WAS'
        }
        
        # BRUTE FORCE HTML TABLE SEARCH
        for table in soup.find_all('table'):
            # Try to figure out what team this table belongs to by looking at the previous headers
            team_abbr = None
            prev_tag = table.find_previous(['h2', 'h3', 'div'])
            for _ in range(5): # Look back a few tags
                if prev_tag and prev_tag.text:
                    text_lower = prev_tag.text.lower()
                    for city, abbr in TEAM_MAP.items():
                        if city in text_lower:
                            team_abbr = abbr
                            break
                if team_abbr: break
                prev_tag = prev_tag.find_previous(['h2', 'h3', 'div']) if prev_tag else None

            if not team_abbr: continue
            
            players = []
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 4: # Player | Pos | Date | Injury | Status
                    p_text = cols[0].get_text(strip=True)
                    injury = cols[len(cols)-2].get_text(strip=True)
                    status = cols[len(cols)-1].get_text(strip=True)
                    
                    # Ignore players who are probable or cleared
                    if status.lower() not in ['expected to play', 'probable', 'active']:
                        players.append(f"{p_text} ({injury})")
                        
            if players: 
                news[team_abbr] = players 
                
        return news
    except: return {}

@st.cache_data(ttl=600)
def get_back_to_back(yest_date_string):
    b2b_list = set()
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={yest_date_string}"
    try:
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b_list.add(norm(c['team']['abbreviation']))
    except: pass
    return b2b_list

# ─────────────────────────────────────────────────────────────────────────────
# 3. WNBA PREDICTION ENGINE (40-Minute Recalibration)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td = TEAM_DATA.get(h, {'off_rtg': 100, 'def_rtg': 100})
    a_td = TEAM_DATA.get(a, {'off_rtg': 100, 'def_rtg': 100})
    h_std = standings.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    a_std = standings.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5})
    
    factors, total = [], 0.0
    
    # 1. Win % Edge (WNBA variance is lower, top teams dominate more consistently)
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']
    
    if use_l10:
        h_l10 = h_std.get('l10_pct', h_pct)
        a_l10 = a_std.get('l10_pct', a_pct)
        h_pct = (h_pct * 0.7) + (h_l10 * 0.3)
        a_pct = (a_pct * 0.7) + (a_l10 * 0.3)
        
    base_adj = (h_pct - a_pct) * 20.0  # Reduced multiplier for 40-min game
    total += base_adj
    edge_name = "Blended Win % Edge (L10)" if use_l10 else "Win % Edge"
    factors.append({"icon": "📊", "name": edge_name, "adj": base_adj, "why": f"{h} vs {a}"})

    # 2. Home Court (WNBA HCA is slightly lower than NBA)
    hca = 2.5
    total += hca
    factors.append({"icon": "🏠", "name": "Home Court", "adj": hca, "why": f"Advantage for {h}"})

    # 3. INJURY DETECTION
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    
    def get_player_impact(scraped_string):
        raw = scraped_string.lower().split(" (")[0].replace(".", "").replace("'", "").strip()
        
        val, tier = 1.0, "Role"
        for star in SUPERSTARS:
            if star.lower().replace(".", "").replace("'", "") in raw: val, tier = 8.0, "Superstar"; break
        if tier == "Role":
            for star in ALL_STARS:
                if star.lower().replace(".", "").replace("'", "") in raw: val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for star in HIGH_IMPACT:
                if star.lower().replace(".", "").replace("'", "") in raw: val, tier = 2.5, "High-Impact"; break
                
        archetype = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw: archetype = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw: archetype = "Off_Liability"; break
            
        return val, tier, archetype

    def calc_injury_penalty(inj_list):
        o_pen, d_pen = 0.0, 0.0
        details = []
        core_missing = 0
        
        for p in inj_list:
            val, tier, archetype = get_player_impact(p)
            if tier in ["Superstar", "All-Star", "High-Impact"]: core_missing += 1
                
            if archetype == "Def_Liability":
                o, d = val * 1.3, val * -0.3 
            elif archetype == "Off_Liability":
                o, d = val * -0.3, val * 1.3
            else:
                o, d = val * 0.6, val * 0.4
                
            o_pen += o; d_pen += d
            details.append(f"{p.split(' (')[0]} ({tier})")
            
        # WNBA Exponential Collapse (Hit harder because of 12-woman rosters)
        multiplier = 1.0
        if core_missing == 2: multiplier = 1.35 
        elif core_missing >= 3: multiplier = 1.75
            
        return o_pen * multiplier, d_pen * multiplier, details, multiplier

    h_off_pen, h_def_pen, h_det, h_mult = calc_injury_penalty(h_inj) if h_inj else (0.0, 0.0, [], 1.0)
    a_off_pen, a_def_pen, a_det, a_mult = calc_injury_penalty(a_inj) if a_inj else (0.0, 0.0, [], 1.0)

    # 4. Efficiency (Adjusted Net Rating for ~80 possessions)
    adj_h_off = h_td['off_rtg'] - h_off_pen
    adj_h_def = h_td['def_rtg'] + h_def_pen 
    h_net = adj_h_off - adj_h_def
    
    adj_a_off = a_td['off_rtg'] - a_off_pen
    adj_a_def = a_td['def_rtg'] + a_def_pen
    a_net = adj_a_off - adj_a_def
    
    # Scale Net Rating down for 40-minute pacing
    net_edge = ((h_net - a_net) / 100.0) * 82.0 * 0.6
    total += net_edge
    
    factors.append({"icon": "⚖️", "name": "Adj. Net Rating Edge", "adj": net_edge, "why": "Adjusted for 40-minute pacing"})

    if h_inj:
        h_why = f"Impact baked into Net Rating. Missing: {', '.join(h_det)}"
        if h_mult > 1.0: h_why += f" (🚨 Depth Collapse: {h_mult}x Penalty)"
        factors.append({"icon": "🤕", "name": f"{h} Injuries", "adj": 0.0, "why": h_why})
    if a_inj:
        a_why = f"Impact baked into Net Rating. Missing: {', '.join(a_det)}"
        if a_mult > 1.0: a_why += f" (🚨 Depth Collapse: {a_mult}x Penalty)"
        factors.append({"icon": "🤕", "name": f"{a} Injuries", "adj": 0.0, "why": a_why})

    # 5. BACK-TO-BACK FATIGUE (Heavier penalty for WNBA travel)
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0, "why": f"Played yesterday (Commercial flight grind)."})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0, "why": f"Played yesterday (Commercial flight grind)."})

    # Convert Point Spread to Win Probability using Logit (k=0.17)
    win_prob_raw = 1 / (1 + np.exp(-0.17 * total))
    prob = max(5.0, min(95.0, win_prob_raw * 100))
    
    return {'winner': h if prob >= 50.0 else a, 'conf': prob if prob >= 50.0 else 100.0-prob, 'factors': factors, 'h_std': h_std, 'a_std': a_std, 'h_inj': h_inj, 'a_inj': a_inj}

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 WNBA Quant AI v1.1")
st.markdown(f"**Market Date:** {display_date_str}")
st.divider()

slate = get_daily_slate(target_date_str)
standings = get_standings()
injuries = get_injuries()
b2b = get_back_to_back(yest_date_str)

st.sidebar.subheader("📊 Fatigue Status")
if b2b:
    st.sidebar.write(f"**Teams on B2B:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs for this date.")

if debug_mode:
    st.error("DEBUGGER ACTIVE:")
    st.write("Fetched Standings Teams:", list(standings.keys()))
    st.write("Fetched Injury Teams:", list(injuries.keys()))
    st.write("Raw Injury Data:", injuries)

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])

with tab1:
    if not slate:
        st.info(f"No games scheduled for {display_date_str} in the WNBA.")
    else:
        for game in slate:
            h, a = game['h'], game['a']
            pred = predict_game(h, a, standings, injuries, b2b, use_l10=False)
            with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
                st.markdown(f"### 🏆 {pred['winner']} Wins")
                for f in pred['factors']:
                    color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                    st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"#### 🏠 {game['h_name']}")
                    st.write(f"**Record:** {pred['h_std'].get('record', '0-0')}")
                    for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
                with col2:
                    st.markdown(f"#### ✈️ {game['a_name']}")
                    st.write(f"**Record:** {pred['a_std'].get('record', '0-0')}")
                    for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

with tab2:
    if not slate:
        st.info(f"No games scheduled for {display_date_str} in the WNBA.")
    else:
        for game in slate:
            h, a = game['h'], game['a']
            pred = predict_game(h, a, standings, injuries, b2b, use_l10=True)
            with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
                st.markdown(f"### 🏆 {pred['winner']} Wins")
                for f in pred['factors']:
                    color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                    st.markdown(f"{f['icon']} **{f['name']}**: <span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span> — {f['why']}", unsafe_allow_html=True)
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"#### 🏠 {game['h_name']}")
                    st.write(f"**Record:** {pred['h_std'].get('record', '0-0')} *(L10: {pred['h_std'].get('l10_record', 'N/A')})*")
                    for inj in pred['h_inj']: st.warning(f"🤕 {inj}")
                with col2:
                    st.markdown(f"#### ✈️ {game['a_name']}")
                    st.write(f"**Record:** {pred['a_std'].get('record', '0-0')} *(L10: {pred['a_std'].get('l10_record', 'N/A')})*")
                    for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

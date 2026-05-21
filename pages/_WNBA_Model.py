import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="WNBA Quant AI 2026", page_icon="🏀", layout="wide")

st.sidebar.title("⚙️ System Tools")

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

SUPERSTARS = [
    "A'ja Wilson", "Breanna Stewart", "Caitlin Clark", "Napheesa Collier",
    "Alyssa Thomas", "Jewell Loyd", "Sabrina Ionescu"
]

ALL_STARS = [
    "Kelsey Plum", "Jackie Young", "Jonquel Jones", "Nneka Ogwumike",
    "Ariel Atkins", "Kahleah Copper", "Chelsea Gray", "Arike Ogunbowale",
    "Satou Sabally", "DeWanna Bonner", "Cameron Brink", "Aliyah Boston",
    "Diana Taurasi", "Skylar Diggins-Smith", "Ezi Magbegor"
]

HIGH_IMPACT = [
    "Natasha Howard", "Marina Mabrey", "Courtney Vandersloot", "Betnijah Laney-Hamilton",
    "Brionna Jones", "Dearica Hamby", "Allisha Gray", "Rhyne Howard", "Kayla McBride",
    "Natasha Cloud", "Kelsey Mitchell", "NaLyssa Smith", "Brittney Griner",
    "Cheyenne Parker-Tyus", "Courtney Williams", "Alanna Smith", "Sophie Cunningham"
]

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
    'LV':   {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'NY':   {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'CONN': {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'SEA':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'MIN':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'IND':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'DAL':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'ATL':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'PHO':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'CHI':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'LA':   {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
    'WAS':  {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.500, 'l10_pct': 0.5, 'l10_record': '0-0'},
}

TEAM_DATA = {
    'LV':   {'off_rtg': 110.5, 'def_rtg': 99.8},
    'NY':   {'off_rtg': 109.2, 'def_rtg': 100.5},
    'CONN': {'off_rtg': 104.1, 'def_rtg': 97.2},
    'SEA':  {'off_rtg': 103.5, 'def_rtg': 98.8},
    'MIN':  {'off_rtg': 102.8, 'def_rtg': 99.1},
    'IND':  {'off_rtg': 106.5, 'def_rtg': 105.2},
    'DAL':  {'off_rtg': 105.1, 'def_rtg': 104.8},
    'ATL':  {'off_rtg': 100.2, 'def_rtg': 101.5},
    'PHO':  {'off_rtg': 99.5,  'def_rtg': 106.1},
    'CHI':  {'off_rtg': 98.2,  'def_rtg': 103.5},
    'LA':   {'off_rtg': 96.8,  'def_rtg': 105.2},
    'WAS':  {'off_rtg': 97.5,  'def_rtg': 108.4},
}

def norm(abbr):
    mapping = {'LVA': 'LV', 'NYL': 'NY', 'CON': 'CONN', 'PHX': 'PHO', 'LAS': 'LA', 'MINN': 'MIN'}
    return mapping.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
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
                games.append({
                    'h': norm(home['team']['abbreviation']),
                    'a': norm(away['team']['abbreviation']),
                    'h_name': home['team']['displayName'],
                    'a_name': away['team']['displayName'],
                })
        return games
    except:
        return []

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: STANDINGS — ESPN uses camelCase stat names; keep original case in dict
# Also: L10 lives in entry['records'], not entry['stats']
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/standings"
    try:
        data = requests.get(url, timeout=8).json()
        result = {}

        # Collect all entries across conferences
        all_entries = []
        for group in data.get('children', []):
            all_entries.extend(group.get('standings', {}).get('entries', []))
        # Fallback: standings at top level
        if not all_entries:
            all_entries = data.get('standings', {}).get('entries', [])

        for entry in all_entries:
            abbr = norm(entry['team']['abbreviation'])

            # ── stats block: keep ORIGINAL case so 'wins'/'losses'/'winPercent' all match ──
            stats = {s.get('name', ''): s for s in entry.get('stats', [])}

            wins   = int(float(stats.get('wins',   {}).get('value', 0)))
            losses = int(float(stats.get('losses', {}).get('value', 0)))
            win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5

            # ── L10 lives in entry['records'], type == 'lastTen' ──
            l10_record = '0-0'
            l10_pct    = win_pct
            for rec in entry.get('records', []):
                rec_type = rec.get('type', '') or rec.get('name', '')
                if 'ten' in rec_type.lower() or 'last10' in rec_type.lower() or 'l10' in rec_type.lower():
                    l10_record = rec.get('summary', '0-0')
                    break
            # Fallback: check stats block for any key containing 'ten' or 'l10'
            if l10_record == '0-0':
                for key, val in stats.items():
                    if 'ten' in key.lower() or 'l10' in key.lower():
                        l10_record = val.get('displayValue', '0-0')
                        break
            try:
                l10_w, l10_l = map(int, l10_record.split('-'))
                l10_pct = l10_w / (l10_w + l10_l) if (l10_w + l10_l) > 0 else win_pct
            except:
                pass

            result[abbr] = {
                'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}",
                'win_pct': win_pct, 'l10_pct': l10_pct, 'l10_record': l10_record,
            }

        return result if len(result) >= 6 else BACKUP_STANDINGS
    except Exception as e:
        st.sidebar.warning(f"Standings fetch failed: {e}")
        return BACKUP_STANDINGS

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: INJURIES — replace unreliable CBS scraper with ESPN's injury API
# ESPN endpoint: /injuries returns athletes + status per team
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_injuries():
    """
    Fetches WNBA injuries from ESPN's sports core API.
    Falls back to an empty dict if the request fails.
    """
    # ESPN's core API lists active injuries by team
    url = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/injuries?limit=300"
    SKIP_STATUSES = {'active', 'probable', 'expected to play', 'day-to-day'}
    result = {}

    try:
        data = requests.get(url, timeout=8).json()
        items = data.get('items', [])

        for item in items:
            # Each item has a $ref we need to fetch for details
            ref = item.get('$ref', '')
            if not ref:
                continue
            try:
                detail = requests.get(ref, timeout=5).json()
            except:
                continue

            status_txt = detail.get('status', {}).get('type', {}).get('description', 'Unknown')
            if status_txt.lower() in SKIP_STATUSES:
                continue

            athlete_ref = detail.get('athlete', {}).get('$ref', '')
            injury_type = detail.get('type', {}).get('description', 'Injury')

            # Get athlete name + team from their ref
            if not athlete_ref:
                continue
            try:
                ath = requests.get(athlete_ref, timeout=5).json()
            except:
                continue

            player_name = ath.get('displayName', 'Unknown')
            team_abbr = norm(ath.get('team', {}).get('abbreviation', ''))
            if not team_abbr:
                continue

            entry = f"{player_name} ({injury_type} — {status_txt})"
            result.setdefault(team_abbr, []).append(entry)

        return result

    except Exception:
        # Secondary fallback: try ESPN's scoreboard-embedded injury data per team
        return _get_injuries_from_teams()


def _get_injuries_from_teams():
    """
    Secondary injury source: scrape each team's ESPN roster page for injury flags.
    Only runs if the primary endpoint fails.
    """
    TEAM_IDS = {
        'ATL': 'atl', 'CHI': 'chi', 'CONN': 'conn', 'DAL': 'dal',
        'IND': 'ind', 'LV': 'lv',   'LA': 'la',    'MIN': 'min',
        'NY': 'ny',   'PHO': 'phx',  'SEA': 'sea',  'WAS': 'was',
    }
    SKIP_STATUSES = {'active', 'probable', 'day-to-day'}
    result = {}

    for abbr, slug in TEAM_IDS.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{slug}/injuries"
        try:
            data = requests.get(url, timeout=5).json()
            players = []
            for inj in data.get('injuries', []):
                status = inj.get('status', 'Unknown')
                if status.lower() in SKIP_STATUSES:
                    continue
                name   = inj.get('athlete', {}).get('displayName', 'Unknown')
                injury = inj.get('injury', {}).get('details', {}).get('type', 'Injury')
                players.append(f"{name} ({injury} — {status})")
            if players:
                result[abbr] = players
        except:
            continue

    return result

@st.cache_data(ttl=600)
def get_back_to_back(yest_date_string):
    b2b_list = set()
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={yest_date_string}"
    try:
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b_list.add(norm(c['team']['abbreviation']))
    except:
        pass
    return b2b_list

# ─────────────────────────────────────────────────────────────────────────────
# 3. WNBA PREDICTION ENGINE (40-Minute Recalibration)
# ─────────────────────────────────────────────────────────────────────────────
def predict_game(h, a, standings, injuries, b2b_set, use_l10=False):
    h_td  = TEAM_DATA.get(h, {'off_rtg': 100, 'def_rtg': 100})
    a_td  = TEAM_DATA.get(a, {'off_rtg': 100, 'def_rtg': 100})
    h_std = standings.get(h, BACKUP_STANDINGS.get(h, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': '0-0'}))
    a_std = standings.get(a, BACKUP_STANDINGS.get(a, {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'l10_pct': 0.5, 'l10_record': '0-0'}))

    factors, total = [], 0.0

    # 1. Win % Edge
    h_pct = h_std['win_pct']
    a_pct = a_std['win_pct']

    if use_l10:
        h_l10 = h_std.get('l10_pct', h_pct)
        a_l10 = a_std.get('l10_pct', a_pct)
        h_pct = (h_pct * 0.7) + (h_l10 * 0.3)
        a_pct = (a_pct * 0.7) + (a_l10 * 0.3)

    base_adj = (h_pct - a_pct) * 20.0
    total += base_adj
    edge_name = "Blended Win % Edge (L10)" if use_l10 else "Win % Edge"
    factors.append({"icon": "📊", "name": edge_name, "adj": base_adj, "why": f"{h} vs {a}"})

    # 2. Home Court
    hca = 2.5
    total += hca
    factors.append({"icon": "🏠", "name": "Home Court", "adj": hca, "why": f"Advantage for {h}"})

    # 3. Injury Detection
    h_inj = injuries.get(h, [])
    a_inj = injuries.get(a, [])

    def get_player_impact(scraped_string):
        raw = scraped_string.lower().split(" (")[0].replace(".", "").replace("'", "").strip()
        val, tier = 1.0, "Role"
        for star in SUPERSTARS:
            if star.lower().replace(".", "").replace("'", "") in raw:
                val, tier = 8.0, "Superstar"; break
        if tier == "Role":
            for star in ALL_STARS:
                if star.lower().replace(".", "").replace("'", "") in raw:
                    val, tier = 4.5, "All-Star"; break
        if tier == "Role":
            for star in HIGH_IMPACT:
                if star.lower().replace(".", "").replace("'", "") in raw:
                    val, tier = 2.5, "High-Impact"; break

        archetype = "Balanced"
        for p in DEFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                archetype = "Def_Liability"; break
        for p in OFFENSIVE_LIABILITIES:
            if p.lower().replace(".", "").replace("'", "") in raw:
                archetype = "Off_Liability"; break
        return val, tier, archetype

    def calc_injury_penalty(inj_list):
        o_pen, d_pen = 0.0, 0.0
        details = []
        core_missing = 0
        for p in inj_list:
            val, tier, archetype = get_player_impact(p)
            if tier in ["Superstar", "All-Star", "High-Impact"]:
                core_missing += 1
            if archetype == "Def_Liability":
                o, d = val * 1.3, val * -0.3
            elif archetype == "Off_Liability":
                o, d = val * -0.3, val * 1.3
            else:
                o, d = val * 0.6, val * 0.4
            o_pen += o; d_pen += d
            details.append(f"{p.split(' (')[0]} ({tier})")
        multiplier = 1.0
        if core_missing == 2:   multiplier = 1.35
        elif core_missing >= 3: multiplier = 1.75
        return o_pen * multiplier, d_pen * multiplier, details, multiplier

    h_off_pen, h_def_pen, h_det, h_mult = calc_injury_penalty(h_inj) if h_inj else (0.0, 0.0, [], 1.0)
    a_off_pen, a_def_pen, a_det, a_mult = calc_injury_penalty(a_inj) if a_inj else (0.0, 0.0, [], 1.0)

    # 4. Efficiency
    adj_h_off = h_td['off_rtg'] - h_off_pen
    adj_h_def = h_td['def_rtg'] + h_def_pen
    h_net     = adj_h_off - adj_h_def

    adj_a_off = a_td['off_rtg'] - a_off_pen
    adj_a_def = a_td['def_rtg'] + a_def_pen
    a_net     = adj_a_off - adj_a_def

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

    # 5. Back-to-Back Fatigue
    if h in b2b_set:
        total -= 5.0
        factors.append({"icon": "😴", "name": f"{h} B2B Fatigue", "adj": -5.0, "why": "Played yesterday (Commercial flight grind)."})
    if a in b2b_set:
        total += 5.0
        factors.append({"icon": "😴", "name": f"{a} B2B Fatigue", "adj": 5.0, "why": "Played yesterday (Commercial flight grind)."})

    win_prob_raw = 1 / (1 + np.exp(-0.17 * total))
    prob = max(5.0, min(95.0, win_prob_raw * 100))

    return {
        'winner': h if prob >= 50.0 else a,
        'conf':   prob if prob >= 50.0 else 100.0 - prob,
        'factors': factors,
        'h_std': h_std, 'a_std': a_std,
        'h_inj': h_inj, 'a_inj': a_inj,
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. USER INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 WNBA Quant AI v1.1")
st.markdown(f"**Market Date:** {display_date_str}")
st.divider()

with st.spinner("Loading slate, standings, and injuries…"):
    slate     = get_daily_slate(target_date_str)
    standings = get_standings()
    injuries  = get_injuries()
    b2b       = get_back_to_back(yest_date_str)

# ── Sidebar injury & B2B status ──
st.sidebar.subheader("📊 Fatigue Status")
if b2b:
    st.sidebar.write(f"**Teams on B2B:** {', '.join(sorted(b2b))}")
else:
    st.sidebar.info("No teams on back-to-backs for this date.")

st.sidebar.subheader("🤕 Injury Report")
if injuries:
    for team, players in sorted(injuries.items()):
        st.sidebar.markdown(f"**{team}**")
        for p in players:
            st.sidebar.warning(p)
else:
    st.sidebar.info("No significant injuries found.")

tab1, tab2 = st.tabs(["📊 Standard Model", "🔥 L10 Enhanced Model"])

def render_tab(use_l10):
    if not slate:
        st.info(f"No games scheduled for {display_date_str} in the WNBA.")
        return
    for game in slate:
        h, a = game['h'], game['a']
        pred = predict_game(h, a, standings, injuries, b2b, use_l10=use_l10)
        with st.expander(f"{game['h_name']} vs {game['a_name']} | Winner: {pred['winner']} ({pred['conf']:.1f}%)"):
            st.markdown(f"### 🏆 {pred['winner']} Wins")
            for f in pred['factors']:
                color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
                st.markdown(
                    f"{f['icon']} **{f['name']}**: "
                    f"<span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span>"
                    f" — {f['why']}",
                    unsafe_allow_html=True,
                )
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {game['h_name']}")
                rec_line = f"**Record:** {pred['h_std'].get('record', '0-0')}"
                if use_l10:
                    rec_line += f" *(L10: {pred['h_std'].get('l10_record', 'N/A')})*"
                st.write(rec_line)
                for inj in pred['h_inj']:
                    st.warning(f"🤕 {inj}")
            with col2:
                st.markdown(f"#### ✈️ {game['a_name']}")
                rec_line = f"**Record:** {pred['a_std'].get('record', '0-0')}"
                if use_l10:
                    rec_line += f" *(L10: {pred['a_std'].get('l10_record', 'N/A')})*"
                st.write(rec_line)
                for inj in pred['a_inj']:
                    st.warning(f"🤕 {inj}")

with tab1:
    render_tab(use_l10=False)

with tab2:
    render_tab(use_l10=True)

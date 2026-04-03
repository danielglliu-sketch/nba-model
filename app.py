import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="NBA Master AI Predictor", page_icon="🏀", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# ABBREVIATION NORMALIZER
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {
    'GS':   'GSW',   'SA':   'SAS',   'NY':   'NYK',   'NO':   'NOP',
    'UTAH': 'UTA',   'WSH':  'WAS',   'CHAR': 'CHA',   'BKLN': 'BKN',
}

def norm(abbr):
    return ESPN_TO_STD.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# BASELINE EFFICIENCY STATS (Math Only)
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'DET': {'off_rtg': 112.5, 'def_rtg': 113.0, 'pace': 99.8},
    'BOS': {'off_rtg': 121.6, 'def_rtg': 107.2, 'pace': 99.1},
    'NYK': {'off_rtg': 115.4, 'def_rtg': 111.2, 'pace': 97.8},
    'CLE': {'off_rtg': 114.0, 'def_rtg': 110.8, 'pace': 98.2},
    'ATL': {'off_rtg': 116.5, 'def_rtg': 118.4, 'pace': 100.8},
    'PHI': {'off_rtg': 115.5, 'def_rtg': 114.2, 'pace': 97.0},
    'TOR': {'off_rtg': 112.8, 'def_rtg': 115.0, 'pace': 98.0},
    'CHA': {'off_rtg': 110.2, 'def_rtg': 119.0, 'pace': 100.5},
    'ORL': {'off_rtg': 111.0, 'def_rtg': 111.5, 'pace': 97.0},
    'MIA': {'off_rtg': 111.5, 'def_rtg': 112.0, 'pace': 97.5},
    'MIL': {'off_rtg': 118.6, 'def_rtg': 115.7, 'pace': 99.5},
    'CHI': {'off_rtg': 111.8, 'def_rtg': 114.4, 'pace': 98.5},
    'IND': {'off_rtg': 119.0, 'def_rtg': 118.5, 'pace': 102.1},
    'BKN': {'off_rtg': 112.0, 'def_rtg': 116.5, 'pace': 97.5},
    'WAS': {'off_rtg': 110.0, 'def_rtg': 119.0, 'pace': 101.5},
    'OKC': {'off_rtg': 119.5, 'def_rtg': 111.0, 'pace': 100.5},
    'SAS': {'off_rtg': 110.0, 'def_rtg': 114.5, 'pace': 100.5},
    'LAL': {'off_rtg': 114.5, 'def_rtg': 113.8, 'pace': 101.8},
    'DEN': {'off_rtg': 117.0, 'def_rtg': 111.5, 'pace': 97.0},
    'HOU': {'off_rtg': 112.0, 'def_rtg': 111.0, 'pace': 98.8},
    'MIN': {'off_rtg': 114.5, 'def_rtg': 108.0, 'pace': 98.5},
    'PHX': {'off_rtg': 116.0, 'def_rtg': 114.0, 'pace': 98.0},
    'LAC': {'off_rtg': 117.5, 'def_rtg': 113.0, 'pace': 97.5},
    'POR': {'off_rtg': 108.0, 'def_rtg': 118.5, 'pace': 98.5},
    'GSW': {'off_rtg': 116.0, 'def_rtg': 115.0, 'pace': 100.0},
    'SAC': {'off_rtg': 115.0, 'def_rtg': 115.5, 'pace': 100.5},
    'MEM': {'off_rtg': 106.5, 'def_rtg': 112.0, 'pace': 98.2},
    'DAL': {'off_rtg': 117.8, 'def_rtg': 115.5, 'pace': 100.0},
    'NOP': {'off_rtg': 115.0, 'def_rtg': 112.5, 'pace': 99.5},
    'UTA': {'off_rtg': 114.0, 'def_rtg': 120.2, 'pace': 100.5},
}

# ─────────────────────────────────────────────────────────────────────────────
# LIVE AUTO-FETCHERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_daily_slate():
    now_est = datetime.utcnow() - timedelta(hours=4)
    target_date = now_est.strftime('%Y-%m-%d')
    yest_str = (now_est - timedelta(days=1)).strftime('%Y%m%d')
    tom_str = (now_est + timedelta(days=1)).strftime('%Y%m%d')
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest_str}-{tom_str}"
    
    try:
        data = requests.get(url, timeout=8).json()
        games = []
        for event in data.get('events', []):
            dt_utc = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')
            dt_est = dt_utc - timedelta(hours=4)
            
            if dt_est.strftime('%Y-%m-%d') != target_date:
                continue

            comp  = event['competitions'][0]
            comps = comp.get('competitors', [])
            home  = next((c for c in comps if c.get('homeAway') == 'home'), None)
            away  = next((c for c in comps if c.get('homeAway') == 'away'), None)
            if not (home and away): continue
                
            h_abbr, a_abbr = norm(home['team']['abbreviation']), norm(away['team']['abbreviation'])
            
            games.append({
                'h': h_abbr, 'a': a_abbr,
                'h_name': home['team'].get('displayName', h_abbr),
                'a_name': away['team'].get('displayName', a_abbr),
                'venue': comp.get('venue', {}).get('fullName', 'Unknown Arena'),
                'time': dt_est.strftime('%I:%M %p ET').lstrip('0'),
                'status': comp.get('status', {}).get('type', {}).get('description', 'Scheduled'),
            })
        return games
    except Exception:
        return []

@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings"
    result = {}
    try:
        data = requests.get(url, timeout=8).json()
        for conf in data.get('children', []):
            for entry in conf.get('standings', {}).get('entries', []):
                abbr  = norm(entry['team']['abbreviation'])
                stats = {s.get('name', '').lower(): s for s in entry.get('stats', [])}
                
                def val(k, d=0): return stats.get(k.lower(), {}).get('value') or d
                def disp(k, d=''): return stats.get(k.lower(), {}).get('displayValue') or d
                
                def parse_rec(s):
                    try:
                        w, l = s.split('-')
                        return int(w) / (int(w) + int(l)) if (int(w) + int(l)) else 0.5
                    except: return 0.5

                h_str = disp('home') or disp('homerecord') or '0-0'
                a_str = disp('away') or disp('awayrecord') or '0-0'
                wins, losses = int(val('wins', 0)), int(val('losses', 0))
                win_pct = float(val('winpercent', 0.5))

                if win_pct > 0.65: auto_status = "🏆 Elite Contender"
                elif win_pct > 0.55: auto_status = "✅ Playoff Lock"
                elif win_pct > 0.40: auto_status = "⚠️ Play-In Threat"
                else: auto_status = "🚫 Lottery Bound"

                result[abbr] = {
                    'wins': wins, 'losses': losses, 'record': f"{wins}-{losses}",
                    'win_pct': win_pct, 'home_record': h_str, 'away_record': a_str,
                    'home_wpct': parse_rec(h_str), 'away_wpct': parse_rec(a_str),
                    'streak': disp('streak') or 'N/A', 'status': auto_status,
                    'point_diff': float(val('pointdifferential') or val('avgpointdifferential') or val('diff', 0)),
                }
    except Exception: pass
    return result

@st.cache_data(ttl=600)
def get_recent_form():
    form = {}
    today = datetime.utcnow()
    try:
        for days_ago in range(1, 18):
            date_str = (today - timedelta(days=days_ago)).strftime('%Y%m%d')
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
            data = requests.get(url, timeout=5).json()
            for event in data.get('events', []):
                comp = event['competitions'][0]
                if not comp.get('status', {}).get('type', {}).get('completed'): continue
                for c in comp['competitors']:
                    abbr = norm(c['team']['abbreviation'])
                    form.setdefault(abbr, [])
                    if len(form[abbr]) < 10: form[abbr].append(1 if c.get('winner', False) else 0)
    except: pass
    return form

@st.cache_data(ttl=600)
def get_back_to_back():
    b2b = set()
    yest = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest}"
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b.add(norm(c['team']['abbreviation']))
    except: pass
    return b2b

@st.cache_data(ttl=600)
def get_injury_news():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=50"
    kwords = ['out', 'questionable', 'doubtful', 'injured', 'misses', 'ankle', 'knee', 'hamstring']
    news = {}
    try:
        articles = requests.get(url, timeout=6).json().get('articles', [])
        for art in articles:
            hl = art.get('headline', '')
            if len(hl) > 150 or not any(k in hl.lower() for k in kwords): continue
            for cat in art.get('categories', []):
                if cat.get('type') == 'team':
                    abbr = norm(cat.get('teamAbbrev', '') or cat.get('abbreviation', ''))
                    if abbr: news.setdefault(abbr, []).append(hl)
        return {k: list(dict.fromkeys(v))[:2] for k, v in news.items()}
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# LOGIC ENGINE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_STD = {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.5, 'home_wpct': 0.5, 'away_wpct': 0.5, 'home_record': '0-0', 'away_record': '0-0', 'streak': 'N/A', 'point_diff': 0.0, 'status': 'Unknown'}
DEFAULT_TD = {'off_rtg': 112.0, 'def_rtg': 115.0, 'pace': 99.0}

def predict_game(h, a, standings, form, b2b_set, injuries):
    h_td, a_td = TEAM_DATA.get(h, DEFAULT_TD), TEAM_DATA.get(a, DEFAULT_TD)
    h_std, a_std = standings.get(h, DEFAULT_STD), standings.get(a, DEFAULT_STD)
    h_frm, a_frm = form.get(h, []), form.get(a, [])
    
    factors = []
    total = 0.0
    
    # 1. Base Win % / Power
    base_adj = max(-15.0, min(15.0, (h_std['win_pct'] - a_std['win_pct']) * 25.0))
    total += base_adj
    factors.append({"icon": "📊", "name": "Win % Edge", "why": f"Overall record disparity", "adj": base_adj})

    # 2. Home Court Advantage
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "why": f"Standard advantage for {h}", "adj": 3.5})

    # 3. Defensive Efficiency
    def_adj = max(-8.0, min(8.0, (a_td['def_rtg'] - h_td['def_rtg']) * 0.4))
    total += def_adj
    factors.append({"icon": "🛡️", "name": "Defensive Matchup", "why": f"Pts allowed per 100 poss", "adj": def_adj})

    # 4. Recent Form (Momentum)
    h_fpct, a_fpct = sum(h_frm)/len(h_frm) if h_frm else 0.5, sum(a_frm)/len(a_frm) if a_frm else 0.5
    form_adj = max(-8.0, min(8.0, (h_fpct - a_fpct) * 12.0))
    total += form_adj
    factors.append({"icon": "📈", "name": "Recent Momentum", "why": f"Win percentage in last 10 games", "adj": form_adj})
    
    # 5. Back-to-Back Fatigue
    if h in b2b_set:
        total -= 4.5
        factors.append({"icon": "😴", "name": "Fatigue", "why": f"{h} is on 2nd night of B2B", "adj": -4.5})
    if a in b2b_set:
        total += 4.5
        factors.append({"icon": "😴", "name": "Fatigue", "why": f"{a} is on 2nd night of B2B", "adj": 4.5})
        
    # 6. DYNAMIC Tanking Logic
    if h_std['win_pct'] < 0.35 and h_std['wins'] + h_std['losses'] > 10:
        total -= 8.0
        factors.append({"icon": "🎯", "name": "Tanking Penalty", "why": f"{h} is prioritizing lottery odds", "adj": -8.0})
    if a_std['win_pct'] < 0.35 and a_std['wins'] + a_std['losses'] > 10:
        total += 8.0
        factors.append({"icon": "🎯", "name": "Tanking Boost", "why": f"{a} is prioritizing lottery odds", "adj": 8.0})

    # 7. Live Injury Impact
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj: 
        inj_adj = min(8.0, len(h_inj) * 3.0)
        total -= inj_adj
        factors.append({"icon": "🤕", "name": "Live Injuries", "why": f"{h} reporting health issues", "adj": -inj_adj})
    if a_inj: 
        inj_adj = min(8.0, len(a_inj) * 3.0)
        total += inj_adj
        factors.append({"icon": "🤕", "name": "Live Injuries", "why": f"{a} reporting health issues", "adj": inj_adj})

    prob = max(2.0, min(98.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': round(prob if prob >= 50.0 else 100.0 - prob, 1),
        'prob_h': round(prob, 1), 'factors': factors,
        'h_td': h_td, 'a_td': a_td, 'h_std': h_std, 'a_std': a_std,
        'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# UI RENDER
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI Predictor")
st.caption(f"Fully Automated Live Engine · {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

with st.spinner("📡 Fetching Live Standings, Injuries, and Schedules..."):
    slate = get_daily_slate()
    standings = get_standings()
    form = get_recent_form()
    b2b_set = get_back_to_back()
    injuries = get_injury_news()

if not slate:
    st.error("❌ Waiting for NBA Daily Slate to populate. Check back later or ensure games are scheduled today.")
    st.stop()

st.subheader(f"Today's AI Predictions — {len(slate)} Games")
st.caption("AI evaluates Live Win %, Defensive Matchups, Streaks, Fatigue, and Tanking Motivation.")
st.divider()

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, form, b2b_set, injuries)
    conf, winner, prob_h = pred['conf'], pred['winner'], pred['prob_h']

    icon = "🔒" if conf >= 85 else ("🔥" if conf >= 70 else "⚖️")
    badge = "HIGH LOCK" if conf >= 85 else ("STRONG LEAN" if conf >= 70 else "CLOSE GAME")
    header = f"{icon} {game['h_name']} vs {game['a_name']} | {winner} wins · {conf:.1f}%"

    with st.expander(header):
        bdr = '#28a745' if conf >= 70 else '#ffc107' if conf >= 60 else '#17a2b8'
        st.markdown(f"""
        <div style="border-left:5px solid {bdr};background:{bdr}18;border-radius:6px;padding:12px 16px;margin-bottom:14px;">
            <div style="font-size:1.35em;font-weight:800;">🏆 {winner} WINS <span style="font-size:.75em;opacity:.8;">{icon} {badge}</span></div>
            <div style="font-size:.85em;color:#aaa;margin-top:4px;">📍 {game['venue']} · 🕐 {game['time']}</div>
        </div>""", unsafe_allow_html=True)

        # --- REASONING LOG ---
        st.markdown("#### 🧠 AI Reasoning Log")
        for f in pred['factors']:
            c1, c2, c3 = st.columns([0.5, 4, 1])
            c1.markdown(f['icon'])
            c2.markdown(f"**{f['name']}** - *{f['why']}*")
            color = "#28a745" if f['adj'] > 0 else "#dc3545"
            c3.markdown(f"<span style='color:{color};font-weight:bold;'>{f['adj']:+.1f}</span>", unsafe_allow_html=True)
        st.divider()

        # --- PROBABILITY BAR ---
        st.markdown(f"**Final Win Probability** — {h}: **{prob_h:.0f}%** vs {a}: **{100-prob_h:.0f}%**")
        st.markdown(f"""
        <div style="display:flex;height:24px;border-radius:6px;overflow:hidden;margin-bottom:14px;border:1px solid #444;">
            <div style="width:{prob_h:.0f}%;background:#28a745;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;">{h}</div>
            <div style="width:{100-prob_h:.0f}%;background:#dc3545;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;">{a}</div>
        </div>""", unsafe_allow_html=True)

        # --- LIVE TEAM DATA ---
        col_h, col_vs, col_a = st.columns([5, 1, 5])
        with col_h:
            st.markdown(f"#### 🏠 {h} — {game['h_name']}")
            st.markdown(f"**{pred['h_std']['status']}**")
            st.write(f"Record: **{pred['h_std']['record']}** | Home: {pred['h_std']['home_record']}")
            st.write(f"Def Rating: {pred['h_td']['def_rtg']} | Off Rating: {pred['h_td']['off_rtg']}")
            for inj in pred['h_inj']: st.warning(f"🤕 {inj}")

        with col_vs:
            st.markdown("<br><br><div style='text-align:center;font-size:1.6em;opacity:0.5;'>VS</div>", unsafe_allow_html=True)

        with col_a:
            st.markdown(f"#### ✈️ {a} — {game['a_name']}")
            st.markdown(f"**{pred['a_std']['status']}**")
            st.write(f"Record: **{pred['a_std']['record']}** | Away: {pred['a_std']['away_record']}")
            st.write(f"Def Rating: {pred['a_td']['def_rtg']} | Off Rating: {pred['a_td']['off_rtg']}")
            for inj in pred['a_inj']: st.warning(f"🤕 {inj}")

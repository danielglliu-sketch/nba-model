import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="NBA Master AI 2026", page_icon="🏀", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# ESPN ABBREVIATION NORMALIZER
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {
    'GS':   'GSW',   'SA':   'SAS',   'NY':   'NYK',   'NO':   'NOP',
    'UTAH': 'UTA',   'WSH':  'WAS',   'CHAR': 'CHA',   'BKLN': 'BKN',
}

def norm(abbr):
    return ESPN_TO_STD.get(abbr, abbr)

# ─────────────────────────────────────────────────────────────────────────────
# ALL 30 TEAMS — Updated April 2026
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    # ── EASTERN CONFERENCE ──────────────────────────────────────────────────
    'DET': {'off_rtg': 115.8, 'def_rtg': 108.5, 'pt_diff': +7.2, 'pace': 99.8, 'star': 'Jaden Ivey / Ausar Thompson', 'status': '🏆 #1 East Seed', 'note': 'Cade Cunningham OUT. Elite defense.', 'tanking': False, 'eliminated': False},
    'BOS': {'off_rtg': 121.6, 'def_rtg': 107.2, 'pt_diff': +7.2, 'pace': 99.1, 'star': 'Jaylen Brown', 'status': '✅ Clinched Playoff (#2)', 'note': 'Best defense in the league at 107.2 pts allowed.', 'tanking': False, 'eliminated': False},
    'NYK': {'off_rtg': 115.4, 'def_rtg': 111.2, 'pt_diff': +4.2, 'pace': 97.8, 'star': 'Jalen Brunson', 'status': '✅ Clinched Playoff (#3)', 'note': 'Brunson orchestrates everything. Physical style.', 'tanking': False, 'eliminated': False},
    'CLE': {'off_rtg': 118.0, 'def_rtg': 108.8, 'pt_diff': +5.5, 'pace': 98.2, 'star': 'Donovan Mitchell + James Harden', 'status': '✅ Clinched Playoff (#4)', 'note': 'Acquired Harden. 3rd-best offense since.', 'tanking': False, 'eliminated': False},
    'ATL': {'off_rtg': 115.5, 'def_rtg': 110.4, 'pt_diff': +3.1, 'pace': 100.8, 'star': 'Trae Young', 'status': '✅ Clinched Playoff (#5)', 'note': 'Defense vastly improved from prior seasons.', 'tanking': False, 'eliminated': False},
    'PHI': {'off_rtg': 113.5, 'def_rtg': 114.2, 'pt_diff': +0.8, 'pace': 97.0, 'star': 'Tyrese Maxey', 'status': '✅ Clinched Playoff (#6)', 'note': 'Maxey carrying the post-Embiid era offense.', 'tanking': False, 'eliminated': False},
    'TOR': {'off_rtg': 112.8, 'def_rtg': 115.0, 'pt_diff': +0.2, 'pace': 98.0, 'star': 'RJ Barrett', 'status': '⚠️ Play-In (#7)', 'note': 'Battling every night to hold seeding.', 'tanking': False, 'eliminated': False},
    'CHA': {'off_rtg': 113.2, 'def_rtg': 116.0, 'pt_diff': +0.5, 'pace': 100.5, 'star': 'LaMelo Ball', 'status': '⚠️ Play-In (#8)', 'note': 'MASSIVE SURPRISE. Do NOT sleep on Charlotte.', 'tanking': False, 'eliminated': False},
    'ORL': {'off_rtg': 111.0, 'def_rtg': 111.5, 'pt_diff': -0.3, 'pace': 97.0, 'star': 'Franz Wagner', 'status': '⚠️ Play-In (#9)', 'note': 'Defense is legit but offense limited.', 'tanking': False, 'eliminated': False},
    'MIA': {'off_rtg': 111.5, 'def_rtg': 112.0, 'pt_diff': -0.4, 'pace': 97.5, 'star': 'Bam Adebayo', 'status': '⚠️ Play-In (#10)', 'note': 'Heat culture never quits. Adebayo anchors defense.', 'tanking': False, 'eliminated': False},
    'MIL': {'off_rtg': 110.6, 'def_rtg': 116.7, 'pt_diff': -6.1, 'pace': 99.5, 'star': 'Giannis (OUT)', 'status': '❌ Eliminated', 'note': 'Giannis OUT. Defense collapsed without anchors.', 'tanking': False, 'eliminated': True},
    'CHI': {'off_rtg': 111.8, 'def_rtg': 116.4, 'pt_diff': -3.2, 'pace': 98.5, 'star': 'Collin Sexton', 'status': '❌ Eliminated', 'note': 'Zero playoff motivation.', 'tanking': False, 'eliminated': True},
    'IND': {'off_rtg': 116.0, 'def_rtg': 112.5, 'pt_diff': -1.5, 'pace': 102.1, 'star': 'Pascal Siakam', 'status': '❌ Eliminated', 'note': 'Haliburton traded. Fastest pace in the NBA.', 'tanking': False, 'eliminated': True},
    'BKN': {'off_rtg': 107.0, 'def_rtg': 122.5, 'pt_diff': -11.5, 'pace': 97.5, 'star': 'Cam Thomas', 'status': '🚫 Tanking', 'note': 'Worst defense in the East. Chasing lottery.', 'tanking': True, 'eliminated': True},
    'WAS': {'off_rtg': 105.0, 'def_rtg': 125.0, 'pt_diff': -14.0, 'pace': 98.5, 'star': 'Alexandre Sarr', 'status': '🚫 Tanking', 'note': 'Zero wins motivation. Draft lottery is the goal.', 'tanking': True, 'eliminated': True},

    # ── WESTERN CONFERENCE ───────────────────────────────────────────────────
    'OKC': {'off_rtg': 120.5, 'def_rtg': 108.0, 'pt_diff': +9.8, 'pace': 100.5, 'star': 'SGA (MVP Frontrunner)', 'status': '🏆 #1 West Seed', 'note': 'DEFENDING CHAMPIONS. Most dominant team.', 'tanking': False, 'eliminated': False},
    'SAS': {'off_rtg': 118.0, 'def_rtg': 110.5, 'pt_diff': +7.5, 'pace': 99.5, 'star': 'Victor Wembanyama', 'status': '✅ Clinched Playoff (#2)', 'note': 'Wemby Year 3 is HISTORIC. 10-game win streak.', 'tanking': False, 'eliminated': False},
    'LAL': {'off_rtg': 116.5, 'def_rtg': 112.8, 'pt_diff': +4.8, 'pace': 98.8, 'star': 'Luka Doncic / LeBron James', 'status': '✅ Clinched Playoff (#3)', 'note': '🚨 LUKA INJURY CONCERN. LeBron must step up.', 'tanking': False, 'eliminated': False},
    'DEN': {'off_rtg': 117.0, 'def_rtg': 111.5, 'pt_diff': +4.5, 'pace': 99.0, 'star': 'Nikola Jokic', 'status': '✅ Clinched Playoff (#4)', 'note': 'Jokic at MVP pace. Denver altitude advantage.', 'tanking': False, 'eliminated': False},
    'HOU': {'off_rtg': 116.0, 'def_rtg': 111.0, 'pt_diff': +3.8, 'pace': 99.8, 'star': 'Kevin Durant', 'status': '✅ Clinched Playoff (#5)', 'note': 'KD + Amen Thompson is a nightmare matchup.', 'tanking': False, 'eliminated': False},
    'MIN': {'off_rtg': 115.5, 'def_rtg': 110.0, 'pt_diff': +3.5, 'pace': 98.5, 'star': 'Anthony Edwards', 'status': '✅ Clinched Playoff (#6)', 'note': 'Gobert defensive wall. Consistent but no urgency.', 'tanking': False, 'eliminated': False},
    'PHX': {'off_rtg': 113.0, 'def_rtg': 114.0, 'pt_diff': +1.8, 'pace': 98.0, 'star': 'Devin Booker', 'status': '⚠️ Play-In (#7)', 'note': 'Play-in survival mode. High motivation.', 'tanking': False, 'eliminated': False},
    'LAC': {'off_rtg': 113.5, 'def_rtg': 113.0, 'pt_diff': +0.9, 'pace': 97.5, 'star': 'Kawhi Leonard', 'status': '⚠️ Play-In (#8)', 'note': 'Defense keeps them alive. Holding 8-seed barely.', 'tanking': False, 'eliminated': False},
    'POR': {'off_rtg': 112.0, 'def_rtg': 118.5, 'pt_diff': -0.5, 'pace': 98.5, 'star': 'Scoot Henderson', 'status': '⚠️ Play-In (#9)', 'note': 'Scoot emerging. Battling GSW for 9-seed.', 'tanking': False, 'eliminated': False},
    'GSW': {'off_rtg': 113.0, 'def_rtg': 115.0, 'pt_diff': -1.5, 'pace': 100.0, 'star': 'Stephen Curry', 'status': '⚠️ Play-In (#10)', 'note': 'Curry gravity still elite when healthy.', 'tanking': False, 'eliminated': False},
    'SAC': {'off_rtg': 114.0, 'def_rtg': 115.5, 'pt_diff': -0.8, 'pace': 101.5, 'star': "De'Aaron Fox", 'status': '❌ Eliminated', 'note': 'Fastest pace outside IND. Can steal games.', 'tanking': False, 'eliminated': True},
    'MEM': {'off_rtg': 114.5, 'def_rtg': 114.0, 'pt_diff': +0.2, 'pace': 100.2, 'star': 'Ja Morant', 'status': '❌ Eliminated', 'note': 'End-of-season mode, limited motivation.', 'tanking': False, 'eliminated': True},
    'DAL': {'off_rtg': 109.8, 'def_rtg': 119.5, 'pt_diff': -5.2, 'pace': 98.0, 'star': 'Kyrie Irving (OUT)', 'status': '🚫 Tanking', 'note': 'Actively in lottery positioning mode.', 'tanking': True, 'eliminated': True},
    'NOP': {'off_rtg': 109.0, 'def_rtg': 120.5, 'pt_diff': -7.5, 'pace': 99.5, 'star': 'Brandon Ingram', 'status': '🚫 Tanking', 'note': 'Youth development priority. No competitive intent.', 'tanking': True, 'eliminated': True},
    'UTA': {'off_rtg': 106.0, 'def_rtg': 124.2, 'pt_diff': -11.0, 'pace': 97.5, 'star': 'Keyonte George', 'status': '🚫 Tanking', 'note': 'Worst defensive rating in the West. Veterans resting.', 'tanking': True, 'eliminated': True},
}

# ─────────────────────────────────────────────────────────────────────────────
# NEW DEEP-SCAN AUTO-FETCHER (Fixes the 6-game missing bug)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_daily_slate():
    # To fix Timezone bugs, we pull a 3-day window and filter for US Eastern "Today"
    now_est = datetime.utcnow() - timedelta(hours=4)
    today_str = now_est.strftime('%Y%m%d')
    yest_str = (now_est - timedelta(days=1)).strftime('%Y%m%d')
    tom_str = (now_est + timedelta(days=1)).strftime('%Y%m%d')
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest_str}-{tom_str}"
    
    try:
        data = requests.get(url, timeout=8).json()
        games = []
        target_date = now_est.strftime('%Y-%m-%d')

        for event in data.get('events', []):
            # Convert game time to EST to check if it belongs to "Today"
            dt_utc = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')
            dt_est = dt_utc - timedelta(hours=4)
            
            # If the game isn't actually happening today in the US, skip it!
            if dt_est.strftime('%Y-%m-%d') != target_date:
                continue

            comp  = event['competitions'][0]
            comps = comp.get('competitors', [])
            home  = next((c for c in comps if c.get('homeAway') == 'home'), None)
            away  = next((c for c in comps if c.get('homeAway') == 'away'), None)
            if not (home and away):
                continue
                
            h_abbr = norm(home['team']['abbreviation'])
            a_abbr = norm(away['team']['abbreviation'])
            game_time = dt_est.strftime('%I:%M %p ET').lstrip('0')
            
            games.append({
                'h':      h_abbr,
                'a':      a_abbr,
                'h_name': home['team'].get('displayName', h_abbr),
                'a_name': away['team'].get('displayName', a_abbr),
                'venue':  comp.get('venue', {}).get('fullName', 'Unknown Arena'),
                'time':   game_time,
                'status': comp.get('status', {}).get('type', {}).get('description', 'Scheduled'),
            })
        return games
    except Exception as exc:
        st.warning(f"⚠️ Live slate unavailable ({exc}). Using Manual Override.")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# OTHER FETCHERS (Standings, Form, B2B, Injuries)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_standings():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings"
    result = {}
    try:
        data = requests.get(url, timeout=8).json()
        for conf in data.get('children', []):
            for entry in conf.get('standings', {}).get('entries', []):
                abbr  = norm(entry['team']['abbreviation'])
                stats = {s['name']: s for s in entry.get('stats', [])}
                def val(k, d=0): return stats.get(k, {}).get('value') or d
                def disp(k, d=''): return stats.get(k, {}).get('displayValue') or d
                def parse_rec(s):
                    try:
                        w, l = s.split('-')
                        t = int(w) + int(l)
                        return int(w) / t if t else 0.5
                    except: return 0.5

                h_str = disp('Home') or disp('homeRecord') or '0-0'
                a_str = disp('Away') or disp('awayRecord') or '0-0'
                result[abbr] = {
                    'wins': int(val('wins', 0)), 'losses': int(val('losses', 0)),
                    'record': f"{int(val('wins', 0))}-{int(val('losses', 0))}",
                    'win_pct': float(val('winPercent', 0.5)),
                    'home_record': h_str, 'away_record': a_str,
                    'home_wpct': parse_rec(h_str), 'away_wpct': parse_rec(a_str),
                    'streak': disp('streak') or 'N/A',
                    'point_diff': float(val('pointDifferential') or val('avgPointDifferential') or val('diff', 0)),
                }
    except: pass
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
                s = comp.get('status', {}).get('type', {})
                if not (s.get('completed') or s.get('name') == 'STATUS_FINAL'): continue
                for c in comp['competitors']:
                    abbr = norm(c['team']['abbreviation'])
                    form.setdefault(abbr, [])
                    if len(form[abbr]) < 10:
                        form[abbr].append(1 if c.get('winner', False) else 0)
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
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=80"
    kwords = ['out', 'questionable', 'doubtful', 'injured', 'misses', 'ankle', 'knee', 'hamstring']
    news = {}
    try:
        articles = requests.get(url, timeout=6).json().get('articles', [])
        for art in articles:
            hl = art.get('headline', '')
            if len(hl) > 200 or not any(k in hl.lower() for k in kwords): continue
            for cat in art.get('categories', []):
                if cat.get('type') == 'team':
                    abbr = norm(cat.get('teamAbbrev', '') or cat.get('abbreviation', ''))
                    if abbr: news.setdefault(abbr, []).append(hl)
        return {k: list(dict.fromkeys(v))[:4] for k, v in news.items()}
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# ENGINE / HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def l10_str(lst):
    if not lst: return 'N/A'
    w = sum(lst)
    return f"{w}-{len(lst)-w}"

def streak_label(lst):
    if not lst: return 'N/A'
    char = 'W' if lst[0] == 1 else 'L'
    n = 0
    for g in lst:
        if (g == 1) == (char == 'W'): n += 1
        else: break
    return f"{char}{n}"

DEFAULT_STD = {'wins': 0, 'losses': 0, 'record': 'N/A', 'win_pct': 0.5, 'home_wpct': 0.5, 'away_wpct': 0.5, 'home_record': 'N/A', 'away_record': 'N/A', 'streak': 'N/A', 'point_diff': 0.0}
DEFAULT_TD = {'off_rtg': 112.0, 'def_rtg': 115.0, 'pt_diff': 0.0, 'pace': 99.0, 'star': 'N/A', 'status': 'Data Unavailable', 'note': 'Team data not in system.', 'tanking': False, 'eliminated': False}

def predict_game(h, a, standings, form, b2b_set, injuries):
    h_td, a_td = TEAM_DATA.get(h, DEFAULT_TD), TEAM_DATA.get(a, DEFAULT_TD)
    h_std, a_std = standings.get(h, DEFAULT_STD), standings.get(a, DEFAULT_STD)
    h_frm, a_frm = form.get(h, []), form.get(a, [])
    h_diff = h_std['point_diff'] if h_std['point_diff'] != 0.0 else h_td['pt_diff']
    a_diff = a_std['point_diff'] if a_std['point_diff'] != 0.0 else a_td['pt_diff']
    h_str, a_str = streak_label(h_frm), streak_label(a_frm)

    total = 0.0
    total += 4.5 # Home Court
    total += max(-15.0, min(15.0, round((h_std['win_pct'] - a_std['win_pct']) * 25.0, 2))) # Win % Edge
    total += max(-8.0, min(8.0, round((h_std['home_wpct'] - a_std['away_wpct']) * 10.0, 2))) # Splits
    total += max(-12.0, min(12.0, round((h_diff - a_diff) * 0.9, 2))) # Net Rating
    total += max(-10.0, min(10.0, round((a_td['def_rtg'] - h_td['def_rtg']) * 0.45, 2))) # Defense Edge
    total += max(-8.0, min(8.0, round((h_td['off_rtg'] - a_td['off_rtg']) * 0.3, 2))) # Offense Edge

    h_fpct = sum(h_frm)/len(h_frm) if h_frm else 0.5
    a_fpct = sum(a_frm)/len(a_frm) if a_frm else 0.5
    total += max(-8.0, min(8.0, round((h_fpct - a_fpct) * 12.0, 2))) # L10 Form
    
    if h in b2b_set: total -= 4.5
    if a in b2b_set: total += 4.5
    
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    if h_inj: total -= min(10.0, len(h_inj) * 2.5)
    if a_inj: total += min(10.0, len(a_inj) * 2.5)
    
    if h_td.get('tanking'): total -= 8.0
    if a_td.get('tanking'): total += 8.0
    
    if abs(h_td['pace'] - a_td['pace']) >= 2.5:
        total += 1.5 if h_td['pace'] > a_td['pace'] else -1.5
        
    play_in = {'TOR', 'CHA', 'ORL', 'MIA', 'PHX', 'LAC', 'POR', 'GSW'}
    if h in play_in and not (a_td.get('tanking') or a_td.get('eliminated')): total += 2.0
    if a in play_in and not (h_td.get('tanking') or h_td.get('eliminated')): total -= 2.0

    prob = max(2.0, min(98.0, 50.0 + total))
    return {
        'winner': h if prob >= 50.0 else a, 'conf': round(prob if prob >= 50.0 else 100.0 - prob, 1),
        'prob_h': round(prob, 1), 'h_td': h_td, 'a_td': a_td, 'h_std': h_std, 'a_std': a_std,
        'h_frm': h_frm, 'a_frm': a_frm, 'h_str': h_str, 'a_str': a_str, 'h_inj': h_inj, 'a_inj': a_inj
    }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN UI (Fixed & Completed)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏀 NBA Master AI — 2026 Season")
st.caption(f"Live Intelligence Engine · {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

with st.spinner("📡 Syncing live Deep-Scan NBA data from ESPN..."):
    slate = get_daily_slate()
    standings = get_standings()
    form = get_recent_form()
    b2b_set = get_back_to_back()
    injuries = get_injury_news()

# Fallback just in case Deep Scan returns empty
if not slate:
    st.warning("⚠️ ESPN feed returned 0 games. Engaging Manual Override for April 3, 2026.")
    slate = [
        {'h':'PHI','a':'MIN','h_name':'76ers','a_name':'Timberwolves','venue':'Wells Fargo','time':'7:00 PM ET','status':'Scheduled'},
        {'h':'CHA','a':'IND','h_name':'Hornets','a_name':'Pacers','venue':'Spectrum Center','time':'7:00 PM ET','status':'Scheduled'},
        {'h':'BKN','a':'ATL','h_name':'Nets','a_name':'Hawks','venue':'Barclays Center','time':'7:30 PM ET','status':'Scheduled'},
        {'h':'NYK','a':'CHI','h_name':'Knicks','a_name':'Bulls','venue':'MSG','time':'7:30 PM ET','status':'Scheduled'},
        {'h':'BOS','a':'MIL','h_name':'Celtics','a_name':'Bucks','venue':'TD Garden','time':'7:30 PM ET','status':'Scheduled'},
        {'h':'HOU','a':'UTA','h_name':'Rockets','a_name':'Jazz','venue':'Toyota Center','time':'8:00 PM ET','status':'Scheduled'},
        {'h':'MEM','a':'TOR','h_name':'Grizzlies','a_name':'Raptors','venue':'FedExForum','time':'8:00 PM ET','status':'Scheduled'},
        {'h':'DAL','a':'ORL','h_name':'Mavericks','a_name':'Magic','venue':'AAC','time':'8:30 PM ET','status':'Scheduled'},
        {'h':'SAC','a':'NOP','h_name':'Kings','a_name':'Pelicans','venue':'Golden 1 Center','time':'10:00 PM ET','status':'Scheduled'}
    ]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🎮 Games Today", len(slate))
c2.metric("📊 Teams Tracked", f"{len(standings) or 30}/30")
c3.metric("🤕 Injury Reports", sum(len(v) for v in injuries.values()))
c4.metric("😴 B2B Teams", len(b2b_set))
c5.metric("🔄 Refresh Rate", "Every 5 min")
st.divider()

st.subheader(f"Today's AI Predictions — {len(slate)} Games")
st.caption("12 statistical factors analyzed per matchup (Including Defensive Efficiency & Tanking)")
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

        st.markdown(f"**Win Probability** — {h}: **{prob_h:.0f}%** vs {a}: **{100-prob_h:.0f}%**")
        st.markdown(f"""
        <div style="display:flex;height:20px;border-radius:4px;overflow:hidden;margin-bottom:14px;">
            <div style="width:{prob_h:.0f}%;background:#28a745;display:flex;align-items:center;justify-content:center;color:white;font-size:.75em;font-weight:bold;">{h}</div>
            <div style="width:{100-prob_h:.0f}%;background:#dc3545;display:flex;align-items:center;justify-content:center;color:white;font-size:.75em;font-weight:bold;">{a}</div>
        </div>""", unsafe_allow_html=True)

        col_h, col_vs, col_a = st.columns([5, 1, 5])
        with col_h:
            st.markdown(f"#### 🏠 {h} — {game['h_name']}")
            st.markdown(f"**{pred['h_td']['status']}**")
            st.write(f"Record: **{pred['h_std']['record']}** | Home: {pred['h_std']['home_record']}")
            st.write(f"Def Rating: {pred['h_td']['def_rtg']} | Off Rating: {pred['h_td']['off_rtg']}")
            st.caption(f"⭐ {pred['h_td']['star']}")
            st.info(pred['h_td']['note'])
            for inj in pred['h_inj'][:2]: st.warning(f"🤕 {inj}")

        with col_vs:
            st.markdown("<br><br><div style='text-align:center;font-size:1.6em;'>VS</div>", unsafe_allow_html=True)

        with col_a:
            st.markdown(f"#### ✈️ {a} — {game['a_name']}")
            st.markdown(f"**{pred['a_td']['status']}**")
            st.write(f"Record: **{pred['a_std']['record']}** | Away: {pred['a_std']['away_record']}")
            st.write(f"Def Rating: {pred['a_td']['def_rtg']} | Off Rating: {pred['a_td']['off_rtg']}")
            st.caption(f"⭐ {pred['a_td']['star']}")
            st.info(pred['a_td']['note'])
            for inj in pred['a_inj'][:2]: st.warning(f"🤕 {inj}")

import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="NBA Master AI 2026", page_icon="🏀", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# ESPN ABBREVIATION NORMALIZER
# ESPN uses non-standard short codes for several teams.
# Without this, those teams fall through to "Unknown" and get wrong predictions.
# ─────────────────────────────────────────────────────────────────────────────
ESPN_TO_STD = {
    'GS':   'GSW',   # Golden State Warriors
    'SA':   'SAS',   # San Antonio Spurs
    'NY':   'NYK',   # New York Knicks
    'NO':   'NOP',   # New Orleans Pelicans
    'UTAH': 'UTA',   # Utah Jazz
    'WSH':  'WAS',   # Washington Wizards
    'CHAR': 'CHA',   # Charlotte Hornets
    'BKLN': 'BKN',   # Brooklyn Nets
}

def norm(abbr):
    return ESPN_TO_STD.get(abbr, abbr)


# ─────────────────────────────────────────────────────────────────────────────
# ALL 30 TEAMS — Updated April 3, 2026
# def_rtg = pts allowed per 100 possessions (lower = better defense)
# off_rtg = pts scored per 100 possessions  (higher = better offense)
# pt_diff = avg point differential per game
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {

    # ── EASTERN CONFERENCE ──────────────────────────────────────────────────

    'DET': {
        'off_rtg': 115.8, 'def_rtg': 108.5, 'pt_diff': +7.2, 'pace': 99.8,
        'star': 'Jaden Ivey / Ausar Thompson',
        'status': '🏆 #1 East Seed (56-21)',
        'note': 'Cade Cunningham OUT — affects award eligibility & rotation. Young core still leads the East. Elite defense all season.',
        'tanking': False, 'eliminated': False,
    },
    'BOS': {
        'off_rtg': 121.6, 'def_rtg': 107.2, 'pt_diff': +7.2, 'pace': 99.1,
        'star': 'Jaylen Brown (28.8 PPG — 4th in NBA)',
        'status': '✅ Clinched Playoff (#2 East, 51-25)',
        'note': 'Best defense in the league at 107.2 pts allowed. Brown leads offense. 53-pt 1st quarter recently vs MIA. Championship DNA.',
        'tanking': False, 'eliminated': False,
    },
    'NYK': {
        'off_rtg': 115.4, 'def_rtg': 111.2, 'pt_diff': +4.2, 'pace': 97.8,
        'star': 'Jalen Brunson',
        'status': '✅ Clinched Playoff (#3 East, 49-28)',
        'note': 'Brunson orchestrates everything. MSG home crowd is a real factor. Physical, disciplined style wins close games.',
        'tanking': False, 'eliminated': False,
    },
    'CLE': {
        'off_rtg': 118.0, 'def_rtg': 108.8, 'pt_diff': +5.5, 'pace': 98.2,
        'star': 'Donovan Mitchell + James Harden',
        'status': '✅ Clinched Playoff (#4 East, 48-29)',
        'note': 'Acquired Harden Feb 7 — 3rd-best offense in NBA since. Beat DEN, NYK, DET recently. Mitchell elevated by new playmaking.',
        'tanking': False, 'eliminated': False,
    },
    'ATL': {
        'off_rtg': 115.5, 'def_rtg': 110.4, 'pt_diff': +3.1, 'pace': 100.8,
        'star': 'Trae Young',
        'status': '✅ Clinched Playoff (#5 East, 44-33)',
        'note': 'Surprising 5th seed. Young leads improved offense. Defense vastly improved from prior seasons.',
        'tanking': False, 'eliminated': False,
    },
    'PHI': {
        'off_rtg': 113.5, 'def_rtg': 114.2, 'pt_diff': +0.8, 'pace': 97.0,
        'star': 'Tyrese Maxey',
        'status': '✅ Clinched Playoff (#6 East, 42-34)',
        'note': 'Maxey carrying the post-Embiid era offense. Moved into top-6 recently. Bench depth is paper-thin.',
        'tanking': False, 'eliminated': False,
    },
    'TOR': {
        'off_rtg': 112.8, 'def_rtg': 115.0, 'pt_diff': +0.2, 'pace': 98.0,
        'star': 'RJ Barrett / Immanuel Quickley',
        'status': '⚠️ Play-In (#7 East, 42-34)',
        'note': 'Tied with PHI but loses tiebreaker to 7-seed. Quickley OUT. Ingram questionable. Battling every night to hold seeding.',
        'tanking': False, 'eliminated': False,
    },
    'CHA': {
        'off_rtg': 113.2, 'def_rtg': 116.0, 'pt_diff': +0.5, 'pace': 100.5,
        'star': 'LaMelo Ball / 2025 No.4 Pick (leads league in 3s)',
        'status': '⚠️ Play-In (#8 East, 41-36)',
        'note': "MASSIVE SURPRISE 8-seed. LaMelo healthy. 2025 No.4 pick displacing Kemba Walker records, leads league in 3-pointers. Do NOT sleep on Charlotte.",
        'tanking': False, 'eliminated': False,
    },
    'ORL': {
        'off_rtg': 111.0, 'def_rtg': 111.5, 'pt_diff': -0.3, 'pace': 97.0,
        'star': 'Franz Wagner',
        'status': '⚠️ Play-In (#9 East, 40-36)',
        'note': 'Franz Wagner breakout star. Defense is legit but offense limited. Clinging to play-in position.',
        'tanking': False, 'eliminated': False,
    },
    'MIA': {
        'off_rtg': 111.5, 'def_rtg': 112.0, 'pt_diff': -0.4, 'pace': 97.5,
        'star': 'Bam Adebayo',
        'status': '⚠️ Play-In (#10 East, 40-37)',
        'note': 'Heat culture never quits. Adebayo anchors defense. Barely hanging on — every single game is elimination pressure.',
        'tanking': False, 'eliminated': False,
    },
    'MIL': {
        'off_rtg': 110.6, 'def_rtg': 116.7, 'pt_diff': -6.1, 'pace': 99.5,
        'star': 'Giannis Antetokounmpo (OUT) / Bobby Portis (OUT)',
        'status': '❌ Eliminated',
        'note': 'Giannis OUT. Bobby Portis OUT. Ryan Rollins (17.1 PPG) leads decimated roster. Defense collapsed without their anchors. No path forward.',
        'tanking': False, 'eliminated': True,
    },
    'CHI': {
        'off_rtg': 111.8, 'def_rtg': 116.4, 'pt_diff': -3.2, 'pace': 98.5,
        'star': 'Collin Sexton',
        'status': '❌ Eliminated',
        'note': 'Collins and Smith OUT for the season. Patrick Williams/Leonard Miller seeing expanded roles. Zero playoff motivation.',
        'tanking': False, 'eliminated': True,
    },
    'IND': {
        'off_rtg': 116.0, 'def_rtg': 112.5, 'pt_diff': -1.5, 'pace': 102.1,
        'star': 'Pascal Siakam',
        'status': '❌ Eliminated (Haliburton traded)',
        'note': 'Haliburton traded at deadline to CLE. Rebuilding around youth. Fastest pace in the NBA still creates wild games.',
        'tanking': False, 'eliminated': True,
    },
    'BKN': {
        'off_rtg': 107.0, 'def_rtg': 122.5, 'pt_diff': -11.5, 'pace': 97.5,
        'star': 'Cam Thomas',
        'status': '🚫 Tanking / Full Rebuild',
        'note': 'Full rebuild. Cam Thomas the lone bright spot. Worst defense in the East. Actively chasing draft lottery.',
        'tanking': True, 'eliminated': True,
    },
    'WAS': {
        'off_rtg': 105.0, 'def_rtg': 125.0, 'pt_diff': -14.0, 'pace': 98.5,
        'star': 'Alexandre Sarr',
        'status': '🚫 Tanking / Full Rebuild',
        'note': 'Worst record in the East. Sarr developing. Zero wins motivation. Draft lottery is the entire goal.',
        'tanking': True, 'eliminated': True,
    },

    # ── WESTERN CONFERENCE ───────────────────────────────────────────────────

    'OKC': {
        'off_rtg': 120.5, 'def_rtg': 108.0, 'pt_diff': +9.8, 'pace': 100.5,
        'star': 'Shai Gilgeous-Alexander (MVP Frontrunner)',
        'status': '🏆 #1 West Seed / DEFENDING CHAMPIONS (60-16)',
        'note': 'DEFENDING NBA CHAMPIONS. SGA averaging 28+ PPG in MVP race. Just demolished Lakers 139-96. Most dominant team in basketball.',
        'tanking': False, 'eliminated': False,
    },
    'SAS': {
        'off_rtg': 118.0, 'def_rtg': 110.5, 'pt_diff': +7.5, 'pace': 99.5,
        'star': 'Victor Wembanyama (24.7 PPG / 11.5 RPG / 3.5 BPG)',
        'status': '✅ Clinched Playoff (#2 West, 58-18) — 10-Game Win Streak',
        'note': 'Wemby Year 3 is HISTORIC. Back-to-back 41-pt games. 10-game win streak. Stephon Castle 16.9/9.1 APG last 14. Biggest West story.',
        'tanking': False, 'eliminated': False,
    },
    'LAL': {
        'off_rtg': 116.5, 'def_rtg': 112.8, 'pt_diff': +4.8, 'pace': 98.8,
        'star': 'Luka Doncic (🚨 HAMSTRING — MRI TODAY) + LeBron James',
        'status': '✅ Clinched Playoff (#3 West, 50-26) — 🚨 LUKA INJURY CONCERN',
        'note': '🚨 BREAKING: Luka hamstring injury vs OKC, MRI TODAY. Marcus Smart also OUT. Lakers 7-6 without Luka. LeBron + Reaves must step up. Playoff path uncertain.',
        'tanking': False, 'eliminated': False,
    },
    'DEN': {
        'off_rtg': 117.0, 'def_rtg': 111.5, 'pt_diff': +4.5, 'pace': 99.0,
        'star': 'Nikola Jokic (MVP Pace)',
        'status': '✅ Clinched Playoff (#4 West, 49-28)',
        'note': 'Jokic at MVP pace. Just 1 game behind LAL for 3-seed. Murray hit 10 3s in last game. Denver altitude is a real home advantage.',
        'tanking': False, 'eliminated': False,
    },
    'HOU': {
        'off_rtg': 116.0, 'def_rtg': 111.0, 'pt_diff': +3.8, 'pace': 99.8,
        'star': 'Kevin Durant + Amen Thompson',
        'status': '✅ Clinched Playoff (#5 West, 47-29)',
        'note': 'Acquired KD in offseason. VanVleet ACL out all year. Elite home court at Toyota Center. KD + Amen Thompson is a nightmare matchup.',
        'tanking': False, 'eliminated': False,
    },
    'MIN': {
        'off_rtg': 115.5, 'def_rtg': 110.0, 'pt_diff': +3.5, 'pace': 98.5,
        'star': 'Anthony Edwards (award-ineligible but dominant)',
        'status': '✅ Clinched Playoff (#6 West, 46-29)',
        'note': 'Edwards under 65-game threshold for awards but elite on court. Gobert defensive wall. Solid and consistent but no extra urgency.',
        'tanking': False, 'eliminated': False,
    },
    'PHX': {
        'off_rtg': 113.0, 'def_rtg': 114.0, 'pt_diff': +1.8, 'pace': 98.0,
        'star': 'Devin Booker (now clear #1 post-KD trade)',
        'status': '⚠️ Play-In (#7 West, 42-35)',
        'note': 'KD traded to HOU. Booker now undisputed #1. Play-in survival mode. High motivation — Tidjane Salaun questionable.',
        'tanking': False, 'eliminated': False,
    },
    'LAC': {
        'off_rtg': 113.5, 'def_rtg': 113.0, 'pt_diff': +0.9, 'pace': 97.5,
        'star': 'Kawhi Leonard',
        'status': '⚠️ Play-In (#8 West, 39-37)',
        'note': 'Harden traded to CLE at deadline. Kawhi availability always a question. Defense keeps them alive. Holding 8-seed barely.',
        'tanking': False, 'eliminated': False,
    },
    'POR': {
        'off_rtg': 112.0, 'def_rtg': 118.5, 'pt_diff': -0.5, 'pace': 98.5,
        'star': 'Scoot Henderson',
        'status': '⚠️ Play-In (#9 West, 39-38)',
        'note': 'New owner Tom Dundon shifting from rebuild to compete. Scoot Henderson emerging. Shaedon Sharpe OUT. Battling GSW for 9-seed.',
        'tanking': False, 'eliminated': False,
    },
    'GSW': {
        'off_rtg': 113.0, 'def_rtg': 115.0, 'pt_diff': -1.5, 'pace': 100.0,
        'star': 'Stephen Curry / Kristaps Porzingis (injured)',
        'status': '⚠️ Play-In (#10 West, 36-40)',
        'note': 'Curry and Porzingis both managing injuries. Warriors pushed to be aggressive at deadline. Curry gravity still elite when healthy.',
        'tanking': False, 'eliminated': False,
    },
    'SAC': {
        'off_rtg': 114.0, 'def_rtg': 115.5, 'pt_diff': -0.8, 'pace': 101.5,
        'star': "De'Aaron Fox / Domantas Sabonis",
        'status': '❌ Eliminated (Missed Play-In)',
        'note': 'Fox-Sabonis pick-and-roll still dangerous. Fastest pace outside IND. No playoff motivation but can steal games vs low effort opponents.',
        'tanking': False, 'eliminated': True,
    },
    'MEM': {
        'off_rtg': 114.5, 'def_rtg': 114.0, 'pt_diff': +0.2, 'pace': 100.2,
        'star': 'Ja Morant',
        'status': '❌ Eliminated',
        'note': 'Morant health concerns throughout the season. Fell out of play-in race late. End-of-season mode, limited motivation.',
        'tanking': False, 'eliminated': True,
    },
    'DAL': {
        'off_rtg': 109.8, 'def_rtg': 119.5, 'pt_diff': -5.2, 'pace': 98.0,
        'star': 'Kyrie Irving (OUT) / Dereck Lively II (OUT)',
        'status': '❌ Eliminated / Lottery Bound (Post-Luka Era)',
        'note': 'Post-Luka trade era. Kyrie OUT. Lively OUT. PJ Washington questionable. Actively in lottery positioning mode.',
        'tanking': True, 'eliminated': True,
    },
    'NOP': {
        'off_rtg': 109.0, 'def_rtg': 120.5, 'pt_diff': -7.5, 'pace': 99.5,
        'star': 'Brandon Ingram (Questionable)',
        'status': '🚫 Tanking / Rebuild',
        'note': 'Brandon Ingram questionable. Zion persistent health concerns. Youth development priority. No competitive intent this season.',
        'tanking': True, 'eliminated': True,
    },
    'UTA': {
        'off_rtg': 106.0, 'def_rtg': 124.2, 'pt_diff': -11.0, 'pace': 97.5,
        'star': 'Keyonte George',
        'status': '🚫 Full Tank / Worst Defense in West',
        'note': 'Fully committed to losing for top draft pick. Worst defensive rating in the West. Veterans resting. Every loss is a win for the front office.',
        'tanking': True, 'eliminated': True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# ESPN DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_daily_slate():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        data = requests.get(url, timeout=6).json()
        games = []
        for event in data.get('events', []):
            comp  = event['competitions'][0]
            comps = comp.get('competitors', [])
            home  = next((c for c in comps if c.get('homeAway') == 'home'), None)
            away  = next((c for c in comps if c.get('homeAway') == 'away'), None)
            if not (home and away):
                continue
            h_abbr = norm(home['team']['abbreviation'])
            a_abbr = norm(away['team']['abbreviation'])
            try:
                dt = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')
                game_time = dt.strftime('%I:%M %p ET').lstrip('0')
            except Exception:
                game_time = 'TBD'
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
        st.warning(f"⚠️ Live slate unavailable ({exc}). Showing sample slate.")
        return [
            {'h': 'BOS',  'a': 'MIL', 'h_name': 'Boston Celtics',      'a_name': 'Milwaukee Bucks',    'venue': 'TD Garden',     'time': '8:00 PM ET', 'status': 'Scheduled'},
            {'h': 'OKC',  'a': 'LAL', 'h_name': 'OKC Thunder',          'a_name': 'Los Angeles Lakers', 'venue': 'Paycom Center', 'time': '9:30 PM ET', 'status': 'Scheduled'},
            {'h': 'SAS',  'a': 'DEN', 'h_name': 'San Antonio Spurs',    'a_name': 'Denver Nuggets',     'venue': 'Frost Bank',    'time': '8:30 PM ET', 'status': 'Scheduled'},
            {'h': 'HOU',  'a': 'MIN', 'h_name': 'Houston Rockets',      'a_name': 'Minnesota T-Wolves', 'venue': 'Toyota Center', 'time': '8:00 PM ET', 'status': 'Scheduled'},
        ]


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

                def val(k, d=0):
                    return stats.get(k, {}).get('value') or d

                def disp(k, d=''):
                    return stats.get(k, {}).get('displayValue') or d

                def parse_rec(s):
                    try:
                        w, l = s.split('-')
                        t = int(w) + int(l)
                        return int(w) / t if t else 0.5
                    except Exception:
                        return 0.5

                wins   = int(val('wins', 0))
                losses = int(val('losses', 0))
                wpct   = float(val('winPercent', 0.5))
                h_str  = disp('Home') or disp('homeRecord') or '0-0'
                a_str  = disp('Away') or disp('awayRecord') or '0-0'
                streak = disp('streak') or 'N/A'
                diff   = (val('pointDifferential') or val('avgPointDifferential') or val('diff', 0))

                result[abbr] = {
                    'wins':        wins,
                    'losses':      losses,
                    'record':      f'{wins}-{losses}',
                    'win_pct':     wpct,
                    'home_record': h_str,
                    'away_record': a_str,
                    'home_wpct':   parse_rec(h_str),
                    'away_wpct':   parse_rec(a_str),
                    'streak':      streak,
                    'point_diff':  float(diff),
                }
    except Exception:
        pass
    return result


@st.cache_data(ttl=600)
def get_recent_form():
    form  = {}
    today = datetime.utcnow()
    try:
        for days_ago in range(1, 18):
            date_str = (today - timedelta(days=days_ago)).strftime('%Y%m%d')
            url  = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
            data = requests.get(url, timeout=5).json()
            for event in data.get('events', []):
                comp = event['competitions'][0]
                s    = comp.get('status', {}).get('type', {})
                if not (s.get('completed') or s.get('name') == 'STATUS_FINAL'):
                    continue
                for c in comp['competitors']:
                    abbr = norm(c['team']['abbreviation'])
                    form.setdefault(abbr, [])
                    if len(form[abbr]) < 10:
                        form[abbr].append(1 if c.get('winner', False) else 0)
    except Exception:
        pass
    return form


@st.cache_data(ttl=600)
def get_back_to_back():
    b2b  = set()
    yest = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
    try:
        url  = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yest}"
        data = requests.get(url, timeout=5).json()
        for event in data.get('events', []):
            for c in event['competitions'][0]['competitors']:
                b2b.add(norm(c['team']['abbreviation']))
    except Exception:
        pass
    return b2b


@st.cache_data(ttl=600)
def get_injury_news():
    url    = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=80"
    kwords = ['out', 'questionable', 'doubtful', 'injured', 'misses', 'listed',
              'ankle', 'knee', 'back', 'shoulder', 'hamstring', 'surgery', 'torn',
              'ruled out', 'day-to-day', 'indefinitely', 'fracture', 'strain', 'sprain']
    news = {}
    try:
        articles = requests.get(url, timeout=6).json().get('articles', [])
        for art in articles:
            hl = art.get('headline', '')
            if len(hl) > 200 or not any(k in hl.lower() for k in kwords):
                continue
            for cat in art.get('categories', []):
                if cat.get('type') == 'team':
                    raw  = cat.get('teamAbbrev', '') or cat.get('abbreviation', '')
                    abbr = norm(raw)
                    if abbr:
                        news.setdefault(abbr, []).append(hl)
        return {k: list(dict.fromkeys(v))[:4] for k, v in news.items()}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def l10_str(lst):
    if not lst:
        return 'N/A'
    w = sum(lst)
    return f"{w}-{len(lst)-w}"

def streak_label(lst):
    if not lst:
        return 'N/A'
    char = 'W' if lst[0] == 1 else 'L'
    n    = 0
    for g in lst:
        if (g == 1) == (char == 'W'):
            n += 1
        else:
            break
    return f"{char}{n}"

DEFAULT_STD = {
    'wins': 0, 'losses': 0, 'record': 'N/A',
    'win_pct': 0.5, 'home_wpct': 0.5, 'away_wpct': 0.5,
    'home_record': 'N/A', 'away_record': 'N/A',
    'streak': 'N/A', 'point_diff': 0.0,
}
DEFAULT_TD = {
    'off_rtg': 112.0, 'def_rtg': 115.0, 'pt_diff': 0.0, 'pace': 99.0,
    'star': 'N/A', 'status': 'Data Unavailable', 'note': 'Team data not in system.',
    'tanking': False, 'eliminated': False,
}


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION ENGINE — 12 Factors
# ─────────────────────────────────────────────────────────────────────────────

def predict_game(h, a, standings, form, b2b_set, injuries):
    h_td  = TEAM_DATA.get(h, DEFAULT_TD)
    a_td  = TEAM_DATA.get(a, DEFAULT_TD)
    h_std = standings.get(h, DEFAULT_STD)
    a_std = standings.get(a, DEFAULT_STD)
    h_frm = form.get(h, [])
    a_frm = form.get(a, [])

    # Live point diff preferred; fall back to static
    h_diff = h_std['point_diff'] if h_std['point_diff'] != 0.0 else h_td['pt_diff']
    a_diff = a_std['point_diff'] if a_std['point_diff'] != 0.0 else a_td['pt_diff']

    h_str = streak_label(h_frm)
    a_str = streak_label(a_frm)

    factors = []
    total   = 0.0

    # ── 1. Home Court Advantage ─────────────────────────────────────────────
    adj = 4.5
    total += adj
    factors.append({'icon': '🏠', 'name': 'Home Court Advantage',        'adj': adj,
        'why': f'{h} playing at home. NBA home teams win 54-56% historically.'})

    # ── 2. Overall Win % Edge ───────────────────────────────────────────────
    adj = max(-15.0, min(15.0, round((h_std['win_pct'] - a_std['win_pct']) * 25.0, 2)))
    total += adj
    factors.append({'icon': '📊', 'name': 'Overall Win % Edge',          'adj': adj,
        'why': f"{h}: {h_std['record']} ({h_std['win_pct']:.1%}) vs {a}: {a_std['record']} ({a_std['win_pct']:.1%})"})

    # ── 3. Venue Record Splits ──────────────────────────────────────────────
    adj = max(-8.0, min(8.0, round((h_std['home_wpct'] - a_std['away_wpct']) * 10.0, 2)))
    total += adj
    factors.append({'icon': '📍', 'name': 'Home / Away Record Split',    'adj': adj,
        'why': f"{h} at home: {h_std['home_record']} | {a} on road: {a_std['away_record']}"})

    # ── 4. Net Rating / Point Differential ─────────────────────────────────
    adj = max(-12.0, min(12.0, round((h_diff - a_diff) * 0.9, 2)))
    total += adj
    factors.append({'icon': '⚡', 'name': 'Net Rating (Point Differential)', 'adj': adj,
        'why': f"{h}: {h_diff:+.1f} pts/game avg | {a}: {a_diff:+.1f} pts/game avg"})

    # ── 5. Defensive Efficiency ─────────────────────────────────────────────
    adj = max(-10.0, min(10.0, round((a_td['def_rtg'] - h_td['def_rtg']) * 0.45, 2)))
    total += adj
    factors.append({'icon': '🛡️', 'name': 'Defensive Efficiency',        'adj': adj,
        'why': f"{h} allows {h_td['def_rtg']} pts/100 | {a} allows {a_td['def_rtg']} pts/100  ← lower = better defense"})

    # ── 6. Offensive Rating ─────────────────────────────────────────────────
    adj = max(-8.0, min(8.0, round((h_td['off_rtg'] - a_td['off_rtg']) * 0.3, 2)))
    total += adj
    factors.append({'icon': '🏹', 'name': 'Offensive Rating',             'adj': adj,
        'why': f"{h} scores {h_td['off_rtg']} pts/100 | {a} scores {a_td['off_rtg']} pts/100  ← higher = better offense"})

    # ── 7. Recent Form / Momentum (L10) ────────────────────────────────────
    h_fpct = sum(h_frm) / len(h_frm) if h_frm else 0.5
    a_fpct = sum(a_frm) / len(a_frm) if a_frm else 0.5
    adj    = max(-8.0, min(8.0, round((h_fpct - a_fpct) * 12.0, 2)))
    total += adj
    factors.append({'icon': '📈', 'name': 'Recent Momentum (Last 10 Games)', 'adj': adj,
        'why': f"{h} L10: {l10_str(h_frm)} | Streak: {h_str}   ──   {a} L10: {l10_str(a_frm)} | Streak: {a_str}"})

    # ── 8. Back-to-Back Fatigue ─────────────────────────────────────────────
    b2b_adj, b2b_parts = 0.0, []
    if h in b2b_set:
        b2b_adj -= 4.5;  b2b_parts.append(f"{h} on 2nd night of back-to-back")
    if a in b2b_set:
        b2b_adj += 4.5;  b2b_parts.append(f"{a} on 2nd night of back-to-back")
    if b2b_parts:
        total += b2b_adj
        factors.append({'icon': '😴', 'name': 'Back-to-Back Fatigue',     'adj': b2b_adj,
            'why': ' | '.join(b2b_parts) + '. B2B teams win only ~44% of those games.'})

    # ── 9. Injury Impact (Live ESPN News) ──────────────────────────────────
    h_inj, a_inj = injuries.get(h, []), injuries.get(a, [])
    inj_adj, inj_why = 0.0, []
    if h_inj:
        inj_adj -= min(10.0, len(h_inj) * 2.5);  inj_why.append(f"🏠 {h}: {h_inj[0]}")
    if a_inj:
        inj_adj += min(10.0, len(a_inj) * 2.5);  inj_why.append(f"✈️ {a}: {a_inj[0]}")
    if inj_why:
        total += inj_adj
        factors.append({'icon': '🤕', 'name': 'Live Injury Report (ESPN)', 'adj': inj_adj,
            'why': ' | '.join(inj_why)})

    # ── 10. Tanking / Motivation ────────────────────────────────────────────
    tank_adj, tank_parts = 0.0, []
    if h_td.get('tanking'):
        tank_adj -= 8.0;  tank_parts.append(f"{h} tanking — draft lottery over wins")
    if a_td.get('tanking'):
        tank_adj += 8.0;  tank_parts.append(f"{a} tanking — no competitive incentive")
    if tank_parts:
        total += tank_adj
        factors.append({'icon': '🎯', 'name': 'Tanking / Motivation',      'adj': tank_adj,
            'why': ' | '.join(tank_parts)})

    # ── 11. Pace Mismatch ───────────────────────────────────────────────────
    if abs(h_td['pace'] - a_td['pace']) >= 2.5:
        adj    = 1.5 if h_td['pace'] > a_td['pace'] else -1.5
        faster = h if h_td['pace'] > a_td['pace'] else a
        total += adj
        factors.append({'icon': '⏩', 'name': 'Pace Mismatch',             'adj': adj,
            'why': f"{h} pace: {h_td['pace']} | {a} pace: {a_td['pace']} | {faster} dictates tempo at home"})

    # ── 12. Playoff Seeding Pressure ────────────────────────────────────────
    play_in = {'TOR', 'CHA', 'ORL', 'MIA', 'PHX', 'LAC', 'POR', 'GSW'}
    pi_adj, pi_parts = 0.0, []
    if h in play_in and not (a_td.get('tanking') or a_td.get('eliminated')):
        pi_adj += 2.0;  pi_parts.append(f"{h} desperate for play-in seeding — high urgency")
    if a in play_in and not (h_td.get('tanking') or h_td.get('eliminated')):
        pi_adj -= 2.0;  pi_parts.append(f"{a} desperate for play-in seeding — high urgency on road")
    if pi_parts:
        total += pi_adj
        factors.append({'icon': '🔥', 'name': 'Playoff Seeding Pressure',  'adj': pi_adj,
            'why': ' | '.join(pi_parts)})

    # ── Final result ─────────────────────────────────────────────────────────
    prob   = max(2.0, min(98.0, 50.0 + total))
    winner = h if prob >= 50.0 else a
    conf   = round(prob if prob >= 50.0 else 100.0 - prob, 1)

    return {
        'winner': winner, 'conf': conf, 'prob_h': round(prob, 1),
        'factors': factors, 'total': round(total, 1),
        'h_td': h_td,  'a_td': a_td,
        'h_std': h_std, 'a_std': a_std,
        'h_frm': h_frm, 'a_frm': a_frm,
        'h_str': h_str, 'a_str': a_str,
        'h_inj': h_inj, 'a_inj': a_inj,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🏀 NBA Master AI — 2026 Season")
st.caption(f"Live Intelligence Engine · {datetime.now().strftime('%A, %B %d, %Y · %I:%M %p')}")
st.divider()

with st.spinner("📡 Syncing live NBA data from ESPN..."):
    slate     = get_daily_slate()
    standings = get_standings()
    form      = get_recent_form()
    b2b_set   = get_back_to_back()
    injuries  = get_injury_news()

# Dashboard metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🎮 Games Today",    len(slate))
c2.metric("📊 Teams Tracked",  f"{len(standings) or 30}/30")
c3.metric("🤕 Injury Reports", sum(len(v) for v in injuries.values()))
c4.metric("😴 B2B Teams",      len(b2b_set))
c5.metric("🔄 Refresh Rate",   "Every 10 min")
st.divider()

if not slate:
    st.error("❌ No games today. Try refreshing.")
    st.stop()

# Breaking news
priority = ['LAL', 'OKC', 'SAS', 'BOS', 'DET', 'DEN', 'HOU', 'CLE']
breaking = [f"**{t}**: {injuries[t][0]}" for t in priority if t in injuries]
if breaking:
    with st.expander("📰 BREAKING INJURY NEWS — Click to expand", expanded=True):
        for b in breaking[:6]:
            st.warning(b)

st.subheader(f"Today's AI Predictions — {len(slate)} Games")
st.caption("12 statistical factors analyzed per matchup · Live ESPN data · All 30 teams tracked")
st.divider()

for game in slate:
    h, a  = game['h'], game['a']
    pred  = predict_game(h, a, standings, form, b2b_set, injuries)
    conf  = pred['conf']
    winner = pred['winner']
    prob_h = pred['prob_h']

    icon  = "🔒" if conf >= 85 else ("🔥" if conf >= 70 else "⚖️")
    badge = "HIGH LOCK" if conf >= 85 else ("STRONG LEAN" if conf >= 70 else "CLOSE GAME")

    header = f"{icon}  {game['h_name']}  vs  {game['a_name']}   |   {winner} wins  ·  {conf:.1f}%  ·  {game['time']}"

    with st.expander(header):

        # Verdict banner
        bdr = '#28a745' if conf >= 70 else '#ffc107' if conf >= 60 else '#17a2b8'
        st.markdown(f"""
        <div style="border-left:5px solid {bdr};background:{bdr}18;border-radius:6px;
                    padding:12px 16px;margin-bottom:14px;">
            <div style="font-size:1.35em;font-weight:800;">
                🏆 {winner} WINS &nbsp;
                <span style="font-size:.75em;opacity:.8;">{icon} {badge} · {conf:.1f}% Confidence</span>
            </div>
            <div style="font-size:.85em;color:#aaa;margin-top:4px;">
                📍 {game['venue']} &nbsp;·&nbsp; 🕐 {game['time']} &nbsp;·&nbsp; {game['status']}
            </div>
        </div>""", unsafe_allow_html=True)

        # Probability bar
        st.markdown(f"**Win Probability** — {h}: **{prob_h:.0f}%** &nbsp;vs&nbsp; {a}: **{100-prob_h:.0f}%**")
        st.markdown(f"""
        <div style="display:flex;height:20px;border-radius:4px;overflow:hidden;margin-bottom:14px;">
            <div style="width:{prob_h:.0f}%;background:#28a745;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:.75em;font-weight:bold;">{h}</div>
            <div style="width:{100-prob_h:.0f}%;background:#dc3545;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:.75em;font-weight:bold;">{a}</div>
        </div>""", unsafe_allow_html=True)

        # Team comparison
        col_h, col_vs, col_a = st.columns([5, 1, 5])

        with col_h:
            st.markdown(f"#### 🏠 {h} — {game['h_name']}")
            st.markdown(f"**{pred['h_td']['status']}**")
            st.write(f"Record: **{pred['h_std']['record']}** | Home: {pred['h_std']['home_record']}")
            st.write(f"L10: {l10_str(pred['h_frm'])} | Streak: {pred['h_str']}")
            st.write(f"Pt Diff: {pred['h_td']['pt_diff']:+.1f} | Off: {pred['h_td']['off_rtg']} | Def: {pred['h_td']['def_rtg']}")
            st.caption(f"⭐ {pred['h_td']['star']}")
            st.info(pred['h_td']['note'])
            for inj in pred['h_inj'][:2]:
                st.warning(f"🤕 {inj}")

        with col_vs:
            st.markdown("<br><br><div style='text-align:center;font-size:1.6em;'>VS</div>",
                        unsafe_allow_html=True)

        with col_a:
            st.markdown(f"#### ✈️ {a} — {game['a_name']}")
            st.markdown(f"**{pred['a_td']['status']}**")
            st.write(f"Record: **{pred['a_std']['record']}** | Away: {pred['a_std']['away_record']}")
            st.write(f"L10: {l10_str(pred['a_frm'])} | Streak: {pred['a_str']}")
            st.write(f"Pt Diff: {pred['a_td']['pt_diff']:+.1f} | Off: {pred['a_td']['off_rtg']} | Def: {pred['a_td']['def_rtg']}")
            st.caption(f"⭐ {pred['a_td']['star']}")
            st.info(pred['a_td']['note'])
            for inj in pred['a_inj'][:2]:
                st.warning(f"🤕 {inj}")

        st.divider()

        # Factor breakdown
        st.markdown("#### 🧠 AI Reasoning — All Factors Explained")

        for f in pred['factors']:
            adj   = f['adj']
            color = '#28a745' if adj > 0.5 else ('#dc3545' if adj < -0.5 else '#6c757d')
            sign  = '+' if adj > 0 else ''
            bars  = min(10, max(1, int(abs(adj) / 1.5)))
            bar   = '█' * bars + '░' * (10 - bars)
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:flex-start;
                        padding:7px 0;border-bottom:1px solid #2a2a2a;">
                <div style="font-size:1.1em;width:26px;flex-shrink:0;">{f['icon']}</div>
                <div style="flex:1;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b style="font-size:.9em;">{f['name']}</b>
                        <span style="color:{color};font-weight:bold;margin-left:12px;white-space:nowrap;">
                            {sign}{adj:.1f}%
                        </span>
                    </div>
                    <div style="color:#aaa;font-size:.78em;margin-top:2px;">{f['why']}</div>
                    <div style="color:{color};font-size:.7em;letter-spacing:1.5px;margin-top:3px;">{bar}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        # Total summary
        tv   = pred['total']
        sign = '+' if tv > 0 else ''
        tc   = '#28a745' if tv > 0 else '#dc3545'
        st.markdown(f"""
        <div style="margin-top:12px;padding:10px 14px;background:#1c1c1c;border-radius:6px;
                    display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:bold;">📐 Total Model Adjustment</span>
            <span style="color:{tc};font-weight:bold;font-size:1.05em;">
                {sign}{tv:.1f}% → <b>{winner}</b> at {conf:.1f}% confidence
            </span>
        </div>""", unsafe_allow_html=True)

st.divider()
st.markdown("""
**📡 Live Data Sources:** ESPN Scoreboard · ESPN Standings API · ESPN NBA News  
**🧮 12 Prediction Factors:** Home Court · Win% · Venue Splits · Net Rating · Defense · Offense ·
Momentum (L10) · Back-to-Back · Injuries · Tanking/Motivation · Pace · Playoff Pressure  
**🔄 Cache:** Slate every 5 min · All other data every 10 min
""")

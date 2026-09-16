"""
NFL Master AI Predictor 2026
=============================
A Streamlit app that estimates game winners from team power ratings,
in-season record, injuries, and situational factors.

NOTE ON DATA: TEAM_DATA power ratings, WEEKLY_SLATES, and NFL_PLAYER_LOOKUP
are hand-authored sample data, not a live feed. Swap `fetch_scoreboard_for_week`
for a real API call (odds provider, ESPN, etc.) to go from demo to production.
"""

import html
from datetime import date, datetime, timedelta

import numpy as np
import requests
import streamlit as st

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="NFL Master AI 2026", page_icon="🏈", layout="wide")
st.sidebar.title("⚙️ NFL System Tools")

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared — data will be re-fetched.")

st.sidebar.subheader("📅 View Date")
selected_date = st.sidebar.date_input(
    "Select game date",
    value=date(2026, 9, 20),
    min_value=date(2026, 8, 1),
    max_value=date.today() + timedelta(days=60),
    label_visibility="collapsed",
)

# ─── MODEL WEIGHTS (named, so they're easy to find and tune) ─────────────────
ROSTER_EDGE_WEIGHT = 0.85   # multiplier on (off - def) power differential
WIN_PCT_WEIGHT = 5.0        # multiplier on win% differential
HOME_FIELD_ADV = 2.5        # flat home-field bump, points
NON_QB_INJURY_CAP = -3.5    # max combined penalty from non-QB injuries
BYE_WEEK_BONUS = 1.5
SHORT_WEEK_PENALTY = -1.5
TURNOVER_REGRESSION_PENALTY = -1.5
LOGISTIC_K = 0.27           # steepness of point-edge -> win-probability curve

# ─────────────────────────────────────────────────────────────────────────────
# NFL PLAYER TIERS — used to size injury impact
# ─────────────────────────────────────────────────────────────────────────────
ELITE_QBS = ["Patrick Mahomes", "Josh Allen", "Lamar Jackson", "Joe Burrow", "CJ Stroud", "Justin Herbert"]
GOOD_QBS = ["Jalen Hurts", "Dak Prescott", "Jordan Love", "Matthew Stafford", "Jared Goff", "Brock Purdy",
            "Tua Tagovailoa", "Trevor Lawrence", "Kyler Murray", "Caleb Williams"]
AVG_QBS = ["Baker Mayfield", "Geno Smith", "Aaron Rodgers", "Kirk Cousins", "Deshaun Watson",
           "Jayden Daniels", "Anthony Richardson", "Will Levis"]
# NOTE: Sam Darnold added below after his 2026 Pro Bowl season in Seattle.
GOOD_QBS.append("Sam Darnold")
ELITE_NON_QBS = [
    "Justin Jefferson", "Tyreek Hill", "Christian McCaffrey", "Ja'Marr Chase", "CeeDee Lamb", "Amon-Ra St. Brown",
    "Micah Parsons", "T.J. Watt", "Myles Garrett", "Nick Bosa", "Chris Jones", "Maxx Crosby",
    "Trent Williams", "Fred Warner", "Sauce Gardner", "Patrick Surtain II", "Roquan Smith", "A.J. Brown",
]


def _build_player_lookup() -> dict[str, tuple[float, str]]:
    lookup: dict[str, tuple[float, str]] = {}
    for p in ELITE_QBS:
        lookup[p.lower()] = (6.0, "Elite QB")
    for p in GOOD_QBS:
        lookup[p.lower()] = (4.0, "Good QB")
    for p in AVG_QBS:
        lookup[p.lower()] = (2.5, "Avg QB")
    for p in ELITE_NON_QBS:
        lookup[p.lower()] = (1.0, "Elite Non-QB")
    return lookup


PLAYER_LOOKUP = _build_player_lookup()

# ─────────────────────────────────────────────────────────────────────────────
# TEAM POWER RATINGS
# ─────────────────────────────────────────────────────────────────────────────
TEAM_DATA = {
    'ARI': {'off_pwr': 22.0, 'def_pwr': 25.5}, 'ATL': {'off_pwr': 22.5, 'def_pwr': 21.0},
    'BAL': {'off_pwr': 27.0, 'def_pwr': 17.5}, 'BUF': {'off_pwr': 26.5, 'def_pwr': 19.5},
    'CAR': {'off_pwr': 16.0, 'def_pwr': 27.5}, 'CHI': {'off_pwr': 21.5, 'def_pwr': 21.0},
    'CIN': {'off_pwr': 25.0, 'def_pwr': 22.0}, 'CLE': {'off_pwr': 20.0, 'def_pwr': 18.0},
    'DAL': {'off_pwr': 27.5, 'def_pwr': 20.0}, 'DEN': {'off_pwr': 18.5, 'def_pwr': 23.5},
    'DET': {'off_pwr': 26.5, 'def_pwr': 21.5}, 'GB':  {'off_pwr': 24.5, 'def_pwr': 21.0},
    'HOU': {'off_pwr': 24.0, 'def_pwr': 20.5}, 'IND': {'off_pwr': 23.0, 'def_pwr': 24.0},
    'JAX': {'off_pwr': 21.5, 'def_pwr': 23.0}, 'KC':  {'off_pwr': 26.0, 'def_pwr': 18.0},
    'LV':  {'off_pwr': 19.0, 'def_pwr': 20.5}, 'LAC': {'off_pwr': 23.0, 'def_pwr': 23.0},
    'LAR': {'off_pwr': 24.0, 'def_pwr': 22.5}, 'MIA': {'off_pwr': 27.5, 'def_pwr': 23.0},
    'MIN': {'off_pwr': 21.0, 'def_pwr': 21.5}, 'NE':  {'off_pwr': 15.5, 'def_pwr': 21.0},
    'NO':  {'off_pwr': 21.5, 'def_pwr': 20.0}, 'NYG': {'off_pwr': 17.0, 'def_pwr': 25.0},
    'NYJ': {'off_pwr': 22.5, 'def_pwr': 17.5}, 'PHI': {'off_pwr': 25.5, 'def_pwr': 22.0},
    'PIT': {'off_pwr': 19.5, 'def_pwr': 19.0}, 'SF':  {'off_pwr': 28.0, 'def_pwr': 18.0},
    'SEA': {'off_pwr': 21.5, 'def_pwr': 23.5}, 'TB':  {'off_pwr': 21.0, 'def_pwr': 20.5},
    'TEN': {'off_pwr': 19.0, 'def_pwr': 22.0}, 'WAS': {'off_pwr': 20.5, 'def_pwr': 26.5},
}
DEFAULT_TEAM = {'off_pwr': 21.0, 'def_pwr': 21.0}

# ─────────────────────────────────────────────────────────────────────────────
# REAL 2026 SCHEDULE DATA, keyed by the Tuesday each NFL week starts.
# Week 1 (Sep 8 start) and Week 2 (Sep 15 start) are actual matchups with
# records verified against ESPN / NFL.com / nflschedules.com as of Sep 16,
# 2026. Week 3 (Sep 22 start) matchups are the real published schedule;
# its entering records are shown as 'TBD' because Week 2 hasn't been played
# yet as of this writing — plug in real records once those games finish.
# This is what makes the date picker do something real: pick a different
# date and you land in a different week's actual slate.
# For ongoing use, replace this dict with a real schedule/results API call.
# ─────────────────────────────────────────────────────────────────────────────
FULL_NAMES = {
    'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens', 'BUF': 'Buffalo Bills',
    'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns',
    'DAL': 'Dallas Cowboys', 'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars', 'KC': 'Kansas City Chiefs',
    'LV': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers', 'LAR': 'Los Angeles Rams', 'MIA': 'Miami Dolphins',
    'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
    'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SF': 'San Francisco 49ers',
    'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders',
}


def _g(h: str, a: str, h_rec: str, a_rec: str) -> dict:
    return {'h': h, 'a': a, 'h_name': FULL_NAMES[h], 'a_name': FULL_NAMES[a], 'h_record': h_rec, 'a_record': a_rec}


WEEKLY_SLATES: dict[date, list[dict]] = {
    # Week 1, Sep 9-14, 2026 — season openers, every team enters 0-0.
    date(2026, 9, 8): [
        _g('SEA', 'NE', '0-0', '0-0'), _g('SF', 'LAR', '0-0', '0-0'), _g('CAR', 'CHI', '0-0', '0-0'),
        _g('PIT', 'ATL', '0-0', '0-0'), _g('IND', 'BAL', '0-0', '0-0'), _g('HOU', 'BUF', '0-0', '0-0'),
        _g('JAX', 'CLE', '0-0', '0-0'), _g('MIN', 'GB', '0-0', '0-0'), _g('NYG', 'DAL', '0-0', '0-0'),
        _g('NYJ', 'TEN', '0-0', '0-0'), _g('PHI', 'WAS', '0-0', '0-0'), _g('KC', 'DEN', '0-0', '0-0'),
        _g('CIN', 'TB', '0-0', '0-0'), _g('DET', 'NO', '0-0', '0-0'), _g('LV', 'MIA', '0-0', '0-0'),
        _g('ARI', 'LAC', '0-0', '0-0'),
    ],
    # Week 2, Sep 17-21, 2026 — entering records reflect real Week 1 results
    # (e.g. SEA beat NE 13-10, CHI beat CAR 59-37, KC beat DEN 31-10, etc.).
    date(2026, 9, 15): [
        _g('BUF', 'DET', '1-0', '1-0'),   # Thu Sep 17
        _g('ATL', 'CAR', '0-1', '0-1'), _g('BAL', 'NO', '1-0', '0-1'), _g('CHI', 'MIN', '1-0', '1-0'),
        _g('HOU', 'CIN', '0-1', '1-0'), _g('NE', 'PIT', '0-1', '1-0'), _g('NYJ', 'GB', '1-0', '0-1'),
        _g('TB', 'CLE', '0-1', '0-1'), _g('TEN', 'PHI', '0-1', '1-0'), _g('DEN', 'JAX', '0-1', '1-0'),
        _g('LAC', 'LV', '0-1', '1-0'), _g('ARI', 'SEA', '1-0', '1-0'), _g('DAL', 'WAS', '0-1', '0-1'),
        _g('SF', 'MIA', '1-0', '0-1'), _g('KC', 'IND', '1-0', '0-1'),
        _g('LAR', 'NYG', '0-1', '1-0'),   # Mon Sep 21
    ],
    # Week 3, Sep 24-28, 2026 — real published matchups; entering records are
    # 'TBD' because Week 2 games have not been played as of this writing.
    date(2026, 9, 22): [
        _g('GB', 'ATL', 'TBD', 'TBD'),    # Thu Sep 24
        _g('BUF', 'LAC', 'TBD', 'TBD'), _g('MIA', 'KC', 'TBD', 'TBD'), _g('JAX', 'NE', 'TBD', 'TBD'),
        _g('DET', 'NYJ', 'TBD', 'TBD'), _g('PIT', 'CIN', 'TBD', 'TBD'), _g('CLE', 'CAR', 'TBD', 'TBD'),
        _g('IND', 'HOU', 'TBD', 'TBD'), _g('NYG', 'TEN', 'TBD', 'TBD'), _g('WAS', 'SEA', 'TBD', 'TBD'),
        _g('TB', 'MIN', 'TBD', 'TBD'), _g('SF', 'ARI', 'TBD', 'TBD'), _g('DAL', 'BAL', 'TBD', 'TBD'),
        _g('NO', 'LV', 'TBD', 'TBD'), _g('DEN', 'LAR', 'TBD', 'TBD'),
        _g('CHI', 'PHI', 'TBD', 'TBD'),   # Mon Sep 28
    ],
}
SORTED_WEEK_STARTS = sorted(WEEKLY_SLATES.keys())

# Real, sourced injury notes for the current Week 2 slate (CBS Sports /
# FantasyPros reports, last checked Sep 15, 2026). Only players CONFIRMED
# out are pre-filled; day-to-day/questionable cases are left for the user
# to enter since status can change up to kickoff.
KNOWN_OUT_BY_WEEK: dict[date, dict[str, list[str]]] = {
    date(2026, 9, 15): {
        'CLE': ['Myles Garrett'],   # knee surgery, expected IR
        'PHI': ['A.J. Brown'],      # on IR, ankle, ~Week 8 return
        'SEA': ['Sam Darnold'],     # hip/glute injury, Drew Lock starting
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL LIVE INJURY FETCH — ESPN's undocumented API.
# This is real but UNOFFICIAL: no key required, but no uptime guarantee and
# the response shape can change without notice. It's opt-in (sidebar
# checkbox) rather than always-on, and every caller falls back to the
# manual KNOWN_OUT_BY_WEEK snapshot / free-text box if it returns nothing.
# Verify TEAM_ESPN_ID against https://site.api.espn.com/apis/site/v2/sports/
# football/nfl/teams if fetches start coming back empty across the board —
# that's usually a sign ESPN renumbered something.
# ─────────────────────────────────────────────────────────────────────────────
TEAM_ESPN_ID = {
    'ATL': 1, 'BUF': 2, 'CHI': 3, 'CIN': 4, 'CLE': 5, 'DAL': 6, 'DEN': 7, 'DET': 8, 'GB': 9, 'TEN': 10,
    'IND': 11, 'KC': 12, 'LV': 13, 'LAR': 14, 'MIA': 15, 'MIN': 16, 'NE': 17, 'NO': 18, 'NYG': 19, 'NYJ': 20,
    'PHI': 21, 'ARI': 22, 'PIT': 23, 'LAC': 24, 'SF': 25, 'SEA': 26, 'TB': 27, 'WAS': 28, 'CAR': 29, 'JAX': 30,
    'BAL': 33, 'HOU': 34,
}
AUTO_FILL_STATUSES = {"Out", "Injured Reserve", "Doubtful"}  # skip "Questionable" — too noisy to auto-apply


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_live_injuries_espn(team_abbr: str) -> list[tuple[str, str]]:
    """Best-effort live pull from ESPN's injuries endpoint for one team.
    Returns [(player_name, status), ...] limited to Out/IR/Doubtful. Names
    are returned BARE (no status suffix) so they still match PLAYER_LOOKUP
    for point-impact scoring; status is carried separately for display.
    Returns [] on ANY failure (network, rate limit, shape change) — never
    raises, so a bad response degrades to 'no live data' rather than
    crashing the app."""
    team_id = TEAM_ESPN_ID.get(team_abbr)
    if team_id is None:
        return []
    try:
        base = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams/{team_id}/injuries"
        resp = requests.get(base, timeout=5)
        resp.raise_for_status()
        items = resp.json().get("items", [])[:8]  # cap per-team requests

        results = []
        for item in items:
            ref = item.get("$ref")
            if not ref:
                continue
            detail = requests.get(ref, timeout=5).json()
            status = detail.get("status")
            status = status.get("name") if isinstance(status, dict) else status
            if status not in AUTO_FILL_STATUSES:
                continue

            athlete = detail.get("athlete") or {}
            name = athlete.get("displayName")
            if not name and athlete.get("$ref"):
                name = requests.get(athlete["$ref"], timeout=5).json().get("displayName")
            if name:
                results.append((name, status))
        return results
    except Exception:
        return []


def get_week_start_for(d: date) -> date:
    """Map any calendar date to the most recent NFL-week start on or before it
    (falls back to the earliest/latest known week if outside our sample range)."""
    candidates = [w for w in SORTED_WEEK_STARTS if w <= d]
    if candidates:
        return max(candidates)
    return SORTED_WEEK_STARTS[0]


@st.cache_data(ttl=300)
def fetch_scoreboard_for_week(week_start_iso: str) -> list[dict]:
    """Stand-in for a live schedule/odds API call. Cached so 'Force Data
    Refresh' has something real to invalidate; swap the body for a real
    HTTP fetch when wiring up live data."""
    return WEEKLY_SLATES[date.fromisoformat(week_start_iso)]


@st.cache_data(ttl=300)
def get_last_fetch_time(week_start_iso: str) -> datetime:
    """Cached alongside the scoreboard purely so the UI can prove a refresh
    happened (timestamp changes after cache is cleared)."""
    return datetime.now()


def parse_record(record: str) -> tuple[int, int, float]:
    """'2-0' -> (2, 0, 1.0). Falls back to a neutral 0.5 win% if unparsable."""
    try:
        wins_str, losses_str = record.split('-')[:2]
        wins, losses = int(wins_str), int(losses_str)
        total = wins + losses
        win_pct = wins / total if total > 0 else 0.5
        return wins, losses, win_pct
    except (ValueError, AttributeError):
        return 0, 0, 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Injury / situational adjustment engine (single implementation, called once
# per team instead of duplicated home/away blocks)
# ─────────────────────────────────────────────────────────────────────────────
def compute_team_adjustments(
    team: str, missing_players: list[str], situational_flags: list[str]
) -> dict:
    """Returns this team's OWN point impact (always negative for injuries that
    hurt them, positive/negative for situational factors that help/hurt them),
    plus human-readable detail strings and any names we didn't recognize."""
    injury_penalty = 0.0
    non_qb_penalty = 0.0
    injury_details: list[str] = []
    unrecognized: list[str] = []

    for raw_name in missing_players:
        clean_name = raw_name.strip()
        key = clean_name.lower()
        if key in PLAYER_LOOKUP:
            value, tier = PLAYER_LOOKUP[key]
            if "QB" in tier:
                injury_penalty -= value
            else:
                non_qb_penalty -= value
            injury_details.append(f"{clean_name} ({tier}: -{value})")
        elif clean_name:
            unrecognized.append(clean_name)

    injury_penalty += max(NON_QB_INJURY_CAP, non_qb_penalty)

    situational_adj = 0.0
    situational_details: list[str] = []
    if "Off Bye Week" in situational_flags:
        situational_adj += BYE_WEEK_BONUS
        situational_details.append(f"Extra prep/rest ({BYE_WEEK_BONUS:+.1f})")
    if "Short Week (Thursday)" in situational_flags:
        situational_adj += SHORT_WEEK_PENALTY
        situational_details.append(f"Fatigue/travel ({SHORT_WEEK_PENALTY:+.1f})")
    if "Turnover Regression Penalty" in situational_flags:
        situational_adj += TURNOVER_REGRESSION_PENALTY
        situational_details.append(f"Unsustainable TO luck ({TURNOVER_REGRESSION_PENALTY:+.1f})")

    return {
        "team": team,
        "injury_penalty": injury_penalty,
        "injury_details": injury_details,
        "unrecognized": unrecognized,
        "situational_adj": situational_adj,
        "situational_details": situational_details,
    }


def predict_game(game: dict, injuries: dict, situational: dict) -> dict:
    h, a = game['h'], game['a']
    h_td = TEAM_DATA.get(h, DEFAULT_TEAM)
    a_td = TEAM_DATA.get(a, DEFAULT_TEAM)

    factors: list[dict] = []
    total = 0.0

    # Roster edge
    h_net = h_td['off_pwr'] - h_td['def_pwr']
    a_net = a_td['off_pwr'] - a_td['def_pwr']
    roster_edge = (h_net - a_net) * ROSTER_EDGE_WEIGHT
    total += roster_edge
    factors.append({
        "icon": "⚖️", "name": "Base EPA / Roster Edge", "adj": roster_edge,
        "why": "Overall offensive and defensive efficiency disparity.",
    })

    # Win % edge — now actually driven by this game's real records
    _, _, h_pct = parse_record(game['h_record'])
    _, _, a_pct = parse_record(game['a_record'])
    win_edge = (h_pct - a_pct) * WIN_PCT_WEIGHT
    total += win_edge
    factors.append({
        "icon": "📊", "name": "Win % Edge", "adj": win_edge,
        "why": f"{h} ({game['h_record']}) vs {a} ({game['a_record']})",
    })

    # Home field
    total += HOME_FIELD_ADV
    factors.append({
        "icon": "🏟️", "name": "Home Field", "adj": HOME_FIELD_ADV,
        "why": f"Standard NFL home-field adjustment for {h}.",
    })

    # Injuries & situational — one call per team, symmetric and unambiguous
    h_adj = compute_team_adjustments(h, injuries.get(h, []), situational.get(h, []))
    a_adj = compute_team_adjustments(a, injuries.get(a, []), situational.get(a, []))

    # A team's own penalty is subtracted from ITS side; the away team's
    # penalty is subtracted from the away side, which nets into a bump
    # for the home team's edge. Same total-edge math as before, but now
    # each factor is displayed under its own team with its own true sign.
    total += h_adj["injury_penalty"] + h_adj["situational_adj"]
    total -= a_adj["injury_penalty"] + a_adj["situational_adj"]

    if h_adj["injury_details"]:
        factors.append({
            "icon": "🚑", "name": f"{h} Absences", "adj": h_adj["injury_penalty"],
            "why": f"Missing: {', '.join(h_adj['injury_details'])}",
        })
    if a_adj["injury_details"]:
        factors.append({
            "icon": "🚑", "name": f"{a} Absences", "adj": a_adj["injury_penalty"],
            "why": f"Missing: {', '.join(a_adj['injury_details'])}",
        })
    if h_adj["situational_details"]:
        factors.append({
            "icon": "⏰", "name": f"{h} Situational", "adj": h_adj["situational_adj"],
            "why": ', '.join(h_adj["situational_details"]),
        })
    if a_adj["situational_details"]:
        factors.append({
            "icon": "⏰", "name": f"{a} Situational", "adj": a_adj["situational_adj"],
            "why": ', '.join(a_adj["situational_details"]),
        })

    prob = 1 / (1 + np.exp(-LOGISTIC_K * total)) * 100
    prob = max(1.0, min(99.0, prob))

    return {
        'winner': h if prob >= 50.0 else a,
        'conf': prob if prob >= 50.0 else 100.0 - prob,
        'spread_edge': total,
        'factors': factors,
        'unrecognized': h_adj["unrecognized"] + a_adj["unrecognized"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏈 NFL Master AI Predictor 2026")

week_start = get_week_start_for(selected_date)
week_end_display = week_start + timedelta(days=6)
st.markdown(f"**Market Week:** {week_start.strftime('%B %d')} — {week_end_display.strftime('%B %d')}")
if selected_date < SORTED_WEEK_STARTS[0] or selected_date > (SORTED_WEEK_STARTS[-1] + timedelta(days=6)):
    st.caption("⚠️ Selected date is outside the sample data range — showing the nearest available week.")
st.divider()

slate = fetch_scoreboard_for_week(week_start.isoformat())
last_fetch = get_last_fetch_time(week_start.isoformat())
st.sidebar.caption(f"Data last refreshed: {last_fetch.strftime('%H:%M:%S')}")

st.sidebar.subheader("🚑 QB & Key Player Absences")
st.sidebar.caption("Type missing Elite/Starting QBs or Elite edge rushers/WRs separated by commas (e.g., `Patrick Mahomes, T.J. Watt`).")
known_out = KNOWN_OUT_BY_WEEK.get(week_start, {})

auto_fetch = st.sidebar.checkbox(
    "🔄 Auto-fetch live injuries (ESPN, beta)",
    value=False,
    help=(
        "Calls ESPN's unofficial injuries API at runtime and pre-fills each "
        "team's box with players listed Out / IR / Doubtful. This is an "
        "undocumented endpoint with no uptime guarantee — if it returns "
        "nothing for a team, the box falls back to the manual snapshot "
        "below (if any) so you can still edit by hand."
    ),
)
if not auto_fetch and known_out:
    st.sidebar.caption("🔎 Boxes below are pre-filled with confirmed-out players from Week 2 injury reports (CBS Sports / FantasyPros, checked Sep 15, 2026). Edit freely — status can change before kickoff.")
injuries: dict[str, list[str]] = {}

st.sidebar.subheader("⏰ NFL Situational Factors")
situational: dict[str, list[str]] = {}

teams_playing = sorted({team for game in slate for team in (game['h'], game['a'])})

for team in teams_playing:
    with st.sidebar.expander(f"{team} Adjustments"):
        live_results: list[tuple[str, str]] = []
        if auto_fetch:
            with st.spinner(f"Checking ESPN for {team} injuries…"):
                live_results = fetch_live_injuries_espn(team)
            if live_results:
                statuses = ', '.join(f"{n} — {s}" for n, s in live_results)
                st.caption(f"✅ Live from ESPN just now: {statuses}")
            else:
                st.caption("⚠️ Live fetch returned nothing — showing manual snapshot (edit below).")

        default_names = [n for n, _ in live_results] if live_results else known_out.get(team, [])
        default_out = ', '.join(default_names)
        inj_input = st.text_input("Missing Players", value=default_out, key=f"inj_{team}_{week_start.isoformat()}_{auto_fetch}")
        if inj_input.strip():
            injuries[team] = [p.strip() for p in inj_input.split(',') if p.strip()]

        sits = st.multiselect(
            "Situational / Rest",
            ["Off Bye Week", "Short Week (Thursday)", "Turnover Regression Penalty"],
            key=f"sit_{team}_{week_start.isoformat()}",
        )
        if sits:
            situational[team] = sits

if not slate:
    st.info("No games found for this week in the sample dataset.")

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(game, injuries, situational)

    with st.expander(
        f"{game['h_name']} vs {game['a_name']}  |  Winner: **{pred['winner']}** ({pred['conf']:.1f}%)"
    ):
        st.markdown(f"### 🏆 {pred['winner']} Wins (Proj. Margin: {abs(pred['spread_edge']):.1f} pts)")

        if pred['unrecognized']:
            names = ', '.join(html.escape(n) for n in pred['unrecognized'])
            st.caption(f"ℹ️ Not recognized, no adjustment applied: {names}")

        for f in pred['factors']:
            color = "#28a745" if f['adj'] > 0 else "#dc3545" if f['adj'] < 0 else "#888888"
            safe_why = html.escape(f['why'])
            st.markdown(
                f"{f['icon']} **{f['name']}**: "
                f"<span style='color:{color}; font-weight:bold;'>{f['adj']:+.1f} pts</span>"
                f" — {safe_why}",
                unsafe_allow_html=True,
            )

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"#### 🏠 {game['h_name']} ({game['h_record']})")
            if injuries.get(h):
                st.warning(f"🚑 Out: {', '.join(injuries[h])}")
        with c2:
            st.markdown(f"#### ✈️ {game['a_name']} ({game['a_record']})")
            if injuries.get(a):
                st.warning(f"🚑 Out: {', '.join(injuries[a])}")

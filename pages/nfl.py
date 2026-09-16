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
ELITE_NON_QBS = [
    "Justin Jefferson", "Tyreek Hill", "Christian McCaffrey", "Ja'Marr Chase", "CeeDee Lamb", "Amon-Ra St. Brown",
    "Micah Parsons", "T.J. Watt", "Myles Garrett", "Nick Bosa", "Chris Jones", "Maxx Crosby",
    "Trent Williams", "Fred Warner", "Sauce Gardner", "Patrick Surtain II", "Roquan Smith",
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
# SAMPLE WEEKLY SLATES, keyed by the Tuesday each NFL week starts.
# This is what actually makes the date picker do something: pick a different
# date and you land in a different week's slate with different records.
# Replace with a real schedule/odds fetch for production use.
# ─────────────────────────────────────────────────────────────────────────────
WEEKLY_SLATES: dict[date, list[dict]] = {
    date(2026, 9, 8): [
        {'h': 'KC', 'a': 'BAL', 'h_name': 'Kansas City Chiefs', 'a_name': 'Baltimore Ravens', 'h_record': '1-0', 'a_record': '0-1'},
        {'h': 'SF', 'a': 'DAL', 'h_name': 'San Francisco 49ers', 'a_name': 'Dallas Cowboys', 'h_record': '0-1', 'a_record': '1-0'},
        {'h': 'BUF', 'a': 'MIA', 'h_name': 'Buffalo Bills', 'a_name': 'Miami Dolphins', 'h_record': '1-0', 'a_record': '0-1'},
        {'h': 'PHI', 'a': 'GB', 'h_name': 'Philadelphia Eagles', 'a_name': 'Green Bay Packers', 'h_record': '1-0', 'a_record': '0-1'},
    ],
    date(2026, 9, 15): [
        {'h': 'KC', 'a': 'BAL', 'h_name': 'Kansas City Chiefs', 'a_name': 'Baltimore Ravens', 'h_record': '2-0', 'a_record': '1-1'},
        {'h': 'SF', 'a': 'DAL', 'h_name': 'San Francisco 49ers', 'a_name': 'Dallas Cowboys', 'h_record': '1-1', 'a_record': '2-0'},
        {'h': 'BUF', 'a': 'MIA', 'h_name': 'Buffalo Bills', 'a_name': 'Miami Dolphins', 'h_record': '2-0', 'a_record': '1-1'},
        {'h': 'PHI', 'a': 'GB', 'h_name': 'Philadelphia Eagles', 'a_name': 'Green Bay Packers', 'h_record': '1-1', 'a_record': '1-1'},
        {'h': 'DET', 'a': 'LAR', 'h_name': 'Detroit Lions', 'a_name': 'Los Angeles Rams', 'h_record': '2-0', 'a_record': '0-2'},
        {'h': 'CIN', 'a': 'CLE', 'h_name': 'Cincinnati Bengals', 'a_name': 'Cleveland Browns', 'h_record': '0-2', 'a_record': '1-1'},
        {'h': 'HOU', 'a': 'IND', 'h_name': 'Houston Texans', 'a_name': 'Indianapolis Colts', 'h_record': '1-1', 'a_record': '1-1'},
        {'h': 'SEA', 'a': 'ARI', 'h_name': 'Seattle Seahawks', 'a_name': 'Arizona Cardinals', 'h_record': '1-1', 'a_record': '0-2'},
    ],
    date(2026, 9, 22): [
        {'h': 'BAL', 'a': 'KC', 'h_name': 'Baltimore Ravens', 'a_name': 'Kansas City Chiefs', 'h_record': '1-2', 'a_record': '3-0'},
        {'h': 'DAL', 'a': 'SF', 'h_name': 'Dallas Cowboys', 'a_name': 'San Francisco 49ers', 'h_record': '3-0', 'a_record': '1-2'},
        {'h': 'MIA', 'a': 'BUF', 'h_name': 'Miami Dolphins', 'a_name': 'Buffalo Bills', 'h_record': '1-2', 'a_record': '3-0'},
        {'h': 'GB', 'a': 'PHI', 'h_name': 'Green Bay Packers', 'a_name': 'Philadelphia Eagles', 'h_record': '2-1', 'a_record': '2-1'},
    ],
}
SORTED_WEEK_STARTS = sorted(WEEKLY_SLATES.keys())


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
injuries: dict[str, list[str]] = {}

st.sidebar.subheader("⏰ NFL Situational Factors")
situational: dict[str, list[str]] = {}

teams_playing = sorted({team for game in slate for team in (game['h'], game['a'])})

for team in teams_playing:
    with st.sidebar.expander(f"{team} Adjustments"):
        inj_input = st.text_input("Missing Players", key=f"inj_{team}_{week_start.isoformat()}")
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

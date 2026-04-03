import streamlit as st
import pandas as pd

# --- 1. TEAM DATA & CONFIGURATION ---
# This is where we define which teams are currently "tanking" (8pt penalty)
TEAM_DATA = {
    'BKN': {'name': 'Brooklyn Nets', 'status': 'Tanking', 'tanking': True, 'note': 'Prioritizing 2025 Draft positioning.'},
    'WAS': {'name': 'Washington Wizards', 'status': 'Tanking', 'tanking': True, 'note': 'Focusing on youth development.'},
    'UTA': {'name': 'Utah Jazz', 'status': 'Tanking', 'tanking': True, 'note': 'Late season roster experimentation.'},
    'POR': {'name': 'Portland Trail Blazers', 'status': 'Tanking', 'tanking': True, 'note': 'Heavy injury report / Lottery focus.'},
    'DET': {'name': 'Detroit Pistons', 'status': 'Tanking', 'tanking': True, 'note': 'Lottery bound.'},
    'LAL': {'name': 'LA Lakers', 'status': 'Contending', 'tanking': False, 'note': 'Pushing for playoff seeding.'},
    'BOS': {'name': 'Boston Celtics', 'status': 'Contending', 'tanking': False, 'note': 'Title favorites.'},
    # Add other teams as needed...
}

# --- 2. PREDICTION ENGINE ---
def predict_game(h, a, standings, form, b2b_set):
    h_td = TEAM_DATA.get(h, {'name': h, 'status': 'Active', 'tanking': False, 'note': 'N/A'})
    a_td = TEAM_DATA.get(a, {'name': a, 'status': 'Active', 'tanking': False, 'note': 'N/A'})
    
    factors = []
    
    # A. Base Power Rating (Net Rating difference)
    h_net = standings.get(h, {}).get('net_rating', 0.0)
    a_net = standings.get(a, {}).get('net_rating', 0.0)
    total = h_net - a_net
    factors.append({"icon": "📊", "name": "Base Power Rating", "why": f"{h} ({h_net}) vs {a} ({a_net})", "adj": total})

    # B. Home Court Advantage (Static +3.5)
    total += 3.5
    factors.append({"icon": "🏠", "name": "Home Court", "why": f"Standard advantage for {h}", "adj": 3.5})

    # C. Recent Form (Last 10 Games weight)
    h_f = form.get(h, 5) # Default 5 wins if no data
    a_f = form.get(a, 5)
    form_adj = (h_f - a_f) * 0.8
    total += form_adj
    factors.append({"icon": "📈", "name": "Recent Form", "why": f"{h} L10: {h_f}W | {a} L10: {a_f}W", "adj": form_adj})

    # D. Back-to-Back (Fatigue Penalty -4.5)
    if h in b2b_set:
        total -= 4.5
        factors.append({"icon": "😴", "name": "B2B Fatigue (Home)", "why": f"{h} played yesterday", "adj": -4.5})
    if a in b2b_set:
        total += 4.5
        factors.append({"icon": "😴", "name": "B2B Fatigue (Away)", "why": f"{a} played yesterday", "adj": 4.5})

    # E. Tanking / Motivation (Massive 8pt swing)
    if h_td.get('tanking'):
        total -= 8.0
        factors.append({"icon": "🎯", "name": "Tanking Penalty", "why": f"{h} is prioritizing lottery odds", "adj": -8.0})
    if a_td.get('tanking'):
        total += 8.0
        factors.append({"icon": "🎯", "name": "Tanking Boost", "why": f"{a} is prioritizing lottery odds", "adj": 8.0})

    # F. Probability Calculation (Elo-style Sigmoid)
    prob_h = 1 / (1 + 10**(-total/15)) * 100
    winner = h if prob_h > 50 else a
    conf = prob_h if prob_h > 50 else (100 - prob_h)

    return {
        "winner": winner,
        "conf": conf,
        "prob_h": prob_h,
        "factors": factors,
        "h_td": h_td, "a_td": a_td,
        "h_frm": h_f, "a_frm": a_f
    }

# --- 3. MOCK DATA (In a real app, this comes from an API) ---
# Simulating the daily slate and stats
slate = [
    {'h': 'LAL', 'h_name': 'LA Lakers', 'a': 'BKN', 'a_name': 'Brooklyn Nets', 'venue': 'Crypto.com Arena', 'time': '10:00 PM'},
    {'h': 'UTA', 'h_name': 'Utah Jazz', 'a': 'WAS', 'a_name': 'Washington Wizards', 'venue': 'Delta Center', 'time': '9:00 PM'}
]
standings = {'LAL': {'net_rating': 1.5}, 'BKN': {'net_rating': -4.2}, 'UTA': {'net_rating': -3.0}, 'WAS': {'net_rating': -8.5}}
form = {'LAL': 7, 'BKN': 3, 'UTA': 2, 'WAS': 1}
b2b_set = {'LAL'} # Let's say Lakers played last night

# --- 4. STREAMLIT UI ---
st.set_page_config(page_title="NBA AI Predictor", layout="wide")
st.title("🏀 NBA AI Game Predictor")
st.subheader("Data-driven projections considering Fatigue, Motivation, and Net Ratings")

for game in slate:
    h, a = game['h'], game['a']
    pred = predict_game(h, a, standings, form, b2b_set)
    
    # Header Styling
    icon = "🔒" if pred['conf'] >= 85 else ("🔥" if pred['conf'] >= 75 else "⚖️")
    badge = "HIGH LOCK" if pred['conf'] >= 85 else ("STRONG LEAN" if pred['conf'] >= 75 else "CLOSE CALL")
    header = f"{icon} {game['h_name']} vs {game['a_name']} | AI Pick: {pred['winner']} ({pred['conf']:.1f}%)"

    with st.expander(header):
        # 1. Verdict Banner
        banner_color = '#28a745' if pred['conf'] >= 75 else '#ffc107'
        st.markdown(f"""
        <div style="border-left:5px solid {banner_color};background:{banner_color}18;padding:15px;border-radius:8px;">
            <h2 style="margin:0;">🏆 {pred['winner']} wins</h2>
            <p style="margin:0;opacity:0.8;">{badge} | {game['time']} @ {game['venue']}</p>
        </div>""", unsafe_allow_html=True)

        # 2. THE REASONING LOG (The part you requested)
        st.markdown("### 🧠 AI Reasoning Log")
        for f in pred['factors']:
            c1, c2, c3 = st.columns([0.5, 5, 1])
            c1.markdown(f"<div style='font-size:20px;'>{f['icon']}</div>", unsafe_allow_html=True)
            c2.markdown(f"**{f['name']}**\n\n<span style='font-size:12px;color:gray;'>{f['why']}</span>", unsafe_allow_html=True)
            
            # Color code based on if it helps the Home team (positive) or Away team (negative)
            pt_color = "#28a745" if f['adj'] > 0 else "#dc3545"
            c3.markdown(f"<h4 style='color:{pt_color};'>{f['adj']:+.1f}</h4>", unsafe_allow_html=True)
        
        st.divider()

        # 3. Probability Visualization
        st.write(f"**Win Probability:** {h}: {pred['prob_h']:.1f}% | {a}: {100-pred['prob_h']:.1f}%")
        st.progress(pred['prob_h'] / 100)

        # 4. Contextual Team Notes
        col_left, col_right = st.columns(2)
        with col_left:
            st.info(f"**{h} Info:** {pred['h_td']['note']}")
        with col_right:
            st.info(f"**{a} Info:** {pred['a_td']['note']}")

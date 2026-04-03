import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="NBA AI 2026", page_icon="🏀")

# --- 1. BASE POWER RATINGS (L10 Momentum) ---
RATINGS = {
    'BOS': 10.5, 'MIL': -4.2, 'HOU': 12.0, 'UTA': -12.5, 
    'ATL': 8.8, 'BKN': -6.1, 'MEM': 5.5, 'TOR': -5.8,
    'PHI': 4.2, 'MIN': 1.5, 'CHA': 6.2, 'IND': -3.1,
    'NYK': 7.5, 'CHI': -4.8, 'ORL': 3.9, 'DAL': -8.2,
    'SAC': 4.1, 'NOP': -5.5, 'WAS': -7.0, 'OKC': 15.7
}

# --- 2. THE "INTELLIGENCE" LAYER (Injuries & Context) ---
# This is where we tell the code WHY a team might lose despite a good rating
IMPACT_MODIFIERS = {
    'MIL': {'penalty': -15.0, 'reason': 'Giannis Antetokounmpo (OUT)'},
    'MIN': {'penalty': -5.0, 'reason': 'Anthony Edwards (Minutes Restriction)'},
    'UTA': {'penalty': -10.0, 'reason': 'Official Tanking / Resting Starters'},
    'DAL': {'penalty': -10.0, 'reason': 'Lottery Mode / 13-game home slide'},
    'ATL': {'bonus': 5.0, 'reason': 'Post-Trae Trade Defensive Surge'},
    'WAS': {'bonus': 8.0, 'reason': 'Trae Young / AD Trade Era Debut'}
}

def fetch_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        res = requests.get(url).json()
        return [{'h': e['competitions'][0]['competitors'][0]['team']['abbreviation'],
                 'a': e['competitions'][0]['competitors'][1]['team']['abbreviation']} 
                for e in res.get('events', [])]
    except: return []

# --- APP UI ---
st.title("🏀 NBA Smart AI")
st.write(f"**Scouting Report:** {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

live_games = fetch_games()

if live_games:
    for game in live_games:
        h, a = game['h'], game['a']
        
        # MATH ENGINE
        # Start with Home Edge (54.5%) + Rating Diff
        prob = 54.5 + ((RATINGS.get(h, 0) - RATINGS.get(a, 0)) * 2)
        
        # Apply Logic Penalties/Bonuses
        reasons = []
        for team in [h, a]:
            if team in IMPACT_MODIFIERS:
                mod = IMPACT_MODIFIERS[team]
                effect = mod.get('penalty', mod.get('bonus', 0))
                # If it's a penalty for the Home team, prob goes down. 
                # If it's a penalty for Away, prob goes up for Home.
                prob += effect if team == h else -effect
                reasons.append(mod['reason'])

        # Final Verdict Logic
        final_prob = max(1, min(99, prob))
        winner = h if final_prob > 50 else a
        confidence = final_prob if final_prob > 50 else (100 - final_prob)
        
        # UI
        with st.expander(f"{'🔒' if confidence > 85 else '🏀'} {h} vs {a}"):
            st.subheader(f"🏆 VERDICT: {winner} WINS")
            st.metric("Model Confidence", f"{confidence:.1f}%")
            
            if reasons:
                st.write("**Adjustments Applied:**")
                for r in reasons:
                    st.info(f"📍 {r}")
            else:
                st.write("📊 *Based on pure statistical momentum.*")

else:
    st.warning("No games found for today.")

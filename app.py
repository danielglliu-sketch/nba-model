import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- APP CONFIGURATION ---
st.set_page_config(page_title="NBA AI 2026 - Master", page_icon="🏀", layout="wide")

# --- 2026 LIVE RATINGS DATABASE ---
# OFF = Offensive Rating, DEF = Defensive Rating (Lower is better for DEF)
TEAM_STATS = {
    'BOS': {'off': 118.5, 'def': 107.5, 'seed': 2, 'status': 'Title Contender'},
    'DET': {'off': 112.4, 'def': 109.6, 'seed': 1, 'status': 'Title Contender'},
    'OKC': {'off': 122.1, 'def': 108.2, 'seed': 1, 'status': 'Title Contender'},
    'HOU': {'off': 116.8, 'def': 109.2, 'seed': 3, 'status': 'Climbing'},
    'NYK': {'off': 115.5, 'def': 111.1, 'seed': 4, 'status': 'Seeding Battle'},
    'PHI': {'off': 114.2, 'def': 115.9, 'seed': 6, 'status': 'Injured'},
    'ATL': {'off': 110.1, 'def': 110.0, 'seed': 8, 'status': 'Play-In Fight'},
    'MIN': {'off': 112.5, 'def': 114.7, 'seed': 7, 'status': 'Play-In Fight'},
    'LAL': {'off': 113.1, 'def': 115.6, 'seed': 10, 'status': 'Play-In Fight'},
    'UTA': {'off': 105.2, 'def': 125.7, 'seed': 15, 'status': 'Tanking'},
    'DAL': {'off': 106.1, 'def': 118.0, 'seed': 14, 'status': 'Tanking'},
    'MIL': {'off': 110.2, 'def': 115.6, 'seed': 9, 'status': 'Struggling'}
}

# --- DYNAMIC INJURY REPORT (Auto-applied to logic) ---
INJURIES = {
    'MIL': 'Giannis Antetokounmpo (OUT)',
    'PHI': 'Joel Embiid (Doubtful)',
    'DET': 'Cade Cunningham (OUT)',
    'MIN': 'Anthony Edwards (OUT)',
    'BOS': 'Jayson Tatum (Available - Post-Achilles)'
}

# --- CORE ENGINE FUNCTIONS ---
@st.cache_data(ttl=600)
def fetch_nba_data():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        data = requests.get(url).json()
        return data.get('events', [])
    except:
        return []

def calculate_probability(home_id, away_id):
    h = TEAM_STATS.get(home_id, {'off': 110, 'def': 115, 'seed': 11, 'status': 'Neutral'})
    a = TEAM_STATS.get(away_id, {'off': 110, 'def': 115, 'seed': 11, 'status': 'Neutral'})

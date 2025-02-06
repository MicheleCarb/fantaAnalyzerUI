import streamlit as st
import sqlite3
import os

from modules.findOpportunities import get_players_with_opportunities, find_latest_giornata
from modules.playerStat import fetch_player_stats, create_plot, get_all_players
from modules.config import year

# Set up page title
st.title("📊 FantaAnalyzer")

# Description of the app
st.write("Benvenuto in FantaAnalyzer! Qui puoi analizzare i dati del tuo fantacalcio o trovare opportunità di mercato.")

# Divider
st.markdown("---")

### SECTION: Players Opportunity ###
st.header("💰 Players Opportunity")

# Load the latest giornata dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current directory
DATA_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "../data"))  # Adjust path
giornate_dir = os.path.join(DATA_FOLDER, year, "giornate")
db_path = os.path.join(DATA_FOLDER, year, "fantacalcio.db")

try:
    latest_giornata = find_latest_giornata(giornate_dir)
except ValueError:
    latest_giornata = None

if latest_giornata and latest_giornata > 1:
    st.write(f"Mostra opportunità che si sono create dopo la giornata {latest_giornata}. Le opportunità non sono altro che giocatori che hanno perso valore in questa giornata.")

    # User inputs
    crediti = st.number_input("Inserisci numero massimo di crediti (opzionale):", min_value=0, step=1, value=None)
    ruolo = st.selectbox("Seleziona ruolo (opzionale):", ["All", "P", "D", "C", "A"])

    # Convert "All" to None for the function
    if ruolo == "All":
        ruolo = None

    # Fetch opportunities when button is clicked
    if st.button("🔍 Find Opportunities"):
        players = get_players_with_opportunities(db_path, latest_giornata, crediti, ruolo)

        if players:
            st.success(f"Found {len(players)} opportunities!")
            st.table(
                [{"Player": p[0], "Current Value": p[1], "Value Change": p[2], "Role": p[3]} for p in players]
            )
        else:
            st.warning("No opportunities found for the selected filters.")
else:
    st.error("Not enough giornate available for opportunity analysis.")

### SECTION: Player Statistics ###
st.header("📈 Player Statistics")

# Fetch all player names for autocomplete suggestions
player_names = get_all_players()

# Search bar for player selection
selected_player = st.selectbox("Select a player:", player_names)

# Show player stats when the button is clicked
if st.button("📊 Show Statistics"):
    stats = fetch_player_stats(selected_player)

    if stats:
        st.success(f"Showing stats for {selected_player}")
        fig = create_plot(selected_player, stats)
        st.pyplot(fig)  # Display the figure in Streamlit
    else:
        st.warning(f"No stats found for {selected_player}")

import os
import sqlite3
import matplotlib.pyplot as plt
import streamlit as st
from modules.config import year

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current directory
DATA_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "../../data"))  # Adjust path
#DATA_FOLDER = "../data"
DATA_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "../../data"))  # Adjust path
DB_PATH = os.path.join(DATA_FOLDER, year, "fantacalcio.db")

def fetch_player_stats(player_name):
    """Fetch stats for a given player from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT nGame, curValue, nFantaTeam
    FROM game_stats
    WHERE playerName = ?
    ORDER BY nGame
    """
    
    cursor.execute(query, (player_name,))
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_all_players():
    """Fetch distinct player names from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT DISTINCT playerName FROM players ORDER BY playerName"
    cursor.execute(query)
    
    players = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return players

def create_plot(player_name, stats):
    """Generate a plot dynamically and return the figure instead of saving it."""
    nGames = [row[0] for row in stats]
    curValues = [row[1] for row in stats]
    nFantaTeams = [row[2] for row in stats]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(nGames, curValues, label="Current Value", color="blue", marker="o")
    ax.plot(nGames, nFantaTeams, label="Fantasy Team Ownership", color="green", marker="o")
    
    ax.set_title(f"{player_name} - Performance Over Time")
    ax.set_xlabel("Giornata")
    ax.set_ylabel("Value / Ownership")
    ax.legend()
    
    return fig

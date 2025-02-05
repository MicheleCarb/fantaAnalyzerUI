import os
import pandas as pd
import sqlite3
import json
import re
import sys
import glob

# Funzione per trovare il file delle quotazioni
def trova_file_quotazioni(cartella_giornata):
    # Cerca tutti i file che iniziano con "Quotazioni_Fantacalcio_Stagione_" e terminano con ".xlsx"
    files = glob.glob(os.path.join(cartella_giornata, "Quotazioni_Fantacalcio_Stagione_*.xlsx"))
    if files:
        return files[0]  # Restituisci il primo file trovato
    return None

# Function to create SQLite database tables
def create_tables(conn):
    cursor = conn.cursor()

    # Create players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            playerName TEXT PRIMARY KEY,
            initvalue INTEGER,
            role TEXT
        )
    ''')

    # Create game_stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            nGame INTEGER,
            playerName TEXT,
            curValue INTEGER,
            team TEXT,
            nFantaTeam INTEGER,
            PRIMARY KEY (nGame, playerName),
            FOREIGN KEY (playerName) REFERENCES players (playerName)
        )
    ''')

    # Create matches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            gameweek INTEGER PRIMARY KEY,
            matches_data TEXT
        )
    ''')

    conn.commit()

# Function to insert data into players table
def insert_players_data(conn, df, dfGame, nGame, missing_game_stats_flag):
    total_rows = len(df) - 2
    n = 1

    cursor = conn.cursor()

    for index, row in df.iterrows():
        player_name = row['Nome']

        # Check if the player already exists
        cursor.execute('SELECT COUNT(*) FROM players WHERE playerName = ?', (player_name,))
        count = cursor.fetchone()[0]

        if count == 0:
            print(f"New player found: {player_name}")
            try:
                cursor.execute('''
                    INSERT INTO players (playerName, initvalue, role)
                    VALUES (?, ?, ?)
                ''', (row['Nome'], row['Qt.I'], row['R']))
            except sqlite3.IntegrityError as e:
                print(f"Error inserting record for player {player_name}: {e}")
        
        # A prescindere aggiorna la tabella game_stats
        percentage = round(n / total_rows * 100, 2)
        n = n + 1
        insert_game_stats_data(cursor, dfGame, nGame, player_name, row['Squadra'], row['Qt.A'], percentage, missing_game_stats_flag)

    conn.commit()

# Function to insert data into game_stats table
def insert_game_stats_data(cursor, df, nGame, playerName, team, curValue, percentage, missing_game_stats_flag):
    print(f"[{percentage}%] GameStats for {playerName}")

    # Use the flag to set nFantaTeam to 0 if game_stats file is missing
    if missing_game_stats_flag:
        nFantaTeam = 0
    else:
        nFantaTeam = sum(df.apply(lambda row: row.astype(str).eq(playerName).sum(), axis=1))
        nFantaTeam = int(nFantaTeam)

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO game_stats (nGame, playerName, curValue, team, nFantaTeam)
            VALUES (?, ?, ?, ?, ?)
        ''', (nGame, playerName, curValue, team, nFantaTeam))
    except sqlite3.IntegrityError:
        print(f"Error inserting or replacing record for nGame={nGame}, playerName={playerName}")

def populate_matches_table(conn, json_file):
    cursor = conn.cursor()

    with open(json_file, 'r') as file:
        data = json.load(file)

    for matches_info in data["Match"]:
        gameweek = matches_info[0]
        matches_list = matches_info[1:]
        try:
            cursor.execute('''
                INSERT INTO matches (gameweek, matches_data)
                VALUES (?, ?)
            ''', (gameweek.rpartition(' ')[-1], json.dumps(matches_list)))
        except sqlite3.IntegrityError:
            print(f"Error inserting record for gameweek={gameweek}: Duplicate entry.")

    conn.commit()

# Main function
def main(stagione, giornata):
    # Percorsi relativi alla nuova struttura
    DATA_FOLDER = "../data"
    base_folder_path = os.path.join(DATA_FOLDER, stagione, "giornate")

    # Crea la connessione al database
    db_path = os.path.join(DATA_FOLDER, stagione, "fantacalcio.db")
    conn = sqlite3.connect(db_path)

    # Crea le tabelle nel database
    create_tables(conn)

    # Verifica se la tabella 'matches' è vuota e popolala se necessario
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM matches;')
    row_count = cursor.fetchone()[0]

    if row_count == 0:
        print("Filling matches table")
        json_file_path = os.path.join(DATA_FOLDER, stagione, "matches", f"match{stagione}.json")
        if os.path.exists(json_file_path):
            populate_matches_table(conn, json_file_path)
        else:
            print(f"File JSON delle partite non trovato: {json_file_path}")

    # Percorso della cartella della giornata
    subfolder_path = os.path.join(base_folder_path, str(giornata))

    if not os.path.isdir(subfolder_path):
        print(f"Cartella della giornata non trovata: {subfolder_path}")
        return

    print(f"Trovata nuova giornata! Processing subfolder '{giornata}'")

    # Trova il file Excel per i giocatori
    excel_file_players_path = trova_file_quotazioni(subfolder_path)
    if excel_file_players_path:
        df_players = pd.read_excel(excel_file_players_path, sheet_name='Tutti', header=1)
    else:
        print(f"Error: File delle quotazioni non trovato nella directory: {subfolder_path}")
        return

    # Trova il file Excel per le statistiche di gioco
    df_game_stats = None
    missing_game_stats_flag = True
    try:
        excel_file_game_stats = next(file for file in os.listdir(subfolder_path) if file.startswith("Formazioni") and file.endswith(".xlsx"))
        excel_file_game_stats_path = os.path.join(subfolder_path, excel_file_game_stats)
        print(f"Path: {excel_file_game_stats_path}")
        df_game_stats = pd.read_excel(excel_file_game_stats_path)
        missing_game_stats_flag = False
    except StopIteration:
        print(f"Game stats file not found in subfolder: {subfolder_path}")
    except FileNotFoundError:
        print(f"Error: File not found in the directory: {subfolder_path}")

    # Inserisci i dati nella tabella dei giocatori
    insert_players_data(conn, df_players, df_game_stats, giornata, missing_game_stats_flag)

    # Chiudi la connessione al database
    conn.close()
    print("All done!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python dbFiller.py <stagione> <giornata>")
        sys.exit(1)

    stagione = sys.argv[1]  # Esempio: "2024-25"
    giornata = int(sys.argv[2])  # Esempio: 12
    main(stagione, giornata)
import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import ast
import base64

from modules.config import year  # Import from correct location

def get_db_path():
    """Get correct database path based on project structure"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(current_dir, f"../../data/{year}/fantacalcio.db"))

def get_upcoming_matches(next_game_n):
    """Retrieve matches for the next 5 game weeks (original logic preserved)"""
    db_path = get_db_path()
    upcoming_matches = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for game_n in range(next_game_n, next_game_n + 5):
            cursor.execute("SELECT matches_data FROM matches WHERE gameweek = ?", (game_n,))
            result = cursor.fetchone()
            if result and result[0]:
                try:
                    matches = ast.literal_eval(result[0])
                    upcoming_matches.extend(matches)
                except (SyntaxError, ValueError):
                    raise ValueError(f"Invalid match format for gameweek {game_n}")
        
    except sqlite3.Error as e:
        raise RuntimeError(f"Database error: {e}")
    finally:
        conn.close()
    return upcoming_matches

def get_next_game_number():
    """Original logic preserved with path adjustment"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(nGame) FROM game_stats")
        last_game_n = cursor.fetchone()[0]
        return last_game_n + 1 if last_game_n else 1
    except sqlite3.OperationalError as e:
        raise RuntimeError(f"Database error: {e}")
    finally:
        conn.close()

def calculate_difficulty_index(team_entry, form_table):
    """Original calculation logic preserved"""
    total = 0.0
    valid_matches = 0
    
    for match in team_entry.get('Next Matches', []):
        if ' (HOME)' in match:
            opponent = match.replace(' (HOME)', '').strip()
            weight = 0.9
        elif ' (AWAY)' in match:
            opponent = match.replace(' (AWAY)', '').strip()
            weight = 1.1
        else:
            continue
        
        opponent_data = next((t for t in form_table if t['Team'] == opponent), None)
        if opponent_data and opponent_data['PPG']:
            try:
                ppg = float(opponent_data['PPG'])
                total += ppg * weight
                valid_matches += 1
            except ValueError:
                continue
    
    return round(total / valid_matches, 2) if valid_matches > 0 else 0.0

def get_hidden_url():
    # I mean hidden.. it's base64
    encoded = "aHR0cHM6Ly9mb290eXN0YXRzLm9yZy9pdC9pdGFseS9zZXJpZS1hL2Zvcm0tdGFibGU="
    return base64.b64decode(encoded).decode()

def scrape_form_table():
    """Original scraping logic preserved without modifications"""

    url = get_hidden_url()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        table = soup.find('table', class_='full-league-table table-sort form-table mobify-table')
        if not table:
            raise ValueError("Form table not found in the page")

        form_table = []
        tbody = table.find('tbody')

        for row in tbody.find_all('tr'):
            try:
                # Original parsing logic preserved
                rank_cell = row.find('td', class_=lambda c: c and 'position' in c and 'bold' in c)
                rank = rank_cell.get_text(strip=True) if rank_cell else None

                team_cell = row.find('td', class_=lambda c: c and 'team' in c and 'bold' in c)
                team_anchor = team_cell.find('a') if team_cell else None
                team_strings = list(team_anchor.stripped_strings) if team_anchor else []
                team_name = team_strings[0] if team_strings else None

                # Original team name standardization
                if team_name == "Atalanta Bergamasca Calcio":
                    team_name = "Atalanta BC"
                elif team_name == "Calcio Como":
                    team_name = "Como 1907"
                elif team_name == "SS Monza 1912":
                    team_name = "AC Monza"

                ppg_cell = row.find('td', class_='ppg')
                ppg_div = ppg_cell.find('div', class_='form-box') if ppg_cell else None
                ppg = ppg_div.get_text(strip=True) if ppg_div else None

                if all([rank, team_name, ppg]):
                    form_table.append({
                        'Rank': rank,
                        'Team': team_name,
                        'PPG': ppg,
                        'Next Matches': [],
                        'Difficulty': 0.0
                    })
                    
            except Exception as e:
                continue

        return form_table

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Connection error: {e}")
    except Exception as e:
        raise RuntimeError(f"Scraping error: {e}")

def get_full_analysis():
    """Main function to get complete analysis"""
    try:
        form_table = scrape_form_table()
        next_game_n = get_next_game_number()
        upcoming_matches = get_upcoming_matches(next_game_n)

        # Original match processing logic
        for team_entry in form_table:
            team_name = team_entry['Team']
            opponents = []
            
            for match in upcoming_matches:
                if ' vs ' in match:
                    home, away = map(str.strip, match.split(' vs '))
                    if team_name == home:
                        opponents.append(f"{away} (HOME)")
                    elif team_name == away:
                        opponents.append(f"{home} (AWAY)")
            
            team_entry['Next Matches'] = opponents[:5]
            team_entry['Difficulty'] = calculate_difficulty_index(team_entry, form_table)

        return form_table

    except Exception as e:
        raise RuntimeError(f"Analysis failed: {e}")
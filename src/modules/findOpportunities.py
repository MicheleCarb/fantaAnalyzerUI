import os
import sqlite3
import sys

def find_latest_giornata(giornate_dir):
    # Find all folders in /giornate and convert folder names to integers
    giornate_folders = [int(folder) for folder in os.listdir(giornate_dir) if folder.isdigit()]
    # Return the highest folder number (latest giornata)
    return max(giornate_folders)

def get_players_with_opportunities(db_path, giornata, cur_value=None, role=None):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Base query for the current giornata (nGame = giornata), including player role
    query_current = """
    SELECT g.playerName, g.curValue, p.role
    FROM game_stats g
    JOIN players p ON g.playerName = p.playerName
    """
    
    # If a role is provided, filter by role
    if role is not None:
        query_current += """
        WHERE g.nGame = ? AND p.role = ?
        """
        params_current = (giornata, role)
    else:
        query_current += "WHERE g.nGame = ?"
        params_current = (giornata,)

    # If cur_value is provided, filter further
    if cur_value is not None:
        query_current += " AND g.curValue = ?"
        params_current += (cur_value,)
    
    # Execute the query for the current giornata
    cursor.execute(query_current, params_current)
    current_players = cursor.fetchall()

    opportunities = []

    # Query for the previous giornata (nGame = giornata - 1)
    query_previous = """
    SELECT playerName, curValue
    FROM game_stats
    WHERE nGame = ? AND playerName = ?
    """

    # Check their value in the previous giornata
    for player, cur_val, role in current_players:
        previous_giornata = giornata - 1
        cursor.execute(query_previous, (previous_giornata, player))
        previous_player = cursor.fetchone()

        if previous_player:
            prev_val = previous_player[1]
            # If the value in the previous giornata was greater than the current value
            if prev_val > cur_val:
                delta = cur_val - prev_val
                opportunities.append((player, cur_val, delta, role))

    conn.close()

    # Sort players by the delta (difference in value), then by current value, both in descending order
    opportunities_sorted = sorted(opportunities, key=lambda x: (x[2], x[1]), reverse=True)

    return opportunities_sorted

if __name__ == "__main__":
    # Check the number of arguments to determine the mode
    if len(sys.argv) > 3:
        print("Usage: /findOpportunities.py [N] [role]")
        sys.exit(1)

    cur_value = None
    role = None

    # Parse command line arguments
    if len(sys.argv) >= 2:
        try:
            cur_value = int(sys.argv[1])
        except ValueError:
            if sys.argv[1] in ["P", "D", "C", "A"]:
                role = sys.argv[1]
            else:
                print("Please provide a valid integer for curValue or a valid role (P, D, C, A).")
                sys.exit(1)

    # Check if the second argument is the role
    if len(sys.argv) == 3:
        if sys.argv[2] in ["P", "D", "C", "A"]:
            role = sys.argv[2]
        else:
            print("Role must be one of the following: P, D, C, A.")
            sys.exit(1)

    # Define paths
    year = "2024-25"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    giornate_dir = os.path.join(base_dir, f"../{year}/giornate")
    db_path = os.path.join(base_dir, f"../{year}/fantacalcio.db")

    # Find the latest giornata
    try:
        latest_giornata = find_latest_giornata(giornate_dir)
    except ValueError:
        print("No valid giornate folders found.")
        sys.exit(1)

    if latest_giornata <= 1:
        print("This algorithm is useful only starting from game week number 2. Exiting.")
        sys.exit(1)

    # Fetch players with opportunities
    players = get_players_with_opportunities(db_path, latest_giornata, cur_value, role)

    # Print the result
    if players:
        if cur_value is not None:
            print(f"Players with curValue = {cur_value} in giornata {latest_giornata} but had a higher value in previous giornata:")
        else:
            print(f"All players who lost value from giornata {latest_giornata - 1} to giornata {latest_giornata}:")
        for player, cur_val, delta, role in players:
            print(f"{player}. Current Value: {cur_val}. Value difference: {delta}. Role: {role}")
    else:
        if cur_value is not None:
            print(f"No players found with curValue = {cur_value} and a higher value in the previous giornata.")
        else:
            print("No players found who lost value between the last two giornate.")

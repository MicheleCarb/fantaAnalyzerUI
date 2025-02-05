import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current directory
DATA_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "../../data"))  # Adjust path

def trova_stagione_piu_recente():
    """Finds the most recent season by scanning available folders."""
    stagioni = [d for d in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, d))]
    return max(stagioni) if stagioni else None

# Compute the season ONCE and store it globally
year = trova_stagione_piu_recente()

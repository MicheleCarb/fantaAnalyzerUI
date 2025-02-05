import streamlit as st
import os
import subprocess
import shutil

from modules.config import year

st.title("📤 Carica File per Aggiornare il Database")

if st.button("🏠 Torna alla Homepage"):
    st.switch_page("fantaAnalyzer.py")  # Torna al file principale

# Configurazione
DATA_FOLDER = "../data"
SCRIPT_PATH = "dbFiller.py"

# Funzione per cancellare la cartella della giornata
def cancella_cartella_giornata(stagione, giornata):
    giornata_folder = os.path.join(DATA_FOLDER, stagione, "giornate", str(giornata))
    if os.path.exists(giornata_folder):
        shutil.rmtree(giornata_folder)
        print(f"Cartella della giornata {giornata} cancellata.")

# Funzione per resettare lo stato della sessione
def resetta_stato():
    st.session_state.files_uploaded = False
    st.rerun()  # Ricarica la pagina

# Funzione per trovare la stagione più recente
def trova_stagione_piu_recente():
    stagioni = [d for d in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, d))]
    return max(stagioni) if stagioni else None

# Funzione per trovare la prossima giornata
def trova_prossima_giornata(stagione):
    giornate_path = os.path.join(DATA_FOLDER, stagione, "giornate")
    if not os.path.exists(giornate_path):
        return 1
    giornate = [int(d) for d in os.listdir(giornate_path) if os.path.isdir(os.path.join(giornate_path, d))]
    return max(giornate) + 1 if giornate else 1

# Funzione per eseguire lo script
def esegui_script(stagione, giornata):
    try:
        result = subprocess.run(
            ["python3", SCRIPT_PATH, stagione, str(giornata)], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            st.success("✅ Script eseguito con successo!")
            st.code(result.stdout, language="bash")
            # Resetta lo stato e ricarica la pagina
            resetta_stato()
        else:
            st.error("❌ Errore durante l'esecuzione dello script:")
            st.code(result.stderr, language="bash")
            # Cancella la cartella della giornata in caso di errore
            cancella_cartella_giornata(stagione, giornata)
            st.warning(f"⚠️ La cartella della giornata {giornata} è stata cancellata a causa dell'errore.")
            
    except Exception as e:
        st.error(f"Errore imprevisto: {str(e)}")
        # Cancella la cartella della giornata in caso di errore
        cancella_cartella_giornata(stagione, giornata)
        st.warning(f"⚠️ La cartella della giornata {giornata} è stata cancellata a causa dell'errore.")


# Selezione Stagione
stagione = year
if not stagione:
    st.error("Nessuna stagione trovata nella cartella 'data'!")
    st.stop()

st.header(f"Stagione: {stagione.replace('_', '-')} ")

# Trova la prossima giornata
prossima_giornata = trova_prossima_giornata(stagione)
st.header(f"📅 Prossima Giornata: {prossima_giornata}")

# Sezione Upload File
st.header("📂 Carica i File")
col1, col2 = st.columns(2)

with col1:
    uploaded_file_quotazioni = st.file_uploader("📈 Quotazioni Fantacalcio", type=["xlsx"], key="file_quotazioni")
with col2:
    uploaded_file_giornata = st.file_uploader("📄 Formazioni della Giornata", type=["xlsx"], key="file_giornata")

if st.button("📥 Salva File ed Esegui Script"):
    if uploaded_file_quotazioni:
        giornata_folder = os.path.join(DATA_FOLDER, stagione, "giornate", str(prossima_giornata))
        os.makedirs(giornata_folder, exist_ok=True)
        
        file_quotazioni_path = os.path.join(giornata_folder, uploaded_file_quotazioni.name)
        with open(file_quotazioni_path, "wb") as f:
            f.write(uploaded_file_quotazioni.getbuffer())
        
        if uploaded_file_giornata:
            file_giornata_path = os.path.join(giornata_folder, uploaded_file_giornata.name)
            with open(file_giornata_path, "wb") as f:
                f.write(uploaded_file_giornata.getbuffer())
        
        st.success("✅ File caricati correttamente!")
        
        with st.spinner("🚀 Esecuzione script in corso..."):
            esegui_script(stagione, prossima_giornata)
    else:
        st.warning("⚠️ Devi caricare almeno il file delle quotazioni per procedere!")
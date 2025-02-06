import streamlit as st
import base64
import os
from pdfReporter import generate_slides, get_existing_reports, REPORT_FOLDER, execute_query, year

def show_pdf(file_path):
    """Carica e mostra un PDF nella UI."""
    try:
        with open(file_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")
        pdf_display = f'''
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="800px" 
                type="application/pdf"
                style="border: none; margin-top: 20px;">
            </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Errore: Il file PDF non è stato trovato.")

st.title("📊 Report Analitico PDF")
col1, col2 = st.columns([1,3])

# Trova i report esistenti
existing_reports = get_existing_reports()
latest_giornata = execute_query("SELECT MAX(nGame) FROM game_stats")[0][0]
latest_report_path = f"{REPORT_FOLDER}/report_players_giornata_{latest_giornata}.pdf"

# Menu a tendina per scegliere un report esistente
selected_report = st.selectbox("📂 Seleziona un report esistente:", existing_reports, index=len(existing_reports)-1 if existing_reports else None)

if selected_report:
    show_pdf(f"{REPORT_FOLDER}/{selected_report}")

with col1:
    if st.button("🏠 Torna alla Homepage", key="pdf_home"):
        st.switch_page("../fantaAnalyzer.py")
    
    # Nascondi il pulsante "Genera Nuovo Report" se il report dell'ultima giornata esiste già
    if not os.path.exists(latest_report_path):
        # Messaggio informativo sulla giornata che verrà generata
        st.info(f"⚠️ Il report per la giornata **{latest_giornata}** non è ancora stato generato.")
        
        if st.button("🔄 Genera Nuovo Report", key="gen_report"):
            try:
                with st.spinner(f"Generazione report per la giornata {latest_giornata} in corso..."):
                    pdf_output = generate_slides()
                    if pdf_output:
                        st.success(f"Report per la giornata {latest_giornata} generato con successo!")
                        show_pdf(pdf_output)  # Mostra subito il nuovo report
            except Exception as e:
                st.error(f"Errore nella generazione: {str(e)}")
    else:
        st.info(f"✅ Il report per la giornata **{latest_giornata}** è già disponibile. Selezionalo dal menu a tendina per visualizzarlo.")
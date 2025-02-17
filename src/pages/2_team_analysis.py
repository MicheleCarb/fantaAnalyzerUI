import streamlit as st
import pandas as pd
from modules.currentShape import get_full_analysis

st.title("⚽ Analisi Squadre Serie A")

if st.button("🏠 Torna alla Homepage"):
    st.switch_page("fantaAnalyzer.py")

try:
    with st.spinner("Analisi in corso..."):
        data = get_full_analysis()
        
        # Converti i dati
        df = pd.DataFrame(data)[['Rank', 'Team', 'PPG', 'Difficulty', 'Next Matches']]
        
        # Mostra i risultati
        st.header("📊 Classifica di Forma")
        st.write("Punti/Partita si basano sugli ultimi 5 scontri.")
        st.write("L'indice di difficolta' si basa sui prossimi 5 scontri.")
        st.dataframe(
            df.sort_values('Difficulty', ascending=True),
            column_config={
                "Rank": st.column_config.NumberColumn(
                    "Posizione",
                    format="%d",  # Formato intero
                    help="Posizione in classifica"
                ),
                "PPG": "Punti/Partita",
                "Difficulty": st.column_config.NumberColumn(
                    "Indice Difficoltà",
                    format="%.2f",
                    help="Valore più alto indica partite più difficili"
                ),
                "Next Matches": "Prossimi 5 avversari"
            },
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"Errore durante l'analisi: {str(e)}")
    st.stop()
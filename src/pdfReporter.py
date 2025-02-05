import os
import sqlite3
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import base64
import streamlit as st

from modules.config import year

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current directory
DATA_FOLDER = os.path.abspath(os.path.join(BASE_DIR, f"../data/{year}/fantacalcio.db"))  # Adjust path
#REPORT_FOLDER = f"../data/{year}/report"
REPORT_FOLDER = os.path.abspath(os.path.join(BASE_DIR, f"../data/{year}/report"))  # Adjust path

def execute_query(query):
    print(f"Connecting to database at: {DATA_FOLDER}")
    connection = sqlite3.connect(DATA_FOLDER)
    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()
    return rows

def get_existing_reports():
    """Trova tutti i report PDF già generati nella cartella report."""
    if not os.path.exists(REPORT_FOLDER):
        return []
    
    reports = [f for f in os.listdir(REPORT_FOLDER) if f.startswith("report_players_giornata_") and f.endswith(".pdf")]
    return sorted(reports, key=lambda x: int(x.split("_")[-1].split(".")[0]))  # Ordina per numero giornata

def generate_slides():
    """Genera il PDF per la giornata più recente solo se non esiste già, e restituisce il percorso del file."""
    global year
    if not year:
        return None

    giornata = execute_query("SELECT MAX(nGame) FROM game_stats")[0][0]
    pdf_path = f"{REPORT_FOLDER}/report_players_giornata_{giornata}.pdf"

    # Se il report esiste già, restituiamo semplicemente il percorso del file esistente
    if os.path.exists(pdf_path):
        return pdf_path

    # Procediamo con la generazione del PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                            leftMargin=0.25*inch, rightMargin=0.25*inch,
                            topMargin=0.25*inch, bottomMargin=0.25*inch)
    styles = getSampleStyleSheet()

    # Creiamo il titolo del report
    title = Paragraph(f"Fantacalcio: report calciatori giornata {giornata}", styles["Title"])
    slides = [title]
    
    # Slide 1: I più svalutati nelle ultime 3 giornate
    slide1_title = Paragraph(f"I più svalutati nelle ultime 3 giornate [dalla {giornata-3} alla {giornata}]", styles["Heading1"])
    data1 = execute_query("""
        WITH MaxGames AS (
            SELECT playerName, MAX(nGame) AS maxGame 
            FROM game_stats 
            GROUP BY playerName
        ),
        MaxCurValues AS (
            SELECT gs.playerName, gs.curValue
            FROM game_stats gs
            JOIN MaxGames mg ON gs.playerName = mg.playerName AND gs.nGame = mg.maxGame
        ),
        RecentDifferences AS (
            SELECT 
                gs.playerName,
                gs.nGame,
                gs.curValue - LAG(gs.curValue, 1) OVER (PARTITION BY gs.playerName ORDER BY gs.nGame ASC) AS curValueDifference,
                ps.role,
                gs.team,
                gs.nFantaTeam
            FROM 
                game_stats gs
            JOIN 
                players ps ON gs.playerName = ps.playerName 
            JOIN
                MaxGames mg ON gs.playerName = mg.playerName AND gs.nGame IN (mg.maxGame, mg.maxGame - 1, mg.maxGame - 2, mg.maxGame - 3)
        ),
        ComputedValues AS (
            SELECT 
                rd.playerName, 
                SUM(rd.curValueDifference) AS totalDifference, 
                (SELECT curValue FROM MaxCurValues WHERE playerName=rd.playerName) AS curValue,
                rd.role, 
                rd.team, 
                rd.nFantaTeam
            FROM RecentDifferences rd
            WHERE rd.curValueDifference IS NOT NULL
            GROUP BY rd.playerName
        )
        SELECT 
            playerName,
            totalDifference,
            curValue,
            ROUND((totalDifference * 100.0 / (curValue + ABS(totalDifference))), 2) AS percentageDecrement,
            role,
            team,
            nFantaTeam
        FROM ComputedValues
        ORDER BY totalDifference ASC, percentageDecrement ASC
        LIMIT 5;
    """)
    data1.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 svalutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    for role in roles:
        data = execute_query(f"""
            WITH MaxGames AS (
            SELECT playerName, MAX(nGame) AS maxGame 
            FROM game_stats 
            GROUP BY playerName
        ),
        MaxCurValues AS (
            SELECT gs.playerName, gs.curValue
            FROM game_stats gs
            JOIN MaxGames mg ON gs.playerName = mg.playerName AND gs.nGame = mg.maxGame
        ),
        RecentDifferences AS (
            SELECT 
                gs.playerName,
                gs.nGame,
                gs.curValue - LAG(gs.curValue, 1) OVER (PARTITION BY gs.playerName ORDER BY gs.nGame ASC) AS curValueDifference,
                ps.role,
                gs.team,
                gs.nFantaTeam
            FROM 
                game_stats gs
            JOIN 
                players ps ON gs.playerName = ps.playerName 
            JOIN
                MaxGames mg ON gs.playerName = mg.playerName AND gs.nGame IN (mg.maxGame, mg.maxGame - 1, mg.maxGame - 2, mg.maxGame - 3)
            WHERE ps.role = '{role}'
        ),
        ComputedValues AS (
            SELECT 
                rd.playerName, 
                SUM(rd.curValueDifference) AS totalDifference, 
                (SELECT curValue FROM MaxCurValues WHERE playerName=rd.playerName) AS curValue,
                rd.role, 
                rd.team, 
                rd.nFantaTeam
            FROM RecentDifferences rd
            WHERE rd.curValueDifference IS NOT NULL
            GROUP BY rd.playerName
        )
        SELECT 
            playerName,
            totalDifference,
            curValue,
            ROUND((totalDifference * 100.0 / (curValue + ABS(totalDifference))), 2) AS percentageDecrement,
            role,
            team,
            nFantaTeam
        FROM ComputedValues
        ORDER BY totalDifference ASC, percentageDecrement ASC
        LIMIT 5;
        """)
        data.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch)) 


    ########
    slides.append(PageBreak())
    ########

    # Slide 2: Giocatori piu svalutati da inizio stagione
    slide1_title = Paragraph("I più svalutati da inizio stagione", styles["Heading1"])
    data1 = execute_query("""
        WITH LastGameStats AS (
            SELECT playerName,
                curValue,
                team,
                ROW_NUMBER() OVER (PARTITION BY playerName ORDER BY nGame DESC) AS rn,
				nFantaTeam
            FROM game_stats
        ),
        PlayerDevaluation AS (
            SELECT ps.playerName,
                ps.initvalue,
                lg.curValue AS lastCurValue,
                lg.curValue - ps.initvalue AS maxDevaluation,
				lg.curValue,
                ps.role,
                lg.team,
				lg.nFantaTeam
            FROM players ps
            JOIN LastGameStats lg ON ps.playerName = lg.playerName
            WHERE lg.rn = 1
        )
        SELECT pd.playerName,
            pd.maxDevaluation,
			pd.curValue,
			ROUND((pd.maxDevaluation * 100.0 / (pd.curValue + ABS(maxDevaluation))), 2) AS percentageDecrement,
            pd.role,
            pd.team,
			pd.nFantaTeam
        FROM PlayerDevaluation pd
        ORDER BY pd.maxDevaluation ASC, percentageDecrement ASC
        LIMIT 5;
    """)
    data1.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 svalutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    role_tables = []
    for role in roles:
        data = execute_query(f"""
            WITH LastGameStats AS (
                SELECT playerName,
                    curValue,
                    ROW_NUMBER() OVER (PARTITION BY playerName ORDER BY nGame DESC) AS rn,
                    team,
					nFantaTeam
                FROM game_stats
            ),
            PlayerDevaluation AS (
                SELECT ps.playerName,
                    ps.initvalue,
                    lg.curValue AS lastCurValue,
                    lg.curValue- ps.initvalue AS maxDevaluation,
					lg.curValue,
                    ps.role,
                    lg.team,
					lg.nFantaTeam
                FROM players ps
                JOIN LastGameStats lg ON ps.playerName = lg.playerName
                WHERE lg.rn = 1 AND ps.role = '{role}'
            )
            SELECT pd.playerName,
                pd.maxDevaluation,
				pd.curValue,
				ROUND((pd.maxDevaluation * 100.0 / (pd.curValue + ABS(maxDevaluation))), 2) AS percentageDecrement,
                pd.role,
                pd.team,
				pd.nFantaTeam
            FROM PlayerDevaluation pd
            ORDER BY pd.maxDevaluation ASC, percentageDecrement ASC
            LIMIT 5;
        """)
        data.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch))


    ########
    slides.append(PageBreak())
    ########

    # Slide 3: Giocatori più valutati nelle ultime n (3) partite
    slide1_title = Paragraph("I giocatori che hanno acquistato più valore nelle ultime 3 giornate", styles["Heading1"])
    data1 = execute_query("""
        WITH RecentDifferences AS (
            SELECT gs.playerName,
                gs.nGame,
                LAG(gs.curValue, 1) OVER (PARTITION BY gs.playerName ORDER BY gs.nGame DESC) - gs.curValue AS curValueDifference,
                ps.role,
				gs.curValue,
                gs.team,
				gs.nFantaTeam
            FROM game_stats gs, players ps
            WHERE gs.playerName = ps.playerName 
            AND gs.nGame IN (
                SELECT MAX(nGame) FROM game_stats
                UNION
                SELECT MAX(nGame) - 1 FROM game_stats
                UNION
                SELECT MAX(nGame) - 2 FROM game_stats
                UNION
                SELECT MAX(nGame) - 3 FROM game_stats
            )
        )
        SELECT rd.playerName,
            SUM(rd.curValueDifference) AS totalIncement,
			rd.curValue,
			ROUND(rd.curValue * 100 / (rd.curValue - SUM(rd.curValueDifference)) - 100, 2) AS percentageIncrement,
            rd.role,
            rd.team,
			rd.nFantaTeam
        FROM RecentDifferences rd
        GROUP BY rd.playerName
        ORDER BY totalIncement DESC, percentageIncrement DESC
        LIMIT 5;
    """)
    data1.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 valutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    role_tables = []
    for role in roles:
        data = execute_query(f"""
            WITH RecentDifferences AS (
            SELECT gs.playerName,
                gs.nGame,
                LAG(gs.curValue, 1) OVER (PARTITION BY gs.playerName ORDER BY gs.nGame DESC) - gs.curValue AS curValueDifference,
                ps.role,
				gs.curValue,
                gs.team,
				gs.nFantaTeam
            FROM game_stats gs, players ps
            WHERE gs.playerName = ps.playerName AND ps.role = '{role}'
            AND gs.nGame IN (
                    SELECT MAX(nGame) FROM game_stats
                    UNION
                    SELECT MAX(nGame) - 1 FROM game_stats
                    UNION
                    SELECT MAX(nGame) - 2 FROM game_stats
                    UNION
                    SELECT MAX(nGame) - 3 FROM game_stats
                )
            )
            SELECT rd.playerName,
                SUM(rd.curValueDifference) AS totalIncement,
                rd.curValue,
                ROUND(rd.curValue * 100 / (rd.curValue - SUM(rd.curValueDifference)) - 100, 2) AS percentageIncrement,
                rd.role,
                rd.team,
                rd.nFantaTeam
            FROM RecentDifferences rd
            GROUP BY rd.playerName
            ORDER BY totalIncement DESC, percentageIncrement DESC
            LIMIT 5;
        """)
        data.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch))

    ########
    slides.append(PageBreak())
    ########

    # Slide 4: Giocatori più valutati da inizio stagione
    slide1_title = Paragraph("I giocatori che hanno acquistato più valore da inizio stagione", styles["Heading1"])
    data1 = execute_query("""
        WITH LastGameStats AS (
            SELECT playerName,
                curValue,
                ROW_NUMBER() OVER (PARTITION BY playerName ORDER BY nGame DESC) AS rn,
                team,
				nFantaTeam
            FROM game_stats
        ),
        playerValueDelta AS (
            SELECT ps.playerName,
                ps.initvalue,
                lg.curValue AS lastCurValue,
                lg.curValue - ps.initvalue AS valueIncrement,
                lg.team,
                ps.role,
				lg.nFantaTeam,
				lg.curValue
            FROM players ps
            JOIN LastGameStats lg ON ps.playerName = lg.playerName
            WHERE lg.rn = 1
        )
        SELECT pd.playerName,
            pd.valueIncrement,
			pd.curValue,
			ROUND(pd.curValue * 100 / (pd.curValue - pd.valueIncrement) - 100, 2) AS percentageIncrement,
            pd.role,
            pd.team,
			pd.nFantaTeam
        FROM playerValueDelta pd
        ORDER BY pd.valueIncrement DESC, percentageIncrement DESC
        LIMIT 5;
    """)
    data1.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 valutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    role_tables = []
    for role in roles:
        data = execute_query(f"""
            WITH LastGameStats AS (
            SELECT playerName,
                curValue,
                ROW_NUMBER() OVER (PARTITION BY playerName ORDER BY nGame DESC) AS rn,
                team,
				nFantaTeam
            FROM game_stats
            ),
            playerValueDelta AS (
                SELECT ps.playerName,
                    ps.initvalue,
                    lg.curValue AS lastCurValue,
                    lg.curValue - ps.initvalue AS valueIncrement,
                    lg.team,
                    ps.role,
                    lg.nFantaTeam,
                    lg.curValue
                FROM players ps
                JOIN LastGameStats lg ON ps.playerName = lg.playerName
                WHERE lg.rn = 1 AND ps.role = '{role}'
            )
            SELECT pd.playerName,
                pd.valueIncrement,
                pd.curValue,
                ROUND(pd.curValue * 100 / (pd.curValue - pd.valueIncrement) - 100, 2) AS percentageIncrement,
                pd.role,
                pd.team,
                pd.nFantaTeam
            FROM playerValueDelta pd
            ORDER BY pd.valueIncrement DESC, percentageIncrement DESC
            LIMIT 5;
        """)
        data.insert(0, ("Player", "+/-", "Val.", "+/-%", "Role", "Squadra", "#FANTA"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch))

    ########
    slides.append(PageBreak())
    ########

    # Slide 5: Giocatori più acquistati nelle ultime 3 giornate
    slide1_title = Paragraph(f"Giocatori più acquistati nelle ultime 3 giornate [dalla {giornata-2} alla {giornata}]", styles["Heading1"])
    data1 = execute_query(f"""
        WITH TeamIncrement AS (
            SELECT
                gs.playerName,
                SUM(CASE WHEN gs.nGame = {giornata} THEN gs.nFantaTeam ELSE 0 END) - 
                SUM(CASE WHEN gs.nGame = {giornata-2} THEN gs.nFantaTeam ELSE 0 END) AS teamIncrement,
                ps.role,
                MAX(CASE WHEN gs.nGame = {giornata} THEN gs.team END) AS latestTeam
            FROM
                game_stats gs, players ps
            WHERE gs.playerName = ps.playerName AND
                gs.nGame IN ({giornata}, {giornata-2})
            GROUP BY
                gs.playerName
        )
        SELECT
            playerName,
            COALESCE(teamIncrement, 0) AS totalIncrement,
            role,
            latestTeam as team
        FROM
            TeamIncrement
        ORDER BY
            totalIncrement DESC
        LIMIT 5;
    """)
    data1.insert(0, ("Player Name", "Incremento", "Ruolo", "Squadra"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 valutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    role_tables = []
    for role in roles:
        data = execute_query(f"""
            WITH TeamIncrement AS (
                SELECT
                    gs.playerName,
                    SUM(CASE WHEN gs.nGame = {giornata} THEN gs.nFantaTeam ELSE 0 END) - 
                    SUM(CASE WHEN gs.nGame = {giornata-2} THEN gs.nFantaTeam ELSE 0 END) AS teamIncrement,
                    ps.role,
                    gs.team
                FROM
                    game_stats gs, players ps
                WHERE gs.playerName = ps.playerName AND
                    gs.nGame IN ({giornata-2}, {giornata}) AND ps.role = '{role}'
                GROUP BY
                    gs.playerName
            )
            SELECT
                playerName,
                COALESCE(teamIncrement, 0) AS totalIncrement,
                role,
                team
            FROM
                TeamIncrement
            ORDER BY
                totalIncrement DESC
            LIMIT 5;
        """)
        data.insert(0, ("Player Name", "Incremento", "Ruolo", "Squadra"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch)) 

    ########
    slides.append(PageBreak())
    ########

    # Slide 6: Giocatori più ceduti nell'ultimo mercato (dalla giornata 21 alla 23)
    slide1_title = Paragraph(f"Giocatori più ceduti nelle ultime 3 giornate [dalla {giornata-2} alla {giornata}]", styles["Heading1"])
    data1 = execute_query(f"""
        WITH TeamIncrement AS (
            SELECT
                gs.playerName,
                SUM(CASE WHEN gs.nGame = {giornata} THEN gs.nFantaTeam ELSE 0 END) - 
                SUM(CASE WHEN gs.nGame = {giornata-2} THEN gs.nFantaTeam ELSE 0 END) AS teamIncrement,
                ps.role,
                gs.team
            FROM
                game_stats gs, players ps
            WHERE gs.playerName = ps.playerName AND
                gs.nGame IN ({giornata-2}, {giornata})
            GROUP BY
                gs.playerName
        )
        SELECT
            playerName,
            COALESCE(teamIncrement, 0) AS totalIncrement,
            role,
            team
        FROM
            TeamIncrement
        ORDER BY
            totalIncrement ASC
        LIMIT 5;
    """)
    data1.insert(0, ("Player Name", "Decremento", "Ruolo", "Squadra"))
    table1 = Table(data1)
    table1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
    slides.append(slide1_title)
    slides.append(table1)

    # Slide 2-5: Top 5 valutati per ruolo
    slide2_title = Paragraph("Per ruolo: ")
    slides.append(slide2_title)
    roles = ["P", "D", "C", "A"]
    role_tables = []
    for role in roles:
        data = execute_query(f"""
            WITH TeamIncrement AS (
                SELECT
                    gs.playerName,
                    SUM(CASE WHEN gs.nGame = {giornata} THEN gs.nFantaTeam ELSE 0 END) - 
                    SUM(CASE WHEN gs.nGame = {giornata-2} THEN gs.nFantaTeam ELSE 0 END) AS teamIncrement,
                    ps.role,
                    gs.team
                FROM
                    game_stats gs, players ps
                WHERE gs.playerName = ps.playerName AND
                    gs.nGame IN ({giornata-2}, {giornata}) AND ps.role = '{role}'
                GROUP BY
                    gs.playerName
            )
            SELECT
                playerName,
                COALESCE(teamIncrement, 0) AS totalIncrement,
                role,
                team
            FROM
                TeamIncrement
            ORDER BY
                totalIncrement ASC
            LIMIT 5;
        """)
        data.insert(0, ("Player Name", "Decremento", "Ruolo", "Squadra"))
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                                   ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                   ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                   ('BACKGROUND', (0,1), (-1,-1), colors.white),
                                   ('GRID', (0,0), (-1,-1), 0.1, colors.black)]))
        slides.append(table)
        slides.append(Spacer(1, 0.2 * inch))

    # Ensure directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Save the PDF
    doc.build(slides)

    # Set file permissions to 644 (readable by everyone)
    os.chmod(pdf_path, 0o644)

    buffer.seek(0)

    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")

        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="900" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        return 1

    except FileNotFoundError:
        st.error("Errore: Il file PDF non è stato trovato.")
        return -1

        

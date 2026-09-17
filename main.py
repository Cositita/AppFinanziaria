import sqlite3
from datetime import datetime
import flet as ft
import re
import csv

DB_NAME = "appfinance_v19.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            importo REAL NOT NULL,
            tipo TEXT NOT NULL,
            conto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descrizione TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM conti")
    if cursor.fetchone()[0] == 0:
        conti_iniziali = [
            ('Conto Corrente',),
            ('Banca',),
            ('Posta',),
            ('ATM',)
        ]
        cursor.executemany("INSERT INTO conti (nome) VALUES (?)", conti_iniziali)
        
    cursor.execute("SELECT COUNT(*) FROM categorie")
    if cursor.fetchone()[0] == 0:
        categorie_iniziali = [
            ('Stipendio', 'Entrata'),
            ('Rimborso / Extra', 'Entrata'),
            ('Altro (Entrate)', 'Entrata'),
            ('Alimentari / Supermercato', 'Uscita'),
            ('Bollette (Luce, Gas, Acqua)', 'Uscita'),
            ('Affitto / Mutuo', 'Uscita'),
            ('Condominio', 'Uscita'),
            ('Carburante / Trasporti', 'Uscita'),
            ('Bollo Auto / Assicurazione', 'Uscita'),
            ('Salute / Farmacia', 'Uscita'),
            ('Assegno al coniuge (Uscita)', 'Uscita'),
            ('Spese universitarie / Scolastiche', 'Uscita'),
            ('Svago / Ristoranti', 'Uscita'),
            ('Abbonamenti (Netflix, Spotify, ecc.)', 'Uscita'),
            ('Shopping / Abbigliamento', 'Uscita'),
            ('Spese Varie / Generico', 'Uscita')
        ]
        cursor.executemany("INSERT INTO categorie (nome, tipo) VALUES (?, ?)", categorie_iniziali)
        
    conn.commit()
    conn.close()

def get_db_data(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data

def calcola_saldi_conto(conto_nome, data_oggi_str):
    movimenti_attuali = get_db_data("SELECT tipo, importo FROM movimenti WHERE conto = ? AND data <= ?", (conto_nome, data_oggi_str))
    saldo_attuale = 0.0
    for tipo, importo in movimenti_attuali:
        if tipo == "Entrata":
            saldo_attuale += importo
        else:
            saldo_attuale -= importo
            
    movimenti_totali = get_db_data("SELECT tipo, importo FROM movimenti WHERE conto = ?", (conto_nome,))
    saldo_futuro = 0.0
    for tipo, importo in movimenti_totali:
        if tipo == "Entrata":
            saldo_futuro += importo
        else:
            saldo_futuro -= importo
            
    return saldo_attuale, saldo_futuro

def calcola_date_future(data_str, mesi):
    dt = datetime.strptime(data_str, "%Y-%m-%d")
    date_list = []
    for i in range(mesi):
        m = dt.month - 1 + i
        y = dt.year + m // 12
        m = m % 12 + 1
        try:
            d = dt.replace(year=y, month=m)
        except ValueError:
            d = datetime(y, m, 28)
        date_list.append(d.strftime("%Y-%m-%d"))
    return date_list

def parse_notifica_universale(testo, conti_disponibili, categorie_disponibili):
    testo_lower = testo.lower()
    
    # Inserite tutte le parole chiave di rifiuto/annullamento richieste
    parole_rifiuto = ["rifiutata", "negata", "fallita", "bloccata", "non autorizzata", "rifiutato", "negato", "annullato", "non accettato"]
    if any(p in testo_lower for p in parole_rifiuto):
        return {"stato": "rifiutata", "descrizione": testo}
    
    importo = 0.0
    match_importo = re.search(r'(\d+[\.,]\d{2})', testo)
    if match_importo:
        importo = float(match_importo.group(1).replace(',', '.'))
    
    parole_entrata = ["accredito", "ricevuto", "stipendio", "bonifico in entrata", "rimborso", "storno", "entrata", "accreditato", "stornata"]
    tipo = "Entrata" if any(p in testo_lower for p in parole_entrata) else "Uscita"
    
    conto_trovato = conti_disponibili[0] if conti_disponibili else "Conto Corrente"
    for c in conti_disponibili:
        if c.lower() in testo_lower:
            conto_trovato = c
            break
            
    categoria_trovata = "Rimborso / Extra" if tipo == "Entrata" and any(p in testo_lower for p in ["rimborso", "storno", "stornata"]) else "Spese Varie / Generico"
    
    if "coniuge" in testo_lower or "mantenimento" in testo_lower:
        categoria_trovata = "Assegno al coniuge (Uscita)"
        tipo = "Uscita"
    elif tipo == "Uscita" or categoria_trovata == "Spese Varie / Generico":
        for cat in categorie_disponibili:
            if cat.lower() in testo_lower or any(parola in testo_lower for parola in cat.lower().split("/")):
                categoria_trovata = cat
                break
            
    return {
        "stato": "ok",
        "importo": importo,
        "tipo": tipo,
        "conto": conto_trovato,
        "categoria": categoria_trovata,
        "descrizione": testo
    }

def main(page: ft.Page):
    page.title = "AppFinance"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121824"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 15
    
    init_db()
    
    conti_db = [c[0] for c in get_db_data("SELECT nome FROM conti")]
    cat_db = [c[0] for c in get_db_data("SELECT nome FROM categorie")]
    
    saldo_cc_att = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    saldo_cc_fut = ft.Text(size=14, color="amber")
    
    saldo_banca_att = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    saldo_banca_fut = ft.Text(size=14, color="amber")
    
    saldo_posta_att = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    saldo_posta_fut = ft.Text(size=14, color="amber")
    
    saldo_atm_att = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    saldo_atm_fut = ft.Text(size=14, color="amber")
    
    saldo_tot_att = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    saldo_tot_fut = ft.Text(size=14, color="amber")
    
    status_text = ft.Text("", size=11, color="green")
    movimenti_list_view = ft.ListView(expand=1, spacing=6, padding=5, height=220)

    filtro_conto_dropdown = ft.Dropdown(
        label="Filtra Conto",
        options=[ft.dropdown.Option("Tutti i conti")] + [ft.dropdown.Option(c) for c in conti_db],
        value="Tutti i conti",
        width=170, text_size=11,
        on_select=lambda e: aggiorna_interfaccia()
    )
    
    filtro_cat_dropdown = ft.Dropdown(
        label="Filtra Categoria",
        options=[ft.dropdown.Option("Tutte le categorie")] + [ft.dropdown.Option(c) for c in cat_db],
        value="Tutte le categorie",
        width=190, text_size=11,
        on_select=lambda e: aggiorna_interfaccia()
    )

    edit_id_field = ft.Text(visible=False)
    edit_conto_dropdown = ft.Dropdown(label="Conto", options=[ft.dropdown.Option(c) for c in conti_db], width=200, text_size=12)
    edit_tipo_dropdown = ft.Dropdown(label="Tipologia", options=[ft.dropdown.Option("Uscita"), ft.dropdown.Option("Entrata")], width=140, text_size=12)
    edit_importo_input = ft.TextField(label="Importo (€)", keyboard_type=ft.KeyboardType.NUMBER, width=140, text_size=12)
    edit_cat_dropdown = ft.Dropdown(label="Categoria", options=[ft.dropdown.Option(c) for c in cat_db], width=200, text_size=12)
    edit_desc_input = ft.TextField(label="Descrizione", width=350, text_size=12)
    edit_data_input = ft.TextField(label="Data", width=140, text_size=12)

    def aggiorna_interfaccia():
        oggi_str = datetime.now().strftime("%Y-%m-%d")
        
        s_cc_a, s_cc_f = calcola_saldi_conto("Conto Corrente", oggi_str)
        s_banca_a, s_banca_f = calcola_saldi_conto("Banca", oggi_str)
        s_posta_a, s_posta_f = calcola_saldi_conto("Posta", oggi_str)
        s_atm_a, s_atm_f = calcola_saldi_conto("ATM", oggi_str)
        
        s_tot_a = s_cc_a + s_banca_a + s_posta_a + s_atm_a
        s_tot_f = s_cc_f + s_banca_f + s_posta_f + s_atm_f
        
        saldo_cc_att.value = f"€ {s_cc_a:,.2f}"
        saldo_cc_att.color = "green" if s_cc_a >= 0 else "red"
        saldo_cc_fut.value = f"Futuro: € {s_cc_f:,.2f}"
        
        saldo_banca_att.value = f"€ {s_banca_a:,.2f}"
        saldo_banca_att.color = "green" if s_banca_a >= 0 else "red"
        saldo_banca_fut.value = f"Futuro: € {s_banca_f:,.2f}"
        
        saldo_posta_att.value = f"€ {s_posta_a:,.2f}"
        saldo_posta_att.color = "green" if s_posta_a >= 0 else "red"
        saldo_posta_fut.value = f"Futuro: € {s_posta_f:,.2f}"
        
        saldo_atm_att.value = f"€ {s_atm_a:,.2f}"
        saldo_atm_att.color = "green" if s_atm_a >= 0 else "red"
        saldo_atm_fut.value = f"Futuro: € {s_atm_f:,.2f}"
        
        saldo_tot_att.value = f"€ {s_tot_a:,.2f}"
        saldo_tot_att.color = "green" if s_tot_a >= 0 else "red"
        saldo_tot_fut.value = f"Futuro: € {s_tot_f:,.2f}"

        tutti_cronologici = get_db_data("SELECT id, data, importo, tipo, conto, categoria, descrizione FROM movimenti ORDER BY data ASC, id ASC")
        saldati_per_id = {}
        running_sald = {c: 0.0 for c in conti_db}
        
        for m_id, data, importo, tipo, conto, categoria, desc in tutti_cronologici:
            if conto not in running_sald:
                running_sald[conto] = 0.0
            if tipo == "Entrata":
                running_sald[conto] += importo
            else:
                running_sald[conto] -= importo
            saldati_per_id[m_id] = running_sald[conto]

        query_storico = "SELECT id, data, importo, tipo, conto, categoria, descrizione FROM movimenti WHERE 1=1"
        params_storico = []
        
        c_filtro = filtro_conto_dropdown.value
        cat_filtro = filtro_cat_dropdown.value
        
        if c_filtro and c_filtro != "Tutti i conti":
            query_storico += " AND conto = ?"
            params_storico.append(c_filtro)
        if cat_filtro and cat_filtro != "Tutte le categorie":
            query_storico += " AND categoria = ?"
            params_storico.append(cat_filtro)
            
        query_storico += " ORDER BY data DESC, id DESC"
        
        movimenti_list_view.controls.clear()
        righe = get_db_data(query_storico, tuple(params_storico))
        
        if not righe:
            movimenti_list_view.controls.append(ft.Text("Nessun movimento trovato con i filtri selezionati.", size=12, color="grey"))
        else:
            categorie_fiscali = ["Assegno al coniuge (Uscita)", "Spese universitarie / Scolastiche", "Salute / Farmacia"]
            
            for r in righe:
                m_id, data, importo, tipo, conto, categoria, desc = r
                is_programmato = data > oggi_str
                segno = "+" if tipo == "Entrata" else "-"
                
                colore_importo = "amber" if is_programmato else ("red" if tipo == "Uscita" else "green")
                
                badge_fiscale = ft.Container(
                    content=ft.Text(" FISCO ", size=13, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor="purple",
                    border_radius=4,
                    padding=4
                ) if categoria in categorie_fiscali else ft.Container()

                badge_prog = ft.Container(
                    content=ft.Text(" PROGRAMMATO ", size=13, weight=ft.FontWeight.BOLD, color="black"),
                    bgcolor="amber",
                    border_radius=4,
                    padding=4
                ) if is_programmato else ft.Container()

                saldo_alla_data = saldati_per_id.get(m_id, 0.0)
                
                def apri_modifica(e, r_dati=r):
                    edit_id_field.value = str(r_dati[0])
                    edit_data_input.value = r_dati[1]
                    edit_importo_input.value = str(r_dati[2])
                    edit_tipo_dropdown.value = r_dati[3]
                    edit_conto_dropdown.value = r_dati[4]
                    edit_cat_dropdown.value = r_dati[5]
                    edit_desc_input.value = r_dati[6] if r_dati[6] else ""
                    page.dialog = edit_dialog
                    edit_dialog.open = True
                    page.update()

                def elimina_movimento(e, id_mov=m_id):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM movimenti WHERE id = ?", (id_mov,))
                    conn.commit()
                    conn.close()
                    aggiorna_interfaccia()

                riga_container = ft.Container(
                    content=ft.Row([
                        ft.Row([
                            ft.Text(data, size=11, color="grey", width=75),
                            badge_prog,
                            badge_fiscale,
                            ft.VerticalDivider(width=1, color="transparent"),
                            ft.Text(f"{conto} • {categoria}", size=12, weight=ft.FontWeight.W_500, color="white", width=220),
                            ft.Text(f"({desc})" if desc else "", size=11, color="grey", italic=True, width=160, overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=4, alignment=ft.MainAxisAlignment.START),
                        ft.Row([
                            ft.Text(f"{segno}€{importo:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=colore_importo, width=90),
                            ft.Text(f"[Saldo: €{saldo_alla_data:,.2f}]", size=10, color="grey", width=110),
                            ft.TextButton("Modifica", on_click=apri_modifica),
                            ft.TextButton("Elimina", on_click=elimina_movimento)
                        ], spacing=2, alignment=ft.MainAxisAlignment.END)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    bgcolor="#161f30",
                    padding=6,
                    border_radius=5
                )
                
                movimenti_list_view.controls.append(riga_container)
                
        # Aggiornamento mirato immediato per Windows e Android
        movimenti_list_view.update()
        page.update()

    def esporta_csv(e):
        try:
            righe_export = get_db_data("SELECT id, data, importo, tipo, conto, categoria, descrizione FROM movimenti ORDER BY data DESC, id DESC")
            filename = f"report_movimenti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Data", "Importo", "Tipo", "Conto", "Categoria", "Descrizione"])
                for r in righe_export:
                    writer.writerow(r)
            status_text.value = f"Esportato con successo in {filename}"
            status_text.color = "green"
            page.update()
        except Exception as ex:
            status_text.value = f"Errore esportazione: {ex}"
            status_text.color = "red"
            page.update()

    def salva_modifica_db(e):
        try:
            m_id = int(edit_id_field.value)
            nuova_data = edit_data_input.value
            nuovo_importo = float(edit_importo_input.value.replace(",", "."))
            nuovo_tipo = edit_tipo_dropdown.value
            nuovo_conto = edit_conto_dropdown.value
            nuova_cat = edit_cat_dropdown.value
            nuova_desc = edit_desc_input.value

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE movimenti 
                SET data = ?, importo = ?, tipo = ?, conto = ?, categoria = ?, descrizione = ?
                WHERE id = ?
            """, (nuova_data, nuovo_importo, nuovo_tipo, nuovo_conto, nuova_cat, nuova_desc, m_id))
            conn.commit()
            conn.close()

            edit_dialog.open = False
            aggiorna_interfaccia()
        except ValueError:
            pass

    edit_dialog = ft.AlertDialog(
        title=ft.Text("Modifica Movimento", size=14),
        content=ft.Column([
            edit_id_field,
            ft.Row([edit_conto_dropdown, edit_tipo_dropdown], spacing=8),
            ft.Row([edit_importo_input, edit_cat_dropdown], spacing=8),
            ft.Row([edit_desc_input, edit_data_input], spacing=8),
        ], tight=True, spacing=8),
        actions=[
            ft.TextButton("Annulla", on_click=lambda e: setattr(edit_dialog, 'open', False) or page.update()),
            ft.ElevatedButton("Salva", on_click=salva_modifica_db, bgcolor="blue", color="white")
        ],
    )

    def crea_card_saldo(titolo, val_att, val_fut):
        return ft.Container(
            content=ft.Column([
                ft.Text(titolo, size=14, color="lightBlue", weight=ft.FontWeight.BOLD),
                val_att,
                val_fut
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#1b2230",
            padding=18,
            height=175,
            border_radius=8,
            expand=True
        )

    cards_row = ft.Row([
        crea_card_saldo("C. Corrente", saldo_cc_att, saldo_cc_fut),
        crea_card_saldo("Banca", saldo_banca_att, saldo_banca_fut),
        crea_card_saldo("Posta", saldo_posta_att, saldo_posta_fut),
        crea_card_saldo("ATM", saldo_atm_att, saldo_atm_fut),
        crea_card_saldo("Totale", saldo_tot_att, saldo_tot_fut),
    ], spacing=6)

    conto_dropdown = ft.Dropdown(
        label="Conto",
        options=[ft.dropdown.Option(c) for c in conti_db],
        expand=2, text_size=12
    )
    conto_dropdown.value = None

    tipo_dropdown = ft.Dropdown(
        label="Tipologia",
        options=[ft.dropdown.Option("Uscita"), ft.dropdown.Option("Entrata")],
        value="Uscita",
        expand=1, text_size=12
    )
    
    importo_input = ft.TextField(label="Importo (€)", keyboard_type=ft.KeyboardType.NUMBER, expand=1, text_size=12)

    cat_dropdown = ft.Dropdown(
        label="Categoria",
        options=[ft.dropdown.Option(c) for c in cat_db],
        expand=2, text_size=12
    )
    cat_dropdown.value = None
        
    desc_input = ft.TextField(label="Descrizione", expand=3, text_size=12)
    data_input = ft.TextField(label="Data", value=datetime.now().strftime("%Y-%m-%d"), expand=1, text_size=12)
    mesi_input = ft.TextField(label="Mesi (Rate)", value="1", expand=1, text_size=12)

    def salva_movimento(e):
        try:
            if not conto_dropdown.value or not cat_dropdown.value:
                status_text.value = "Seleziona Conto e Categoria!"
                status_text.color = "red"
                page.update()
                return

            importo = float(importo_input.value.replace(",", "."))
            tipo = tipo_dropdown.value
            conto = conto_dropdown.value
            categoria = cat_dropdown.value
            descrizione = desc_input.value
            data_iniziale = data_input.value
            mesi = int(mesi_input.value) if mesi_input.value.isdigit() else 1
            
            date_list = calcola_date_future(data_iniziale, mesi)
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            for d in date_list:
                cursor.execute("""
                    INSERT INTO movimenti (data, importo, tipo, conto, categoria, descrizione)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (d, importo, tipo, conto, categoria, descrizione))
            conn.commit()
            conn.close()
            
            status_text.value = f"Salvato ({mesi} rate)!"
            status_text.color = "green"
            importo_input.value = ""
            desc_input.value = ""
            mesi_input.value = "1"
            conto_dropdown.value = None
            cat_dropdown.value = None
            aggiorna_interfaccia()
        except ValueError:
            status_text.value = "Errore nei campi numerici."
            status_text.color = "red"
            page.update()

    salva_btn = ft.ElevatedButton("Salva", on_click=salva_movimento, bgcolor="blue", color="white", height=45)

    form_section = ft.Container(
        content=ft.Column([
            ft.Text("Nuovo Movimento / Programmato", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([conto_dropdown, tipo_dropdown, importo_input, cat_dropdown], spacing=10),
            ft.Row([desc_input, data_input, mesi_input, salva_btn, status_text], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=10),
        bgcolor="#1b2230",
        padding=12,
        border_radius=6
    )

    testo_notifica_input = ft.TextField(label="Incolla testo notifica bancaria...", expand=4, text_size=11)
    risultato_parser_text = ft.Text("", size=11, color="yellow")

    def testa_parser(e):
        testo = testo_notifica_input.value
        if not testo:
            risultato_parser_text.value = "Inserisci testo."
            risultato_parser_text.color = "red"
            page.update()
            return
            
        dati = parse_notifica_universale(testo, conti_db, cat_db)
        
        if dati["stato"] == "rifiutata":
            risultato_parser_text.value = "Ignorata: Transazione rifiutata o bloccata."
            risultato_parser_text.color = "orange"
            testo_notifica_input.value = ""
            page.update()
            return

        if dati["importo"] == 0.0:
            risultato_parser_text.value = "Importo non rilevato."
            risultato_parser_text.color = "red"
            page.update()
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movimenti (data, importo, tipo, conto, categoria, descrizione)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), dati["importo"], dati["tipo"], dati["conto"], dati["categoria"], dati["descrizione"]))
        conn.commit()
        conn.close()
        
        azione_str = "Storno/Rimborso" if dati["tipo"] == "Entrata" else "Registrato"
        risultato_parser_text.value = f"{azione_str}: {dati['conto']} ({dati['categoria']}) €{dati['importo']}"
        risultato_parser_text.color = "green"
        testo_notifica_input.value = ""
        aggiorna_interfaccia()

    parser_btn = ft.ElevatedButton("Interpreta", on_click=testa_parser, bgcolor="orange", color="black", height=38)

    parser_section = ft.Container(
        content=ft.Column([
            ft.Text("Test Notifiche Rapide", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([testo_notifica_input, parser_btn, risultato_parser_text], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=6),
        bgcolor="#1b2230",
        padding=10,
        border_radius=6
    )

    esporta_csv_btn = ft.ElevatedButton("Esporta CSV", on_click=esporta_csv, bgcolor="green", color="white", height=35)

    movimenti_section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Storico e Movimenti Programmati", size=13, weight=ft.FontWeight.BOLD),
                ft.Row([filtro_conto_dropdown, filtro_cat_dropdown, esporta_csv_btn], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            movimenti_list_view
        ], spacing=6),
        bgcolor="#1b2230",
        padding=10,
        border_radius=6
    )

    page.add(
        ft.Column([
            ft.Text("AppFinance - Dashboard", size=16, weight=ft.FontWeight.BOLD),
            cards_row,
            form_section,
            parser_section,
            movimenti_section
        ], spacing=8)
    )

    aggiorna_interfaccia()

if __name__ == "__main__":
    ft.app(target=main)

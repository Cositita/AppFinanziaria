import sqlite3
from datetime import datetime, timedelta
import flet as ft

def init_db():
    conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conto TEXT,
            tipo TEXT,
            importo REAL,
            categoria TEXT,
            descrizione TEXT,
            mesi_ripetizione INTEGER,
            data TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE transazioni ADD COLUMN data TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorie_custom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            nome TEXT
        )
    """)
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Gestione Spese & Tasse Multi-Conto"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#12161f"
    page.padding = 25
    page.scroll = ft.ScrollMode.AUTO
    page.window_width = 1150
    page.window_height = 850
    
    init_db()

    modifica_id_val = [None]

    data_corrente_odierna = datetime.now()
    anno_corrente_str = str(data_corrente_odierna.year)
    anno_selezionato_val = [anno_corrente_str]

    # Storico decennale
    anno_corrente_int = data_corrente_odierna.year
    anni_disponibili = [str(y) for y in range(anno_corrente_int - 5, anno_corrente_int + 6)]

    def cambia_anno_filtro(e):
        anno_selezionato_val[0] = dd_filtro_anno.value
        carica_dati()

    dd_filtro_anno = ft.Dropdown(
        label="Visualizza Anno",
        options=[ft.dropdown.Option(a) for a in anni_disponibili],
        value=anno_corrente_str if anno_corrente_str in anni_disponibili else anni_disponibili[0],
        on_select=cambia_anno_filtro,
        width=200
    )

    lbl_saldo_bcc = ft.Text("€ 0.00", size=20, weight=ft.FontWeight.BOLD, color="#66bb6a")
    lbl_proiettato_bcc = ft.Text("€ 0.00", size=14, color="#bdbdbd")

    lbl_saldo_hype = ft.Text("€ 0.00", size=20, weight=ft.FontWeight.BOLD, color="#66bb6a")
    lbl_proiettato_hype = ft.Text("€ 0.00", size=14, color="#bdbdbd")

    lbl_saldo_totale = ft.Text("€ 0.00", size=20, weight=ft.FontWeight.BOLD, color="#81d4fa")
    lbl_proiettato_totale = ft.Text("€ 0.00", size=14, color="#bdbdbd")

    card_bcc = ft.Container(
        content=ft.Column([
            ft.Text("Saldo BCC (Effettivo)", size=12, color="#bdbdbd"),
            lbl_saldo_bcc,
            ft.Divider(height=5, color="transparent"),
            ft.Text("Proiettato a fine anno:", size=11, color="#80cbc4"),
            lbl_proiettato_bcc
        ]),
        bgcolor="#1e2530",
        padding=15,
        border_radius=10,
        expand=True
    )

    card_hype = ft.Container(
        content=ft.Column([
            ft.Text("Saldo Hype (Effettivo)", size=12, color="#bdbdbd"),
            lbl_saldo_hype,
            ft.Divider(height=5, color="transparent"),
            ft.Text("Proiettato a fine anno:", size=11, color="#80cbc4"),
            lbl_proiettato_hype
        ]),
        bgcolor="#1e2530",
        padding=15,
        border_radius=10,
        expand=True
    )

    card_totale = ft.Container(
        content=ft.Column([
            ft.Text("Saldo Totale (Effettivo)", size=12, color="#81d4fa"),
            lbl_saldo_totale,
            ft.Divider(height=5, color="transparent"),
            ft.Text("Proiettato a fine anno:", size=11, color="#81d4fa"),
            lbl_proiettato_totale
        ]),
        bgcolor="#1e2530",
        padding=15,
        border_radius=10,
        expand=True
    )

    sezione_avvisi = ft.Column(spacing=5)
    container_avvisi = ft.Container(visible=False, padding=12, bgcolor="#3b1c1c", border_radius=8)

    dd_conto = ft.Dropdown(
        label="Conto",
        options=[ft.dropdown.Option("BCC"), ft.dropdown.Option("Hype")],
        value="BCC",
        expand=True
    )

    base_entrate = sorted(["Altro (Entrata)", "Entrate extra", "Stipendio"])
    base_uscite = sorted([
        "Acqua", "Assegno divorzile", "Condominio", "Donazioni varie", 
        "Gas", "Luce", "Mutuo", "Rete wifi", "Ricariche telefoniche", 
        "Spese casa", "Spese mediche", "Supermercato", "Tari", 
        "Tasse fisse", "Tasse variabili", "Trasferimenti bancari", "Altro (Uscita)"
    ])

    def carica_opzioni_categorie():
        conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
        cursor = conn.cursor()
        cursor.execute("SELECT tipo, nome FROM categorie_custom")
        custom_rows = cursor.fetchall()
        conn.close()

        entrate = list(base_entrate)
        uscite = list(base_uscite)

        for t, nome in custom_rows:
            if t == "Entrata" and nome not in entrate:
                entrate.append(nome)
            elif t == "Uscita" and nome not in uscite:
                uscite.append(nome)

        return sorted(entrate), sorted(uscite)

    entrate_ordinate, uscite_ordinate = carica_opzioni_categorie()

    dd_categoria = ft.Dropdown(
        label="Categoria",
        options=[ft.dropdown.Option(c) for c in uscite_ordinate],
        value=uscite_ordinate[0] if uscite_ordinate else "",
        expand=True
    )

    def aggiorna_dropdown_categorie(tipo):
        entrate, uscite = carica_opzioni_categorie()
        if tipo == "Entrata":
            dd_categoria.options = [ft.dropdown.Option(c) for c in entrate]
            dd_categoria.value = entrate[0] if entrate else ""
        else:
            dd_categoria.options = [ft.dropdown.Option(c) for c in uscite]
            dd_categoria.value = uscite[0] if uscite else ""
        page.update()

    def cambia_tipo(e):
        aggiorna_dropdown_categorie(dd_tipo.value)

    dd_tipo = ft.Dropdown(
        label="Tipologia",
        options=[ft.dropdown.Option("Entrata"), ft.dropdown.Option("Uscita")],
        value="Uscita",
        on_select=cambia_tipo,
        expand=True
    )

    txt_importo = ft.TextField(label="Importo (€)", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    txt_descrizione = ft.TextField(label="Descrizione (es. Rata Mutuo)", expand=True)
    txt_data = ft.TextField(label="Data Inizio (YYYY-MM-DD)", value=data_corrente_odierna.strftime('%Y-%m-%d'), expand=True)
    txt_ripetizione = ft.TextField(label="Mesi programmati (es. 3 per Ott-Nov-Dic, o 12)", value="1", expand=True)
    txt_nuova_cat = ft.TextField(label="Nuova categoria personalizzata", expand=True)

    def aggiungi_nuova_categoria(e):
        if not txt_nuova_cat.value:
            return
        nuova = txt_nuova_cat.value.strip()
        tipo_corrente = dd_tipo.value

        conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorie_custom (tipo, nome) VALUES (?, ?)", (tipo_corrente, nuova))
        conn.commit()
        conn.close()

        txt_nuova_cat.value = ""
        aggiorna_dropdown_categorie(tipo_corrente)
        dd_categoria.value = nuova
        page.update()

    btn_aggiungi_cat = ft.ElevatedButton(
        content=ft.Text("Aggiungi Categoria"),
        on_click=aggiungi_nuova_categoria
    )

    lbl_titolo_form = ft.Text("Aggiungi / Modifica Movimento Programmato", size=18, weight=ft.FontWeight.BOLD)
    lista_storico = ft.Column(spacing=10)

    def controlla_avvisi_globali():
        conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, conto, tipo, importo, categoria, descrizione, data 
            FROM transazioni 
            WHERE data >= ? AND data <= ? AND tipo = 'Uscita'
            ORDER BY data ASC
        """, (data_corrente_odierna.strftime("%Y-%m-%d"), (data_corrente_odierna + timedelta(days=7)).strftime("%Y-%m-%d")))
        scadenze = cursor.fetchall()
        conn.close()

        sezione_avvisi.controls.clear()
        if scadenze:
            sezione_avvisi.controls.append(ft.Text("⚠️ ATTENZIONE: Pagamenti in scadenza nei prossimi 7 giorni!", weight=ft.FontWeight.BOLD, color="#ff5252", size=14))
            for s_id, s_conto, s_tipo, s_imp, s_cat, s_desc, s_data in scadenze:
                data_dt = datetime.strptime(s_data, "%Y-%m-%d")
                giorni_mancanti = (data_dt.date() - data_corrente_odierna.date()).days
                testo_giorni = "Oggi!" if giorni_mancanti == 0 else (f"Tra {giorni_mancanti} giorni" if giorni_mancanti > 1 else "Domani!")
                
                desc_str = f" - {s_desc}" if s_desc else ""
                sezione_avvisi.controls.append(
                    ft.Text(f"• [{s_data} - {testo_giorni}] {s_conto} | {s_cat}{desc_str}: € {s_imp:.2f}", color="#ff8a80", size=13)
                )
            container_avvisi.visible = True
        else:
            container_avvisi.visible = False

    def carica_dati():
        lista_storico.controls.clear()
        controlla_avvisi_globali()

        conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
        cursor = conn.cursor()
        
        anno_filtro = anno_selezionato_val[0]
        cursor.execute("""
            SELECT id, conto, tipo, importo, categoria, descrizione, mesi_ripetizione, data 
            FROM transazioni 
            WHERE strftime('%Y', data) = ? 
            ORDER BY data DESC, id DESC
        """, (anno_filtro,))
        rows = cursor.fetchall()
        conn.close()

        effettivo_bcc = 0.0
        proiettato_bcc = 0.0
        effettivo_hype = 0.0
        proiettato_hype = 0.0

        stringa_oggi = data_corrente_odierna.strftime("%Y-%m-%d")
        data_limite_settimana = (data_corrente_odierna + timedelta(days=7)).strftime("%Y-%m-%d")

        for row_id, conto, tipo, importo, categoria, descrizione, ripetizione, data_transazione in rows:
            valore = importo if tipo == "Entrata" else -importo
            data_str = data_transazione if data_transazione else stringa_oggi

            if conto == "BCC":
                proiettato_bcc += valore
            elif conto == "Hype":
                proiettato_hype += valore

            is_effettivo = False
            if data_str <= stringa_oggi:
                is_effettivo = True

            if is_effettivo:
                if conto == "BCC":
                    effettivo_bcc += valore
                elif conto == "Hype":
                    effettivo_hype += valore

            colore_testo = "#66bb6a" if tipo == "Entrata" else "#ef5350"
            segno = "+" if tipo == "Entrata" else "-"

            sfondo_riga = "#1e2530"
            if tipo == "Uscita" and stringa_oggi <= data_str <= data_limite_settimana:
                sfondo_riga = "#3d241c"

            def prepara_modifica(e, rid=row_id, c=conto, t=tipo, imp=importo, cat=categoria, desc=descrizione, rip=ripetizione, dt=data_transazione):
                modifica_id_val[0] = rid
                dd_conto.value = c
                dd_tipo.value = t
                aggiorna_dropdown_categorie(t)
                dd_categoria.value = cat if cat else dd_categoria.options[0].key
                txt_importo.value = str(imp)
                txt_descrizione.value = desc if desc else ""
                txt_data.value = dt if dt else data_corrente_odierna.strftime('%Y-%m-%d')
                txt_ripetizione.value = str(rip) if rip else "1"
                lbl_titolo_form.value = f"Modifica Movimento #{rid}"
                txt_btn_salva.value = "Aggiorna Movimento"
                page.update()

            def elimina_movimento(e, rid=row_id):
                conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transazioni WHERE id = ?", (rid,))
                conn.commit()
                conn.close()
                carica_dati()

            btn_modifica = ft.TextButton(
                content=ft.Text("Modifica", color="#ffca28", weight=ft.FontWeight.BOLD),
                on_click=prepara_modifica
            )

            btn_elimina = ft.TextButton(
                content=ft.Text("Elimina", color="#ef5350", weight=ft.FontWeight.BOLD),
                on_click=elimina_movimento
            )

            riga_elemento = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(f"[{data_str}] {conto} - {categoria or 'Senza categoria'}", weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(f"{descrizione or 'Nessuna descrizione'}", size=12, color="#bdbdbd"),
                    ], expand=True),
                    ft.Text(f"{segno}€ {importo:.2f}", color=colore_testo, weight=ft.FontWeight.BOLD, size=16),
                    ft.Row([btn_modifica, btn_elimina], spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=sfondo_riga,
                padding=12,
                border_radius=8
            )
            lista_storico.controls.append(riga_elemento)

        lbl_saldo_bcc.value = f"€ {effettivo_bcc:.2f}"
        lbl_proiettato_bcc.value = f"€ {proiettato_bcc:.2f}"
        lbl_saldo_hype.value = f"€ {effettivo_hype:.2f}"
        lbl_proiettato_hype.value = f"€ {proiettato_hype:.2f}"

        effettivo_totale = effettivo_bcc + effettivo_hype
        proiettato_totale = proiettato_bcc + proiettato_hype
        lbl_saldo_totale.value = f"€ {effettivo_totale:.2f}"
        lbl_proiettato_totale.value = f"€ {proiettato_totale:.2f}"

        container_avvisi.content = sezione_avvisi
        page.update()

    def salva_movimento(e):
        if not txt_importo.value:
            page.snack_bar = ft.SnackBar(ft.Text("Inserisci un importo valido!"))
            page.snack_bar.open = True
            page.update()
            return
        
        try:
            importo = float(txt_importo.value.replace(",", "."))
            ripetizione = int(txt_ripetizione.value)
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Errore nel formato dell'importo o dei mesi!"))
            page.snack_bar.open = True
            page.update()
            return

        cat_val = dd_categoria.value if dd_categoria.value else ""
        data_iniziale_str = txt_data.value.strip()

        try:
            data_base = datetime.strptime(data_iniziale_str, "%Y-%m-%d")
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Formato data errato! Usa YYYY-MM-DD (es. 2026-09-12)"))
            page.snack_bar.open = True
            page.update()
            return

        conn = sqlite3.connect("gestione_finanziaria_avanzata.db")
        cursor = conn.cursor()

        if modifica_id_val[0] is None:
            for i in range(ripetizione):
                anno_i = data_base.year + (data_base.month - 1 + i) // 12
                mese_i = (data_base.month - 1 + i) % 12 + 1
                giorno_i = data_base.day
                
                try:
                    data_rata_dt = datetime(anno_i, mese_i, giorno_i)
                except ValueError:
                    if mese_i == 12:
                        data_rata_dt = datetime(anno_i + 1, 1, 1) - timedelta(days=1)
                    else:
                        data_rata_dt = datetime(anno_i, mese_i + 1, 1) - timedelta(days=1)

                data_rata = data_rata_dt.strftime("%Y-%m-%d")

                cursor.execute("""
                    INSERT INTO transazioni (conto, tipo, importo, categoria, descrizione, mesi_ripetizione, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (dd_conto.value, dd_tipo.value, importo, cat_val, txt_descrizione.value, ripetizione, data_rata))
        else:
            cursor.execute("""
                UPDATE transazioni 
                SET conto = ?, tipo = ?, importo = ?, categoria = ?, descrizione = ?, mesi_ripetizione = ?, data = ?
                WHERE id = ?
            """, (dd_conto.value, dd_tipo.value, importo, cat_val, txt_descrizione.value, ripetizione, data_iniziale_str, modifica_id_val[0]))
            modifica_id_val[0] = None
            lbl_titolo_form.value = "Aggiungi / Modifica Movimento Programmato"
            txt_btn_salva.value = "Salva Movimento"

        conn.commit()
        conn.close()

        txt_importo.value = ""
        txt_descrizione.value = ""
        txt_ripetizione.value = "1"
        txt_data.value = data_corrente_odierna.strftime('%Y-%m-%d')
        
        carica_dati()

    txt_btn_salva = ft.Text("Salva Movimento")
    btn_salva = ft.ElevatedButton(
        content=txt_btn_salva,
        on_click=salva_movimento,
        bgcolor="#2e7d32",
        color="white"
    )

    sezione_storico = ft.ExpansionTile(
        title=ft.Text("Storico Movimenti dell'Anno Selezionato", size=18, weight=ft.FontWeight.BOLD),
        bgcolor="#1e2530",
        collapsed_bgcolor="#181f29",
        controls=[
            ft.Container(
                content=lista_storico,
                padding=10
            )
        ]
    )

    page.add(
        ft.Text("Gestione Spese & Tasse Multi-Conto", size=24, weight=ft.FontWeight.BOLD),
        container_avvisi,
        ft.Row([dd_filtro_anno], alignment=ft.MainAxisAlignment.END),
        ft.Row([card_bcc, card_hype, card_totale], spacing=15),
        ft.Divider(height=20, color="transparent"),
        lbl_titolo_form,
        ft.Row([dd_conto, dd_tipo, txt_importo], spacing=15),
        ft.Row([dd_categoria, txt_descrizione], spacing=15),
        ft.Row([txt_data, txt_ripetizione], spacing=15),
        ft.Row([txt_nuova_cat, btn_aggiungi_cat], spacing=15),
        ft.Row([btn_salva], spacing=15),
        ft.Divider(height=20, color="transparent"),
        sezione_storico
    )

    carica_dati()

ft.run(main)

import flet as ft
import sqlite3
import datetime
import os
import sys

# Configurazione del Database
DB_NAME = "spese.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            importo REAL,
            categoria TEXT,
            descrizione TEXT,
            tipo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "App Finanziaria"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK

    init_db()

    # Elementi dell'interfaccia
    txt_importo = ft.TextField(label="Importo (€)", keyboard_type=ft.KeyboardType.NUMBER)
    txt_categoria = ft.TextField(label="Categoria (es. Spesa, Stipendio)")
    txt_descrizione = ft.TextField(label="Descrizione")
    
    dropdown_tipo = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option("Uscita"),
            ft.dropdown.Option("Entrata"),
        ],
        value="Uscita"
    )

    lista_transazioni = ft.ListView(expand=1, spacing=10, padding=10, auto_scroll=True)
    txt_saldo = ft.Text("Saldo: 0.00 €", size=20, weight=ft.FontWeight.BOLD)

    def carica_dati():
        lista_transazioni.controls.clear()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, importo, categoria, descrizione, tipo FROM transazioni ORDER BY id DESC")
        righe = cursor.fetchall()
        
        entrate_totali = 0.0
        uscite_totali = 0.0

        for riga in righe:
            id_t, data, importo, categoria, descrizione, tipo = riga
            
            if tipo == "Entrata":
                entrate_totali += importo
                colore = ft.colors.GREEN
                segno = "+"
            else:
                uscite_totali += importo
                colore = ft.colors.RED
                segno = "-"

            # Elemento grafico per la transazione
            item = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.ARROW_FORWARD_IOS, color=colore),
                            title=ft.Text(f"{segno} {importo:.2f} € - {categoria}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"{descrizione} ({data})"),
                        ),
                    ]),
                    padding=10
                )
            )
            lista_transazioni.controls.append(item)

        saldo_finale = entrate_totali - uscite_totali
        txt_saldo.value = f"Saldo: {saldo_finale:.2f} €"
        if saldo_finale >= 0:
            txt_saldo.color = ft.colors.GREEN
        else:
            txt_saldo.color = ft.colors.RED

        conn.close()
        page.update()

    def aggiungi_transazione(e):
        try:
            importo = float(txt_importo.value.replace(",", "."))
            categoria = txt_categoria.value if txt_categoria.value else "Generale"
            descrizione = txt_descrizione.value if txt_descrizione.value else ""
            tipo = dropdown_tipo.value
            data = datetime.date.today().strftime("%Y-%m-%d")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transazioni (data, importo, categoria, descrizione, tipo) VALUES (?, ?, ?, ?, ?)",
                (data, importo, categoria, descrizione, tipo)
            )
            conn.commit()
            conn.close()

            # Pulisci i campi
            txt_importo.value = ""
            txt_categoria.value = ""
            txt_descrizione.value = ""
            
            carica_dati()
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Inserisci un importo valido!"))
            page.snack_bar.open = True
            page.update()

    btn_aggiungi = ft.ElevatedButton(text="Aggiungi Transazione", on_click=aggiungi_transazione, icon=ft.icons.ADD)

    # Layout principale della pagina
    page.add(
        ft.Row([txt_saldo], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        txt_importo,
        dropdown_tipo,
        txt_categoria,
        txt_descrizione,
        btn_aggiungi,
        ft.Divider(),
        ft.Text("Ultime Transazioni:", weight=ft.FontWeight.BOLD),
        lista_transazioni
    )

    carica_dati()

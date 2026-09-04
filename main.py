import flet as ft
import re

# ==========================================
# LOGICA PARSER NOTIFICHE HYPE & FILTRO SALDO
# ==========================================

def parse_hype_notification(notification_text: str):
    """
    Analizza la notifica Hype intercettando qualsiasi tipo di rifiuto 
    o fallimento ed estraendo i dati solo se la transazione è andata a buon fine.
    """
    testo = notification_text.strip()
    testo_lower = testo.lower()
    
    # 1. Lista estesa di termini che indicano un rifiuto o un blocco della transazione
    parole_rifiuto = [
        "pagamento rifiutato", 
        "transazione rifiutata", 
        "non autorizzato", 
        "operazione rifiutata",
        "pagamento non riuscito",
        "fallito"
    ]
    
    if any(termine in testo_lower for termine in parole_rifiuto):
        return {
            "stato": "rifiutato",
            "valido": False,
            "messaggio_originale": testo
        }

    # 2. Estrazione dell'importo per i pagamenti andati a buon fine (es. 9.73 € o 9,73 €)
    importo_match = re.search(r"(\d+[\.,]\d{2})\s*€", testo)
    if not importo_match:
        importo_match = re.search(r"€\s*(\d+[\.,]\d{2})", testo)
        
    if importo_match:
        importo_str = importo_match.group(1).replace(",", ".")
        importo = float(importo_str)
        
        return {
            "stato": "completato",
            "valido": True,
            "importo": importo,
            "messaggio_originale": testo
        }
        
    return None


def calcola_saldo_effettivo(lista_transazioni):
    """
    Calcola il saldo escludendo i mancati addebiti o transazioni non valide.
    """
    saldo = 0.0
    for t in lista_transazioni:
        # Consideriamo solo le transazioni valide ed escludiamo quelle rifiutate
        if t.get("valido", True) and t.get("stato") != "rifiutato":
            importo = t.get("importo", 0.0)
            tipo = t.get("tipo", "uscita")
            
            if tipo == "uscita":
                saldo -= importo
            elif tipo == "entrata":
                saldo += importo
                
    return saldo


# ==========================================
# APPLICAZIONE FLET (INTERFACCIA GRAFICA)
# ==========================================

def main(page: ft.Page):
    page.title = "App Finanziaria Personale"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Esempio di transazioni iniziali (inclusa una transazione rifiutata di prova)
    transazioni = [
        {"descrizione": "Spesa Supermercato", "importo": 45.50, "tipo": "uscita", "valido": True, "stato": "completato"},
        {"descrizione": "Benzina Distributore", "importo": 9.73, "tipo": "uscita", "valido": False, "stato": "rifiutato"} # Non deve intaccare il saldo
    ]

    # Calcolo iniziale del saldo pulito
    saldo_corrente = calcola_saldo_effettivo(transazioni)

    # Elementi visivi
    txt_saldo = ft.Text(f"Saldo Attuale: {saldo_corrente:.2f} €", size=24, weight=ft.FontWeight.BOLD)
    
    txt_notifica_test = ft.Text("Test Notifica Hype: In attesa...", italic=True)
    list_view_transazioni = ft.ListView(expand=1, spacing=10, padding=20)

    def aggiorna_lista_interfaccia():
        list_view_transazioni.controls.clear()
        for t in transazioni:
            colore = ft.colors.RED if t["tipo"] == "uscita" and t["valido"] else ft.colors.GREEN
            if not t["valido"]:
                colore = ft.colors.GREY
                testo_voce = f"[RIFIUTATO] {t.get('messaggio_originale', 'Transazione bloccata')}"
            else:
                testo_voce = f"{t['descrizione']}: -{t['importo']} €" if t["tipo"] == "uscita" else f"{t['descrizione']}: +{t['importo']} €"
            
            list_view_transazioni.controls.append(ft.Text(testo_voce, color=colore))
        
        txt_saldo.value = f"Saldo Attuale: {calcola_saldo_effettivo(transazioni):.2f} €"
        page.update()

    aggiorna_lista_interfaccia()

    # Pulsante di simulazione arrivo notifica Hype (es. distributore rifiutato)
    def simula_notifica_rifiutata(e):
        notifica_simulata = "Pagamento rifiutato\n01 lug - 10:57\nDIESSE SRL\n- 9.73 €\nRiprova inserendo la carta nel POS"
        risultato_parser = parse_hype_notification(notifica_simulata)
        
        if risultato_parser:
            transazioni.append({
                "descrizione": "Tentativo Carburante",
                "importo": risultato_parser.get("importo", 9.73),
                "tipo": "uscita",
                "valido": risultato_parser["valido"],
                "stato": risultato_parser["stato"],
                "messaggio_originale": risultato_parser["messaggio_originale"]
            })
            txt_notifica_test.value = "Ultima notifica: Rifiutata ed esclusa dal saldo correttamente!"
            aggiorna_lista_interfaccia()

    btn_simula = ft.ElevatedButton(text="Simula Notifica Hype Rifiutata", on_click=simula_notifica_rifiutata)

    page.add(
        txt_saldo,
        ft.Divider(),
        btn_simula,
        txt_notifica_test,
        ft.Divider(),
        ft.Text("Storico Transazioni:", weight=ft.FontWeight.BOLD),
        list_view_transazioni
    )

if __name__ == "__main__":
    ft.app(target=main)

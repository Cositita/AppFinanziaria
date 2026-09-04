import flet as ft
import re

# ==========================================
# LOGICA PARSER NOTIFICHE HYPE (CON FILTRO ANTIRICARICA TELEFONICA)
# ==========================================

def parse_hype_notification(notification_text: str):
    """
    Analizza qualsiasi notifica Hype in modo sicuro:
    - Intercetta i rifiuti ed esclude la spesa.
    - Distingue correttamente tra ricarica del conto (entrata) e ricarica telefonica (uscita).
    - Estrae automaticamente l'importo e la descrizione.
    """
    if not notification_text:
        return None
        
    testo = notification_text.strip()
    testo_lower = testo.lower()
    
    # 1. Controllo di sicurezza per pagamenti non riusciti / rifiutati
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
            "descrizione": "Transazione Rifiutata",
            "importo": 0.0,
            "tipo": "uscita",
            "stato": "rifiutato",
            "valido": False,
            "messaggio_originale": testo
        }

    # 2. Estrazione flessibile dell'importo (es. 15,00 € oppure 30.00€)
    importo_match = re.search(r"(\d+[\.,]\d{2})\s*€", testo)
    if not importo_match:
        importo_match = re.search(r"€\s*(\d+[\.,]\d{2})", testo)
        
    if importo_match:
        importo_str = importo_match.group(1).replace(",", ".")
        importo = float(importo_str)
        
        # 3. Gestione intelligente della direzione (Entrata vs Uscita)
        # Se c'è una ricarica ma riguarda telefonia o operatori, è un'USCITA.
        operatori_telefonici = ["tim", "vodafone", "wind", "tre", "iliad", "ho.", "fastweb", "kasko", "cellulare", "telefono"]
        
        is_telefonica = any(op in testo_lower for op in operatori_telefonici) and "ricarica" in testo_lower
        
        if is_telefonica:
            tipo_transazione = "uscita"
        else:
            # Parole che indicano una vera entrata di soldi sul conto
            parole_entrata = ["accredito", "ricarica conto", "ricevuto", "bonifico da", "stipendio", "rimborso"]
            tipo_transazione = "entrata" if any(p in testo_lower for p in parole_entrata) else "uscita"
        
        # Pulizia della descrizione rimuovendo l'importo
        descrizione_pulita = re.sub(r"(\d+[\.,]\d{2})\s*€|€\s*(\d+[\.,]\d{2})", "", testo).strip()
        if not descrizione_pulita:
            descrizione_pulita = "Ricarica Telefonica" if tipo_transazione == "uscita" and is_telefonica else "Spesa Hype"
            
        return {
            "descrizione": descrizione_pulita,
            "importo": importo,
            "tipo": tipo_transazione,
            "stato": "completato",
            "valido": True,
            "messaggio_originale": testo
        }
        
    return None


def calcola_saldo_effettivo(lista_transazioni):
    """
    Calcola il saldo sommando le entrate e sottraendo le uscite valide.
    """
    saldo = 0.0
    for t in lista_transazioni:
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

    # Esempio di transazioni iniziali
    transazioni = [
        {"descrizione": "Spesa Supermercato", "importo": 45.50, "tipo": "uscita", "valido": True, "stato": "completato"},
        {"descrizione": "Accredito da Mario", "importo": 50.00, "tipo": "entrata", "valido": True, "stato": "completato"}
    ]

    saldo_corrente = calcola_saldo_effettivo(transazioni)

    txt_saldo = ft.Text(f"Saldo Attuale: {saldo_corrente:.2f} €", size=24, weight=ft.FontWeight.BOLD)
    txt_notifica_test = ft.Text("Test Notifica Hype: In attesa...", italic=True)
    list_view_transazioni = ft.ListView(expand=1, spacing=10, padding=20)

    def aggiorna_lista_interfaccia():
        list_view_transazioni.controls.clear()
        for t in transazioni:
            if not t["valido"]:
                colore = ft.colors.GREY
                testo_voce = f"[RIFIUTATO] {t.get('messaggio_originale', 'Transazione bloccata')}"
            elif t["tipo"] == "entrata":
                colore = ft.colors.GREEN
                testo_voce = f"{t['descrizione']}: +{t['importo']} €"
            else:
                colore = ft.colors.RED
                testo_voce = f"{t['descrizione']}: -{t['importo']} €"
            
            list_view_transazioni.controls.append(ft.Text(testo_voce, color=colore))
        
        txt_saldo.value = f"Saldo Attuale: {calcola_saldo_effettivo(transazioni):.2f} €"
        page.update()

    aggiorna_lista_interfaccia()

    # Pulsanti di simulazione per testare i vari casi (inclusa la ricarica telefonica)
    def simula_ricarica_telefonica(e):
        notifica = "Hype ricarica Vodafone 15,00 €"
        res = parse_hype_notification(notifica)
        if res:
            transazioni.append(res)
            txt_notifica_test.value = f"Ricarica telefonica gestita come Uscita: -{res['importo']}€"
            aggiorna_lista_interfaccia()

    btn_tel = ft.ElevatedButton(text="Simula Ricarica Vodafone (Uscita)", on_click=simula_ricarica_telefonica)

    page.add(
        txt_saldo,
        ft.Divider(),
        btn_tel,
        txt_notifica_test,
        ft.Divider(),
        ft.Text("Storico Transazioni:", weight=ft.FontWeight.BOLD),
        list_view_transazioni
    )

if __name__ == "__main__":
    ft.app(target=main)

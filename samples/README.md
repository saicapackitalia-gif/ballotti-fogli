# Foto di test

Cartella per le foto reali usate per validare il prototipo.

Per ogni foto che aggiungete, indicate qui sotto (o nel nome del file) almeno:

- **profilo onda** (B, E, C, EB, BC...)
- **altezza reale nota di una singola fila** in mm (misura fisica, non dal
  cartellino: il cartellino spesso riporta la quantità totale su più file
  affiancate, non quella di una fila sola)
- **conteggio manuale reale per singola fila**, se disponibile

Calibrazione: tutte le foto hanno un foglio A4 appoggiato accanto alla fila,
usato come riferimento di scala (rilevato automaticamente per luminosità/
saturazione, verificato controllando che il rapporto lati misurato torni
vicino a 210/297 = 0,707).

## Foto caricate

| File | Cliente | Profilo | Altezza reale fila (mm) | Altezza misurata (mm) | Errore altezza | Stima per divisione | Stima per conteggio righe | Note |
|------|---------|---------|--------------------------|-------------------------|----------------|----------------------|------------------------------|------|
| SAMO - 970mm.jfif | SAMO | EB | 970 | 975,8 | **+0,6%** | 229 fogli | 326 fogli (+42% vs atteso) | Camera quasi perpendicolare: miglior risultato finora, valida il metodo di calibrazione A4 |
| SAMO - 1110mm.jfif | SAMO | C | 1110 | 992,1 | -10,6% | 242 fogli | 345 fogli | Il foglio A4 appare visibilmente trapezoidale in foto (angolo di ripresa più marcato): probabile causa dell'errore maggiore sull'altezza |
| ICM - 1180mm.jfif | ICM | B | 1180 | — | — | — | — | Bordo superiore della fila fuori inquadratura (confermato: la texture arriva fino al bordo della foto senza soluzione di continuità) — non misurabile |
| c9d645df...jfif (Biellese) | Biellese | BC | 1110 | 1110 (corretta a mano) | — | 165 | 199 | Prima lettura errata (1007,5mm, bordo superiore cliccato male) poi corretta; 170 fogli reali noti da conferma utente |
| 60038ca9...jfif (Princes) | Princes Ready to Drink | B | — | — | — | — | — | Bordo superiore fuori inquadratura, come ICM |

### Regola pratica emersa: come leggere il "bordo superiore"

Quando la camera non è perfettamente perpendicolare, si vede una sottile fascia
della superficie superiore del ballotto (in prospettiva) prima del vero taglio
frontale. Usare il punto **più alto visibile della sagoma del ballotto**
(non il punto dove inizia la trama frontale verticale) dà risultati migliori:
su SAMO EB questo ha prodotto un errore di solo 0,6%. Più la foto è vicina
alla perpendicolare, meno questa scelta influisce e più il risultato è
affidabile — coerente con quanto raccomandato nella guida allo scatto.

### Conclusione sul metodo per conteggio righe

Su tutti e 4 i casi misurabili finora, il conteggio per righe **sovrastima
sistematicamente** (dal +17% al +43%). Non è un problema di taratura fine:
serve rivedere l'algoritmo di rilevamento picchi (probabilmente conta più
picchi per singolo foglio), non solo i suoi parametri. Il metodo per
divisione resta l'unico affidabile allo stato attuale, a condizione di
leggere correttamente l'altezza (foto con camera perpendicolare e bordo
superiore interamente in inquadratura).

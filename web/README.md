# Conta Fogli — app web per telefono

Pagina singola (HTML + CSS + JS, nessuna dipendenza esterna da installare)
che fa girare nel browser del telefono la stessa logica di calibrazione e
conteggio del prototipo Python in `src/ballotti_fogli/`, senza bisogno di
Python sul telefono.

## Uso

Apri `conta-fogli.html` in un browser (anche solo facendo doppio click dal
telefono, o pubblicandolo come pagina statica). Non serve un server: legge
la foto localmente con FileReader/Canvas.

Flusso:
1. Scegli il profilo onda (spessore modificabile) e inserisci la larghezza
   nota di riferimento (larghezza di una fila, o un oggetto come un
   righello).
2. Carica/scatta la foto.
3. Calibrazione: tocca con precisione i 2 estremi del riferimento (con
   lente d'ingrandimento per centrare il punto).
4. Fila: traccia una linea lungo il bordo superiore e una lungo il bordo
   inferiore della fila da contare.
5. Risultato: altezza stimata e fogli per divisione (spessore).

## Limiti noti (vedi anche i messaggi di avviso nell'app)

- **Nessuna correzione prospettica**: a differenza della modalità
  `--auto-a4` del prototipo Python (omografia da 4 angoli), questa versione
  usa una calibrazione scalare semplice da una sola misura nota. Precisione
  buona con camera perpendicolare, peggiora su foto storte.
- **Aggancio automatico al bordo**: presente come opzione sperimentale
  (disattivata di default) nel passo di misura della fila. In un test reale
  si è agganciato a un bordo sbagliato ma più marcato (una riga di
  segnaletica a terra) invece del vero bordo del ballotto — va usato solo
  controllando a vista dove finisce la linea dopo l'aggancio, non è
  affidabile come default.
- **Metodo per conteggio righe**: mostrato solo per trasparenza nel
  risultato finale. Su tutte le foto reali testate finora sovrastima in
  modo sistematico (dal +17% al +43%): non fidatevi di quel numero, solo
  di quello per divisione.
- Nessun salvataggio di uno storico misure tra una foto e l'altra.

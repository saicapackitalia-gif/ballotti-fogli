# Ballotti Fogli — Conteggio automatico fogli da foto

Prototipo per stimare il **numero di fogli di cartone ondulato per fila/ballotto**
a partire da una foto della testata (il lato tagliato dove si vedono gli strati),
usando l'altezza media nota del profilo d'onda.

> Stato: **prototipo/MVP** in Python + OpenCV, da validare sul campo prima di
> qualsiasi uso in produzione o per decisioni contabili/di magazzino.

## 1. Risposta diretta: può funzionare?

**Sì, con riserve.** È un problema di visione artificiale ben noto (analogo al
conteggio di fogli di carta o assi di legno in pacco), tecnicamente fattibile
con un budget di sviluppo contenuto, ma la precisione dipende in modo critico
da alcuni fattori che vanno gestiti esplicitamente (vedi §4).

Esistono due strategie, non mutuamente esclusive:

1. **Metodo per divisione (altezza / spessore medio)**
   `numero_fogli ≈ altezza_ballotto_mm / altezza_media_onda_mm`
   Semplice, robusto, ma l'errore cresce linearmente con l'altezza del
   ballotto se lo spessore medio usato non è rappresentativo del lotto reale
   (umidità, pressatura, reggette che comprimono la pila, tolleranze di
   produzione della carta/onda).

2. **Metodo per conteggio righe (image processing sul bordo)**
   Rilevamento dei singoli strati/creste dell'onda visibili sul taglio,
   tramite analisi del profilo di intensità/gradiente lungo l'altezza della
   pila (edge detection + ricerca di picchi). Più preciso in teoria perché
   non dipende da uno spessore "medio" ma conta gli strati realmente
   visibili, ma più sensibile a: illuminazione, sfocatura, polvere, righe non
   perfettamente parallele, fogli molto sottili (onda E/F) che a fila alta
   diventano difficili da distinguere otticamente.

Questo prototipo implementa **entrambi** e li confronta: se i due valori
sono in disaccordo oltre una soglia, l'app segnala bassa confidenza invece di
restituire un numero silenziosamente sbagliato.

## 1bis. "Punto la fotocamera e basta, il sistema capisce l'altezza da solo?"

**Risposta diretta: no, non da una singola foto scattata a mano libera a
distanza/angolo qualsiasi.** Una fotocamera 2D non ha modo di sapere quanti
millimetri reali corrisponde un pixel se non conosce almeno uno tra: la
distanza dal soggetto + i parametri ottici della camera (lunghezza focale,
dimensione sensore), oppure un oggetto di dimensione nota nell'inquadratura,
oppure un sensore di profondità. Senza uno di questi, "20 cm di ballotto" e
"2 metri di ballotto fotografati da più lontano" producono la stessa
immagine.

Opzioni concrete, in ordine di praticità per un contesto industriale:

1. **Larghezza di taglio nota della commessa (consigliata nel vostro caso)**
   — le foto non vengono scattate da una postazione fissa, quindi la
   calibrazione va rifatta ad ogni scatto. Non serve però portare un
   oggetto fisico di riferimento: se la foto inquadra per intero la
   larghezza della fila (i due bordi laterali), e quella larghezza è un
   dato già noto dalla commessa/ordine di produzione, si può usare
   **quella stessa larghezza come riferimento**, cliccando i due bordi
   laterali invece degli estremi di un righello. Zero oggetti da portare o
   posizionare. È già supportato nel prototipo (vedi §6) usando
   `--ref-length-mm` con il valore della larghezza di commessa e cliccando
   i bordi laterali della fila invece che un oggetto esterno.
   **Attenzione**: vale solo se quella larghezza è affidabile nella foto
   specifica — misuratela in un punto dove la pila è ben squadrata (es.
   alla base, dove il peso allinea i fogli), non in un punto dove i fogli
   sono visibilmente sfalsati o rigonfi, altrimenti la larghezza apparente
   non corrisponde più al dato di commessa.

2. **Riferimento fisico portato ad ogni scatto** (righello, foglio A4,
   tessera) — da usare se la larghezza della fila non è sempre visibile per
   intero o non è abbastanza affidabile. Stesso meccanismo di calibrazione
   dell'opzione 1, cambia solo cosa si clicca. Anche questa già supportata
   in §6.

3. **Postazione fissa** — utile solo se in futuro si rendesse disponibile
   un punto di scatto fisso (staffa/cavalletto): la calibrazione andrebbe
   fatta una sola volta invece che ad ogni foto (vedi `--save-calibration`
   / `--calibration-file` in §6). Non applicabile al vostro flusso attuale,
   dato che le foto non sono scattate da un punto fisso.

4. **Riferimento fisso nell'inquadratura, rilevato automaticamente** — es.
   un marker stampato (tipo ArUco/QR) rilevato via software invece che
   cliccato a mano. Toglie il click manuale ma richiede comunque un
   oggetto fisico in ogni foto; non è ancora implementato in questo
   prototipo (vedi §7).

5. **API di realtà aumentata dello smartphone (ARKit su iOS, ARCore su
   Android)** — usano fusione di camera + sensori di movimento (e, sugli
   iPhone Pro con LiDAR, un sensore di profondità dedicato) per stimare
   distanze reali senza marker fisico né posizione fissa. Precisione: buona
   (ordine del mm-cm) sui modelli con LiDAR, più incerta (cm) sui modelli
   che usano solo visual-inertial odometry. Richiede però di sviluppare
   un'app nativa (Swift/Kotlin) invece di un semplice upload foto, quindi
   è un impegno di sviluppo nettamente maggiore.

**Raccomandazione pratica per il vostro caso**: dato che non avete una
postazione fissa, l'opzione 1 (larghezza di commessa come riferimento) è la
più conveniente perché non richiede nessun oggetto fisico aggiuntivo — a
patto di validare che la larghezza apparente nella foto corrisponda davvero
al dato di commessa su un campione di prova prima di fidarsene.

## 2. Requisiti indispensabili per un risultato utilizzabile

- **Riferimento di scala nella foto**: un oggetto di lunghezza nota (righello,
  target stampato, distanziale) nello stesso piano della testata del
  ballotto. Senza calibrazione pixel→mm ogni misura di altezza è arbitraria.
- **Camera ragionevolmente perpendicolare** alla superficie fotografata se si
  usa la calibrazione semplice (`--ref-length-mm`/`--rows`): la prospettiva
  (foto in diagonale) distorce le distanze e introduce errore sistematico.
  La modalità `--auto-a4` (§6, Modalità C) rilassa molto questo vincolo:
  corregge la distorsione prospettica invece di ignorarla, quindi tollera
  foto scattate storte/in angolo — vedi i test reali in §4.
- **Illuminazione uniforme e messa a fuoco**: ombre dure o foto mosse
  peggiorano molto il metodo per conteggio righe.
- **Altezze medie per profilo d'onda misurate da voi**: già inserite in
  `config/flute_profiles.yaml` con i valori forniti (B 2,87 mm, E 1,64 mm,
  C 4,1 mm, EB 4,26 mm, BC 6,73 mm — per foglio). Sono dati vostri, non di
  letteratura: aggiornateli se cambiano fornitore carta, grammatura o
  taratura del corrugatore.

## 3. Come è strutturato il prototipo

```
src/ballotti_fogli/
  calibration.py           # Calibration (mm/px scalare) e PlaneCalibration (omografia)
  reference_detection.py   # rilevamento automatico del foglio A4 (per PlaneCalibration)
  linecount.py             # rilevamento righe/creste onda lungo un profilo 1D
  counting.py              # combina calibrazione + spessore medio + conteggio righe
  cli.py                   # interfaccia a riga di comando (selezione punti a click)
config/
  flute_profiles.example.yaml   # template da copiare e compilare con i vostri dati
tests/
  test_calibration.py
  test_linecount.py
samples/
  README.md   # tabella di confronto tra stime e misure reali sulle foto di test
```

## 4. Limiti noti / incertezze, e cosa dicono i test su foto reali finora

Il prototipo è stato testato su 5 foto reali fornite dall'azienda (vedi
`samples/README.md` per il dettaglio completo). Risultati:

- **Metodo per divisione, foto con camera quasi perpendicolare**: errore di
  altezza dello 0,6% (onda EB) — molto buono.
- **Metodo per divisione, foto con angolo di ripresa marcato (foglio A4
  visibilmente trapezoidale)**: con la calibrazione scalare semplice
  l'errore sale al -10,6% (onda C). Con la rettifica prospettica automatica
  (`--auto-a4`, Modalità C) lo stesso scatto scende a **-2,2%** — la
  correzione della prospettiva funziona, ma non elimina completamente
  l'errore (restano a incidere l'imprecisione nel cliccare i bordi della
  fila e possibili distorsioni ottiche dell'obiettivo, non corrette da
  un'omografia). Su una foto già quasi perpendicolare, invece, la rettifica
  prospettica può essere leggermente **peggiore** dello scalare semplice
  (5,4% contro 0,6% su EB): l'omografia è più sensibile a piccole
  imprecisioni nel rilevare i 4 angoli del foglio quando c'è poca vera
  prospettiva da correggere. **Indicazione pratica**: usare `--auto-a4`
  quando la foto è visibilmente storta/in diagonale; per scatti già ben
  frontali la calibrazione scalare va bene così.
- **2 foto su 5 non erano misurabili**: bordo superiore della fila fuori
  inquadratura (confermato verificando che la texture del cartone arriva
  fino al bordo immagine senza soluzione di continuità). Nessuna
  calibrazione, per quanto accurata, può recuperare un'altezza non
  fotografata: va sempre verificato che l'intera fila entri nell'inquadratura.
- **Il metodo per conteggio righe sovrastima sistematicamente su tutti i
  casi reali testati finora** (dal +17% al +43%). Non è un problema di
  soglie da regolare fine: l'algoritmo di rilevamento picchi va rivisto.
  **Allo stato attuale non è affidabile**: usate il metodo per divisione
  come stima principale.
- La reggetta che stringe il ballotto comprime leggermente i fogli vicino
  alla legatura: l'altezza misurata lì non è rappresentativa dell'altezza
  "a riposo" usata per calibrare lo spessore medio.
- Il sistema non stima automaticamente un margine d'errore statistico:
  riporta le due stime e la loro differenza, ma la decisione se fidarsi va
  presa da un operatore, almeno nella fase di validazione iniziale.
- Prima di usare i numeri per aggiustare bolle, fatture o giacenze di
  magazzino, fate una campagna di confronto tra conteggio manuale e
  automatico su un campione più ampio per misurare l'errore reale nel
  vostro contesto — 5 foto bastano per una prima validazione, non per
  certificare l'accuratezza del sistema.

## 5. Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 6. Uso (prototipo a riga di comando)

`config/flute_profiles.yaml` contiene già le altezze medie fornite
dall'azienda (B, E, C, EB, BC); aggiornatelo se cambiano.

### Modalità A1 — larghezza di commessa come riferimento (consigliata per voi)

Se la foto inquadra per intero la larghezza della fila e conoscete la
larghezza di taglio della commessa (es. 800 mm):

```bash
python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --ref-length-mm 800
```

Lo script apre due finestre interattive:
1. cliccate i **due bordi laterali della fila** (non un oggetto esterno) —
   la larghezza nota di commessa fa da riferimento per calibrare mm/pixel;
2. cliccate il punto in alto e il punto in basso della fila di fogli da
   contare.

Va rifatto ad ogni foto (la calibrazione non si riusa da uno scatto
all'altro), ma non richiede alcun oggetto fisico da portare o posizionare.

### Modalità A2 — oggetto fisico di riferimento ad ogni foto

Da usare quando la larghezza della fila non è visibile per intero o non è
abbastanza affidabile in quello scatto:

```bash
python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --ref-length-mm 100
```

Stessa procedura della A1, ma al primo click si indicano i due estremi di
un oggetto di riferimento (es. un righello da 100 mm) invece dei bordi
della fila.

### Modalità C — rettifica prospettica automatica (foto storte/in diagonale)

Da usare quando non potete garantire uno scatto perfettamente frontale
(es. operatore che scatta a mano, in fretta, da un'angolazione qualunque).
Richiede un foglio A4 appoggiato accanto alla fila, sullo stesso piano del
taglio:

```bash
python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --auto-a4
```

Lo script apre due finestre interattive:
1. cliccate **due angoli approssimativi opposti** del foglio A4 (basta
   indicare l'area, non serve precisione: il programma poi trova da solo
   i 4 angoli esatti dentro quella zona);
2. cliccate il punto in alto e il punto in basso della fila di fogli da
   contare.

A differenza delle modalità A1/A2 (un solo rapporto mm/pixel), qui il
programma calcola una trasformazione prospettica completa dai 4 angoli del
foglio, che corregge la distorsione dovuta all'inclinazione della camera,
non solo la scala. Se il foglio rilevato ha proporzioni troppo diverse da
un A4 vero (oltre l'8%, es. per una ROI troppo larga che include anche
l'etichetta), il programma si ferma con un errore invece di calibrare in
modo silenziosamente sbagliato.

**Quando conviene rispetto a A1/A2**: se la foto è visibilmente storta (il
foglio A4 appare come un trapezio, non un rettangolo), questa modalità
riduce sensibilmente l'errore (vedi §4). Se la foto è già ben frontale, non
dà benefici certi e può essere leggermente meno precisa della calibrazione
scalare semplice: usatela quando serve, non come default automatico.

### Modalità B — postazione fissa (solo se in futuro disponibile)

Calibrazione una tantum, da rifare solo se si sposta la fotocamera:

```bash
python -m ballotti_fogli.cli foto_calibrazione.jpg \
    --profile C \
    --ref-length-mm 100 \
    --save-calibration config/camera_calibration.yaml
```

Da quel momento, per ogni nuova foto scattata dalla stessa postazione fissa
(stessa distanza/angolo/zoom):

```bash
python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --calibration-file config/camera_calibration.yaml
```

Verrà chiesto solo il click su bordo superiore e inferiore della fila, non
più il riferimento di calibrazione.

### Output

In entrambi i casi l'output riporta: altezza stimata in mm, stima per
divisione, stima per conteggio righe, ed eventuale avviso di bassa
confidenza se le due stime divergono oltre la soglia (default 10%,
configurabile in `flute_profiles.yaml`).

## 6bis. App web per telefono (senza Python)

`web/conta-fogli.html` è una versione della stessa logica (calibrazione +
conteggio per divisione) che gira nel browser del telefono, senza bisogno
di installare Python. Vedi `web/README.md` per uso e limiti — in
particolare: calibrazione scalare semplice (non corregge foto storte come
la modalità `--auto-a4` di questo prototipo) e un aggancio automatico al
bordo sperimentale, disattivato di default perché si è dimostrato capace
di agganciarsi al bordo sbagliato su un test reale.

## 7. Prossimi passi ragionevoli

1. Raccogliere un set di foto reali con conteggio manuale noto (ground
   truth) per misurare l'errore reale dei due metodi sul vostro prodotto.
2. Se l'errore è accettabile, automatizzare la selezione dei punti (rilevamento
   automatico del riferimento e dei bordi del ballotto) per togliere il click
   manuale.
3. Solo a quel punto valutare se e come incapsulare la logica in un'app
   mobile (per scattare la foto direttamente da smartphone in produzione),
   riusando questo stesso algoritmo lato server o embedded.

## Avvertenza

Questo è materiale sperimentale a scopo di prototipazione tecnica. Non è
stato validato in campo. Non usatelo come unica fonte per decisioni
gestionali, contrattuali o contabili senza prima verificarne l'accuratezza
con test comparativi sul vostro processo reale.

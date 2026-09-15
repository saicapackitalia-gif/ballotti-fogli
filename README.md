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

1. **Postazione fissa (consigliata)** — montare il telefono su una staffa/
   cavalletto a distanza e angolo costanti dal ballotto. Si calibra
   **una sola volta** (foto con un riferimento noto, es. un righello) e da
   quel momento ogni foto scattata dalla stessa postazione riusa lo stesso
   rapporto mm/pixel, **senza bisogno di riferimento ad ogni scatto**. È
   l'opzione più economica e affidabile, ed è già supportata nel prototipo
   (vedi `--save-calibration` / `--calibration-file` in §6). Limite: se
   qualcuno sposta il telefono, cambia lo zoom o l'inquadratura, la
   calibrazione salvata non è più valida e va rifatta.

2. **Riferimento fisso nell'inquadratura, rilevato automaticamente** — es.
   un marker stampato (tipo ArUco/QR) attaccato vicino al ballotto,
   rilevato via software invece che cliccato a mano. Toglie il click
   manuale ma richiede comunque un oggetto fisico di riferimento in ogni
   foto; non è ancora implementato in questo prototipo (vedi §7).

3. **API di realtà aumentata dello smartphone (ARKit su iOS, ARCore su
   Android)** — usano fusione di camera + sensori di movimento (e, sugli
   iPhone Pro con LiDAR, un sensore di profondità dedicato) per stimare
   distanze reali senza marker fisico. Precisione: buona (ordine del mm-cm)
   sui modelli con LiDAR, più incerta (cm) sui modelli che usano solo
   visual-inertial odometry. Richiede però di sviluppare un'app nativa
   (Swift/Kotlin) invece di un semplice upload foto, quindi è un impegno
   di sviluppo maggiore rispetto alle opzioni 1-2.

4. **Dimensione nota e costante del ballotto/pallet stesso** (es. se i
   pallet o la larghezza di taglio dei fogli sono sempre standard in
   azienda) — si potrebbe usare quella dimensione orizzontale come
   riferimento implicito invece di un marker fisico. Fattibile ma dipende
   dal fatto che quella dimensione sia davvero sempre costante e ben
   visibile nella foto.

**Raccomandazione pratica**: per un primo rollout in produzione, l'opzione 1
(postazione fissa con calibrazione una tantum) dà il miglior rapporto tra
affidabilità e sforzo di sviluppo, ed è quella già cablata nel prototipo.

## 2. Requisiti indispensabili per un risultato utilizzabile

- **Riferimento di scala nella foto**: un oggetto di lunghezza nota (righello,
  target stampato, distanziale) nello stesso piano della testata del
  ballotto. Senza calibrazione pixel→mm ogni misura di altezza è arbitraria.
- **Camera perpendicolare** alla superficie fotografata: la prospettiva
  (foto in diagonale) distorce le distanze e introduce errore sistematico.
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
  calibration.py   # calcolo mm/pixel da due punti di riferimento noti
  linecount.py      # rilevamento righe/creste onda lungo un profilo 1D
  counting.py       # combina calibrazione + spessore medio + conteggio righe
  cli.py            # interfaccia a riga di comando (selezione punti a click)
config/
  flute_profiles.example.yaml   # template da copiare e compilare con i vostri dati
tests/
  test_calibration.py
  test_linecount.py
```

## 4. Limiti noti / incertezze (da leggere prima di fidarsi del numero)

- Non è stato validato su foto reali di ballotti: questo è un algoritmo di
  riferimento, non un modello già tarato sul vostro prodotto.
- Il metodo per conteggio righe può fallire silenziosamente su onde molto
  sottili (E/F) o pile molto alte con molte righe ravvicinate: in quei casi
  fidatevi di più del metodo per divisione, ma tenete presente il suo limite
  (dipende dallo spessore medio, non dal foglio reale).
- La reggetta che stringe il ballotto comprime leggermente i fogli vicino
  alla legatura: l'altezza misurata lì non è rappresentativa dell'altezza
  "a riposo" usata per calibrare lo spessore medio.
- Il sistema non stima automaticamente un margine d'errore statistico:
  riporta le due stime e la loro differenza, ma la decisione se fidarsi va
  presa da un operatore, almeno nella fase di validazione iniziale.
- Prima di usare i numeri per aggiustare bolle, fatture o giacenze di
  magazzino, fate una campagna di confronto tra conteggio manuale e
  automatico su un campione rappresentativo di ballotti (altezze e profili
  diversi) per misurare l'errore reale nel vostro contesto.

## 5. Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 6. Uso (prototipo a riga di comando)

`config/flute_profiles.yaml` contiene già le altezze medie fornite
dall'azienda (B, E, C, EB, BC); aggiornatelo se cambiano.

### Modalità A — calibrazione manuale ad ogni foto

```bash
python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --ref-length-mm 100
```

Lo script apre due finestre interattive:
1. cliccate i due estremi di un oggetto di riferimento di lunghezza nota
   (es. un righello da 100 mm nella foto) per calibrare mm/pixel;
2. cliccate il punto in alto e il punto in basso della fila di fogli da
   contare.

### Modalità B — postazione fissa (consigliata, niente riferimento ad ogni scatto)

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

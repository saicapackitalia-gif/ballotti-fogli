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

## 2. Requisiti indispensabili per un risultato utilizzabile

- **Riferimento di scala nella foto**: un oggetto di lunghezza nota (righello,
  target stampato, distanziale) nello stesso piano della testata del
  ballotto. Senza calibrazione pixel→mm ogni misura di altezza è arbitraria.
- **Camera perpendicolare** alla superficie fotografata: la prospettiva
  (foto in diagonale) distorce le distanze e introduce errore sistematico.
- **Illuminazione uniforme e messa a fuoco**: ombre dure o foto mosse
  peggiorano molto il metodo per conteggio righe.
- **Altezze medie per profilo d'onda misurate da voi** (come indicato):
  vanno inserite in `config/flute_profiles.yaml`. Il repository **non**
  contiene valori numerici precompilati: i valori di spessore onda variano
  per fornitore carta, grammatura, umidità e taratura del corrugatore, quindi
  usare valori di letteratura generici invece dei vostri dati misurati
  sarebbe un errore. (Per riferimento, in letteratura tecnica FEFCO si
  citano ordini di grandezza indicativi tipo: onda A ~4-5 mm, B ~2-3 mm,
  C ~3,5-4 mm, E ~1,5 mm, F/N <1 mm — ma sono range generici, **non dati da
  usare al posto dei vostri**.)

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

```bash
cp config/flute_profiles.example.yaml config/flute_profiles.yaml
# modificate config/flute_profiles.yaml con le VOSTRE altezze medie misurate

python -m ballotti_fogli.cli foto_ballotto.jpg \
    --profile C \
    --profiles-config config/flute_profiles.yaml \
    --ref-length-mm 100
```

Lo script apre due finestre interattive:
1. cliccate i due estremi di un oggetto di riferimento di lunghezza nota
   (es. un righello da 100 mm nella foto) per calibrare mm/pixel;
2. cliccate il punto in alto e il punto in basso della fila di fogli da
   contare.

L'output riporta: altezza stimata in mm, stima per divisione, stima per
conteggio righe, ed eventuale avviso di bassa confidenza se le due stime
divergono oltre la soglia (default 10%, configurabile).

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

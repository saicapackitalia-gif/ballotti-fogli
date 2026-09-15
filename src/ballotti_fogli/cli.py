"""CLI di prototipo: selezione manuale dei punti di calibrazione e della
fila da misurare tramite click su finestra OpenCV, poi stampa del risultato.
"""
from __future__ import annotations

import argparse
import sys

import cv2
import yaml

from .calibration import calibrate_from_reference, homography_from_quad, load_calibration, save_calibration
from .counting import count_sheets
from .reference_detection import ReferenceNotFoundError, detect_reference_quad


def _pick_two_points(image, window_title: str) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    display = image.copy()

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))
            cv2.circle(display, (x, y), 5, (0, 0, 255), -1)
            if len(points) == 2:
                cv2.line(display, points[0], points[1], (0, 255, 0), 2)
            cv2.imshow(window_title, display)

    cv2.namedWindow(window_title)
    cv2.setMouseCallback(window_title, on_click)
    cv2.imshow(window_title, display)

    print(f"[{window_title}] Cliccare due punti, poi premere un tasto qualsiasi.")
    while len(points) < 2:
        if cv2.waitKey(50) != -1:
            break
    cv2.waitKey(0)
    cv2.destroyWindow(window_title)

    if len(points) != 2:
        raise RuntimeError(f"Selezione non completata per: {window_title}")
    return points


def load_flute_profiles(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stima il numero di fogli per fila da una foto del ballotto."
    )
    parser.add_argument("image", help="Percorso immagine del ballotto")
    parser.add_argument("--profile", required=True, help="Nome profilo onda (deve esistere nel file di configurazione)")
    parser.add_argument(
        "--profiles-config",
        default="config/flute_profiles.yaml",
        help="Percorso file YAML con le altezze medie misurate per profilo",
    )
    parser.add_argument(
        "--ref-length-mm",
        type=float,
        help=(
            "Lunghezza reale nota in mm da usare per calibrare, richiesto se non si usa "
            "--calibration-file. Puo' essere un oggetto fisico di riferimento (righello, A4, "
            "tessera) oppure, se visibile per intero nella foto, la larghezza di taglio nota "
            "del foglio da commessa: in tal caso i due punti da cliccare in fase di "
            "calibrazione sono i due bordi laterali del blocco fotografato, non serve alcun "
            "oggetto fisico. Se nella foto sono legate insieme piu' file affiancate (es. 3 file "
            "da 780 mm per ottimizzare il carico camion), passare qui la larghezza di UNA SOLA "
            "fila e usare --rows per il numero di file, invece di calcolare voi il totale."
        ),
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=1,
        help=(
            "Numero di file affiancate legate insieme nel blocco fotografato (default 1). "
            "Se >1, --ref-length-mm deve essere la larghezza di UNA fila: il programma calcola "
            "da solo la larghezza totale del blocco (ref-length-mm x rows) per calibrare sui "
            "bordi esterni, cliccabili con certezza anche quando le file non hanno una cucitura "
            "visibile tra loro. Richiede che le file abbiano tutte la stessa altezza (stesso "
            "numero di fogli): verificatelo a vista prima di fidarvi del risultato."
        ),
    )
    parser.add_argument(
        "--auto-a4",
        action="store_true",
        help=(
            "Calibrazione robusta a foto storte/in diagonale: individua automaticamente "
            "i 4 angoli di un foglio A4 nella foto e calcola una rettifica prospettica "
            "(omografia) invece di un singolo rapporto mm/pixel. Da preferire quando non "
            "si puo' garantire uno scatto perfettamente perpendicolare. In alternativa a "
            "--ref-length-mm/--calibration-file; non si combina con --rows o "
            "--save-calibration (la rettifica va ricalcolata ad ogni foto)."
        ),
    )
    parser.add_argument(
        "--calibration-file",
        help=(
            "Percorso di una calibrazione salvata in precedenza (vedi --save-calibration). "
            "Da usare SOLO se la foto e' scattata dalla stessa postazione fissa "
            "(stessa distanza/angolo/zoom) usata per generare quella calibrazione: "
            "in tal caso salta la selezione manuale del riferimento."
        ),
    )
    parser.add_argument(
        "--save-calibration",
        help="Se impostato, salva la calibrazione calcolata da --ref-length-mm in questo file per riusarla in seguito",
    )
    args = parser.parse_args(argv)

    if args.auto_a4:
        if args.ref_length_mm is not None or args.calibration_file or args.save_calibration or args.rows != 1:
            print(
                "Errore: --auto-a4 non si combina con --ref-length-mm, --calibration-file, "
                "--save-calibration o --rows.",
                file=sys.stderr,
            )
            return 1
    elif not args.calibration_file and args.ref_length_mm is None:
        print(
            "Errore: specificare --ref-length-mm (calibrazione manuale), --calibration-file "
            "(postazione fissa gia' calibrata) oppure --auto-a4 (rettifica prospettica).",
            file=sys.stderr,
        )
        return 1

    if args.rows < 1:
        print("Errore: --rows deve essere almeno 1.", file=sys.stderr)
        return 1

    config = load_flute_profiles(args.profiles_config)
    profiles = config.get("flute_profiles", {})
    thickness_mm = profiles.get(args.profile)
    if thickness_mm is None:
        print(
            f"Errore: nessuna altezza media configurata per il profilo '{args.profile}' "
            f"in {args.profiles_config}. Compilare il file prima dell'uso.",
            file=sys.stderr,
        )
        return 1

    disagreement_threshold_pct = config.get("disagreement_threshold_pct", 10)

    image = cv2.imread(args.image)
    if image is None:
        print(f"Errore: impossibile leggere l'immagine {args.image}", file=sys.stderr)
        return 1
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if args.auto_a4:
        ref_a, ref_b = _pick_two_points(
            image,
            "Rettifica prospettica: click sui 2 angoli OPPOSTI approssimativi del foglio A4 "
            "(basta indicare l'area, non serve precisione)",
        )
        margin = 40
        x1, x2 = sorted((ref_a[0], ref_b[0]))
        y1, y2 = sorted((ref_a[1], ref_b[1]))
        roi = (
            max(x1 - margin, 0),
            max(y1 - margin, 0),
            min(x2 + margin, image.shape[1]),
            min(y2 + margin, image.shape[0]),
        )
        try:
            quad = detect_reference_quad(image, roi)
        except ReferenceNotFoundError as exc:
            print(f"Errore: {exc}", file=sys.stderr)
            return 1

        calibration = homography_from_quad(quad.corners_px)
        print(
            f"Foglio A4 rilevato: rapporto lati misurato {quad.measured_ratio:.3f} "
            f"(atteso {quad.expected_ratio:.3f}, scarto {quad.ratio_error_pct:.1f}%)"
        )
    elif args.calibration_file:
        calibration = load_calibration(args.calibration_file)
        print(
            f"Uso calibrazione salvata da {args.calibration_file} "
            f"({calibration.mm_per_px:.5f} mm/pixel). "
            "Valida solo se la foto e' dalla stessa postazione fissa usata per calibrare."
        )
    else:
        total_ref_length_mm = args.ref_length_mm * args.rows
        window_title = (
            "Calibrazione: click sui 2 bordi laterali della fila (larghezza nota) "
            "oppure sui 2 estremi di un oggetto di riferimento"
            if args.rows == 1
            else f"Calibrazione: click sui 2 bordi ESTERNI del blocco ({args.rows} file affiancate)"
        )
        if args.rows > 1:
            print(
                f"Larghezza totale del blocco: {args.ref_length_mm:g} mm x {args.rows} file "
                f"= {total_ref_length_mm:g} mm"
            )
        ref_a, ref_b = _pick_two_points(image, window_title)
        calibration = calibrate_from_reference(ref_a, ref_b, total_ref_length_mm)
        if args.save_calibration:
            save_calibration(
                calibration,
                args.save_calibration,
                notes=(
                    f"Calibrato da {args.image} con riferimento di {args.ref_length_mm} mm "
                    f"x {args.rows} file = {total_ref_length_mm} mm"
                ),
            )
            print(f"Calibrazione salvata in {args.save_calibration}")

    p_top, p_bottom = _pick_two_points(image, "Fila da contare: click su bordo superiore e inferiore")

    result = count_sheets(
        gray,
        calibration,
        p_top,
        p_bottom,
        avg_sheet_thickness_mm=float(thickness_mm),
        disagreement_threshold_pct=float(disagreement_threshold_pct),
    )

    print(f"Altezza stimata fila: {result.height_mm:.1f} mm")
    print(f"Stima per divisione (altezza / spessore medio '{args.profile}'): {result.count_by_division} fogli")
    print(f"Stima per conteggio righe: {result.count_by_lines} fogli")
    print(f"Disaccordo tra i due metodi: {result.disagreement_pct:.1f}%")
    if result.low_confidence:
        print(
            "ATTENZIONE: le due stime divergono oltre la soglia configurata. "
            "Verificare manualmente prima di usare questo numero."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

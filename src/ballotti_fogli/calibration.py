"""Calibrazione pixel -> millimetri.

Tre modalita', dalla piu' semplice alla piu' robusta rispetto a una foto
scattata storta/in angolo:

1. ``calibrate_from_reference`` (``Calibration``): un solo rapporto mm/pixel
   da due punti di lunghezza nota. Assume implicitamente che la camera sia
   ragionevolmente perpendicolare al soggetto: se la foto e' inclinata, la
   scala non e' la stessa in ogni punto dell'immagine e la misura sballa
   (e' il problema riscontrato sulle foto con angolo di ripresa marcato).

2. ``save_calibration`` / ``load_calibration``: riusa una ``Calibration``
   calcolata una volta da una postazione fissa. Stesso limite del punto 1
   sull'inclinazione, in piu' richiede che camera/distanza/zoom non
   cambino mai tra uno scatto e l'altro.

3. ``homography_from_quad`` (``PlaneCalibration``): usa i **quattro angoli**
   di un riferimento rettangolare noto (es. un foglio A4) per calcolare una
   trasformazione prospettica (omografia) che raddrizza il piano della
   testata del ballotto, invece di un singolo rapporto mm/pixel. Corregge
   la distorsione prospettica dovuta a una foto storta/in diagonale, non
   solo la scala: e' la modalita' consigliata quando non si puo' garantire
   uno scatto perfettamente perpendicolare. Richiede che il riferimento e i
   punti misurati (alto/basso della fila) giacciano sullo stesso piano.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Protocol

import cv2
import numpy as np
import yaml


class SupportsDistanceMm(Protocol):
    def distance_mm(self, p1: tuple[float, float], p2: tuple[float, float]) -> float: ...


@dataclass(frozen=True)
class Calibration:
    mm_per_px: float

    def px_to_mm(self, distance_px: float) -> float:
        return distance_px * self.mm_per_px

    def distance_mm(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return self.px_to_mm(distance_px(p1, p2))


def distance_px(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def calibrate_from_reference(
    ref_point_a: tuple[float, float],
    ref_point_b: tuple[float, float],
    ref_length_mm: float,
) -> Calibration:
    """Calcola mm/pixel da due punti che delimitano un oggetto di lunghezza
    reale nota (``ref_length_mm``), fotografato sullo stesso piano del
    ballotto da misurare.
    """
    if ref_length_mm <= 0:
        raise ValueError("ref_length_mm deve essere positivo")

    px = distance_px(ref_point_a, ref_point_b)
    if px <= 0:
        raise ValueError("I due punti di riferimento coincidono: impossibile calibrare")

    return Calibration(mm_per_px=ref_length_mm / px)


def save_calibration(calibration: Calibration, path: str, notes: str | None = None) -> None:
    """Salva la calibrazione su file YAML per riutilizzarla su foto successive
    scattate dalla stessa postazione fissa (stessa distanza/angolo/zoom).
    """
    data = {**asdict(calibration), "notes": notes}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def load_calibration(path: str) -> Calibration:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Calibration(mm_per_px=float(data["mm_per_px"]))


@dataclass(frozen=True)
class PlaneCalibration:
    """Calibrazione prospettica: mappa punti immagine (pixel) a coordinate
    reali in mm sul piano del riferimento, tramite un'omografia. A differenza
    di ``Calibration`` non assume un rapporto mm/pixel costante in tutta
    l'immagine, quindi resta accurata anche se la foto e' storta/in
    diagonale, purche' il punto misurato giaccia sullo stesso piano del
    riferimento usato per calibrare.
    """

    homography: np.ndarray  # 3x3, pixel -> mm

    def to_mm(self, point_px: tuple[float, float]) -> tuple[float, float]:
        pts = np.array([[point_px]], dtype=np.float64)
        mapped = cv2.perspectiveTransform(pts, self.homography)
        return float(mapped[0, 0, 0]), float(mapped[0, 0, 1])

    def distance_mm(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        x1, y1 = self.to_mm(p1)
        x2, y2 = self.to_mm(p2)
        return math.hypot(x2 - x1, y2 - y1)

    def local_mm_per_px(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        """Rapporto mm/pixel equivalente tra due punti specifici (non
        costante altrove nell'immagine se la prospettiva e' marcata). Utile
        per riusare codice che ragiona in mm/pixel su un segmento locale,
        es. il conteggio righe attorno alla stessa zona misurata.
        """
        px = distance_px(p1, p2)
        if px <= 0:
            raise ValueError("I due punti coincidono: impossibile calcolare mm/pixel locale")
        return self.distance_mm(p1, p2) / px


def order_quad_points(points: np.ndarray) -> np.ndarray:
    """Ordina 4 punti (in qualsiasi ordine) in senso antiorario partendo dal
    punto piu' in alto a sinistra, per un mapping coerente col rettangolo
    di riferimento in ``homography_from_quad``.
    """
    pts = np.asarray(points, dtype=np.float64).reshape(4, 2)
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    return pts[np.argsort(angles)]


def homography_from_quad(
    corners_px: np.ndarray,
    short_side_mm: float = 210.0,
    long_side_mm: float = 297.0,
) -> PlaneCalibration:
    """Calcola l'omografia pixel->mm da 4 angoli (in qualsiasi ordine) di un
    riferimento rettangolare noto (default: dimensioni A4), fotografato sullo
    stesso piano della fila da misurare.
    """
    ordered = order_quad_points(corners_px)

    # order_quad_points ordina per angolo crescente attorno al baricentro; in
    # coordinate immagine (y verso il basso) questo percorre il quadrilatero
    # in senso orario. Il rettangolo di destinazione deve seguire lo stesso
    # verso, altrimenti la corrispondenza tra i punti si "attorciglia" e
    # l'omografia risultante e' invalida (l'errore osservato in fase di
    # test era proprio questo: >25% di errore su distanze note).
    #
    # Il primo lato (ordered[0]->ordered[1]) puo' essere sia il lato corto
    # che quello lungo del riferimento, a seconda di come e' orientato nella
    # foto (es. A4 orizzontale invece che verticale): va confrontata la sua
    # lunghezza in pixel con quella del lato successivo per assegnare
    # correttamente short_side_mm/long_side_mm. Assumere sempre "il primo
    # lato e' quello corto" e' un bug reale scoperto in fase di test: su un
    # riferimento ruotato di 90 gradi produceva oltre il 40% di errore.
    edge_01 = float(np.linalg.norm(ordered[1] - ordered[0]))
    edge_12 = float(np.linalg.norm(ordered[2] - ordered[1]))

    if edge_01 <= edge_12:
        first_side_mm, second_side_mm = short_side_mm, long_side_mm
    else:
        first_side_mm, second_side_mm = long_side_mm, short_side_mm

    dst = np.array(
        [
            [0.0, 0.0],
            [first_side_mm, 0.0],
            [first_side_mm, second_side_mm],
            [0.0, second_side_mm],
        ],
        dtype=np.float64,
    )

    homography, _ = cv2.findHomography(ordered.astype(np.float64), dst, method=0)
    if homography is None:
        raise ValueError("Impossibile calcolare l'omografia dai 4 punti forniti")
    return PlaneCalibration(homography=homography)

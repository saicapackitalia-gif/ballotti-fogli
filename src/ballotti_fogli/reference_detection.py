"""Rilevamento automatico di un foglio di riferimento rettangolare (default:
A4) in una foto, per calibrare senza dover cliccare a mano i 4 angoli.

Cerca una regione chiara (bianca, anche con dominante di colore dovuta a
riflessi/ombre) dentro una ROI indicata dall'utente, isola il contorno
principale e lo approssima a un quadrilatero. Non cerca su tutta la foto
per evitare falsi positivi su etichette o altre superfici chiare.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


class ReferenceNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class DetectedQuad:
    corners_px: np.ndarray  # (4, 2), nelle coordinate dell'immagine originale
    measured_ratio: float  # lato_corto / lato_lungo misurato
    expected_ratio: float  # lato_corto / lato_lungo atteso (es. A4: 210/297)

    @property
    def ratio_error_pct(self) -> float:
        return abs(self.measured_ratio - self.expected_ratio) / self.expected_ratio * 100


def _whiteness_mask(bgr_region: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr_region, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # Foglio bianco: o neutro (bassa saturazione) o con una dominante
    # bluastra/grigia da ombra/riflesso, ma sempre abbastanza luminoso e mai
    # sui toni aranciati/marroni del cartone (H circa 10-25).
    near_white = (s < 40) & (v > 140)
    tinted_white = (h > 70) & (h < 160) & (s < 130) & (v > 150)
    return ((near_white | tinted_white).astype(np.uint8)) * 255


def detect_reference_quad(
    bgr_image: np.ndarray,
    roi: tuple[int, int, int, int],
    short_side_mm: float = 210.0,
    long_side_mm: float = 297.0,
    max_ratio_error_pct: float = 8.0,
) -> DetectedQuad:
    """Cerca il foglio di riferimento dentro ``roi`` = (x1, y1, x2, y2).

    Solleva ``ReferenceNotFoundError`` se non trova un quadrilatero
    plausibile, o se la sua forma si discosta troppo dal rapporto atteso
    (default entro l'8%: oltre, e' piu' probabile aver trovato un'etichetta
    o un riflesso che il vero foglio).
    """
    x1, y1, x2, y2 = roi
    region = bgr_image[y1:y2, x1:x2]
    if region.size == 0:
        raise ReferenceNotFoundError("ROI vuota o fuori dai bordi dell'immagine")

    mask = _whiteness_mask(region)
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ReferenceNotFoundError("Nessuna regione chiara trovata nella ROI indicata")

    largest = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(largest, True)

    approx = None
    for eps_frac in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1):
        candidate = cv2.approxPolyDP(largest, eps_frac * perimeter, True)
        if len(candidate) == 4:
            approx = candidate
            break

    if approx is None:
        raise ReferenceNotFoundError(
            "Il contorno piu' chiaro trovato non si approssima a un quadrilatero: "
            "restringere la ROI attorno al solo foglio di riferimento"
        )

    from .calibration import order_quad_points  # import locale per evitare cicli

    pts = order_quad_points(approx.reshape(4, 2).astype(np.float64))
    edges = [float(np.linalg.norm(pts[i] - pts[(i + 1) % 4])) for i in range(4)]
    pair_a = (edges[0] + edges[2]) / 2
    pair_b = (edges[1] + edges[3]) / 2
    short_side, long_side = sorted([pair_a, pair_b])

    measured_ratio = short_side / long_side
    expected_ratio = short_side_mm / long_side_mm
    quad = DetectedQuad(
        corners_px=pts + np.array([x1, y1]),
        measured_ratio=measured_ratio,
        expected_ratio=expected_ratio,
    )

    if quad.ratio_error_pct > max_ratio_error_pct:
        raise ReferenceNotFoundError(
            f"Trovato un quadrilatero ma con proporzioni troppo diverse dal riferimento "
            f"atteso (rapporto misurato {measured_ratio:.3f}, atteso {expected_ratio:.3f}, "
            f"scarto {quad.ratio_error_pct:.1f}%): probabilmente non e' il foglio giusto. "
            "Restringere la ROI o verificare che il foglio sia ben visibile e non "
            "eccessivamente inclinato."
        )

    return quad

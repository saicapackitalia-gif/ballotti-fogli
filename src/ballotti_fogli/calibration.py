"""Calibrazione pixel -> millimetri.

Due modalita':

1. ``calibrate_from_reference``: da due punti che delimitano un oggetto di
   lunghezza reale nota nella foto (es. un righello). Va rifatta ogni volta
   che cambiano distanza/zoom/angolo della camera rispetto al soggetto.

2. ``save_calibration`` / ``load_calibration``: se la fotocamera e' montata
   su un supporto fisso a distanza e angolo costanti rispetto al ballotto
   (es. una staffa/cavalletto), il rapporto mm/pixel calcolato una sola
   volta resta valido per tutte le foto successive scattate da quella
   postazione, eliminando il bisogno di un riferimento in ogni scatto.
   ATTENZIONE: la calibrazione salvata e' valida SOLO se camera, distanza,
   zoom e inquadratura restano identici a quelli usati per calibrare; uno
   smartphone tenuto a mano non garantisce questo, quindi questa modalita'
   richiede un supporto fisico fisso.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import yaml


@dataclass(frozen=True)
class Calibration:
    mm_per_px: float

    def px_to_mm(self, distance_px: float) -> float:
        return distance_px * self.mm_per_px


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

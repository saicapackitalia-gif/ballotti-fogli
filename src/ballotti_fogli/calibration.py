"""Calibrazione pixel -> millimetri a partire da due punti di riferimento
di lunghezza reale nota (es. estremi di un righello visibile nella foto).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


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

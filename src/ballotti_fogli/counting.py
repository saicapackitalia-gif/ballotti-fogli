"""Combina calibrazione, spessore medio noto del profilo d'onda e conteggio
righe per produrre una stima finale del numero di fogli, con indicazione di
confidenza.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calibration import Calibration, distance_px
from .linecount import estimate_sheet_count_by_lines


@dataclass(frozen=True)
class CountResult:
    height_mm: float
    count_by_division: int
    count_by_lines: int
    disagreement_pct: float
    low_confidence: bool


def count_sheets(
    gray_image: np.ndarray,
    calibration: Calibration,
    p_top: tuple[float, float],
    p_bottom: tuple[float, float],
    avg_sheet_thickness_mm: float,
    disagreement_threshold_pct: float = 10.0,
) -> CountResult:
    if avg_sheet_thickness_mm <= 0:
        raise ValueError("avg_sheet_thickness_mm deve essere positivo")

    height_px = distance_px(p_top, p_bottom)
    height_mm = calibration.px_to_mm(height_px)

    count_by_division = max(round(height_mm / avg_sheet_thickness_mm), 0)

    expected_thickness_px = avg_sheet_thickness_mm / calibration.mm_per_px
    count_by_lines = estimate_sheet_count_by_lines(
        gray_image, p_top, p_bottom, expected_thickness_px
    )

    reference = max(count_by_division, 1)
    disagreement_pct = abs(count_by_division - count_by_lines) / reference * 100

    return CountResult(
        height_mm=height_mm,
        count_by_division=count_by_division,
        count_by_lines=count_by_lines,
        disagreement_pct=disagreement_pct,
        low_confidence=disagreement_pct > disagreement_threshold_pct,
    )

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pytest

from ballotti_fogli.calibration import (
    calibrate_from_reference,
    distance_px,
    homography_from_quad,
    load_calibration,
    order_quad_points,
    save_calibration,
)


def test_distance_px():
    assert distance_px((0, 0), (3, 4)) == pytest.approx(5.0)


def test_calibrate_from_reference():
    calib = calibrate_from_reference((0, 0), (100, 0), ref_length_mm=50.0)
    assert calib.mm_per_px == pytest.approx(0.5)
    assert calib.px_to_mm(10) == pytest.approx(5.0)


def test_calibrate_rejects_zero_length():
    with pytest.raises(ValueError):
        calibrate_from_reference((0, 0), (100, 0), ref_length_mm=0)


def test_calibrate_rejects_coincident_points():
    with pytest.raises(ValueError):
        calibrate_from_reference((5, 5), (5, 5), ref_length_mm=50.0)


def test_save_and_load_calibration_roundtrip(tmp_path):
    calib = calibrate_from_reference((0, 0), (200, 0), ref_length_mm=100.0)
    path = tmp_path / "calibration.yaml"

    save_calibration(calib, str(path), notes="test")
    loaded = load_calibration(str(path))

    assert loaded.mm_per_px == pytest.approx(calib.mm_per_px)


def _project(points_mm: np.ndarray, homography_mm_to_px: np.ndarray) -> np.ndarray:
    pts_h = np.hstack([points_mm, np.ones((len(points_mm), 1))])
    proj = pts_h @ homography_mm_to_px.T
    return proj[:, :2] / proj[:, 2:3]


# A well-conditioned synthetic perspective transform (mm-space -> pixel
# space), standing in for a photo taken at an angle instead of head-on.
_TILTED_VIEW = np.array(
    [
        [1.3, 0.25, 300],
        [-0.05, 1.1, 150],
        [0.0004, 0.00015, 1.0],
    ]
)


def test_homography_from_quad_recovers_known_distance_on_tilted_photo():
    a4_corners_mm = np.array([[0, 0], [210, 0], [210, 297], [0, 297]], dtype=np.float64)
    top_mm = np.array([[500.0, 50.0]])
    bottom_mm = np.array([[500.0, 850.0]])
    true_height_mm = 800.0

    corners_px = _project(a4_corners_mm, _TILTED_VIEW)
    top_px = _project(top_mm, _TILTED_VIEW)[0]
    bottom_px = _project(bottom_mm, _TILTED_VIEW)[0]

    calib = homography_from_quad(corners_px, short_side_mm=210, long_side_mm=297)
    measured = calib.distance_mm(tuple(top_px), tuple(bottom_px))

    assert measured == pytest.approx(true_height_mm, rel=1e-3)


@pytest.mark.parametrize(
    "index_order",
    [
        [0, 1, 2, 3],  # ordine naturale
        [2, 0, 3, 1],  # mescolato
        [3, 2, 1, 0],  # verso invertito
    ],
)
def test_homography_from_quad_is_robust_to_input_corner_order(index_order):
    a4_corners_mm = np.array([[0, 0], [210, 0], [210, 297], [0, 297]], dtype=np.float64)
    top_mm = np.array([[500.0, 50.0]])
    bottom_mm = np.array([[500.0, 850.0]])

    corners_px = _project(a4_corners_mm, _TILTED_VIEW)[index_order]
    top_px = _project(top_mm, _TILTED_VIEW)[0]
    bottom_px = _project(bottom_mm, _TILTED_VIEW)[0]

    calib = homography_from_quad(corners_px, short_side_mm=210, long_side_mm=297)
    measured = calib.distance_mm(tuple(top_px), tuple(bottom_px))

    assert measured == pytest.approx(800.0, rel=1e-3)


def test_homography_from_quad_handles_landscape_reference_orientation():
    """Regressione: se il riferimento e' fotografato ruotato di 90 gradi
    (es. A4 orizzontale invece che verticale), il primo lato rilevato dopo
    l'ordinamento angolare puo' essere quello lungo, non quello corto.
    Assumerlo sempre corto (bug reale trovato manualmente) dava oltre il 40%
    di errore su questo identico caso.
    """
    a4_landscape_mm = np.array([[0, 0], [297, 0], [297, 210], [0, 210]], dtype=np.float64)
    top_mm = np.array([[500.0, 50.0]])
    bottom_mm = np.array([[500.0, 850.0]])

    corners_px = _project(a4_landscape_mm, _TILTED_VIEW)
    top_px = _project(top_mm, _TILTED_VIEW)[0]
    bottom_px = _project(bottom_mm, _TILTED_VIEW)[0]

    calib = homography_from_quad(corners_px, short_side_mm=210, long_side_mm=297)
    measured = calib.distance_mm(tuple(top_px), tuple(bottom_px))

    assert measured == pytest.approx(800.0, rel=1e-3)


def test_order_quad_points_returns_four_points():
    pts = np.array([[10, 10], [0, 10], [0, 0], [10, 0]], dtype=np.float64)
    ordered = order_quad_points(pts)
    assert ordered.shape == (4, 2)
    # Stesso insieme di punti, solo riordinato.
    assert {tuple(p) for p in ordered} == {tuple(p) for p in pts}

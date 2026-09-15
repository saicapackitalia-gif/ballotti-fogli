import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from ballotti_fogli.calibration import calibrate_from_reference, distance_px


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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from ballotti_fogli.linecount import find_peaks, sample_profile


def test_find_peaks_simple():
    signal = np.array([0, 1, 0, 0, 1, 0, 0, 1, 0], dtype=float)
    peaks = find_peaks(signal, min_distance=2, prominence=0.5)
    assert peaks == [1, 4, 7]


def test_find_peaks_respects_min_distance():
    signal = np.array([0, 1, 0.9, 0, 0, 0], dtype=float)
    peaks = find_peaks(signal, min_distance=3, prominence=0.1)
    assert len(peaks) == 1


def test_sample_profile_horizontal_line():
    image = np.tile(np.arange(10, dtype=np.uint8), (5, 1))
    profile = sample_profile(image, (0, 2), (9, 2), num_samples=10)
    assert profile[0] == 0
    assert profile[-1] == 9

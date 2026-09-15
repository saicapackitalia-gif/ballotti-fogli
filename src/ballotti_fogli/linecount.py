"""Stima del numero di fogli per conteggio diretto delle righe/creste
dell'onda visibili sul bordo tagliato del ballotto, tramite analisi di un
profilo di intensita' 1D campionato lungo l'altezza della pila.
"""
from __future__ import annotations

import numpy as np


def sample_profile(gray_image: np.ndarray, p1: tuple[float, float], p2: tuple[float, float], num_samples: int) -> np.ndarray:
    """Campiona i valori di grigio lungo il segmento p1-p2 (coordinate x, y
    in pixel) con interpolazione bilineare, restituendo un array 1D.
    """
    x1, y1 = p1
    x2, y2 = p2
    xs = np.linspace(x1, x2, num_samples)
    ys = np.linspace(y1, y2, num_samples)

    h, w = gray_image.shape[:2]
    xs_c = np.clip(xs, 0, w - 1)
    ys_c = np.clip(ys, 0, h - 1)

    x0 = np.floor(xs_c).astype(int)
    y0 = np.floor(ys_c).astype(int)
    x1i = np.clip(x0 + 1, 0, w - 1)
    y1i = np.clip(y0 + 1, 0, h - 1)

    fx = xs_c - x0
    fy = ys_c - y0

    img = gray_image.astype(np.float32)
    top = img[y0, x0] * (1 - fx) + img[y0, x1i] * fx
    bottom = img[y1i, x0] * (1 - fx) + img[y1i, x1i] * fx
    return top * (1 - fy) + bottom * fy


def find_peaks(signal: np.ndarray, min_distance: int, prominence: float) -> list[int]:
    """Ricerca di massimi locali con distanza minima e prominenza minima,
    senza dipendenze esterne oltre numpy (in alternativa a scipy.signal.find_peaks).
    """
    if len(signal) < 3:
        return []

    candidates = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] >= signal[i + 1]:
            candidates.append(i)

    candidates.sort(key=lambda i: signal[i], reverse=True)

    accepted: list[int] = []
    for idx in candidates:
        if any(abs(idx - a) < min_distance for a in accepted):
            continue
        left = signal[max(0, idx - min_distance):idx]
        right = signal[idx + 1:idx + 1 + min_distance]
        baseline = min(
            left.min() if len(left) else signal[idx],
            right.min() if len(right) else signal[idx],
        )
        if signal[idx] - baseline < prominence:
            continue
        accepted.append(idx)

    return sorted(accepted)


def estimate_sheet_count_by_lines(
    gray_image: np.ndarray,
    p_top: tuple[float, float],
    p_bottom: tuple[float, float],
    expected_sheet_thickness_px: float,
) -> int:
    """Stima il numero di fogli contando i picchi di gradiente lungo il
    profilo top->bottom. ``expected_sheet_thickness_px`` (ricavato dallo
    spessore medio noto convertito in pixel tramite la calibrazione) e'
    usato solo per fissare la distanza minima tra picchi attesi, non per
    determinare direttamente il conteggio.
    """
    length_px = int(max(abs(p_bottom[1] - p_top[1]), abs(p_bottom[0] - p_top[0])))
    num_samples = max(length_px * 2, 50)

    profile = sample_profile(gray_image, p_top, p_bottom, num_samples)
    gradient = np.abs(np.gradient(profile))

    scale = num_samples / max(length_px, 1)
    min_distance = max(int(expected_sheet_thickness_px * scale * 0.5), 2)
    prominence = float(np.std(gradient) * 0.5)

    peaks = find_peaks(gradient, min_distance=min_distance, prominence=prominence)
    # Ogni foglio produce tipicamente un bordo/riga visibile: il numero di
    # fogli e' approssimato al numero di picchi rilevati.
    return len(peaks)

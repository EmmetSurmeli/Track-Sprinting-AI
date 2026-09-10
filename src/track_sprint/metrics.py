"""Pure 2D geometry. Coordinates are pixels, x forward, y up."""
import numpy as np
from scipy.signal import find_peaks, savgol_filter

SIDES = {"left": (11, 23, 25, 27), "right": (12, 24, 26, 28)}
METRICS = {
    "knee": "Knee flexion", "hip": "Trunk–thigh flexion",
    "trunk": "Trunk / frame vertical", "thigh": "Thigh / downward vertical",
}


def angle(a, b, c):
    u, v = np.asarray(a) - b, np.asarray(c) - b
    denominator = np.linalg.norm(u) * np.linalg.norm(v)
    if not np.isfinite(denominator) or denominator < 1e-8:
        return float("nan")
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / denominator, -1, 1))))


def signed_angle(a, b):
    if min(np.linalg.norm(a), np.linalg.norm(b)) < 1e-8:
        return float("nan")
    return float(np.degrees(np.arctan2(a[0] * b[1] - a[1] * b[0], np.dot(a, b))))


def side_metrics(points, side, width, height, direction, threshold=0.7):
    """Input rows: normalized x, y, visibility, presence. Invalid stays NaN."""
    ids = SIDES[side]
    p = np.asarray(points)[list(ids)]
    xy = p[:, :2] * [width, height]
    xy = xy * [1 if direction == "right" else -1, -1]
    valid = (np.isfinite(p).all(axis=1) & (p[:, 2:].min(axis=1) >= threshold)
             & (p[:, :2].min(axis=1) >= 0) & (p[:, :2].max(axis=1) <= 1))
    s, h, k, a = xy
    values = {name: float("nan") for name in METRICS}
    if valid[[1, 2, 3]].all():
        values["knee"] = 180 - angle(h, k, a)
    if valid[[0, 1, 2]].all():
        values["hip"] = signed_angle(h - s, k - h)
    if valid[[0, 1]].all() and np.linalg.norm(s - h) > 1e-8:
        values["trunk"] = float(np.degrees(np.arctan2((s - h)[0], (s - h)[1])))
    if valid[[1, 2]].all() and np.linalg.norm(k - h) > 1e-8:
        values["thigh"] = float(np.degrees(np.arctan2((k - h)[0], -(k - h)[1])))
    return values


def valid_segments(values):
    indices = np.flatnonzero(np.isfinite(values))
    return np.split(indices, np.where(np.diff(indices) != 1)[0] + 1)


def smooth(values, times, window=5):
    """Centered, timestamp-aware smoothing within valid intervals; never fills gaps."""
    result = np.array(values, dtype=float, copy=True)
    for segment in valid_segments(result):
        if len(segment) < window:
            continue
        tt = np.asarray(times)[segment]
        if np.any(np.diff(tt) <= 0):
            continue
        raw = np.degrees(np.unwrap(np.radians(result[segment])))
        uniform = np.linspace(tt[0], tt[-1], len(tt))
        filtered = savgol_filter(np.interp(uniform, tt, raw), window, 2)
        result[segment] = np.interp(tt, uniform, filtered)
    return result


def cycles_from_thigh(values):
    """Repeated forward-thigh maxima delimit observed cycles, not contact events."""
    cycles = []
    for seg in valid_segments(values):
        if len(seg) < 15:
            continue
        peaks, _ = find_peaks(np.asarray(values)[seg], prominence=20, distance=8)
        for a, b in zip(peaks[:-1], peaks[1:]):
            lo, hi = int(seg[a]), int(seg[b])
            cycles.append({"start_index": lo, "end_index": hi,
                "front_deg": round(max(0, float(np.max(values[lo:hi + 1]))), 1),
                "rear_deg": round(max(0, -float(np.min(values[lo:hi + 1]))), 1),
                "rom_deg": round(float(np.ptp(values[lo:hi + 1])), 1)})
    return cycles


def select_keyframes(series, min_spacing=8, maximum=4):
    candidates = []
    for key, label in [("thigh", "Forward thigh position"), ("knee", "Knee recovery"),
                       ("thigh_min", "Rear thigh position"), ("knee_min", "Extended knee position")]:
        name = key.replace("_min", "")
        v = np.asarray(series[name])
        if not np.isfinite(v).any():
            continue
        index = int(np.nanargmin(v) if key.endswith("_min") else np.nanargmax(v))
        if all(abs(index - c["index"]) >= min_spacing for c in candidates):
            candidates.append({"index": index, "label": label, "metric": name})
    return sorted(candidates[:maximum], key=lambda x: x["index"])

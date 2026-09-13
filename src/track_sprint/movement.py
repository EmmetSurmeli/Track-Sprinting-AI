"""Deterministic, review-gated bilateral movement evidence; never estimates strength.

Cycles are front-thigh peak to front-thigh peak using trunk-relative flexion.
They are geometric cycles, not detected touchdown/toe-off events. All gates are
engineering review rules, not validated clinical cutoffs.
"""
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from .artifacts import read_json, stable_hash, write_json
from .metrics import angle, signed_angle, smooth, valid_segments

VERSION = "1.0"
REVIEW_DEFAULTS = {"stable_side_view": False, "labels_checked": False, "cycles_checked": False}
LABELS = {"hip": "Trunk–thigh flexion", "knee": "Knee flexion",
          "arm": "Upper arm / trunk", "elbow": "Elbow flexion"}


def arm_metrics(points, side, width, height, direction, threshold):
    ids = (11, 13, 15, 23) if side == "left" else (12, 14, 16, 24)
    p = np.asarray(points)[list(ids)]
    valid = (np.isfinite(p).all(axis=1) & (p[:, 2:].min(axis=1) >= threshold)
             & (p[:, :2].min(axis=1) >= 0) & (p[:, :2].max(axis=1) <= 1))
    s, e, w, h = p[:, :2] * [width * (1 if direction == "right" else -1), -height]
    result = {"arm": float("nan"), "elbow": float("nan")}
    if valid[[0, 1, 3]].all() and min(np.linalg.norm(h-s), np.linalg.norm(e-s)) >= 5:
        result["arm"] = signed_angle(h-s, e-s)
    if valid[:3].all() and min(np.linalg.norm(e-s), np.linalg.norm(w-e)) >= 5:
        result["elbow"] = 180 - angle(s, e, w)
    return result


def candidate_cycles(values, frames, times):
    """Never bridge a missing point or invent a boundary peak at the clip edge."""
    a = np.array(values, dtype=float)
    cycles = []
    for seg in valid_segments(a):
        if len(seg) < 17:
            continue
        peaks, _ = find_peaks(a[seg], prominence=20, distance=8)
        for first, last in zip(peaks[:-1], peaks[1:]):
            start, end = int(seg[first]), int(seg[last])
            rear = start + int(np.argmin(a[start:end+1]))
            if not start < rear < end or min(a[start], a[end]) < 10 or a[rear] > -5:
                continue
            tt = np.asarray(times[start:end+1], float)
            if not np.isfinite(tt).all() or np.any(np.diff(tt) <= 0):
                continue
            cycles.append({"start_index": start, "rear_index": rear, "end_index": end,
                "start_frame": int(frames[start]), "rear_frame": int(frames[rear]), "end_frame": int(frames[end]),
                "front_deg": float(a[start]), "rear_deg": float(-a[rear]),
                "return_media_seconds": float(times[end]-times[rear]),
                "cycle_media_seconds": float(times[end]-times[start])})
    return cycles


def load_review(directory, identity):
    path = Path(directory) / "movement_review.json"
    saved = read_json(path) if path.exists() else {}
    if saved.get("analysis_id") != identity:
        return dict(REVIEW_DEFAULTS)
    return {key: saved.get(key) is True for key in REVIEW_DEFAULTS}


def movement_data(directory, summary):
    """Derive additional evidence from existing landmarks; no model/API rerun required."""
    directory = Path(directory)
    landmark_path = directory / "landmarks.npz"
    series_path = directory / "series.json"
    if not landmark_path.exists() or not series_path.exists():
        return None
    fingerprint = stable_hash({"version": VERSION, "analysis": summary["analysis_id"],
        "landmarks_mtime": landmark_path.stat().st_mtime_ns, "series_mtime": series_path.stat().st_mtime_ns})
    cache = directory / "movement.json"
    if cache.exists():
        stored = read_json(cache)
        if stored.get("fingerprint") == fingerprint:
            return stored
    with np.load(landmark_path, allow_pickle=False) as z:
        points, frames, times = z["accepted"], z["frame_ids"], z["times"]
    if list(frames) != summary["frames"] or not np.allclose(times, summary["times"], atol=1e-7):
        raise ValueError("Movement landmarks do not match source frames/timestamps.")
    series = read_json(series_path)
    w, h = summary["analysis_dimensions"]
    result = {"version": VERSION, "fingerprint": fingerprint, "analysis_id": summary["analysis_id"],
              "sides": {}, "frames": list(map(int, frames))}
    for side in ("left", "right"):
        arms = [arm_metrics(p, side, w, h, summary["config"]["direction"], summary["config"]["score_threshold"]) for p in points]
        traces = {name: np.array(series[side][name]["raw"], float) for name in ("hip", "knee")}
        traces.update({name: np.array([p[name] for p in arms]) for name in ("arm", "elbow")})
        measured = {}
        for name, raw in traces.items():
            filtered = smooth(raw, times)
            valid = np.isfinite(filtered)
            info = {"label": LABELS[name], "coverage": float(valid.mean()),
                    "values": [round(float(v), 4) if np.isfinite(v) else None for v in filtered]}
            if valid.any():
                lo, hi = int(np.nanargmin(filtered)), int(np.nanargmax(filtered))
                info.update(min=round(float(filtered[lo]), 2), max=round(float(filtered[hi]), 2),
                            min_frame=int(frames[lo]), max_frame=int(frames[hi]))
            measured[name] = info
        cycles = candidate_cycles(measured["hip"]["values"], frames, times)
        # Changing smoothing must not create a different set of geometric cycles.
        sensitivity = []
        for window in (3, 7):
            other = candidate_cycles(smooth(traces["hip"], times, window), frames, times)
            stable = len(other) == len(cycles) and all(
                max(abs(a[k]-b[k]) for k in ("start_index", "rear_index", "end_index")) <= 3
                for a, b in zip(cycles, other))
            sensitivity.append(stable)
        result["sides"][side] = {"metrics": measured, "cycles": cycles,
                                  "cycle_smoothing_stable": all(sensitivity)}
    write_json(cache, result)
    return result


def movement_evidence(data, summary, review=None, contacts=None):
    """Only reviewed repeated cycles produce bilateral coaching facts."""
    if not data or data.get("analysis_id") != summary["analysis_id"]:
        return {"available": False, "facts": {}, "comparisons": [], "blockers": ["Movement trajectories are unavailable."]}
    review = {key: (review or {}).get(key) is True for key in REVIEW_DEFAULTS}
    reasons = []
    if not review["stable_side_view"]:
        reasons.append("Confirm a consistent side-on view through the cycles; panning alone does not correct changing perspective.")
    if summary["config"]["near_side"] == "unknown" or not review["labels_checked"]:
        reasons.append("Confirm anatomical sides and inspect tracking for left/right swaps and occlusions.")
    if not review["cycles_checked"]:
        reasons.append("Review all candidate front/rear/front boundaries against the original footage.")
    if summary["quality"] == "insufficient":
        reasons.append("Tracking is insufficient.")
    for side, item in data["sides"].items():
        if len(item["cycles"]) < 2:
            reasons.append(f"{side.title()} has fewer than two complete continuously tracked thigh cycles.")
        if not item["cycle_smoothing_stable"]:
            reasons.append(f"{side.title()} cycle boundaries change when smoothing changes.")
    # A similar time window prevents comparing early vs late parts of a changing pass.
    left, right = [data["sides"][s]["cycles"] for s in ("left", "right")]
    if left and right:
        overlap = min(left[-1]["end_index"], right[-1]["end_index"]) - max(left[0]["start_index"], right[0]["start_index"])
        span = min(left[-1]["end_index"]-left[0]["start_index"], right[-1]["end_index"]-right[0]["start_index"])
        if overlap < span * .5:
            reasons.append("The sides do not cover sufficiently overlapping parts of the passage.")
    timing = bool(summary["config"].get("timing_verified"))
    scale = 1.0
    if contacts and contacts.get("analysis_id") == summary["analysis_id"] and contacts.get("timing_verified_by_user"):
        # Contact result structure supplies the same verified timeline used by the app.
        timing = True
        scale = 1.0 / contacts.get("slow_motion_factor", 1.0)
    result = {"available": True, "version": VERSION, "review": review, "blockers": reasons,
        "cycle_counts": {s: len(v["cycles"]) for s, v in data["sides"].items()},
        "coverage": {s: {m: round(v["coverage"], 3) for m, v in item["metrics"].items()} for s, item in data["sides"].items()},
        "timing_verified": timing, "facts": {}, "comparisons": [],
        "scope": "Projected geometric cycles, not contact events. No strength, power, ideal-angle or causal-injury inference."}
    if reasons:
        return result
    specs = [("cycle_front", "Peak forward thigh / trunk", "hip", "degrees"),
             ("cycle_rear", "Peak rear thigh / trunk", "hip", "degrees"),
             ("cycle_arm", "Peak forward upper arm / trunk", "arm", "degrees"),
             ("cycle_elbow", "Peak elbow flexion", "arm", "degrees")]
    if timing:
        specs.append(("cycle_return", "Rear-to-front thigh rotation duration", "hip", "ms"))
    for name, label, topic, unit in specs:
        pair = {}
        for side, item in data["sides"].items():
            values, ids, supporting = [], [], []
            for c in item["cycles"]:
                if name == "cycle_front":
                    value, fid = c["front_deg"], c["start_frame"]
                elif name == "cycle_rear":
                    value, fid = c["rear_deg"], c["rear_frame"]
                elif name == "cycle_return":
                    value, fid = c["return_media_seconds"] * scale * 1000, c["rear_frame"]
                else:
                    field = "arm" if name == "cycle_arm" else "elbow"
                    a = np.array(item["metrics"][field]["values"][c["start_index"]:c["end_index"]+1], float)
                    if not np.isfinite(a).all():
                        continue  # Missing arm data can conceal the actual peak.
                    j = int(np.argmax(a)); value = float(a[j]); fid = data["frames"][c["start_index"]+j]
                values.append(value); ids.append(fid)
                supporting.extend([fid, c["rear_frame"], c["end_frame"]] if name == "cycle_return" else [fid])
            if len(values) < 2:
                continue
            lo, hi = int(np.argmin(values)), int(np.argmax(values))
            pair[side] = {"id": f"{side}.{name}", "metric": topic, "comparison_group": name,
                "label": label, "side": side, "units": unit, "min": round(values[lo], 2), "max": round(values[hi], 2),
                "mean": round(float(np.mean(values)), 2), "count": len(values), "coverage": 1.0,
                "min_frame": ids[lo], "max_frame": ids[hi],
                "reference_frames": sorted(set(supporting)),
                "interpretation": "Across reviewed complete geometric cycles; quantities are projected and not individual targets."}
        if len(pair) != 2:
            continue
        a, b = pair["left"], pair["right"]
        delta = round(a["mean"]-b["mean"], 2)
        spread = round(max(a["max"]-a["min"], b["max"]-b["min"]), 2)
        result["facts"].update({v["id"]: v for v in pair.values()})
        result["comparisons"].append({"id": name, "label": label, "metric_refs": [a["id"], b["id"]],
            "left_mean": a["mean"], "right_mean": b["mean"], "left_minus_right": delta, "units": unit,
            "direction": "similar" if abs(delta) <= .01 else "left_greater" if delta > 0 else "right_greater",
            "within_side_spread": spread, "exceeds_observed_cycle_spread": abs(delta) > spread,
            "interpretation": "Descriptive difference only. Within-side spread is not a measurement-error bound or significance test."})
    return result


def load_movement_evidence(directory, summary, contacts=None):
    data = movement_data(directory, summary)
    evidence = movement_evidence(data, summary, load_review(directory, summary["analysis_id"]), contacts)
    # Retain the ordered measured motion even when repeated-cycle comparison is
    # unavailable. Missing samples stay missing; this never creates contact events.
    evidence["sequence_facts"] = {}
    if data and summary["quality"] != "insufficient":
        evidence["sequence"] = {"frames": data["frames"], "angles": {},
            "scope": "Ordered projected angles at every analyzed frame. No inferred contact phase, force or muscular capacity. Incomplete cycles cannot establish a repeatable imbalance."}
        for side, item in data["sides"].items():
            for name, metric in item["metrics"].items():
                if metric["coverage"] < .85:
                    continue
                ref = f"{side}.sequence_{name}"
                values = metric["values"]
                evidence["sequence"]["angles"][ref] = [round(v, 1) if v is not None else None for v in values]
                evidence["sequence_facts"][ref] = {"id": ref, "metric": "arm" if name in ("arm", "elbow") else name,
                    "side": side, "label": metric["label"], "units": "degrees", "min": metric["min"], "max": metric["max"],
                    "min_frame": metric["min_frame"], "max_frame": metric["max_frame"], "coverage": metric["coverage"],
                    "reference_frames": [fid for fid, value in zip(data["frames"], values) if value is not None],
                    "sampling": "Chronological angle sequence across this passage",
                    "interpretation": evidence["sequence"]["scope"]}
    return evidence

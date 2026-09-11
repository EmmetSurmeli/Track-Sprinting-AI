"""Human-reviewed shoe-contact boundaries, with explicit timestamp uncertainty."""
from pathlib import Path

import numpy as np

from .artifacts import read_json, write_json
from .schemas import ContactReview


def load_contact_review(directory: Path, summary):
    path = directory / "contacts.json"
    if not path.exists():
        return ContactReview(analysis_id=summary["analysis_id"])
    review = ContactReview.model_validate(read_json(path))
    if review.analysis_id != summary["analysis_id"]:
        raise ValueError("Contact review belongs to another analysis.")
    return review


def contact_results(summary, review: ContactReview):
    if review.analysis_id != summary["analysis_id"]:
        raise ValueError("Contact review belongs to another analysis.")
    frames, times = summary["frames"], np.array(summary["times"], dtype=float)
    if len(frames) != len(times) or len(set(frames)) != len(frames) or np.any(np.diff(times) <= 0):
        raise ValueError("Contact review requires unique frames and increasing timestamps.")
    timed = review.timing_confirmed and review.timing_basis != "Unverified"
    factor = review.slow_motion_factor if review.timing_basis == "Known constant slow-motion factor" else 1.0
    results, intervals = [], {"left": [], "right": []}
    for mark in review.marks:
        if mark.touchdown_frame not in frames or mark.toeoff_frame not in frames:
            raise ValueError("Choose frames from this analyzed passage.")
        td, off = frames.index(mark.touchdown_frame), frames.index(mark.toeoff_frame)
        if td == 0 or off <= td:
            raise ValueError("Touchdown needs a preceding airborne frame, and toe-off must follow touchdown.")
        if any(not (off < a or td > b) for a, b in intervals[mark.side]):
            raise ValueError("Contact intervals on the same side cannot overlap or be duplicated.")
        intervals[mark.side].append((td, off))
        lo = max(0.0, (times[off - 1] - times[td]) / factor * 1000)
        hi = (times[off] - times[td - 1]) / factor * 1000
        estimate = (lo + hi) / 2
        boundary_gap = max(times[td] - times[td - 1], times[off] - times[off - 1]) / factor * 1000
        eligible = timed and mark.visibility_confirmed
        results.append({"side": mark.side, "touchdown_frame": mark.touchdown_frame, "toeoff_frame": mark.toeoff_frame,
            "preceding_touchdown_frame": frames[td - 1], "preceding_toeoff_frame": frames[off - 1],
            "reviewed_frame_span": off - td, "timed": eligible,
            "estimate_ms": round(estimate, 2) if eligible else None,
            "lower_ms": round(lo, 2) if eligible else None, "upper_ms": round(hi, 2) if eligible else None,
            "boundary_gap_ms": round(boundary_gap, 2) if eligible else None,
            "comparison_eligible": bool(eligible and review.side_labels_confirmed and boundary_gap <= 1000 / 120 + 1e-6 and lo > 0),
            "visibility_confirmed": mark.visibility_confirmed})
    overlap = False
    for i, a in enumerate(results):
        for b in results[i + 1:]:
            if a["side"] != b["side"] and max(a["touchdown_frame"], b["touchdown_frame"]) < min(a["toeoff_frame"], b["toeoff_frame"]):
                a["comparison_eligible"] = b["comparison_eligible"] = False
                overlap = True
    sides = {}
    for side in ("left", "right"):
        usable = [r for r in results if r["side"] == side and r["comparison_eligible"]]
        if usable:
            sides[side] = {"n": len(usable), "mean_ms": round(float(np.mean([r["estimate_ms"] for r in usable])), 2),
                "lower_ms": round(float(np.mean([r["lower_ms"] for r in usable])), 2),
                "upper_ms": round(float(np.mean([r["upper_ms"] for r in usable])), 2)}
    comparison = None
    if all(sides.get(s, {}).get("n", 0) >= 2 for s in ("left", "right")):
        left, right = sides["left"], sides["right"]
        denominator = (left["mean_ms"] + right["mean_ms"]) / 2
        comparison = {"left_minus_right_ms": round(left["mean_ms"] - right["mean_ms"], 2),
            "absolute_difference_percent": round(abs(left["mean_ms"] - right["mean_ms"]) / denominator * 100, 2),
            "difference_lower_ms": round(left["lower_ms"] - right["upper_ms"], 2),
            "difference_upper_ms": round(left["upper_ms"] - right["lower_ms"], 2),
            "method": "Absolute mean difference divided by the mean of both sides; descriptive only"}
    return {"analysis_id": summary["analysis_id"], "method": "User-marked transitions; interval-censored timing",
        "timing_verified_by_user": timed, "timing_basis": review.timing_basis, "slow_motion_factor": factor,
        "side_labels_confirmed": review.side_labels_confirmed, "contacts": results,
        "sides": sides, "comparison": comparison,
        "overlapping_sides": overlap,
        "limitations": ["Timing bounds reflect adjacent decoded frames, not a calibrated confidence interval or total measurement error.",
            "Shoe-ground contact and force-platform contact definitions can differ.",
            "A side difference does not identify a weaker muscle, its cause, or a future injury.",
            "Comparison requires two reviewed contacts per side and boundary gaps at most one hundred and twentieth of a second; this is an MVP quality gate, not a validated clinical threshold."]}


def save_contact_review(directory, summary, review):
    result = contact_results(summary, review)
    write_json(directory / "contacts.json", review.model_dump())
    write_json(directory / "contact_results.json", result)
    return result


def sampled_side_differences(summary):
    """Side ranges over the same selected interval; not phase-matched anatomical asymmetry."""
    rows = []
    for name in ("knee", "hip"):
        a, b = (summary["metrics"].get(f"{side}.{name}") for side in ("left", "right"))
        if not a or not b or min(a["coverage"], b["coverage"]) < .85:
            continue
        rows.append({"Measurement": a["label"], "Left observed range (°)": round(a["max"] - a["min"], 1),
                     "Right observed range (°)": round(b["max"] - b["min"], 1),
                     "Left − right range (°)": round((a["max"] - a["min"]) - (b["max"] - b["min"]), 1)})
    return rows

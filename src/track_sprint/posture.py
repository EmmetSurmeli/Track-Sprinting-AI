"""Selected landing posture geometry, independent of contact-event timing.

The reviewer selects a visible landing position. This is not a touchdown detector.
All measurements use accepted, unsmoothed points at that exact source frame.
"""
from pathlib import Path

import numpy as np
from pydantic import Field
from typing import Literal

from .artifacts import read_json
from .metrics import angle
from .schemas import StrictModel


class PostureReview(StrictModel):
    analysis_id: str
    frame: int
    side: Literal["left", "right"]
    geometry_checked: bool = False
    provenance: str = Field(default="Selected in the app", max_length=300)


def landing_geometry(points, side, dimensions, direction, threshold):
    ids = [23, 25, 27] if side == "left" else [24, 26, 28]
    p = np.asarray(points)[ids]
    if not (np.isfinite(p).all() and np.min(p[:, 2:]) >= threshold
            and np.min(p[:, :2]) >= 0 and np.max(p[:, :2]) <= 1):
        return None
    hip, knee, ankle = p[:, :2] * dimensions
    thigh, shank = np.linalg.norm(knee-hip), np.linalg.norm(ankle-knee)
    if min(thigh, shank) < 5:
        return None
    forward = 1 if direction == "right" else -1
    return {"ankle_ahead_percent": float((ankle[0]-hip[0])*forward/(thigh+shank)*100),
            "knee_flexion_deg": float(180-angle(hip, knee, ankle))}


def posture_evidence(directory, summary, review=None):
    directory = Path(directory)
    empty = {"facts": {}, "available": False}
    if review is None:
        path = directory / "posture_review.json"
        if not path.exists():
            return empty
        review = PostureReview.model_validate(read_json(path))
    if review.analysis_id != summary["analysis_id"]:
        raise ValueError("Landing review belongs to another analysis.")
    if review.frame not in summary["frames"]:
        raise ValueError("Choose a landing frame from the analyzed passage.")
    if not review.geometry_checked or summary["quality"] == "insufficient":
        return empty
    path = directory / "landmarks.npz"
    if not path.exists():
        return empty
    with np.load(path, allow_pickle=False) as z:
        if list(z["frame_ids"]) != summary["frames"]:
            raise ValueError("Landing landmarks do not match the analyzed frames.")
        points = z["accepted"][summary["frames"].index(review.frame)]
    geometry = landing_geometry(points, review.side, summary["analysis_dimensions"],
                                summary["config"]["direction"], summary["config"]["score_threshold"])
    if geometry is None:
        return {**empty, "reason": "Hip, knee or ankle geometry is missing or unreliable at this frame."}
    result = {"available": True, "review": review.model_dump(), "facts": {},
        "scope": "Reviewer-selected landing posture, not the first instant of ground contact. One frame cannot establish a repeated fault.",
        "placement": "ahead" if geometry["ankle_ahead_percent"] > 0 else "behind" if geometry["ankle_ahead_percent"] < 0 else "aligned",
        "limitations": "Image-horizontal ankle-to-same-side-hip offset divided by projected thigh plus shank length. Not center of mass, ground-calibrated distance, stride length, force or an optimal target. Camera roll and perspective affect it."}
    for name, value, label, metric, unit in (
        ("landing_offset", geometry["ankle_ahead_percent"], "Landing ankle ahead of hip", "touchdown_position", "% projected leg length"),
        ("landing_knee", geometry["knee_flexion_deg"], "Knee flexion at selected landing", "knee", "degrees"),
    ):
        ref = f"{review.side}.{name}"
        result["facts"][ref] = {"id": ref, "metric": metric, "observation_group": "landing_posture",
            "label": label, "side": review.side, "units": unit, "min": round(value, 2), "max": round(value, 2),
            "min_frame": review.frame, "max_frame": review.frame, "reference_frames": [review.frame],
            "coverage": 1.0, "count": 1, "sampling": "Selected landing frame; unsmoothed accepted landmarks",
            "interpretation": result["scope"] + " " + result["limitations"]}
    return result

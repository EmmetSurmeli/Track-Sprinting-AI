"""Sequential, reproducible local analysis. No LLM is allowed to write metrics."""
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import time

import cv2
import numpy as np

from .artifacts import read_json, stable_hash, write_json
from .metrics import METRICS, cycles_from_thigh, select_keyframes, side_metrics, smooth
from .pose import PoseTracker, ensure_model, trajectory_mask
from .render import VideoWriter, overlay
from .schemas import AnalysisConfig
from .video import VideoError, VideoInfo, inspect_video, iter_frames

PIPELINE_VERSION = "1.0"


def finite_list(array):
    return [round(float(v), 4) if np.isfinite(v) else None for v in array]


def analyze(video: Path, config: AnalysisConfig, output: Path, models: Path, progress=None):
    progress = progress or (lambda stage, fraction: None)
    started = time.monotonic()
    info = inspect_video(video)
    if config.end > info.duration + 0.05:
        raise VideoError("The interval ends beyond this video.")
    output.mkdir(parents=True, exist_ok=True)
    # A failed rerun must not leave an older completion marker over partial new files.
    (output / "manifest.json").unlink(missing_ok=True)
    progress("Loading pose model", 0.02)
    model = ensure_model(models, config.model_variant)
    tracker = PoseTracker(model)
    identity = stable_hash({"video": info.sha256, "config": config.model_dump(),
        "pipeline": PIPELINE_VERSION, "model": tracker.model_hash})
    raw_points, times, frame_ids, reasons = [], [], [], []
    try:
        for i, t, rgb in iter_frames(video, info, config.start, config.end):
            p, reason = tracker.detect(rgb, t)
            raw_points.append(p)
            times.append(t)
            frame_ids.append(i)
            reasons.append(reason)
            if len(times) % 10 == 0:
                progress("Tracking joints", 0.05 + 0.55 * (t - config.start) / (config.end - config.start))
    finally:
        tracker.close()
    if len(times) < 6:
        raise VideoError("Select a longer interval with a visible athlete.")
    h, w = rgb.shape[:2]
    points = np.stack(raw_points)
    accepted = trajectory_mask(points, w, h)
    np.savez_compressed(output / "landmarks.npz", raw=points, accepted=accepted,
        times=np.array(times), frame_ids=np.array(frame_ids))
    progress("Calculating motion", 0.62)
    series, summaries = {}, {}
    for side in ("left", "right"):
        per_frame = [side_metrics(p, side, w, h, config.direction, config.score_threshold) for p in accepted]
        series[side] = {}
        for name in METRICS:
            raw = np.array([p[name] for p in per_frame])
            filtered = smooth(raw, times)
            series[side][name] = {"raw": finite_list(raw), "smoothed": finite_list(filtered)}
            valid = np.isfinite(raw)
            if valid.any():
                lo, hi = int(np.nanargmin(filtered)), int(np.nanargmax(filtered))
                summaries[f"{side}.{name}"] = {"id": f"{side}.{name}", "metric": name,
                    "label": METRICS[name], "side": side, "units": "degrees",
                    "min": round(float(filtered[lo]), 1), "max": round(float(filtered[hi]), 1),
                    "median": round(float(np.nanmedian(filtered)), 1), "valid_count": int(valid.sum()),
                    "total_count": len(raw), "coverage": round(float(valid.mean()), 3),
                    "min_frame": frame_ids[lo], "max_frame": frame_ids[hi],
                    "interpretation": "Observed interval only; these are projected angles, not ideal targets."}
    scores = {s: sum(summaries.get(f"{s}.{m}", {}).get("coverage", 0) for m in ("knee", "hip")) for s in ("left", "right")}
    side = config.near_side if config.near_side != "unknown" else max(scores, key=scores.get)
    review_series = {m: np.array([np.nan if x is None else x for x in series[side][m]["smoothed"]]) for m in METRICS}
    keyframes = select_keyframes(review_series)
    cycles = cycles_from_thigh(review_series["thigh"])
    coverage = min((summaries.get(f"{side}.{m}", {}).get("coverage", 0) for m in ("knee", "hip")), default=0)
    warnings = ["All angles are two-dimensional pose estimates, not clinical measurements.",
                "Only the selected passage is analyzed; observed extrema may not represent a complete stride."]
    if config.camera_moving:
        warnings.append("Camera movement and roll affect trunk/thigh orientation relative to frame vertical.")
    if not config.timing_verified:
        warnings.append("Capture timing is unverified. The time axis describes decoded media, not sprint timing.")
    if config.near_side == "unknown":
        warnings.append(f"Review uses the model's {side} side based on coverage. Confirm the camera-facing side before interpreting anatomy.")
    if coverage < 0.85:
        warnings.append("Some core joints have limited visibility. Missing spans are omitted from measurements.")
    quality = "usable" if coverage >= 0.85 else "limited" if coverage >= 0.5 else "insufficient"
    if not np.isfinite(points[:, :, :2]).any():
        quality = "insufficient"
    for k in keyframes:
        k["frame_id"] = frame_ids[k["index"]]
        k["time"] = times[k["index"]]
    summary = {"analysis_id": identity, "review_side": side, "quality": quality,
        "core_coverage": coverage, "warnings": warnings,
        "metrics": summaries, "cycles": cycles, "cycle_method": "Forward thigh extrema, not contact detection",
        "keyframes": keyframes, "frame_count": len(times), "subject_issues": dict(Counter(x for x in reasons if x)),
        "config": config.model_dump(), "frames": frame_ids, "times": times,
        "video": info.to_dict(), "analysis_dimensions": [w, h]}
    write_json(output / "summary.json", summary)
    write_json(output / "series.json", series)
    (output / "frames").mkdir(exist_ok=True)
    progress("Rendering annotated video", 0.70)
    # VFR encoded with per-frame PTS. Fourfold slowdown is an explicit display transform.
    playback_scale = 4.0
    writers = [VideoWriter(output / "annotated.mp4", w, h), VideoWriter(output / "original.mp4", w, h)]
    try:
        for j, (frame_id, t, rgb) in enumerate(iter_frames(video, info, config.start, config.end)):
            values = {m: series[side][m]["smoothed"][j] for m in METRICS}
            annotated = overlay(rgb, accepted[j], values, frame_id, config.score_threshold, side)
            pts = (t - times[0]) * playback_scale
            writers[0].write(annotated, pts)
            writers[1].write(rgb, pts)
            cv2.imwrite(str(output / "frames" / f"{frame_id:06d}.jpg"), cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
            if j % 20 == 0:
                progress("Rendering annotated video", 0.70 + 0.27 * j / len(times))
    finally:
        for writer in writers:
            writer.close()
    manifest = {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "analysis_id": identity,
        "created_at": datetime.now(timezone.utc).isoformat(), "input_sha256": info.sha256,
        "config": config.model_dump(), "model_sha256": tracker.model_hash,
        "model_source": "Google MediaPipe Pose Landmarker / float16 / version 1",
        "dependencies": {m: version(m) for m in ("mediapipe", "av", "numpy", "opencv-contrib-python", "scipy")},
        "frame_count": len(times), "first_source_frame": frame_ids[0], "last_source_frame": frame_ids[-1],
        "playback_time_scale": playback_scale, "duration_seconds": round(time.monotonic() - started, 2),
        "timing_basis": "Decoded presentation timestamps; no capture-time claim",
        "llm_generated": False}
    write_json(output / "manifest.json", manifest)
    progress("Analysis ready", 1.0)
    return summary


def load_analysis(directory: Path):
    return read_json(directory / "summary.json"), read_json(directory / "series.json")

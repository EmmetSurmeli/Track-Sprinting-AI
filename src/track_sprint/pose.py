"""One pose-model boundary, with conservative foreground-subject continuity."""
from pathlib import Path
import hashlib
import os
import urllib.request

import numpy as np

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{variant}/float16/1/pose_landmarker_{variant}.task"


def ensure_model(directory: Path, variant="full") -> Path:
    if variant not in ("full", "heavy"):
        raise ValueError("Unknown pose model.")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"pose_landmarker_{variant}.task"
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    request = urllib.request.Request(MODEL_URL.format(variant=variant), headers={"User-Agent": "TrackSprintAI/0.1"})
    temp = path.with_suffix(f".{os.getpid()}.partial")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temp.open("wb") as out:
            total = 0
            while data := response.read(1024 * 1024):
                total += len(data)
                if total > 100_000_000:
                    raise ValueError("Unexpected model size.")
                out.write(data)
        if total < 1_000_000:
            raise ValueError("The model download is incomplete.")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path


class PoseTracker:
    def __init__(self, model: Path):
        import mediapipe as mp
        self.mp = mp
        self.model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model), delegate=mp.tasks.BaseOptions.Delegate.CPU),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=2, min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5, min_tracking_confidence=0.5,
        )
        self.detector = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.previous = None
        self.previous_size = None
        self.last_timestamp = -1
        self.misses = 0

    def detect(self, rgb, seconds):
        timestamp = max(self.last_timestamp + 1, int(round(seconds * 1000)))
        self.last_timestamp = timestamp
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self.detector.detect_for_video(image, timestamp)
        candidates = []
        for pose in result.pose_landmarks:
            p = np.array([[j.x, j.y, j.visibility, j.presence] for j in pose])
            core = p[[11, 12, 23, 24, 25, 26, 27, 28], :2]
            extent = np.ptp(core, axis=0)
            size = float(np.linalg.norm(extent))
            center = p[[23, 24], :2].mean(axis=0)
            candidates.append((size, center, p))
        if not candidates:
            self.misses += 1
            return np.full((33, 4), np.nan), "No pose"
        candidates.sort(key=lambda c: c[0], reverse=True)
        if self.previous is None:
            if len(candidates) > 1 and candidates[1][0] > candidates[0][0] * 0.85:
                return np.full((33, 4), np.nan), "Multiple similarly sized athletes"
            chosen = candidates[0]
        else:
            nearby = [c for c in candidates if np.linalg.norm(c[1] - self.previous) < max(0.12, self.previous_size * 0.45)
                      and 0.5 < c[0] / max(self.previous_size, 1e-8) < 1.8]
            if not nearby:
                self.misses += 1
                return np.full((33, 4), np.nan), "Subject continuity uncertain"
            chosen = min(nearby, key=lambda c: np.linalg.norm(c[1] - self.previous))
        self.previous_size, self.previous, points = chosen
        self.misses = 0
        return points, ""

    def close(self):
        self.detector.close()


def trajectory_mask(points, width, height):
    """Mark isolated geometric discontinuities; preserve raw scores separately."""
    accepted = points.copy()
    xy = points[:, :, :2] * [width, height]
    for side in ([11, 23, 25, 27], [12, 24, 26, 28]):
        for a, b in zip(side[:-1], side[1:]):
            lengths = np.linalg.norm(xy[:, a] - xy[:, b], axis=1)
            good = np.isfinite(lengths) & (points[:, [a, b], 2:].min(axis=(1, 2)) >= 0.7)
            if good.sum() < 5:
                continue
            median = np.median(lengths[good])
            # Broad sanity bounds only: projection can legitimately shorten a limb.
            bad = (lengths < median * 0.35) | (lengths > median * 1.8)
            accepted[bad, a, 2:] = 0
            accepted[bad, b, 2:] = 0
    return accepted

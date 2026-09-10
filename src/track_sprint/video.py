"""Decode actual presentation timestamps; never infer sprint time from export FPS."""
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib

import av
import cv2
import numpy as np

MAX_BYTES = 100 * 1024 * 1024
MAX_FRAMES = 3600


class VideoError(ValueError):
    pass


@dataclass
class VideoInfo:
    width: int
    height: int
    codec: str
    duration: float
    nominal_fps: float
    declared_frames: int
    rotation: int
    sha256: str
    bytes: int

    def to_dict(self):
        return asdict(self)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_video(path: Path) -> VideoInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoError("The video is empty or missing. Choose the original file again.")
    if path.stat().st_size > MAX_BYTES:
        raise VideoError("Choose a video under 100 MB.")
    try:
        with av.open(str(path)) as c:
            if not c.streams.video:
                raise VideoError("This file has no video track.")
            s = c.streams.video[0]
            duration = float(s.duration * s.time_base) if s.duration else (c.duration or 0) / av.time_base
            if not 0 < duration <= 120:
                raise VideoError("Choose a clip between a fraction of a second and two minutes.")
            if s.width * s.height > 3840 * 2160 or min(s.width, s.height) < 128:
                raise VideoError("Choose a video between 128 pixels and 4K resolution.")
            frame = next(c.decode(s), None)
            if frame is None:
                raise VideoError("No frames could be decoded. Export an H.264 MP4 and try again.")
            rotation = int(round(float(getattr(frame, "rotation", 0) or s.metadata.get("rotate", 0)))) % 360
            w, h = (s.height, s.width) if rotation in (90, 270) else (s.width, s.height)
            return VideoInfo(w, h, s.codec_context.name, duration,
                float(s.average_rate or s.guessed_rate or 30), s.frames, rotation,
                file_hash(path), path.stat().st_size)
    except VideoError:
        raise
    except Exception as e:
        raise VideoError("The video could not be decoded. Try the original file or an H.264 MP4 export.") from e


def orient(rgb: np.ndarray, rotation: int) -> np.ndarray:
    # FFmpeg display rotation uses counter-clockwise positive angles.
    if rotation == 90:
        return cv2.rotate(rgb, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation == 270:
        return cv2.rotate(rgb, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(rgb, cv2.ROTATE_180)
    return rgb


def iter_frames(path: Path, info: VideoInfo, start: float = 0, end: float | None = None):
    """Yield original index, relative presentation seconds, aspect-preserved RGB."""
    end = info.duration if end is None else end
    previous = -1.0
    origin = None
    count = 0
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        for i, frame in enumerate(c.decode(s)):
            if frame.time is None:
                raise VideoError("This video is missing timestamps; export a standard MP4 first.")
            if origin is None:
                origin = float(frame.time)
            t = float(frame.time) - origin
            if t < previous:
                raise VideoError("Video timestamps run backwards. Export a standard MP4 first.")
            previous = t
            if t < start:
                continue
            if t >= end:
                break
            count += 1
            if count > MAX_FRAMES:
                raise VideoError("This interval has too many frames. Select a shorter passage.")
            rgb = orient(frame.to_ndarray(format="rgb24"), info.rotation)
            h, w = rgb.shape[:2]
            scale = min(1.0, 1280 / w, 1080 / h)
            if scale < 1:
                rgb = cv2.resize(rgb, (int(w * scale) // 2 * 2, int(h * scale) // 2 * 2), interpolation=cv2.INTER_AREA)
            yield i, t, rgb


def frame_at(path: Path, info: VideoInfo, t: float):
    # Decode order and original indexes stay consistent with analysis.
    for i, actual, rgb in iter_frames(path, info, max(0, t), info.duration + 0.1):
        return i, actual, rgb
    raise VideoError("The chosen frame is outside this video.")

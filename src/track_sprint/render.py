"""Overlay only observed pose data and export a browser-compatible video."""
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np

COLORS = {"left": (47, 204, 229), "right": (255, 158, 91)}  # RGB
EDGES = {"left": [(11, 13), (13, 15), (11, 23), (23, 25), (25, 27), (27, 29), (29, 31), (27, 31)],
         "right": [(12, 14), (14, 16), (12, 24), (24, 26), (26, 28), (28, 30), (30, 32), (28, 32)]}


def overlay(rgb, points, values, frame_id, threshold=0.7, near_side="unknown"):
    image = rgb.copy()
    h, w = image.shape[:2]
    if points is not None:
        xy = points[:, :2] * [w, h]
        finite = np.isfinite(points).all(axis=1) & (points[:, :2].min(axis=1) >= 0) & (points[:, :2].max(axis=1) <= 1)
        strong = finite & (points[:, 2:].min(axis=1) >= threshold)
        for side, edges in EDGES.items():
            for a, b in edges:
                if finite[a] and finite[b]:
                    color = COLORS[side] if strong[a] and strong[b] else (115, 127, 140)
                    cv2.line(image, tuple(xy[a].astype(int)), tuple(xy[b].astype(int)), color, 3 if strong[a] and strong[b] else 1, cv2.LINE_AA)
            for a in sorted(set(j for edge in edges for j in edge)):
                if finite[a]:
                    cv2.circle(image, tuple(xy[a].astype(int)), 4, COLORS[side] if strong[a] else (140, 140, 140), -1 if strong[a] else 1, cv2.LINE_AA)
        hip_id = 23 if near_side == "left" else 24
        if near_side != "unknown" and strong[hip_id]:
            x, y = xy[hip_id].astype(int)
            for dy in range(-100, 101, 14):
                cv2.line(image, (x, y + dy), (x, y + dy + 6), (213, 230, 225), 1, cv2.LINE_AA)
    panel = image.copy()
    cv2.rectangle(panel, (0, 0), (w, 88), (9, 17, 22), -1)
    image[:88] = cv2.addWeighted(panel[:88], 0.9, image[:88], 0.1, 0)
    cv2.putText(image, f"TRACK SPRINT  /  FRAME {frame_id:04d}", (18, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (229, 239, 235), 1, cv2.LINE_AA)
    pieces = []
    for name, label in [("knee", "KNEE"), ("hip", "TRUNK-THIGH"), ("trunk", "TRUNK/FRAME")]:
        v = values.get(name)
        pieces.append(f"{label}  {v:.0f} deg" if v is not None and np.isfinite(v) else f"{label}  --")
    cv2.putText(image, "     ".join(pieces), (18, 59), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (184, 243, 90), 1, cv2.LINE_AA)
    cv2.putText(image, "L / cyan    R / orange    Gray = low visibility    2D estimates", (18, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (245, 245, 245), 1, cv2.LINE_AA)
    return image


class VideoWriter:
    def __init__(self, path: Path, width, height):
        self.container = av.open(str(path), "w")
        self.stream = self.container.add_stream("libx264", rate=60)
        self.stream.width, self.stream.height = width, height
        self.stream.pix_fmt = "yuv420p"
        self.stream.options = {"crf": "20", "preset": "veryfast"}
        self.stream.time_base = Fraction(1, 60000)
        self.stream.codec_context.time_base = Fraction(1, 60000)
        self.last_pts = -1

    def write(self, rgb, seconds):
        frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
        frame.pts = max(self.last_pts + 1, round(seconds * 60000))
        frame.time_base = Fraction(1, 60000)
        self.last_pts = frame.pts
        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def close(self):
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()

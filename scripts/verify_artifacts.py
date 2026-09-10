"""Verify an actual saved analysis; optionally create a visual audit sheet."""
import argparse
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import av
import numpy as np
from PIL import Image, ImageDraw

from track_sprint.artifacts import read_json, write_json


def verify(directory, montage=False):
    s, m = read_json(directory / "summary.json"), read_json(directory / "manifest.json")
    series = read_json(directory / "series.json")
    n = s["frame_count"]
    assert s["analysis_id"] == m["analysis_id"]
    assert len(s["times"]) == len(s["frames"]) == n
    assert np.all(np.diff(s["times"]) > 0)
    assert len(set(s["frames"])) == n
    expected_times = (np.array(s["times"]) - s["times"][0]) * m["playback_time_scale"]
    for name in ("original.mp4", "annotated.mp4"):
        with av.open(str(directory / name)) as c:
            frames = list(c.decode(video=0))
        assert len(frames) == n, (name, "frame count")
        np.testing.assert_allclose([f.time for f in frames], expected_times, atol=1e-4)
    for side in series.values():
        for metric in side.values():
            assert len(metric["raw"]) == len(metric["smoothed"]) == n
            assert [v is None for v in metric["raw"]] == [v is None for v in metric["smoothed"]]
    for metric in s["metrics"].values():
        values = np.array([np.nan if v is None else v for v in series[metric["side"]][metric["metric"]]["smoothed"]])
        assert metric["min_frame"] == s["frames"][int(np.nanargmin(values))]
        assert metric["max_frame"] == s["frames"][int(np.nanargmax(values))]
        assert abs(metric["max"] - np.nanmax(values)) <= .051
    for fid in s["frames"]:
        assert (directory / "frames" / f"{fid:06d}.jpg").is_file()
    landmarks = np.load(directory / "landmarks.npz")
    assert landmarks["raw"].shape == landmarks["accepted"].shape == (n, 33, 4)
    assert landmarks["frame_ids"].tolist() == s["frames"]
    if montage:
        chosen = np.linspace(0, n - 1, min(24, n), dtype=int)
        sheet = Image.new("RGB", (1200, 6 * 280), "#0C1116")
        draw = ImageDraw.Draw(sheet)
        for cell, index in enumerate(chosen):
            fid = s["frames"][index]
            im = Image.open(directory / "frames" / f"{fid:06d}.jpg")
            p = landmarks["raw"][index]
            valid = np.isfinite(p).all(axis=1) & (p[:, 2:].min(axis=1) > .5)
            if valid.any():
                xy = p[valid, :2] * im.size
                lo, hi = xy.min(axis=0), xy.max(axis=0)
                im = im.crop((max(0, lo[0] - 35), max(0, lo[1] - 35),
                              min(im.width, hi[0] + 35), min(im.height, hi[1] + 35)))
            im.thumbnail((280, 250))
            x, y = (cell % 4) * 300, (cell // 4) * 280
            sheet.paste(im, (x + (300 - im.width) // 2, y + 25))
            draw.text((x + 10, y + 5), f"SOURCE FRAME {fid}", fill="#B8F35A")
        sheet.save(directory / "visual-audit.jpg", quality=92)
    result = {"structural_checks": "passed", "frame_count": n, "analysis_id": s["analysis_id"],
              "videos_aligned_to_source_times": True, "missing_spans_preserved": True,
              "angle_accuracy_validated": False, "live_llm_generated": m["llm_generated"]}
    write_json(directory / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--montage", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.montage), indent=2))

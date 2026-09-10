"""Read-only metadata/frame inspection; derived images stay in ignored artifacts."""
import argparse
import json
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("video")
parser.add_argument("--output", default="artifacts/inspection")
args = parser.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
with av.open(args.video) as container:
    stream = container.streams.video[0]
    print(json.dumps({"codec": stream.codec_context.name, "width": stream.width,
        "height": stream.height, "average_rate": str(stream.average_rate),
        "base_rate": str(stream.base_rate), "guessed_rate": str(stream.guessed_rate),
        "time_base": str(stream.time_base), "stream_duration": stream.duration,
        "container_duration": container.duration, "frames_declared": stream.frames,
        "metadata": stream.metadata}, indent=2))
    times, selected = [], []
    next_time = 0.0
    for i, frame in enumerate(container.decode(stream)):
        t = float(frame.time) if frame.time is not None else float(i / stream.average_rate)
        times.append(t)
        if t >= next_time:
            img = frame.to_image()
            img.thumbnail((480, 270))
            selected.append((i, t, img))
            next_time += 0.4
        if i > 10000:
            raise RuntimeError("Inspection frame limit exceeded")
    print(json.dumps({"decoded_frames": len(times), "first_time": times[0],
        "last_time": times[-1], "median_dt": float(np.median(np.diff(times))),
        "min_dt": float(np.min(np.diff(times))), "max_dt": float(np.max(np.diff(times)))}, indent=2))
    sheet = Image.new("RGB", (480 * 3, 300 * ((len(selected) + 2) // 3)), "#111820")
    draw = ImageDraw.Draw(sheet)
    for j, (i, t, img) in enumerate(selected):
        x, y = (j % 3) * 480, (j // 3) * 300
        sheet.paste(img, (x, y + 25))
        draw.text((x + 10, y + 6), f"Source frame {i} | decoder time {t:.3f}s", fill="white")
    sheet.save(out / "contact_sheet.jpg")
    (out / "timestamps.json").write_text(json.dumps(times))
    print(out / "contact_sheet.jpg")

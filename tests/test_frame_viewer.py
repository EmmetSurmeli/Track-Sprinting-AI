import base64
import io

from PIL import Image
import pytest
import numpy as np

from track_sprint.artifacts import write_json
from track_sprint.frame_viewer import frame_payload
from track_sprint.render import VideoWriter


def test_browser_previews_keep_source_mapping_and_missing_measurements(tmp_path):
    (tmp_path / "frames").mkdir()
    frame_ids = [10, 12, 15]
    colors = [(210, 20, 20), (20, 210, 20), (20, 20, 210)]
    for frame_id, color in zip(frame_ids, colors):
        Image.new("RGB", (2000, 1000), color).save(tmp_path / "frames" / f"{frame_id:06d}.jpg")
    write_json(tmp_path / "summary.json", {"analysis_id": "test", "frames": frame_ids,
        "times": [0.0, .02, .055], "review_side": "left"})
    write_json(tmp_path / "series.json", {"left": {name: {"smoothed": [12.5, None, -3.2]}
                                                   for name in ("knee", "hip", "trunk")}})
    payload = frame_payload(str(tmp_path), "test")
    assert payload["frames"] == frame_ids and payload["times"] == [0, .02, .055]
    assert all(m["values"] == [12.5, None, -3.2] for m in payload["metrics"])
    for encoded, expected in zip(payload["images"], colors):
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as im:
            assert im.size == (960, 480)
            assert all(abs(a-b) < 5 for a, b in zip(im.getpixel((100, 100)), expected))
    with pytest.raises(ValueError, match="does not match"):
        frame_payload(str(tmp_path), "another-analysis")


def test_original_contact_previews_preserve_decoded_order_without_overlays(tmp_path):
    writer = VideoWriter(tmp_path / "original.mp4", 128, 64)
    colors = [(210, 20, 20), (20, 210, 20), (20, 20, 210)]
    try:
        for i, color in enumerate(colors):
            writer.write(np.full((64, 128, 3), color, dtype=np.uint8), i * .04)
    finally:
        writer.close()
    summary = {"analysis_id": "original-test", "frames": [7, 9, 10], "times": [.01, .02, .04], "review_side": "left"}
    write_json(tmp_path / "summary.json", summary)
    write_json(tmp_path / "series.json", {"left": {name: {"smoothed": [None, 1, 2]}
                                                    for name in ("knee", "hip", "trunk")}})
    payload = frame_payload(str(tmp_path), "original-test", "original")
    assert payload["frames"] == [7, 9, 10] and payload["view"] == "original"
    for encoded, expected in zip(payload["images"], colors):
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as im:
            assert all(abs(a-b) < 8 for a, b in zip(im.getpixel((20, 20)), expected))
    summary.update(analysis_id="bad-count", frames=[7, 9, 10, 11])
    write_json(tmp_path / "summary.json", summary)
    with pytest.raises(ValueError, match="count"):
        frame_payload(str(tmp_path), "bad-count", "original")

from pathlib import Path
import json

import av
import numpy as np
import pytest

from track_sprint.artifacts import delete_session
from track_sprint.render import VideoWriter
from track_sprint.schemas import AnalysisConfig
from track_sprint.video import VideoError, inspect_video, iter_frames


def make_video(path):
    writer = VideoWriter(path, 320, 180)
    times = [0., .02, .04, .08, .1, .15, .18, .22, .24, .27, .3, .32]
    for i, t in enumerate(times):
        writer.write(np.full((180, 320, 3), 20 + i * 10, dtype=np.uint8), t)
    writer.close()
    return times


def test_variable_timestamps_and_frame_indexes_survive_decode(tmp_path):
    path = tmp_path / "variable.mp4"
    times = make_video(path)
    info = inspect_video(path)
    frames = list(iter_frames(path, info))
    assert [f[0] for f in frames] == list(range(len(times)))
    assert [f[1] for f in frames] == pytest.approx(times, abs=1e-4)
    selected = list(iter_frames(path, info, .08, .24))
    assert [f[0] for f in selected] == [3, 4, 5, 6, 7]


def test_corrupt_file_has_friendly_failure(tmp_path):
    bad = tmp_path / "bad.mov"
    bad.write_bytes(b"not a video")
    with pytest.raises(VideoError, match="could not be decoded"):
        inspect_video(bad)


def test_cleanup_cannot_delete_arbitrary_directory(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    outside = tmp_path / "important"
    outside.mkdir()
    with pytest.raises(ValueError):
        delete_session(outside, root)
    assert outside.exists()
    linked = root / "session-link"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        delete_session(linked, root)


def test_deterministic_pipeline_preserves_gaps_and_exports(tmp_path, monkeypatch):
    import track_sprint.pipeline as pipeline
    video = tmp_path / "synthetic.mp4"
    times = make_video(video)
    class TestTracker:
        model_hash = "synthetic-test-model"
        def __init__(self, model):
            self.i = -1
        def detect(self, rgb, seconds):
            self.i += 1
            p = np.ones((33, 4))
            p[:, :2] = .5
            for ids in ((11, 23, 25, 27), (12, 24, 26, 28)):
                p[list(ids), :2] = [[.4, .2], [.4, .4], [.5, .6], [.55, .8]]
            if self.i == 5:
                p[27, 2] = .1
            return p, ""
        def close(self):
            pass
    monkeypatch.setattr(pipeline, "PoseTracker", TestTracker)
    monkeypatch.setattr(pipeline, "ensure_model", lambda *args: tmp_path / "test-model")
    output = tmp_path / "result"
    summary = pipeline.analyze(video, AnalysisConfig(start=0, end=.33, near_side="left"), output, tmp_path)
    assert summary["frame_count"] == len(times)
    series = json.loads((output / "series.json").read_text())
    assert series["left"]["knee"]["smoothed"][5] is None
    for name in ("annotated.mp4", "original.mp4"):
        with av.open(str(output / name)) as c:
            decoded = list(c.decode(video=0))
        assert len(decoded) == len(times)
        assert [f.time for f in decoded] == pytest.approx(np.array(times) * 4, abs=1e-4)
    assert len(list((output / "frames").glob("*.jpg"))) == len(times)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["llm_generated"] is False
    assert manifest["analysis_id"] == summary["analysis_id"]


def test_failed_rerun_cannot_reuse_previous_completion_marker(tmp_path, monkeypatch):
    import track_sprint.pipeline as pipeline
    video = tmp_path / "synthetic.mp4"
    make_video(video)
    output = tmp_path / "result"
    output.mkdir()
    (output / "manifest.json").write_text('{"old":true}')
    def fail_model(*args):
        raise RuntimeError("Synthetic runtime failure")
    monkeypatch.setattr(pipeline, "ensure_model", fail_model)
    with pytest.raises(RuntimeError):
        pipeline.analyze(video, AnalysisConfig(start=0, end=.3), output, tmp_path)
    assert not (output / "manifest.json").exists()

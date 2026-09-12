from copy import deepcopy
from datetime import date
import json

import pytest

from track_sprint.artifacts import write_json
from track_sprint.history import HistoryStore, compare_sessions, compare_contact_sessions


@pytest.fixture
def source(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    summary = {"analysis_id": "a" * 64, "review_side": "left", "frame_count": 10, "core_coverage": 1,
        "config": {"near_side": "left", "camera_moving": False, "score_threshold": .7},
        "video": {"sha256": "video-a"}, "metrics": {
            "left.knee": {"side": "left", "metric": "knee", "label": "Knee flexion", "coverage": 1, "min": 10, "max": 100},
            "left.trunk": {"side": "left", "metric": "trunk", "label": "Trunk", "coverage": 1, "min": 0, "max": 20}}}
    manifest = {"analysis_id": "a" * 64, "pipeline_version": "1.0", "model_sha256": "model-a", "dependencies": {"pose": "1"}}
    write_json(directory / "summary.json", summary)
    write_json(directory / "manifest.json", manifest)
    write_json(directory / "series.json", {})
    for name in ("landmarks.npz", "original.mp4", "annotated.mp4"):
        (directory / name).write_bytes(b"synthetic fixture; not real media")
    (directory / "frames").mkdir()
    (directory / "frames" / "000001.jpg").write_bytes(b"synthetic fixture")
    (directory / ".env").write_text("DO_NOT_COPY_TEST_SECRET")
    return directory


def test_history_persists_and_same_analysis_updates_instead_of_duplicating(tmp_path, source):
    store = HistoryStore(tmp_path / "history")
    identity = store.save(source, date(2025, 12, 31), "First run", "100 m", "Coach feedback")
    store = HistoryStore(tmp_path / "history")  # A fresh browser/process uses the same durable store.
    assert store.list()[0]["session_date"] == "2025-12-31"
    store.save(source, date(2026, 1, 2), "Corrected date", "100 m", "Updated note")
    assert len(store.list()) == 1
    assert store.list()[0]["notes"] == "Updated note"
    assert not (store.directory(identity) / ".env").exists()
    assert (store.directory(identity) / "annotated.mp4").exists()


def test_date_edit_reorders_history_and_failed_copy_does_not_log(tmp_path, source):
    store = HistoryStore(tmp_path / "history")
    store.save(source, date(2026, 9, 10), "Run", "100 m")
    store.update("a" * 64, date(2024, 2, 29), "Leap day", "200 m", "Review note")
    assert store.list()[0]["session_date"] == "2024-02-29"
    assert store.list()[0]["event"] == "200 m"
    broken = HistoryStore(tmp_path / "broken")
    (source / "annotated.mp4").unlink()
    with pytest.raises(OSError):
        broken.save(source, date.today(), "Missing artifact", "100 m")
    assert broken.list() == []
    assert not list((tmp_path / "broken" / "analyses").iterdir())


def test_comparison_delta_is_numeric_and_excludes_incompatible_metrics(tmp_path, source):
    store = HistoryStore(tmp_path / "history")
    store.save(source, date.today(), "Test run", "100 m")
    old = store.list()[0]
    new = deepcopy(old)
    new["id"] = "b" * 64
    new["summary"]["video"]["sha256"] = "video-b"
    new["summary"]["metrics"]["left.knee"]["max"] = 110
    rows, warnings = compare_sessions(new, old)
    assert not warnings
    assert next(r for r in rows if r["Measurement"] == "Knee flexion · maximum")["Change (°)"] == 10
    new["summary"]["config"]["camera_moving"] = True
    rows, warnings = compare_sessions(new, old)
    assert len(rows) == 2 and warnings
    new["summary"]["metrics"]["left.knee"]["coverage"] = .5
    assert compare_sessions(new, old)[0] == []


@pytest.mark.parametrize("change", ["event", "side", "model", "threshold"])
def test_comparison_refuses_mismatched_setup(tmp_path, source, change):
    store = HistoryStore(tmp_path / "history")
    store.save(source, date.today(), "Run", "100 m")
    old = store.list()[0]
    new = deepcopy(old)
    new["id"] = "b" * 64
    if change == "event": new["event"] = "200 m"
    if change == "side": new["summary"]["review_side"] = "right"
    if change == "model": new["manifest"]["model_sha256"] = "different"
    if change == "threshold": new["summary"]["config"]["score_threshold"] = .9
    rows, warnings = compare_sessions(new, old)
    assert not rows and warnings


def test_invalid_identifier_cannot_escape_history_root(tmp_path):
    store = HistoryStore(tmp_path / "history")
    with pytest.raises(ValueError):
        store.directory("../../outside")


def test_contact_annotations_survive_archive_and_reopen(tmp_path, source):
    annotations = {"analysis_id": "a" * 64, "marks": [], "timing_confirmed": False}
    results = {"analysis_id": "a" * 64, "contacts": [], "comparison": None}
    write_json(source / "contacts.json", annotations)
    write_json(source / "contact_results.json", results)
    store = HistoryStore(tmp_path / "history")
    identity = store.save(source, date.today(), "Contact review", "100 m")
    assert json.loads((store.directory(identity) / "contacts.json").read_text()) == annotations
    assert HistoryStore(tmp_path / "history").list()[0]["contact_results"] == results
    # Reviewing contacts on a reopened archive is immediately reflected in the calendar.
    results["contacts"] = [{"side": "left", "estimate_ms": None}]
    write_json(store.directory(identity) / "contact_results.json", results)
    assert HistoryStore(tmp_path / "history").list()[0]["contact_results"] == results


def test_contact_history_deltas_preserve_bounds_and_require_compatible_results():
    old = {"event": "100 m", "contact_results": {"method": "user-reviewed", "comparison": {"absolute_difference_percent": 0},
           "sides": {side: {"mean_ms": 100, "lower_ms": 96, "upper_ms": 104} for side in ("left", "right")}}}
    new = deepcopy(old)
    new["contact_results"]["sides"]["left"] = {"mean_ms": 98, "lower_ms": 94, "upper_ms": 102}
    rows = compare_contact_sessions(new, old)
    assert rows[0]["Change (ms)"] == -2
    assert rows[0]["Change lower bound (ms)"] == -10
    assert rows[0]["Change upper bound (ms)"] == 6
    new["event"] = "200 m"
    assert compare_contact_sessions(new, old) == []
    new["event"] = "100 m"
    new["contact_results"]["comparison"] = None
    assert compare_contact_sessions(new, old) == []


def test_explicit_resave_refreshes_reviews_and_reports(tmp_path, source):
    store = HistoryStore(tmp_path/'history')
    identity = store.save(source, date.today(), 'Run', '100 m')
    write_json(source/'posture_review.json', {'frame':155, 'geometry_checked':True})
    (source/'reports').mkdir()
    write_json(source/'reports'/'report.json', {'report':'Test report, not actual coaching'})
    store.save(source, date.today(), 'Run', '100 m')
    archived = store.directory(identity)
    assert json.loads((archived/'posture_review.json').read_text())['frame'] == 155
    assert (archived/'reports'/'report.json').exists()
    # Saving directly from the archive must not copy a file onto itself.
    store.save(archived, date.today(), 'Run', '100 m')
    (source/'posture_review.json').unlink()
    store.save(source, date.today(), 'Run', '100 m')
    assert not (archived/'posture_review.json').exists()
    assert not (archived/'.env').exists()

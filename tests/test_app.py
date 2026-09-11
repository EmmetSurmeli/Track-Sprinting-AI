from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACK_SPRINT_HISTORY_DIR", str(tmp_path / "test-history"))


def test_empty_app_loads_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "Sprint review"
    assert any(b.label == "Clear this session" for b in app.button)


@pytest.mark.skipif(not (ROOT / "artifacts/demo/manifest.json").exists(), reason="Private local demo is not part of the repository")
def test_saved_demo_frame_selection_and_report_setup():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    next(b for b in app.button if b.label == "Open saved analysis").click().run(timeout=30)
    assert not app.exception
    next(b for b in app.button if b.label.startswith("Forward thigh position")).click().run(timeout=30)
    assert not app.exception
    assert app.session_state["frame_index"] == 53
    assert app.session_state["frame_command"] == 1
    # Upgrading an already-open session can remove the old slider-owned key.
    del app.session_state["frame_index"]
    app.run(timeout=30)
    assert not app.exception
    assert 0 <= app.session_state["frame_index"] < 114
    # The final UI includes both local exports and the honest AI connection state.
    assert len(app.tabs) == 6


def test_empty_calendar_accessible_without_an_upload():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    app.radio(key="workspace_page").set_value("Calendar & progress").run()
    assert not app.exception
    assert any("calendar is empty" in i.value for i in app.info)
    app.selectbox(key="log_month").set_value(2).run()
    app.number_input(key="log_year").set_value(2024).run()
    assert not app.exception
    assert any(b.key == "day-2024-02-29" for b in app.button)


@pytest.mark.skipif(not (ROOT / "artifacts/demo/manifest.json").exists(), reason="Private demo not bundled")
def test_calendar_save_edit_reopen_and_persistence():
    from datetime import date
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    next(b for b in app.button if b.label == "Open saved analysis").click().run(timeout=30)
    next(d for d in app.date_input if d.label == "Recording date").set_value(date(2026, 9, 10))
    next(b for b in app.button if b.label == "Save to calendar").click().run(timeout=30)
    assert not app.exception
    app.radio(key="workspace_page").set_value("Calendar & progress").run()
    app.button(key="day-2026-09-10").click().run()
    assert not app.exception
    next(d for d in app.date_input if d.label == "Recording date").set_value(date(2026, 8, 31))
    next(b for b in app.button if b.label == "Save log changes").click().run()
    assert not app.exception
    assert app.selectbox(key="log_month").value == 8
    next(b for b in app.button if b.label == "Open this analysis").click().run(timeout=30)
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Sprint review"
    next(b for b in app.button if b.label == "Clear this session").click().run()
    app.radio(key="workspace_page").set_value("Calendar & progress").run()
    assert not app.exception
    assert any("1 total" in c.value for c in app.caption)


@pytest.mark.skipif(not (ROOT / "artifacts/demo/manifest.json").exists(), reason="Private demo not bundled")
def test_contact_marking_with_unverified_timing_and_profile_context():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    next(b for b in app.button if b.label == "Open saved analysis").click().run(timeout=30)
    assert not app.exception
    assert any(t.label == "Contacts & sides" for t in app.tabs)
    assert next(s for s in app.selectbox if s.label == "Contact side").value is None
    assert next(s for s in app.selectbox if s.label == "Proposed touchdown frame").value is None
    assert not any(b.label == "Add reviewed contact" for b in app.button)
    next(s for s in app.selectbox if s.label == "Contact side").select("left").run()
    next(s for s in app.selectbox if s.label == "Proposed touchdown frame").select(437).run()
    next(s for s in app.selectbox if s.label == "Proposed toe-off frame").select(438).run()
    next(c for c in app.checkbox if c.label.startswith("I checked both transitions")).check().run()
    next(b for b in app.button if b.label == "Add reviewed contact").click().run()
    assert not app.exception
    assert any("milliseconds is withheld" in i.value for i in app.info)
    next(n for n in app.number_input if n.label == "Age in years (optional)").set_value(16).run()
    next(s for s in app.selectbox if s.label == "Sex for research context (optional)").select("Female").run()
    next(s for s in app.selectbox if s.label == "Injury context").select("Current symptoms").run()
    assert not app.exception
    assert any("this review stays observational" in w.value for w in app.warning)

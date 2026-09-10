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
    assert any("Source frame 489" in m.value for m in app.markdown)
    # The final UI includes both local exports and the honest AI connection state.
    assert len(app.tabs) == 4


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

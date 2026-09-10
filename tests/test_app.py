from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


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

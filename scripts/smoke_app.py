"""Optional real-video Streamlit smoke test. Requires ignored local demo_input.mov.

No API calls. Run in a normal desktop session so the native Mac pose runtime can initialize.
"""
from pathlib import Path
import json

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "artifacts" / "demo_input.mov").exists():
    raise SystemExit("This optional author-demo check requires artifacts/demo_input.mov.")
app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
next(b for b in app.button if b.label == "Use my demo clip").click().run(timeout=30)
assert not app.exception
next(b for b in app.button if b.label == "Analyze passage").click().run(timeout=300)
assert not app.exception
directory = Path(app.session_state["analysis_dir"])
summary = json.loads((directory / "summary.json").read_text())
assert summary["frame_count"] == 114
assert summary["frames"][0] == 436
assert summary["frames"][-1] == 549
assert (directory / "annotated.mp4").exists()
assert not json.loads((directory / "manifest.json").read_text())["llm_generated"]
print("Real-video app workflow passed: select demo → configure → child-process analysis → render review.")

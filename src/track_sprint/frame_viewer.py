"""Browser-side frame inspection; only settled selections return to Python."""
import base64
import io
from pathlib import Path

from PIL import Image
import av
import streamlit as st
import streamlit.components.v2 as components

from .artifacts import read_json
from .metrics import METRICS

ASSETS = Path(__file__).parent / "viewer"


@st.cache_data(show_spinner=False, max_entries=3, ttl=3600)
def frame_payload(directory: str, analysis_id: str, view="overlay"):
    """Cache compressed previews, retaining every source frame and its measured values."""
    root = Path(directory)
    summary, series = read_json(root / "summary.json"), read_json(root / "series.json")
    if summary["analysis_id"] != analysis_id:
        raise ValueError("Frame viewer analysis does not match its measurements.")
    def source_images():
        if view == "original":
            with av.open(str(root / "original.mp4")) as container:
                for frame in container.decode(video=0):
                    yield Image.fromarray(frame.to_ndarray(format="rgb24"))
        else:
            for frame_id in summary["frames"]:
                with Image.open(root / "frames" / f"{frame_id:06d}.jpg") as source:
                    yield source

    images = []
    for source in source_images():
        preview = source.convert("RGB")
        preview.thumbnail((960, 640))
        buffer = io.BytesIO()
        preview.save(buffer, format="JPEG", quality=80)
        images.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
    if len(images) != len(summary["frames"]):
        raise ValueError("Frame preview count does not match its measurements.")
    side = summary["review_side"]
    return {"analysis_id": analysis_id, "view": view, "images": images, "frames": summary["frames"],
            "times": summary["times"], "side": side,
            "metrics": [{"name": name, "label": METRICS[name], "values": series[side][name]["smoothed"]}
                        for name in ("knee", "hip", "trunk")]}


def show_frame_viewer(directory, summary, *, namespace="review", view="overlay", on_boundary=None):
    viewer = components.component("sprint_frame_viewer", html=(ASSETS / "viewer.html").read_text(),
                                  css=(ASSETS / "viewer.css").read_text(), js=(ASSETS / "viewer.js").read_text())
    identity = summary["analysis_id"]
    key = "frame-viewer-" + namespace + "-" + identity
    index_key = "frame_index" if namespace == "review" else namespace + "_frame_index"
    # Also migrate live sessions whose former slider-owned key was cleaned up.
    previous = st.session_state.get(key, {}).get("index", 0)
    st.session_state[index_key] = max(0, min(summary["frame_count"] - 1,
        st.session_state.get(index_key, previous)))

    def selected():
        index = st.session_state[key].get("index")
        if isinstance(index, int) and 0 <= index < summary["frame_count"]:
            st.session_state[index_key] = index

    def marked():
        event = st.session_state[key].get("boundary")
        if (on_boundary and isinstance(event, dict) and event.get("kind") in ("touchdown", "toeoff")
                and isinstance(event.get("index"), int) and 0 <= event["index"] < summary["frame_count"]):
            st.session_state[index_key] = event["index"]
            on_boundary(event["kind"], summary["frames"][event["index"]])

    payload = frame_payload(str(directory), identity, view)
    viewer(key=key, data={**payload, "index": st.session_state[index_key], "allow_marking": on_boundary is not None,
                         "command": st.session_state.get("frame_command", 0) if namespace == "review" else 0},
           default={"index": st.session_state[index_key]}, on_index_change=selected, on_boundary_change=marked)

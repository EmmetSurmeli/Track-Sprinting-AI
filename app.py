"""Local Streamlit entry point. Run with: .venv/bin/streamlit run app.py"""
from pathlib import Path
from datetime import date
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / "cache" / "matplotlib"))

import streamlit as st
from dotenv import load_dotenv

from track_sprint.artifacts import clean_expired_sessions, delete_session, read_json, stable_hash, write_json
from track_sprint.charts import motion_figure
from track_sprint.calendar_ui import show_calendar
from track_sprint.history import HistoryStore
from track_sprint.coaching import CoachingError, DEFAULT_MODEL, generate_report, library, report_markdown
from track_sprint.metrics import METRICS
from track_sprint.pipeline import PIPELINE_VERSION, load_analysis
from track_sprint.schemas import AnalysisConfig, AthleteProfile
from track_sprint.video import VideoError, frame_at, inspect_video

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Track Sprint AI · Motion review", page_icon="🏁", layout="wide")
st.markdown("""<style>
  .block-container {max-width:1360px; padding-top:2rem; padding-bottom:3rem}
  h1 {font-size:2.65rem!important; letter-spacing:-.07rem; font-weight:650!important}
  h2 {font-size:1.45rem!important; letter-spacing:-.025rem}
  h3 {font-size:1.1rem!important}
  [data-testid=stSidebar] {border-right:1px solid #25313A}
  [data-testid=stMetric] {background:#151F27; border:1px solid #28363F; padding:16px; border-radius:12px}
  [data-testid=stMetricLabel] {color:#A8B8BC}
  [data-testid=stMetricValue] {font-size:1.7rem; letter-spacing:-.04rem}
  .eyebrow {font-size:11px; color:#B8F35A; font-weight:700; letter-spacing:.18em; margin-bottom:6px}
  .subline {color:#9DB0B6; font-size:15px; margin-top:-10px; margin-bottom:22px}
  .note {padding:16px 20px; border-left:3px solid #B8F35A; background:#17231D; border-radius:0 10px 10px 0; color:#CDDBC9; margin:16px 0}
  .step {font-size:12px; letter-spacing:.12em; color:#A7B6BC; margin-top:18px; margin-bottom:8px}
  .stButton>button {border-radius:8px}
  [data-testid=stTabs] {margin-top:20px}
</style>""", unsafe_allow_html=True)

SESSIONS = ROOT / "artifacts" / "sessions"
SESSIONS.mkdir(parents=True, exist_ok=True)
if "session_dir" not in st.session_state:
    clean_expired_sessions(SESSIONS)
    session_dir = SESSIONS / ("session-" + uuid.uuid4().hex)
    session_dir.mkdir()
    st.session_state.session_dir = str(session_dir)
session_dir = Path(st.session_state.session_dir)
session_dir.mkdir(exist_ok=True)
session_dir.touch(exist_ok=True)
history = HistoryStore(Path(os.environ.get("TRACK_SPRINT_HISTORY_DIR", str(ROOT / "artifacts" / "history"))))


def set_analysis(directory):
    st.session_state.analysis_dir = str(directory)
    st.session_state.frame_index = 0
    st.session_state.pop("report", None)
    st.session_state.pop("report_signature", None)


def adopt_source(path, label):
    info = inspect_video(path)
    st.session_state.source_path = str(path)
    st.session_state.source_label = label
    st.session_state.source_info = info
    st.session_state.demo_selection = False
    st.session_state.pop("analysis_dir", None)
    st.session_state.pop("report", None)


def jump_to(index):
    st.session_state.frame_index = index


def export_bundle(directory):
    out = io.BytesIO()
    # Whitelist only derived data. Never include uploads, secrets or unrelated local files.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("summary.json", "series.json", "manifest.json", "landmarks.npz", "annotated.mp4"):
            path = directory / name
            if path.is_file():
                z.write(path, name)
        for path in sorted((directory / "reports").glob("*.json")):
            z.write(path, "reports/" + path.name)
    return out.getvalue()


with st.sidebar:
    st.markdown('<div class="eyebrow">TRACK SPRINT AI</div>', unsafe_allow_html=True)
    st.caption("A local motion review workspace")
    if page := st.session_state.pop("pending_workspace", None):
        st.session_state.workspace_page = page
    workspace_page = st.radio("Workspace", ["Sprint review", "Calendar & progress"], key="workspace_page")
    st.markdown("### Athlete profile")
    event = st.selectbox("Event", ["100 m", "200 m", "400 m", "Other sprint"])
    experience = st.selectbox("Experience", ["Beginner", "Intermediate", "Experienced"], index=1)
    goal = st.text_area("What do you want to review?", "Understand my upright sprint mechanics", max_chars=500, height=90)
    with st.expander("Optional context"):
        age = st.selectbox("Age band", ["Prefer not to say", "Under 18", "18–24", "25+"])
        height = st.number_input("Height (cm)", min_value=80., max_value=250., value=None, step=1.)
        weight = st.number_input("Weight (kg)", min_value=20., max_value=250., value=None, step=1.)
        injury = st.text_area("Anything affecting training?", max_chars=500, help="Optional. Included in the API request when you generate a report, but not saved in exported input data.")
        pain = st.checkbox("I have pain during running")
    profile = AthleteProfile(event=event, experience=experience, goal=goal, age_band=age,
                             height_cm=height, weight_kg=weight, injury_context=injury, current_pain=pain)
    st.divider()
    st.markdown("### AI connection")
    key = st.text_input("OpenAI API key", type="password", placeholder="Enter your project API key",
                        help="Kept in this browser session. Never written to the project or exported.")
    api_key = key or os.environ.get("OPENAI_API_KEY", "")
    st.caption("Key available" if api_key else "Local video analysis works without a key.")
    with st.expander("Set up an API key"):
        st.markdown("1. Open [OpenAI Platform](https://platform.openai.com/).\n2. Add a payment method or credits under API billing. ChatGPT billing is separate.\n3. Create a project API key under **API keys**.\n4. Paste it into the private field above.")
        st.caption("Only Generate coaching makes a paid request. Each report is limited to two attempts and cached for the same analysis and profile.")
    st.divider()
    st.caption("Your video and pose tracking stay on this computer. AI generation sends the measurement summary, profile and selected research summaries to OpenAI.")
    if st.button("Clear this session", width="stretch"):
        delete_session(session_dir, SESSIONS)
        st.session_state.clear()
        st.rerun()
    st.caption("Temporary files expire after 24 hours of inactivity. Your saved training calendar persists on this computer.")

st.markdown('<div class="eyebrow">MOTION LAB / LOCAL MVP</div>', unsafe_allow_html=True)
st.title("Sprint review" if workspace_page == "Sprint review" else "Calendar & progress")
st.markdown('<div class="subline">See the movement. Inspect the measurement. Build a better conversation with your coach.</div>', unsafe_allow_html=True)
if workspace_page == "Calendar & progress":
    show_calendar(history, set_analysis)
    st.stop()

has_result = bool(st.session_state.get("analysis_dir"))
with st.expander("01  ·  Footage & analysis settings", expanded=not has_result):
    a, b = st.columns([1.5, 1], gap="large")
    with a:
        upload = st.file_uploader("Choose a sprint video", type=["mov", "mp4", "m4v"],
                                  help="Maximum 100 MB, up to 4K. Select a short, side-on passage after upload.")
        if upload:
            identity = hashlib.sha256(upload.getbuffer()).hexdigest()
            if st.session_state.get("upload_id") != identity:
                dest = session_dir / f"input-{identity[:16]}.mov"
                dest.write_bytes(upload.getbuffer())
                try:
                    adopt_source(dest, upload.name)
                    st.session_state.upload_id = identity
                except VideoError as e:
                    st.error(str(e))
                    dest.unlink(missing_ok=True)
        buttons = st.columns(2)
        demo_source = ROOT / "artifacts" / "demo_input.mov"
        if demo_source.exists() and buttons[0].button("Use my demo clip", width="stretch"):
            dest = session_dir / "input.mov"
            shutil.copyfile(demo_source, dest)
            adopt_source(dest, "My local demo clip")
            st.session_state.demo_selection = True
            st.rerun()
        demo = ROOT / "artifacts" / "demo"
        if (demo / "manifest.json").exists() and buttons[1].button("Open saved analysis", width="stretch"):
            dest = session_dir / "saved-demo"
            shutil.copytree(demo, dest, dirs_exist_ok=True)
            set_analysis(dest)
            st.rerun()
    with b:
        st.markdown("**A useful recording**")
        st.markdown("- One main athlete, head and feet in view.\n- Camera close to side-on, with minimal roll.\n- A short passage during the sprint phase you want to review.")
        st.caption("Side-on means you see the runner's profile as they pass across the picture. Slow motion is welcome; capture timing is treated as unverified.")
    if st.session_state.get("source_path"):
        path = Path(st.session_state.source_path)
        info = st.session_state.source_info
        st.caption(f"{st.session_state.source_label} · {info.width} × {info.height} · decoded duration {info.duration:.2f} s")
        dstart, dend = (2.55, 3.20) if st.session_state.get("demo_selection") and info.duration > 3.2 else (0.0, min(2.0, info.duration))
        interval = st.slider("Passage to analyze · decoded media seconds", 0.0, float(round(info.duration, 3)),
            (dstart, min(dend, float(round(info.duration, 3)))), step=0.01, key=f"interval-{info.sha256}")
        setting_cols = st.columns(3)
        direction = setting_cols[0].selectbox("Runner travels", ["Left", "Right"])
        side = setting_cols[1].selectbox("Camera-facing anatomical side", ["Unknown", "Left", "Right"],
            help="The athlete's own left/right side, not the side of the screen. Leave Unknown if unsure.")
        moving = setting_cols[2].checkbox("Camera pans or moves", value=True)
        log_date = st.date_input("Recording date · saved to your calendar", value=date.today(),
            min_value=date(1900, 1, 1), max_value=date(2100, 12, 31), key="analysis_date")
        log_notes = st.text_input("Session note (optional)", max_chars=1000, key="analysis_notes",
                                placeholder="e.g. Upright sprinting after warm-up; coach asked me to review recovery")
        st.caption("Completed results are saved locally to this date, including the reviewed video passage. You can edit the date and notes later.")
        if interval[1] - interval[0] > 10 or interval[1] <= interval[0]:
            st.warning("Select a positive passage no longer than ten decoded seconds.")
        else:
            try:
                previews = st.columns(3)
                for col, t, label in zip(previews, [interval[0], sum(interval) / 2, max(interval[0], interval[1] - .03)], ["Start", "Middle", "End"]):
                    i, actual, rgb = frame_at(path, info, t)
                    col.image(rgb, caption=f"{label} · source frame {i}", width="stretch")
                if st.button("Analyze passage", type="primary", width="stretch"):
                    config = AnalysisConfig(start=interval[0], end=interval[1], direction=direction.lower(),
                                            near_side=side.lower(), camera_moving=moving)
                    output = session_dir / ("analysis-" + stable_hash({"video": info.sha256, "config": config.model_dump(), "pipeline": PIPELINE_VERSION})[:16])
                    config_path = session_dir / "config.json"
                    write_json(config_path, config.model_dump())
                    if not (output / "manifest.json").exists():
                        with st.status("Tracking joints and rendering your passage…", expanded=True) as status:
                            st.write("The first run downloads the local pose model. No API key is needed.")
                            try:
                                result = subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze_video.py"),
                                    str(path), "--config", str(config_path), "--output", str(output)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
                                if result.returncode or not (output / "manifest.json").exists():
                                    status.update(label="Analysis could not finish", state="error")
                                    st.error("The local video/model runtime failed. Try a shorter, clearer MP4 passage. See README troubleshooting if this repeats.")
                                else:
                                    status.update(label="Analysis ready", state="complete")
                            except subprocess.TimeoutExpired:
                                st.error("Analysis exceeded five minutes. Select a shorter passage and retry.")
                    if (output / "manifest.json").exists():
                        set_analysis(output)
                        try:
                            saved_id = history.save(output, log_date, st.session_state.source_label, event, log_notes)
                            set_analysis(history.directory(saved_id))
                        except (OSError, ValueError) as e:
                            st.session_state.log_save_error = "Analysis completed, but calendar storage failed. Your result is still available; use Save to calendar to retry."
                        st.rerun()
            except VideoError as e:
                st.error(str(e))

if not st.session_state.get("analysis_dir"):
    st.markdown('<div class="note">Upload a clip to begin. Pose tracking and measurements run locally; generate an AI review when you are ready.</div>', unsafe_allow_html=True)
    st.stop()

directory = Path(st.session_state.analysis_dir)
summary, series = load_analysis(directory)
if message := st.session_state.pop("log_save_error", None):
    st.warning(message)
logged = next((e for e in history.list() if e["id"] == summary["analysis_id"]), None)
if logged:
    st.caption(f"Saved to your calendar · {logged['session_date']} · {logged['event']}")
else:
    with st.expander("Save this existing result to your calendar"):
        with st.form("save-existing-result"):
            existing_date = st.date_input("Recording date", date.today(), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
            existing_title = st.text_input("Session title", "Sprint review", max_chars=120)
            existing_notes = st.text_area("Session notes / coach feedback", max_chars=1000)
            if st.form_submit_button("Save to calendar"):
                try:
                    saved_id = history.save(directory, existing_date, existing_title or "Sprint review", event, existing_notes)
                    set_analysis(history.directory(saved_id))
                    st.rerun()
                except (OSError, ValueError):
                    st.error("Could not save the calendar entry. Your analysis is still available; check local disk space and retry.")
review_side = summary["review_side"]
metrics = summary["metrics"]
top = st.columns(4)
top[0].metric("Frames reviewed", summary["frame_count"])
top[1].metric("Core joint coverage", f"{summary['core_coverage']:.0%}")
top[2].metric("Review side", review_side.title())
top[3].metric("Tracking coverage", summary["quality"].title())
st.caption("Coverage is the fraction of frames passing visibility and geometry checks. It does not measure angle accuracy.")
if summary["config"]["near_side"] == "unknown":
    st.info("Camera-facing side is unconfirmed. The review side was selected from model coverage; confirm it before anatomical interpretation.")

review_tab, motion_tab, coach_tab, method_tab = st.tabs(["02  Frame review", "Motion curves", "03  AI coach", "Method & evidence"])
with review_tab:
    left, right = st.columns(2)
    left.markdown("**Original passage**")
    left.video(str(directory / "original.mp4"))
    right.markdown("**Pose overlay**")
    right.video(str(directory / "annotated.mp4"))
    st.caption("Both players show the selected passage at a deliberate 4× slowdown of decoded media time. Players operate independently. Use the frame inspector for exact alignment.")
    st.subheader("Frame inspector")
    idx = st.slider("Scrub the analyzed frames", 0, summary["frame_count"] - 1, key="frame_index",
                    format="%d", help="This index maps to the original decoded frame shown below.")
    fid = summary["frames"][idx]
    imcol, statcol = st.columns([2.5, 1], gap="large")
    imcol.image(str(directory / "frames" / f"{fid:06d}.jpg"), width="stretch")
    with statcol:
        st.markdown(f"**Source frame {fid}**")
        st.caption(f"Decoded media time {summary['times'][idx]:.4f} s · model {review_side} side")
        for name in ["knee", "hip", "trunk"]:
            value = series[review_side][name]["smoothed"][idx]
            st.metric(METRICS[name], "Unavailable" if value is None else f"{value:.1f}°")
    st.subheader("Positions worth reviewing")
    if not summary["keyframes"]:
        st.info("No reliable keyframes in this passage. Try a clearer side-on view.")
    else:
        for col, k in zip(st.columns(len(summary["keyframes"])), summary["keyframes"]):
            col.image(str(directory / "frames" / f"{k['frame_id']:06d}.jpg"), width="stretch")
            col.button(f"{k['label']} · {k['frame_id']}", key=f"keyframe-{k['index']}",
                       on_click=jump_to, args=(k["index"],), width="stretch")
    st.caption("These are observed projected-angle positions, not detected foot-contact events or ideal targets.")

with motion_tab:
    st.subheader("Movement across the passage")
    controls = st.columns([2, 1])
    sides = controls[0].multiselect("Model sides to display", ["left", "right"], default=[review_side])
    raw = controls[1].toggle("Show raw measurements", value=False)
    st.plotly_chart(motion_figure(summary, series, sides, summary["frames"][st.session_state.frame_index], raw), width="stretch")
    st.caption("Dashed lime line = inspected frame. Gaps remain gaps; low-visibility frames are not interpolated. Bilateral curves are descriptive and cannot establish an imbalance.")
    rows = [{"Measurement": m["label"], "Side": m["side"], "Observed min (°)": m["min"],
             "Observed max (°)": m["max"], "Valid coverage": f"{m['coverage']:.0%}"}
            for m in metrics.values() if m["side"] in sides]
    st.dataframe(rows, hide_index=True, width="stretch")
    if summary["cycles"]:
        st.caption("Repeated forward-thigh maxima delimit candidate cycles. They do not identify contact or establish true stride timing.")
        st.dataframe(summary["cycles"], hide_index=True, width="stretch")
    else:
        st.caption("No complete candidate thigh cycle found. Ranges describe only the selected passage.")

with coach_tab:
    st.subheader("A review you can trace")
    st.write("Generate a short coaching conversation from the measured passage and a reviewed research library. Each observation links back to source frames and evidence.")
    if pain:
        st.info("With current pain, this app offers recording review only. Discuss symptoms and return-to-training decisions with a qualified professional.")
    st.caption("Only the structured summary, your profile and research summaries are sent to OpenAI. Video frames and the original file stay local. OpenAI's API data policies apply.")
    signature = stable_hash({"analysis": summary["analysis_id"], "profile": profile.model_dump()})
    if st.button("Generate coaching", type="primary", disabled=not bool(api_key), width="stretch"):
        try:
            with st.spinner("Connecting measured frames to research…"):
                saved, cached = generate_report(summary, profile, api_key, directory)
            st.session_state.report = saved
            st.session_state.report_signature = signature
            st.success("Loaded the matching saved report. No API call made." if cached else "AI report generated and reference checks passed.")
        except CoachingError as e:
            st.error(str(e))
    if not api_key:
        st.info("Add your API key in the sidebar to enable generation. The rest of the app is ready for local review.")
    saved = st.session_state.get("report") if st.session_state.get("report_signature") == signature else None
    if saved:
        report, ctx = saved["report"], saved["context"]
        st.markdown(report["overview"])
        sources = {s["id"]: s for s in ctx["evidence"]}
        acts = {a["id"]: a for a in ctx["activities"]}
        for n, item in enumerate(report["observations"]):
            with st.container(border=True):
                st.markdown(f"### {item['title']}")
                st.write(item["explanation"])
                for ref in item["metric_refs"]:
                    m = ctx["facts"][ref]
                    st.caption(f"Measured · {m['side']} {m['label']} · {m['min']}–{m['max']}° in this passage · {m['coverage']:.0%} valid coverage")
                for fid in item["frame_refs"]:
                    st.button(f"Inspect source frame {fid}", key=f"report-{n}-{fid}", on_click=jump_to,
                              args=(summary["frames"].index(fid),))
                st.caption("Use the Frame review tab to see the selected frame.")
                st.info(item["uncertainty"])
                for ref in item["evidence_refs"]:
                    s = sources[ref]
                    st.markdown(f"[{s['authors']} · {s['year']} — {s['title']}]({s['url']})")
                    st.caption(s["limitations"])
                for kind in ("cue", "drill", "exercise"):
                    if ref := item[f"{kind}_id"]:
                        a = acts[ref]
                        st.markdown(f"**{kind.title()} for coach discussion · {a['title']}**")
                        st.write(a["text"])
        st.markdown("**Next review**")
        st.write(report["next_review"])
        st.caption(f"Generated with OpenAI {saved['provenance']['model']}. References are checked by software; research interpretation still needs human review.")
        st.download_button("Download coaching report", report_markdown(saved), "sprint-review.md", "text/markdown")

with method_tab:
    st.subheader("What this app measures")
    st.write("MediaPipe estimates joints on each decoded frame. Python converts normalized points to aspect-correct pixels, rejects low-visibility geometry, then calculates projected angles. A centered five-frame filter smooths valid spans without filling missing data.")
    st.markdown("- **Knee flexion:** straight leg is zero; bending increases the angle.\n- **Trunk–thigh flexion:** signed angle from the downward trunk direction to the thigh; forward is positive. This is a hip-angle proxy.\n- **Trunk / frame vertical:** shoulder–hip orientation relative to the image's vertical.\n- **Thigh / downward vertical:** hip–knee orientation relative to downward image vertical; forward is positive.")
    for warning in summary["warnings"]:
        st.caption("• " + warning)
    st.write("This MVP does not estimate sprint speed, ground-contact time, forces, injury risk, strength deficits or clinically validated joint angles. A high tracking score does not remove projection error.")
    st.subheader("Research library")
    evidence, _ = library()
    for s in evidence["sources"]:
        with st.expander(f"{s['authors']} · {s['year']} · {s['title']}"):
            st.caption(s["type"] + " · " + s["location"] + " paraphrase")
            st.write(s["summary"])
            st.caption(s["population"])
            st.info(s["limitations"])
            st.link_button("Read source", s["url"])
    st.subheader("Reproducibility")
    st.json(read_json(directory / "manifest.json"), expanded=False)
    st.caption("Video, model and configuration hashes bind the saved result to its inputs. No LLM computes or edits the measurement files.")

st.divider()
downloads = st.columns(3)
downloads[0].download_button("Download annotated video", (directory / "annotated.mp4").read_bytes(), "sprint-overlay.mp4", "video/mp4", width="stretch")
downloads[1].download_button("Download measurements", (directory / "summary.json").read_bytes(), "sprint-measurements.json", "application/json", width="stretch")
downloads[2].download_button("Download analysis bundle", export_bundle(directory), "sprint-analysis.zip", "application/zip", width="stretch")
st.caption("TRACK SPRINT AI · Local research MVP · Educational video review, not a medical assessment")

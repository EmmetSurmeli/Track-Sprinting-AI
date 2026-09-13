"""Local Streamlit entry point. Run with: .venv/bin/streamlit run app.py"""
from pathlib import Path
from datetime import date
import hashlib
import io
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / "cache" / "matplotlib"))

import streamlit as st
from dotenv import load_dotenv

from track_sprint.artifacts import clean_expired_sessions, read_json, stable_hash, write_json
from track_sprint.charts import motion_figure
from track_sprint.calendar_ui import show_calendar
from track_sprint.contact_ui import show_contacts
from track_sprint.frame_viewer import show_frame_viewer
from track_sprint.history import HistoryStore
from track_sprint.movement_ui import show_movement
from track_sprint.coaching import CoachingError, DEFAULT_MODEL, PROMPT_VERSION, generate_report, library, report_markdown, comparison_text
from track_sprint.pipeline import PIPELINE_VERSION, load_analysis
from track_sprint.schemas import AnalysisConfig
from track_sprint.video import VideoError, inspect_video

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Track Sprint AI · Motion review", page_icon="🏁", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
  .block-container {max-width:1080px; padding-top:2rem; padding-bottom:3rem}
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
    st.session_state.pop("analysis_dir", None)
    st.session_state.pop("report", None)


def jump_to(index):
    st.session_state.frame_index = index
    st.session_state.frame_command = st.session_state.get("frame_command", 0) + 1


def export_bundle(directory):
    out = io.BytesIO()
    # Whitelist only derived data. Never include uploads, secrets or unrelated local files.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("summary.json", "series.json", "manifest.json", "landmarks.npz", "annotated.mp4", "contacts.json", "contact_results.json", "movement.json", "movement_review.json", "posture_review.json"):
            path = directory / name
            if path.is_file():
                z.write(path, name)
        for path in sorted((directory / "reports").glob("*.json")):
            z.write(path, "reports/" + path.name)
    return out.getvalue()


from track_sprint.profile_setup import load_profile, show_profile_setup
from track_sprint.analysis_cache import find_cached_analysis
from track_sprint.contacts import contact_results, load_contact_review
from track_sprint.movement import load_movement_evidence
from track_sprint.posture import posture_evidence

PROFILE_PATH = Path(os.environ.get('TRACK_SPRINT_PROFILE_PATH', str(ROOT/'artifacts'/'profile.json')))
CACHE = ROOT/'artifacts'/'cache'/'analyses'
profile = load_profile(PROFILE_PATH)
api_key = os.environ.get('OPENAI_API_KEY', '')

def start_new_video():
    for name in ('analysis_dir', 'source_path', 'source_info', 'upload_id', 'report', 'report_signature', 'cached_match'):
        st.session_state.pop(name, None)
    st.session_state.upload_version = st.session_state.get('upload_version', 0)+1
    st.session_state.pending_workspace = 'Sprint review'


with st.sidebar:
    st.markdown('### Track Sprint AI')
    if page := st.session_state.pop('pending_workspace', None):
        st.session_state.workspace_page = page
    workspace_page = st.radio('Workspace', ['Sprint review', 'Calendar & progress'], key='workspace_page')
    if profile:
        st.caption(f'{profile.event} · {profile.experience}')
        if st.button('Edit profile', width='stretch'):
            st.session_state.edit_profile = True
            st.rerun()
    with st.expander('Settings'):
        key = st.text_input('OpenAI API key', type='password', placeholder='Optional override')
        api_key = key or api_key
        st.caption('AI connected' if api_key else 'Add a key to enable coaching.')
        st.caption('Your key stays private. Video processing runs locally.')
    st.button('New video', width='stretch', on_click=start_new_video)

if profile is None or st.session_state.get('edit_profile'):
    show_profile_setup(PROFILE_PATH, profile)
    st.stop()

if workspace_page == 'Calendar & progress':
    st.title('Your training log')
    show_calendar(history, set_analysis)
    st.stop()

st.markdown('<div class="eyebrow">TRACK SPRINT AI</div>', unsafe_allow_html=True)
st.title('See your stride. Find your focus.')
st.caption(f'{profile.event} · {profile.experience}  /  Profile saved')

has_result = bool(st.session_state.get('analysis_dir'))
with st.expander('Upload another video' if has_result else 'Upload your run', expanded=not has_result):
    upload = st.file_uploader('Sprint video', type=['mov', 'mp4', 'm4v'], key=f"upload-{st.session_state.get('upload_version', 0)}")
    if upload:
        identity = hashlib.sha256(upload.getbuffer()).hexdigest()
        if st.session_state.get('upload_id') != identity:
            dest = session_dir/f'input-{identity[:16]}.mov'
            dest.write_bytes(upload.getbuffer())
            try:
                adopt_source(dest, upload.name)
                st.session_state.upload_id = identity
                match = find_cached_analysis(CACHE, identity) or find_cached_analysis(history.root/"analyses", identity)
                st.session_state.cached_match = (str(match[0]), match[1]) if match else None
                st.rerun()
            except VideoError as e:
                st.error(str(e))
    if st.session_state.get('source_path') and not st.session_state.get('analysis_dir'):
        path, info = Path(st.session_state.source_path), st.session_state.source_info
        st.video(str(path))
        match = st.session_state.get('cached_match')
        defaults = match[1] if match else dict(start=0., end=min(5., info.duration), direction='right', near_side='unknown', camera_moving=True)
        with st.expander('Trim & recording details'):
            interval = st.slider('Passage to analyze', 0., float(round(info.duration, 3)),
                (defaults['start'], min(defaults['end'], float(round(info.duration, 3)))), step=.01, key=f'interval-{info.sha256}')
            a, b = st.columns(2)
            direction = a.selectbox('Running direction', ['Right', 'Left'], index=int(defaults['direction']=='left'), key=f'direction-{info.sha256}')
            side = b.selectbox('Camera-facing side', ['Unknown', 'Left', 'Right'], index=['unknown','left','right'].index(defaults['near_side']), key=f'side-{info.sha256}')
            moving = st.checkbox('Camera moves', defaults['camera_moving'], key=f'moving-{info.sha256}')
            log_date = st.date_input('Recording date', date.today(), key='analysis_date')
            st.caption('Choose a clear side-on passage, up to ten media seconds. Leave anatomical side unknown if unsure.')
        if match:
            st.caption('This upload matches a previously analyzed recording. Its saved passage can be reused.')
        valid = 0 < interval[1]-interval[0] <= 10
        if not valid:
            st.warning('Choose a passage between zero and ten seconds.')
        if st.button('Analyze my run', type='primary', width='stretch', disabled=not valid):
            config = AnalysisConfig(start=interval[0], end=interval[1], direction=direction.lower(), near_side=side.lower(), camera_moving=moving)
            output = session_dir/('analysis-'+stable_hash({'video':info.sha256, 'config':config.model_dump(), 'pipeline':PIPELINE_VERSION})[:16])
            reused = bool(match and config.model_dump() == match[1])
            if reused:
                shutil.copytree(Path(match[0]), output, dirs_exist_ok=True)
            elif not (output/'manifest.json').exists():
                config_path = session_dir/'config.json'
                write_json(config_path, config.model_dump())
                with st.spinner('Tracking your movement…'):
                    try:
                        completed = subprocess.run([sys.executable, str(ROOT/'scripts'/'analyze_video.py'), str(path),
                            '--config', str(config_path), '--output', str(output)], cwd=ROOT, capture_output=True, text=True, timeout=300)
                        if completed.returncode:
                            st.error('Tracking could not finish. Try a shorter, clearer passage.')
                    except subprocess.TimeoutExpired:
                        st.error('Tracking took too long. Try a shorter passage.')
            if (output/'manifest.json').exists():
                set_analysis(output)
                st.session_state.analysis_reused = reused
                try:
                    saved_id = history.save(output, log_date, st.session_state.source_label, profile.event)
                    set_analysis(history.directory(saved_id))
                except (OSError, ValueError, sqlite3.Error):
                    st.session_state.log_save_error = 'Your analysis is ready, but it could not be saved to the calendar.'
                st.rerun()
    elif not st.session_state.get('analysis_dir'):
        st.caption('A short side-on clip works best. MOV and MP4 supported.')

if not st.session_state.get('analysis_dir'):
    st.stop()

directory = Path(st.session_state.analysis_dir)
summary, series = load_analysis(directory)
if message := st.session_state.pop('log_save_error', None):
    st.warning(message)
if st.session_state.get('analysis_reused'):
    st.caption('Showing saved tracking for this exact upload and passage.')
st.subheader('Your run, tracked')
st.video(str(directory/'annotated.mp4'))
st.caption('Slow playback · track the movement frame by frame below')

contacts = contact_results(summary, load_contact_review(directory, summary)) if (directory/'contacts.json').exists() else {'analysis_id':summary['analysis_id'], 'contacts':[]}
contacts['posture'] = posture_evidence(directory, summary)
movement = load_movement_evidence(directory, summary, contacts)
signature = stable_hash({'analysis':summary['analysis_id'], 'profile':profile.model_dump(), 'contacts':contacts,
                         'movement':movement, 'model':DEFAULT_MODEL, 'prompt':PROMPT_VERSION})
saved = st.session_state.get('report') if st.session_state.get('report_signature') == signature else None
if not saved:
    if st.button('Explain my technique', type='primary', width='stretch', disabled=not api_key):
        try:
            with st.spinner('Building your coaching review…'):
                report, cached = generate_report(summary, profile, api_key, directory)
            st.session_state.report = report
            st.session_state.report_signature = signature
            st.session_state.report_cached = cached
            st.rerun()
        except CoachingError as e:
            st.error(str(e))
    if not api_key:
        st.caption('Add your API key in Settings to get coaching.')

if saved:
    report, context = saved['report'], saved['context']
    acts = {a['id']:a for a in context['activities']}
    st.subheader('Technique analysis')
    st.write(report['overview'])
    st.subheader('What it means')
    for item in report['observations']:
        st.markdown(f"**{item['title']}**")
        st.write(item['explanation'])
    if not report['observations']:
        st.write('The measurements are available, but this report did not identify a supported technique finding.')
    st.subheader('Your focus')
    cue_ids = list(dict.fromkeys(i['cue_id'] for i in report['observations'] if i['cue_id']))
    for ref in cue_ids:
        st.markdown(f"**{acts[ref]['title']}**")
        st.write(acts[ref]['text'])
    if not cue_ids:
        st.write(report['next_review'])
    st.subheader('Training to discuss')
    training = list(dict.fromkeys(i[k] for i in report['observations'] for k in ('drill_id','exercise_id') if i[k]))
    for ref in training:
        st.markdown(f"**{acts[ref]['title']}**")
        st.write(acts[ref]['text'])
    if not training:
        st.write('Start with the technique focus above. This recording does not support a specific strength program.' if not profile.current_pain and profile.injury_status == 'None reported' else report['next_review'])
    with st.expander('Why this feedback? Measurements & sources'):
        st.write(report['personalization'])
        sources = {s['id']:s for s in context['evidence']}
        for n, item in enumerate(report['observations']):
            st.markdown(f"**{item['title']}**")
            for ref in item['metric_refs']:
                m = context['facts'][ref]
                value = f"{m['min']:g}" if m['min']==m['max'] else f"{m['min']:g}–{m['max']:g}"
                st.caption(f"{m['side']} · {m['label']} · {value} {m.get('units','degrees')}")
            for fid in item['frame_refs']:
                st.button(f'Inspect source frame {fid}', key=f'report-{n}-{fid}', on_click=jump_to, args=(summary['frames'].index(fid),))
            st.caption(item['uncertainty'])
            for ref in item['evidence_refs']:
                s = sources[ref]
                st.markdown(f"[{s['authors']} · {s['year']}]({s['url']})")
        st.caption(f"{'Saved AI report' if st.session_state.get('report_cached') else 'Generated with AI'} · {saved['provenance']['model']}")
    st.download_button('Download coaching', report_markdown(saved), 'sprint-review.md', 'text/markdown')
    st.button('Upload next video', width='stretch', on_click=start_new_video)

with st.expander('Explore your tracking & data'):
    st.subheader('Frame by frame')
    show_frame_viewer(directory, summary)
    with st.expander('Original video'):
        st.video(str(directory/'original.mp4'))
    with st.expander('Leg & arm motion'):
        show_movement(directory, summary, jump_to)
    with st.expander('Landing position & contact timing'):
        show_contacts(directory, summary)
    with st.expander('All measurements'):
        st.plotly_chart(motion_figure(summary, series, [summary['review_side']], summary['frames'][st.session_state.get('frame_index',0)], False), width='stretch')
        st.dataframe([{'Measurement':m['label'], 'Side':m['side'], 'Min (°)':m['min'], 'Max (°)':m['max'], 'Coverage':f"{m['coverage']:.0%}"} for m in summary['metrics'].values()], hide_index=True)
        st.caption('Projected measurements; tracking coverage does not establish anatomical accuracy.')
        for warning in summary['warnings']:
            st.caption(warning)
    downloads = st.columns(2)
    downloads[0].download_button('Tracked video', (directory/'annotated.mp4').read_bytes(), 'sprint-overlay.mp4','video/mp4')
    downloads[1].download_button('Analysis data', export_bundle(directory), 'sprint-analysis.zip','application/zip')

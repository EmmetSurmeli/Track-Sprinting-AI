from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from track_sprint.artifacts import write_json
from track_sprint.schemas import AthleteProfile

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_private_data(tmp_path, monkeypatch):
    monkeypatch.setenv('TRACK_SPRINT_HISTORY_DIR', str(tmp_path/'history'))
    monkeypatch.setenv('TRACK_SPRINT_PROFILE_PATH', str(tmp_path/'profile.json'))
    return tmp_path


def test_profile_first_then_upload_without_preset_clips(isolated_private_data):
    app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == 'Your sprint profile'
    next(b for b in app.button if b.label == 'Save profile & continue').click().run(timeout=30)
    assert not app.exception
    assert (isolated_private_data/'profile.json').stat().st_mode & 0o777 == 0o600
    assert app.title[0].value == 'See your stride. Find your focus.'
    assert not any(b.label in ['Open saved analysis', 'Use my demo clip'] for b in app.button)
    # A fresh browser loads the saved profile, without repeating onboarding.
    fresh = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert fresh.title[0].value == 'See your stride. Find your focus.'
    next(b for b in fresh.button if b.label == 'Edit profile').click().run()
    assert fresh.title[0].value == 'Your sprint profile'


def test_calendar_and_new_video_preserve_profile(isolated_private_data):
    write_json(isolated_private_data/'profile.json', AthleteProfile().model_dump())
    app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    app.radio(key='workspace_page').set_value('Calendar & progress').run()
    assert not app.exception
    assert app.title[0].value == 'Your training log'
    next(b for b in app.button if b.label == 'New video').click().run()
    assert not app.exception
    assert app.radio(key='workspace_page').value == 'Sprint review'
    assert (isolated_private_data/'profile.json').exists()


@pytest.mark.skipif(not (ROOT/'artifacts/second_demo/manifest.json').exists(), reason='Private recording not bundled')
def test_result_has_single_primary_video_and_collapsed_data(isolated_private_data):
    write_json(isolated_private_data/'profile.json', AthleteProfile().model_dump())
    app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    app.session_state['analysis_dir'] = str(ROOT/'artifacts/second_demo')
    app.session_state['frame_index'] = 0
    app.run(timeout=30)
    assert not app.exception
    assert not app.tabs
    assert any(h.value == 'Your run, tracked' for h in app.subheader)
    assert any(e.label == 'Explore your tracking & data' and not e.proto.expanded for e in app.expander)
    assert any(b.label == 'Explain my technique' for b in app.button)
    assert not any(b.label in ['Open saved analysis', 'Use my demo clip'] for b in app.button)

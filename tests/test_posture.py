from copy import deepcopy

import numpy as np
import pytest

from track_sprint.artifacts import write_json
from track_sprint.coaching import build_context, response_schema
from track_sprint.posture import PostureReview, landing_geometry, posture_evidence
from track_sprint.schemas import AthleteProfile


def fixture(tmp_path):
    points = np.full((33, 4), np.nan)
    points[[24, 26, 28]] = [[.4, .2, 1, 1], [.4, .4, 1, 1], [.6, .4, 1, 1]]
    summary = dict(analysis_id='example', frames=[100], times=[0.0], quality='usable',
                   analysis_dimensions=[100, 100], metrics={}, review_side='right', warnings=[],
                   config=dict(direction='right', score_threshold=.7, near_side='unknown', camera_moving=True))
    np.savez(tmp_path/'landmarks.npz', accepted=[points], frame_ids=[100])
    review = PostureReview(analysis_id='example', frame=100, side='right', geometry_checked=True)
    return points, summary, review


def test_landing_geometry_has_known_sign_scale_and_knee_angle(tmp_path):
    p, _, _ = fixture(tmp_path)
    a = landing_geometry(p, 'right', [100, 100], 'right', .7)
    assert a == pytest.approx(dict(ankle_ahead_percent=50, knee_flexion_deg=90))
    assert landing_geometry(p, 'right', [500, 500], 'right', .7) == pytest.approx(a)
    b = landing_geometry(p, 'right', [100, 100], 'left', .7)
    assert b['ankle_ahead_percent'] == -50 and b['knee_flexion_deg'] == 90
    # Correct pixels before angles, so a non-square recording is not distorted.
    assert landing_geometry(p, 'right', [200, 100], 'right', .7)['ankle_ahead_percent'] == pytest.approx(200/3)


@pytest.mark.parametrize('bad', ['occluded', 'missing', 'outside', 'degenerate'])
def test_unreliable_geometry_is_withheld(tmp_path, bad):
    p, _, _ = fixture(tmp_path)
    if bad == 'occluded': p[28, 2] = .4
    if bad == 'missing': p[28, 0] = np.nan
    if bad == 'outside': p[28, 0] = 1.2
    if bad == 'degenerate': p[28] = p[26]
    assert landing_geometry(p, 'right', [100, 100], 'right', .7) is None


def test_posture_requires_review_and_is_analysis_bound(tmp_path):
    _, s, r = fixture(tmp_path)
    assert not posture_evidence(tmp_path, s)['facts']
    r.geometry_checked = False
    assert not posture_evidence(tmp_path, s, r)['facts']
    r.geometry_checked = True
    r.analysis_id = 'another'
    with pytest.raises(ValueError, match='another analysis'): posture_evidence(tmp_path, s, r)
    r.analysis_id = s['analysis_id']; r.frame = 999
    with pytest.raises(ValueError, match='analyzed passage'): posture_evidence(tmp_path, s, r)


def test_posture_reaches_ai_without_inventing_contact_timing(tmp_path):
    _, s, r = fixture(tmp_path)
    write_json(tmp_path/'posture_review.json', r.model_dump())
    posture = posture_evidence(tmp_path, s)
    contacts = {'analysis_id':s['analysis_id'], 'contacts':[], 'posture':posture}
    ctx = build_context(s, AthleteProfile(), contacts)
    assert set(ctx['facts']) == {'right.landing_offset', 'right.landing_knee'}
    assert not ctx['camera_facing_side_confirmed']
    assert all(v['reference_frames'] == [100] for v in ctx['facts'].values())
    assert posture['placement'] == 'ahead'
    assert not any(v['units'] == 'ms' for v in ctx['facts'].values())
    assert ctx['reference_options']['right.landing_offset']['evidence_refs']
    assert 'cue-landing-review' in ctx['reference_options']['right.landing_offset']['activity_ids']
    response_schema(ctx).model_json_schema()
    poor = deepcopy(s); poor['quality'] = 'insufficient'
    assert not posture_evidence(tmp_path, poor)['facts']
    assert not build_context(poor, AthleteProfile(), contacts)['facts']

@pytest.mark.parametrize('mismatch', [None, 'video', 'frame', 'time', 'direction', 'tracking'])
def test_landing_annotation_reuse_requires_same_source_geometry(tmp_path, mismatch):
    from track_sprint.posture import reuse_posture_review
    old=tmp_path/'archive'/'old'; old.mkdir(parents=True)
    _, prior, review=fixture(old)
    prior['video']={'sha256':'same-video'}
    write_json(old/'summary.json',prior)
    write_json(old/'posture_review.json',review.model_dump())
    new=tmp_path/'new'; new.mkdir()
    points, current, _=fixture(new)
    current.update(analysis_id='new-analysis',video={'sha256':'same-video'})
    if mismatch=='video': current['video']['sha256']='other-video'
    if mismatch=='frame': current['frames']=[101]
    if mismatch=='time': current['times']=[1.0]
    if mismatch=='direction': current['config']['direction']='left'
    if mismatch=='tracking':
        points[28,2]=.1
        np.savez(new/'landmarks.npz',accepted=[points],frame_ids=[100])
    assert reuse_posture_review(new,current,tmp_path/'archive') == (mismatch is None)
    if mismatch is None:
        evidence=posture_evidence(new,current)
        assert evidence['available'] and 'Reused source-frame annotation' in evidence['review']['provenance']
        assert evidence['review']['analysis_id']=='new-analysis'
        assert not reuse_posture_review(new,current,tmp_path/'archive')  # No overwriting.

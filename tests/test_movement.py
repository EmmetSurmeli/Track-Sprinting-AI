from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest

from track_sprint.movement import arm_metrics, candidate_cycles, movement_evidence, movement_data, load_review
from track_sprint.coaching import build_context, response_schema
from track_sprint.schemas import AthleteProfile


def synthetic_movement():
    frames = list(range(400))
    times = np.arange(400) / 240
    data = {"analysis_id": "f" * 64, "frames": frames, "sides": {}}
    for side, peak, shift in [("left", 90, 0), ("right", 70, 50)]:
        # Repeated known extrema, with opposite phase. Comparing simultaneous knee
        # positions would be invalid; comparing complete cycles must recover 20 deg.
        a = 20 + (peak-20) * np.cos(2*np.pi*(np.arange(400)-25-shift)/100)
        cycles = candidate_cycles(a, frames, times)
        metrics = {name: {"values": list(a if name == "hip" else np.full(400, 100 if name == "elbow" else 20)),
                          "coverage": 1.0} for name in ("hip", "knee", "arm", "elbow")}
        data["sides"][side] = {"cycles": cycles, "metrics": metrics, "cycle_smoothing_stable": True}
    summary = {"analysis_id": data["analysis_id"], "frames": frames, "times": list(times),
        "review_side": "left", "quality": "usable", "metrics": {}, "warnings": ["Synthetic motion evaluation, not the athlete's video."],
        "config": {"near_side": "left", "camera_moving": False, "timing_verified": True}}
    review = {"stable_side_view": True, "labels_checked": True, "cycles_checked": True}
    return data, summary, review


def test_phase_aligned_cycles_recover_known_asymmetry_and_reversal():
    data, summary, review = synthetic_movement()
    e = movement_evidence(data, summary, review)
    c = next(c for c in e["comparisons"] if c["id"] == "cycle_front")
    assert c["left_minus_right"] == pytest.approx(20)
    assert c["direction"] == "left_greater"
    data["sides"]["left"], data["sides"]["right"] = data["sides"]["right"], data["sides"]["left"]
    reverse = movement_evidence(data, summary, review)
    c = next(c for c in reverse["comparisons"] if c["id"] == "cycle_front")
    assert c["direction"] == "right_greater" and c["left_minus_right"] == pytest.approx(-20)


def test_equal_cycles_do_not_invent_difference():
    data, summary, review = synthetic_movement()
    data["sides"]["right"] = deepcopy(data["sides"]["left"])
    assert all(c["direction"] == "similar" for c in movement_evidence(data, summary, review)["comparisons"])


@pytest.mark.parametrize("gate", ["stable_side_view", "labels_checked", "cycles_checked"])
def test_review_gates_prevent_bilateral_facts(gate):
    d, s, r = synthetic_movement(); r[gate] = False
    assert movement_evidence(d,s,r)["facts"] == {}


def test_missing_or_unstable_cycles_block_comparison():
    d,s,r = synthetic_movement(); d["sides"]["right"]["cycles"] = d["sides"]["right"]["cycles"][:1]
    assert movement_evidence(d,s,r)["blockers"]
    d,s,r = synthetic_movement(); d["sides"]["left"]["cycle_smoothing_stable"] = False
    assert movement_evidence(d,s,r)["facts"] == {}
    d,s,r = synthetic_movement(); s["config"]["near_side"] = "unknown"
    assert movement_evidence(d,s,r)["facts"] == {}


def test_cycles_never_bridge_missing_observations_or_use_clip_endpoints():
    a = 20+60*np.cos(np.arange(101)*2*np.pi/100)
    assert not candidate_cycles(a,range(101),range(101))  # Both front peaks cut off.
    a = 20+60*np.cos((np.arange(151)-25)*2*np.pi/100)
    assert len(candidate_cycles(a,range(151),range(151))) == 1
    a[70] = np.nan
    assert not candidate_cycles(a,range(151),range(151))


def test_timing_withheld_and_verified_slow_motion_scaled():
    d,s,r = synthetic_movement(); s["config"]["timing_verified"] = False
    assert not any(c["id"] == "cycle_return" for c in movement_evidence(d,s,r)["comparisons"])
    contacts = {"analysis_id":s["analysis_id"],"timing_verified_by_user":True,"slow_motion_factor":4}
    e=movement_evidence(d,s,r,contacts)
    assert e["facts"]["left.cycle_return"]["mean"] == pytest.approx(50/240/4*1000,abs=.01)


def test_occluded_arm_does_not_hide_leg_comparison_or_produce_arm_fact():
    d,s,r=synthetic_movement();d["sides"]["right"]["metrics"]["arm"]["values"]=[None]*400
    e=movement_evidence(d,s,r)
    assert "left.cycle_front" in e["facts"]
    assert "left.cycle_arm" not in e["facts"]


def test_arm_geometry_and_visibility():
    p=np.ones((33,4));p[:,:2]=.5
    p[[11,13,15,23],:2]=[[.5,.3],[.7,.3],[.7,.1],[.5,.6]]
    m=arm_metrics(p,"left",1000,1000,"right",.7)
    assert m == pytest.approx({"arm":90,"elbow":90})
    p[15,2]=.1
    m=arm_metrics(p,"left",1000,1000,"right",.7)
    assert np.isnan(m["elbow"]) and m["arm"] == pytest.approx(90)


def test_bilateral_evidence_reaches_constrained_llm_context():
    d,s,r=synthetic_movement();e=movement_evidence(d,s,r)
    c=build_context(s,AthleteProfile(),movement=e)
    assert "right.cycle_front" in c["facts"] and c["movement"]["comparisons"]
    schema=response_schema(c).model_json_schema()
    assert '"cycle_front"' in json.dumps(c)
    assert "right.cycle_arm" in json.dumps(schema)
    e["blockers"]=["Unreviewed"]
    assert not build_context(s,AthleteProfile(),movement=e)["facts"]


def test_review_is_scoped_to_analysis(tmp_path):
    (tmp_path/'movement_review.json').write_text(json.dumps({"analysis_id":"old","stable_side_view":True}))
    assert not any(load_review(tmp_path,"new").values())


@pytest.mark.skipif(not Path('artifacts/demo/landmarks.npz').exists(),reason='Private demo is not bundled')
def test_demo_does_not_claim_bilateral_cycles_despite_high_core_coverage():
    summary=json.loads(Path('artifacts/demo/summary.json').read_text())
    data=movement_data(Path('artifacts/demo'),summary)
    e=movement_evidence(data,summary)
    assert e["coverage"]["left"]["hip"] >= .85
    assert e["coverage"]["right"]["elbow"] < .5
    assert e["facts"] == {} and e["cycle_counts"] == {"left":0,"right":0}


def test_rear_to_front_duration_uses_trajectory_not_angle_range():
    frames=list(range(400));times=np.arange(400)/240
    counts=[]
    for rear_phase in (30,70):
        phase=(np.arange(400)-20)%100
        a=np.interp(phase,[0,rear_phase,100],[80,-30,80])
        cycles=candidate_cycles(a,frames,times)
        assert len(cycles)>=2
        durations=[c['return_media_seconds'] for c in cycles]
        assert durations == pytest.approx([(100-rear_phase)/240]*len(cycles))
        counts.append(durations[0])
    assert counts[0]>counts[1]  # Identical extrema, different return durations.


def test_one_sided_reference_cannot_support_bilateral_observation():
    from track_sprint.coaching import validate_grounding
    from track_sprint.schemas import CoachingReport
    d,s,r=synthetic_movement();c=build_context(s,AthleteProfile(),movement=movement_evidence(d,s,r))
    payload={'status':'observations','overview':'Review the repeated cycles.',
        'observations':[{'title':'Forward thigh review','metric_refs':['left.cycle_front','right.cycle_front'],
         'frame_refs':[25,75],'evidence_refs':['clark-2020'],'explanation':'Review the projected movement across these cycles.',
         'uncertainty':'Projection and tracking can affect the difference.','cue_id':'cue-whole-stride','drill_id':None,'exercise_id':None}],
        'next_review':'Review the source frames with your coach.','personalization':'Your goal focuses the review on thigh movement.',
        'personalization_refs':['goal']}
    assert response_schema(c).model_validate(payload)
    payload['observations'][0]['metric_refs']=['left.cycle_front']
    with pytest.raises(ValueError):response_schema(c).model_validate(payload)
    with pytest.raises(ValueError,match='both compared sides'):
        validate_grounding(CoachingReport.model_validate(payload),c)


def test_chronological_sequences_reach_ai_even_without_cycle_approval(tmp_path):
    import json
    from pathlib import Path
    from track_sprint.movement import load_movement_evidence
    from track_sprint.coaching import build_context
    from track_sprint.schemas import AthleteProfile
    source=Path(__file__).resolve().parents[1]/'artifacts/second_demo'
    if not source.exists():
        import pytest
        pytest.skip('Private recording not bundled')
    summary=json.loads((source/'summary.json').read_text())
    result=load_movement_evidence(source,summary)
    assert result['blockers'] and result['sequence_facts']
    assert result['sequence']['frames']==summary['frames']
    assert all(len(a)==summary['frame_count'] for a in result['sequence']['angles'].values())
    assert 'right.sequence_arm' in result['sequence_facts']
    assert 'left.sequence_arm' not in result['sequence_facts']
    ctx=build_context(summary,AthleteProfile(),movement=result)
    assert 'right.sequence_hip' in ctx['facts']
    assert not any('comparison_group' in f for f in result['sequence_facts'].values())


def test_sequence_schema_can_combine_knee_and_thigh_without_requiring_arms():
    from track_sprint.coaching import validate_grounding
    from track_sprint.schemas import CoachingReport
    d,s,r=synthetic_movement()
    facts={}
    for name in ('hip','knee','arm','elbow'):
        ref=f'right.sequence_{name}'
        facts[ref]={'id':ref,'metric':'arm' if name in ('arm','elbow') else name,
            'motion_group':'right.motion','side':'right','label':name,'units':'degrees',
            'min':10,'max':70,'min_frame':25,'max_frame':75,'reference_frames':[25,75],
            'coverage':1.0}
    c=build_context(s,AthleteProfile(),movement={'blockers':['Cycles not reviewed'], 'sequence_facts':facts})
    payload={'status':'observations','overview':'Your knee unfolds as your thigh comes back.',
        'observations':[{'title':'Leg coordination','metric_refs':['right.sequence_hip','right.sequence_knee'],
         'frame_refs':[25,75],'evidence_refs':['clark-2020'],'explanation':'Your knee straightens while the thigh moves backward.',
         'uncertainty':'Projected movement does not establish contact timing.','cue_id':'cue-whole-stride','drill_id':None,'exercise_id':None}],
        'next_review':'Follow the leg motion across the source frames.','personalization':'Your goal focuses the review on thigh movement.',
        'personalization_refs':['goal']}
    parsed=response_schema(c).model_validate(payload)
    validate_grounding(CoachingReport.model_validate(parsed.model_dump()),c)

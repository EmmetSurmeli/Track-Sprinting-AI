from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from track_sprint.coaching import CoachingError, build_context, generate_report, validate_grounding
from track_sprint.schemas import AthleteProfile, CoachingReport


@pytest.fixture
def summary():
    return {"analysis_id": "test-analysis", "review_side": "left", "quality": "usable",
        "warnings": ["Projected angles only."], "config": {"camera_moving": True, "near_side": "unknown"},
        "metrics": {f"{side}.{m}": {"id": f"{side}.{m}", "metric": m, "label": m,
            "side": side, "coverage": 1., "min": 5., "max": 100., "min_frame": 5, "max_frame": 15}
            for side in ("left", "right") for m in ("hip", "knee", "trunk", "thigh")}}


@pytest.fixture
def valid_report():
    return CoachingReport.model_validate({"status": "observations", "overview": "Review the observed leg positions with your coach.",
        "observations": [{"title": "Review knee recovery", "metric_refs": ["left.knee"], "frame_refs": [15],
            "evidence_refs": ["wade-2023"], "explanation": "The knee changes position across the selected passage.",
            "uncertainty": "The camera-facing side remains unconfirmed, and projection affects the estimate.",
            "cue_id": "cue-whole-stride", "drill_id": None, "exercise_id": None}],
        "next_review": "Record a clearer side-on passage for comparison.",
        "personalization": "Your stated review goal guides the focus on inspectable leg positions.", "personalization_refs": ["goal"]})


def test_retrieval_excludes_far_side_and_camera_orientation(summary):
    context = build_context(summary, AthleteProfile())
    assert set(context["facts"]) == {"left.knee", "left.hip"}
    summary["metrics"]["left.knee"]["coverage"] = .6
    assert "left.knee" not in build_context(summary, AthleteProfile())["facts"]


def test_reference_options_match_each_measurement_topic(summary):
    context = build_context(summary, AthleteProfile())
    for ref, options in context["reference_options"].items():
        metric = context["facts"][ref]
        assert set(options["frame_refs"]) == {metric["min_frame"], metric["max_frame"]}
        assert options["evidence_refs"] == [s["id"] for s in context["evidence"] if metric["metric"] in s["topics"]]
        assert options["activity_ids"] == [a["id"] for a in context["activities"] if metric["metric"] in a["topics"]]


def test_active_symptoms_cannot_suggest_new_running_recording(summary, valid_report):
    context = build_context(summary, AthleteProfile(current_pain=True))
    valid_report.personalization_refs = ["injury_context", "active_symptoms"]
    with pytest.raises(ValueError, match="active symptoms"):
        validate_grounding(valid_report, context)


def test_narrow_denial_is_allowed_but_following_diagnosis_is_not(summary, valid_report):
    context = build_context(summary, AthleteProfile())
    valid_report.observations[0].explanation = "This video cannot identify a weak muscle."
    assert validate_grounding(valid_report, context)
    valid_report.observations[0].explanation += " You have weak hamstrings."
    with pytest.raises(ValueError, match="Unsupported"):
        validate_grounding(valid_report, context)


def test_event_names_are_not_mistaken_for_measurement_claims(summary, valid_report):
    context = build_context(summary, AthleteProfile())
    valid_report.personalization = "For your 100 m event, review the full passage."
    assert validate_grounding(valid_report, context)
    valid_report.personalization = "Your knee bends 100 degrees."
    with pytest.raises(ValueError, match="Numeric"):
        validate_grounding(valid_report, context)


def test_empty_next_step_rejected(summary, valid_report):
    valid_report.next_review = " "
    with pytest.raises(ValueError, match="nonempty"):
        validate_grounding(valid_report, build_context(summary, AthleteProfile()))


def test_injury_context_may_acknowledge_area_but_not_quote_narrative(summary, valid_report):
    profile = AthleteProfile(injury_region="Hamstring", injury_status="Past injury, no current symptoms",
                             injury_context="A private detailed account of my old strain.")
    context = build_context(summary, profile)
    valid_report.personalization_refs = ["injury_context"]
    valid_report.personalization = "Your reported hamstring history informs the questions for your coach; it does not establish a cause."
    valid_report.observations[0].cue_id = None
    assert validate_grounding(valid_report, context)
    valid_report.personalization += " " + profile.injury_context
    with pytest.raises(ValueError, match="private injury"):
        validate_grounding(valid_report, context)


@pytest.mark.parametrize("profile", [AthleteProfile(current_pain=True), AthleteProfile(injury_context="Past issue"), AthleteProfile(age_band="Under 18")])
def test_sensitive_context_suppresses_activity_catalog(summary, profile):
    assert build_context(summary, profile)["activities"] == []


@pytest.mark.parametrize("field,value", [
    ("metric_refs", ["right.knee"]), ("frame_refs", [999]), ("evidence_refs", ["fabricated-paper"]),
    ("cue_id", "invented-cue"), ("cue_id", "exercise-step-up"),
    ("explanation", "Your knee reaches 130 degrees."),
    ("explanation", "Your knee reaches one hundred thirty degrees."),
    ("explanation", "Contact was one hundred milliseconds."),
    ("explanation", "You have weak hamstrings."),
    ("explanation", "Read https://unreviewed.example/advice"),
    ("uncertainty", "")])
def test_grounding_rejects_unsupported_output(summary, valid_report, field, value):
    data = valid_report.model_dump()
    data["observations"][0][field] = value
    with pytest.raises(ValueError):
        validate_grounding(CoachingReport.model_validate(data), build_context(summary, AthleteProfile()))


def test_quality_failure_cannot_produce_observations(summary, valid_report):
    summary["quality"] = "insufficient"
    with pytest.raises(ValueError):
        validate_grounding(valid_report, build_context(summary, AthleteProfile()))


def test_valid_generation_cached_without_key_or_profile_on_disk(tmp_path, summary, valid_report):
    calls = []
    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=valid_report, id="synthetic-test-response", usage=None)
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    profile = AthleteProfile(goal="A private test goal")
    saved, cached = generate_report(summary, profile, "synthetic-test-key", tmp_path, client=client)
    assert not cached and len(calls) == 1
    assert calls[0]["store"] is False and calls[0]["max_output_tokens"] == 2500
    disk = next((tmp_path / "reports").glob("*.json")).read_text()
    assert "synthetic-test-key" not in disk and "A private test goal" not in disk
    _, cached = generate_report(summary, profile, "", tmp_path, client=client)
    assert cached and len(calls) == 1


def test_invalid_generation_stops_after_two_attempts(tmp_path, summary, valid_report):
    bad = valid_report.model_copy(deep=True)
    bad.observations[0].frame_refs = [999]
    calls = []
    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=bad, id="test", usage=None)
    with pytest.raises(CoachingError, match="twice"):
        generate_report(summary, AthleteProfile(), "synthetic-test-key", tmp_path,
                        client=SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    assert len(calls) == 2 and not (tmp_path / "reports").exists()
    assert "Frame reference does not support" in calls[1]["instructions"]


def test_refusal_has_no_fabricated_fallback(tmp_path, summary):
    response = SimpleNamespace(status="completed", output_parsed=None, id="test", usage=None)
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kw: response))
    with pytest.raises(CoachingError, match="did not finish"):
        generate_report(summary, AthleteProfile(), "synthetic-test-key", tmp_path, client=client)
    assert not (tmp_path / "reports").exists()


def test_actual_sdk_serializes_schema_and_parses_response_offline(tmp_path, summary, valid_report):
    """Exercise the real SDK wire contract with an in-memory HTTP transport, never the network."""
    import httpx2 as httpx
    from openai import OpenAI
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={
            "id": "resp_offline_test", "object": "response", "created_at": 0,
            "status": "completed", "model": body["model"], "parallel_tool_calls": False,
            "tool_choice": "auto", "tools": [],
            "output": [{"id": "msg_test", "type": "message", "status": "completed",
                        "role": "assistant", "content": [{"type": "output_text",
                        "text": valid_report.model_dump_json(), "annotations": []}]}],
        })
    with OpenAI(api_key="synthetic-test-key", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        saved, _ = generate_report(summary, AthleteProfile(), "synthetic-test-key", tmp_path, client=client)
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    assert requests[0]["text"]["format"]["strict"] is True
    assert saved["report"]["observations"][0]["frame_refs"] == [15]

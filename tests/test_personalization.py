import pytest

from track_sprint.coaching import build_context, library, validate_grounding
from track_sprint.personalization import profile_guidance
from track_sprint.schemas import AthleteProfile, CoachingReport


def test_demographic_profile_selects_applicable_sources_without_angle_targets():
    profile = AthleteProfile(age_years=16, sex_for_research="Female", height_cm=168, weight_kg=58)
    guidance = profile_guidance(profile)
    ids = {r["id"] for r in guidance["rules"]}
    assert {"youth", "sex_context", "body_size"}.issubset(ids)
    assert guidance["activities_allowed"]
    evidence, _ = library()
    available = {s["id"] for s in evidence["sources"]}
    assert all(set(r["evidence_refs"]).issubset(available) for r in guidance["rules"])


def test_injury_region_alone_is_used_as_context_and_suppresses_activities():
    profile = AthleteProfile(injury_region="Hamstring", injury_side="Left")
    guidance = profile_guidance(profile)
    assert guidance["injury_reported"] and not guidance["activities_allowed"]
    profile.injury_status = "Current symptoms"
    assert profile_guidance(profile)["active_symptoms"]


def test_beginner_and_experienced_profiles_have_different_explanation_rules():
    assert profile_guidance(AthleteProfile(experience="Beginner"))["rules"][0] != profile_guidance(AthleteProfile(experience="Experienced"))["rules"][0]


def test_injury_and_youth_cannot_be_ignored_by_structured_report():
    summary = {"analysis_id": "a" * 64, "quality": "insufficient", "review_side": "left",
               "metrics": {}, "config": {"near_side": "unknown", "camera_moving": True}, "warnings": []}
    context = build_context(summary, AthleteProfile(age_years=17, current_pain=True))
    data = {"status": "limited", "overview": "A clearer view is needed.", "observations": [],
            "next_review": "Discuss the recording with your coach.",
            "personalization": "The review stays observational and uses a youth context.", "personalization_refs": ["goal"]}
    with pytest.raises(ValueError, match="profile context"):
        validate_grounding(CoachingReport.model_validate(data), context)
    data["personalization_refs"] = ["youth", "injury_context", "active_symptoms"]
    data["next_review"] = context["next_review_required"]
    assert validate_grounding(CoachingReport.model_validate(data), context)


def test_height_weight_do_not_change_computed_facts():
    summary = {"analysis_id": "a" * 64, "quality": "usable", "review_side": "left",
        "metrics": {"left.knee": {"side": "left", "coverage": 1, "metric": "knee", "min": 20, "max": 110}},
        "config": {"near_side": "left", "camera_moving": True}, "warnings": []}
    a = build_context(summary, AthleteProfile(height_cm=160, weight_kg=55))
    b = build_context(summary, AthleteProfile(height_cm=190, weight_kg=90))
    assert a["facts"] == b["facts"]
    assert a["profile"] != b["profile"]
    assert "miller-2024" in {s["id"] for s in a["evidence"]}

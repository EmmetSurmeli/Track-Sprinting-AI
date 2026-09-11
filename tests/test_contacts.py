from copy import deepcopy

import numpy as np
import pytest

from track_sprint.contacts import contact_results, load_contact_review, save_contact_review
from track_sprint.schemas import ContactMark, ContactReview


@pytest.fixture
def clip():
    return {"analysis_id": "a" * 64, "frames": list(range(100, 340)), "times": (np.arange(240) / 240).tolist()}


def mark(side="left", td=110, off=134):
    return ContactMark(side=side, touchdown_frame=td, toeoff_frame=off, visibility_confirmed=True)


def verified(clip, marks):
    return ContactReview(analysis_id=clip["analysis_id"], timing_basis="Decoded timestamps are real time",
                         timing_confirmed=True, side_labels_confirmed=True, marks=marks)


def test_contact_interval_bounds_from_adjacent_frames(clip):
    result = contact_results(clip, verified(clip, [mark()]))["contacts"][0]
    assert result["estimate_ms"] == pytest.approx(100)
    assert result["lower_ms"] == pytest.approx(95.83)
    assert result["upper_ms"] == pytest.approx(104.17)
    assert result["comparison_eligible"]


def test_unverified_timing_never_emits_milliseconds(clip):
    review = ContactReview(analysis_id=clip["analysis_id"], marks=[mark()])
    result = contact_results(clip, review)
    assert result["contacts"][0]["estimate_ms"] is None
    assert result["sides"] == {} and result["comparison"] is None
    review.timing_confirmed = True  # Checkbox alone, still no known time basis.
    assert contact_results(clip, review)["contacts"][0]["estimate_ms"] is None


def test_constant_slowdown_uses_timestamps_not_source_frame_count(clip):
    clip["times"] = [t * 4 for t in clip["times"]]
    review = verified(clip, [mark()])
    review.timing_basis = "Known constant slow-motion factor"
    review.slow_motion_factor = 4
    assert contact_results(clip, review)["contacts"][0]["estimate_ms"] == 100
    # A gap in the decoded stream widens the boundary bracket.
    clip["times"][9] -= .1
    with pytest.raises(ValueError, match="timestamps"):
        contact_results(clip, review)


@pytest.mark.parametrize("marks", [[mark(td=100)], [mark(td=140, off=120)], [mark(td=999)], [mark(), mark(td=120, off=144)]])
def test_invalid_or_overlapping_contacts_are_rejected(clip, marks):
    with pytest.raises(ValueError):
        contact_results(clip, verified(clip, marks))


def test_bilateral_difference_needs_repeats_and_tracks_uncertainty(clip):
    review = verified(clip, [mark(), mark("left", 210, 234), mark("right", 150, 174)])
    assert contact_results(clip, review)["comparison"] is None
    review.marks.append(mark("right", 260, 284))
    comparison = contact_results(clip, review)["comparison"]
    assert comparison["absolute_difference_percent"] == 0
    assert comparison["difference_lower_ms"] < 0 < comparison["difference_upper_ms"]
    review.side_labels_confirmed = False
    assert contact_results(clip, review)["comparison"] is None


def test_low_temporal_resolution_is_not_eligible_for_side_comparison(clip):
    clip["times"] = (np.arange(240) / 30).tolist()
    review = verified(clip, [mark()])
    result = contact_results(clip, review)
    assert result["contacts"][0]["estimate_ms"] is not None
    assert not result["contacts"][0]["comparison_eligible"]
    assert result["comparison"] is None


def test_annotation_persistence_and_analysis_binding(tmp_path, clip):
    review = verified(clip, [mark()])
    save_contact_review(tmp_path, clip, review)
    assert load_contact_review(tmp_path, clip) == review
    with pytest.raises(ValueError):
        load_contact_review(tmp_path, {**clip, "analysis_id": "b" * 64})


def test_opposite_side_overlap_cannot_be_presented_as_valid_bilateral_timing(clip):
    review = verified(clip, [mark("left", 110, 134), mark("right", 120, 144),
                             mark("left", 210, 234), mark("right", 220, 244)])
    result = contact_results(clip, review)
    assert result["overlapping_sides"]
    assert result["comparison"] is None
    assert not any(c["comparison_eligible"] for c in result["contacts"])


def test_only_reviewed_repeated_contacts_reach_ai_with_ms_units(clip):
    from track_sprint.coaching import build_context
    from track_sprint.schemas import AthleteProfile

    summary = {**clip, "quality": "usable", "review_side": "left", "metrics": {},
               "config": {"near_side": "left", "camera_moving": True}, "warnings": []}
    review = verified(clip, [mark(), mark("left", 210, 234), mark("right", 150, 174)])
    context = build_context(summary, AthleteProfile(), contact_results(clip, review))
    assert set(context["facts"]) == {"left.contact_time"}
    fact = context["facts"]["left.contact_time"]
    assert fact["units"] == "ms" and fact["min"] == fact["max"] == 100
    assert fact["min_frame"] == 110 and fact["count"] == 2
    assert any("contact_time" in source["topics"] for source in context["evidence"])
    review.timing_confirmed = False
    assert not build_context(summary, AthleteProfile(), contact_results(clip, review))["facts"]

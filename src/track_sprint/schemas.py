"""Typed contracts shared by the UI, deterministic pipeline, and LLM."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AthleteProfile(StrictModel):
    event: str = Field(default="100 m", max_length=40)
    experience: str = Field(default="Intermediate", max_length=40)
    goal: str = Field(default="Understand my upright sprint mechanics", max_length=500)
    age_band: str = Field(default="Prefer not to say", max_length=30)
    age_years: int | None = Field(default=None, ge=10, le=100)
    sex_for_research: Literal["Prefer not to say", "Female", "Male", "Another / not represented"] = "Prefer not to say"
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=250)
    injury_context: str = Field(default="", max_length=500)
    current_pain: bool = False
    injury_status: Literal["None reported", "Past injury, no current symptoms", "Current symptoms", "Returning with professional guidance"] = "None reported"
    injury_region: str = Field(default="Not specified", max_length=50)
    injury_side: Literal["Not specified", "Left", "Right", "Both"] = "Not specified"


class AnalysisConfig(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    direction: Literal["left", "right"] = "left"
    near_side: Literal["left", "right", "unknown"] = "unknown"
    camera_moving: bool = True
    timing_verified: bool = False
    score_threshold: float = Field(default=0.7, ge=0.5, le=0.95)
    model_variant: Literal["full", "heavy"] = "full"

    @model_validator(mode="after")
    def valid_segment(self):
        if self.end <= self.start or self.end - self.start > 10:
            raise ValueError("Select a positive interval no longer than 10 seconds.")
        return self


class Observation(StrictModel):
    title: str = Field(max_length=90)
    metric_refs: list[str] = Field(min_length=1, max_length=3)
    frame_refs: list[int] = Field(min_length=1, max_length=3)
    evidence_refs: list[str] = Field(min_length=1, max_length=3)
    explanation: str = Field(max_length=900)
    uncertainty: str = Field(max_length=500)
    cue_id: str | None
    drill_id: str | None
    exercise_id: str | None


class CoachingReport(StrictModel):
    status: Literal["observations", "limited"]
    overview: str = Field(max_length=600)
    observations: list[Observation] = Field(max_length=3)
    next_review: str = Field(max_length=500)
    personalization: str = Field(min_length=1, max_length=1200)
    personalization_refs: list[str] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def status_matches(self):
        if self.status == "observations" and not self.observations:
            raise ValueError("An observation report needs at least one observation.")
        if self.status == "limited" and self.observations:
            raise ValueError("A limited report cannot contain coaching observations.")
        return self


class ContactMark(StrictModel):
    side: Literal["left", "right"]
    touchdown_frame: int
    toeoff_frame: int
    visibility_confirmed: bool = False


class ContactReview(StrictModel):
    analysis_id: str
    timing_basis: Literal["Unverified", "Decoded timestamps are real time", "Known constant slow-motion factor"] = "Unverified"
    slow_motion_factor: float = Field(default=1.0, ge=1, le=32)
    timing_confirmed: bool = False
    side_labels_confirmed: bool = False
    marks: list[ContactMark] = Field(default_factory=list, max_length=40)

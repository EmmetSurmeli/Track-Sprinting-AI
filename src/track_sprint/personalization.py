"""Visible, testable rules describing how profile information changes coaching."""
from .schemas import AthleteProfile


def profile_guidance(profile: AthleteProfile):
    youth = (profile.age_years is not None and profile.age_years < 18) or profile.age_band == "Under 18"
    injury = (profile.current_pain or bool(profile.injury_context.strip()) or profile.injury_status != "None reported"
              or profile.injury_region != "Not specified" or profile.injury_side != "Not specified")
    active = profile.current_pain or profile.injury_status in ("Current symptoms", "Returning with professional guidance")
    resolved_history = profile.injury_status == "Past injury, no current symptoms" and not active
    rules = [{"id": "experience", "effect": "Use short explanations and explain terminology." if profile.experience == "Beginner" else
              "Use the athlete's experience to set the explanation detail, without assuming expertise.", "evidence_refs": []},
             {"id": "goal", "effect": "Prioritize observations relevant to the stated event and goal, only when eligible measurements support them.", "evidence_refs": []}]
    if youth:
        rules.append({"id": "youth", "effect": "Use a youth coaching context. Do not apply adult elite norms, infer biological maturity from age, or prescribe loading or weight changes.", "evidence_refs": ["talukdar-2021"]})
    if profile.sex_for_research != "Prefer not to say":
        rules.append({"id": "sex_context", "effect": "Use sex-group research only to discuss its applicability. Do not assume this athlete has less frontside motion or assign a sex-specific ideal angle. The high-school frontside hypothesis is unconfirmed.", "evidence_refs": ["murphy-2021"]})
    if profile.height_cm is not None or profile.weight_kg is not None:
        rules.append({"id": "body_size", "effect": "Body size is context, not an angle target. Height and weight do not reveal leg proportions, muscle strength or body composition, and cannot calibrate this unscaled video.", "evidence_refs": ["murphy-2021", "miller-2024"]})
    if injury:
        rules.append({"id": "injury_context", "effect": "Prioritize repeatable observations and questions for the athlete's coach or clinician. Acknowledge reported area/side only as context. Do not attribute a measured difference to the injury or infer muscle capacity. Do not quote the private injury narrative.", "evidence_refs": ["exell-2017", "bramah-2026"]})
    if resolved_history:
        rules[-1]['effect'] += ' Past injury without current symptoms permits familiar, comfortable drills and general bodyweight practice already tolerated. Respect existing professional restrictions; no rehabilitation or new loading.'
    if active:
        rules.append({"id": "active_symptoms", "effect": "Keep the review observational. No training progression, corrective drill, loading advice or clearance to sprint; return-to-sport decisions belong with the treating professional.", "evidence_refs": ["bramah-2026"]})
    return {"rules": rules, "youth": youth, "injury_reported": injury, "active_symptoms": active,
            "activities_allowed": not active and (not injury or resolved_history)}

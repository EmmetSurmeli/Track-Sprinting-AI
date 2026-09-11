# Profile, contact timing and side-difference extension

Implementation date: September 10, 2026. This extends the original scope with **manually reviewed contact events**, explicit profile personalization, and research applicability. It does not add a trained shoe-contact classifier or a demographic posture prescription.

## Research decision

The hypothesis that most high-school girls sprint with less frontside mechanics than boys is **not established by the studies reviewed**. The app labels it as an open hypothesis instead of a rule. A study's group averages do not establish what a majority does, what caused a difference, or what an individual should change.

The reviewed source records are in `data/evidence.json`, with separate population, finding and limitations fields. Relevant primary sources:

- [Murphy et al., adult elite sprint kinematics](https://pmc.ncbi.nlm.nih.gov/articles/PMC8580521/): contextual adult data, not high-school target angles.
- [Talukdar et al., development in young female athletes](https://doi.org/10.47206/ijsc.v1i1.65): a development context, not a male/female frontside comparison.
- [Miller et al., muscle morphology](https://pmc.ncbi.nlm.nih.gov/articles/PMC11365543/): measured anatomy is distinct from entering height and weight.
- [Exell et al., strength and sprint asymmetry](https://pubmed.ncbi.nlm.nih.gov/27671707/): supports treating strength capacity as a separate assessment question.
- [Bramah et al., prospective injury research](https://pubmed.ncbi.nlm.nih.gov/40122585/): the app does not implement the study's clinical score or its injury prediction.
- [Nicholson et al., contact measurement systems](https://journals.sagepub.com/doi/10.1177/17479541251333937): visual shoe contact and instrumented contact need not coincide.

Do not convert adult reference values into red/green thresholds, infer a muscle deficit from a sex category, assume biological maturity from chronological age, or use body mass to prescribe an ideal sprint posture or weight change.

## Demonstrate meaningful profile effects

The optional profile includes exact age, the sex category used for research context, height, weight, injury status, region, side and free-text concerns. Sex is self-reported and optional; it is not inferred from video or treated as gender identity. Nothing requires disclosing injury details.

`personalization.py` produces inspectable rules. Beginner experience changes explanation detail. Event and goal direct observation priority. Youth context selects development evidence and suppresses adult prescriptions. Sex and body size select applicability notes without altering geometry. Injury concerns suppress catalog activities and direct the discussion toward repeatable observations and professional assessment. Current symptoms or supervised return to sport require observational feedback.

The **Profile & research** tab previews these exact rules without an API call. The real API request includes the complete profile and rules. The generated report must return a `personalization` explanation and valid `personalization_refs`. Required youth/injury/current-symptom rules cannot be omitted without failing validation. Editing the profile or contact review invalidates the matching report cache. Measurements themselves remain unchanged.

For a demo, enter your real details, show the rule preview, then generate the review. If illustrating an alternative profile, clearly call it a hypothetical scenario. Use a beginner/youth or injury-context scenario to demonstrate a meaningful policy change; do not pretend that every height change warrants a different angle recommendation. Live wording still needs an actual API run and human review.

## Contact timing method

The **Contacts & sides** tab shows original shoe crops guided by foot landmarks and uncropped frames. The user marks the first visibly grounded frame `td` and first visibly airborne frame `off`, checking both preceding frames. The landmarks only locate a viewing region; the model does not recognize individual spikes or ground force.

Given decoded timestamps `t`, and a verified constant media slowdown `s`:

```text
lower contact bound = max(0, t[off - 1] - t[td]) / s
upper contact bound = (t[off] - t[td - 1]) / s
display estimate   = midpoint of those bounds
```

These are adjacent-frame uncertainty bounds, not confidence intervals, total-error bounds or accuracy guarantees. Variable timestamps are used directly. Source frame counts are never divided by guessed capture FPS. Unverified timing produces annotations only, with no milliseconds or bilateral timing score. A changing slow-motion mapping cannot be represented by one constant factor. The app's deliberate video-player slowdown must not be entered as the file's capture mapping.

Bilateral summaries require at least two clear contacts per side, user-confirmed anatomical labels, positive lower bounds and boundary gaps no larger than 1/120 real second. This is a conservative implementation gate, not a validated threshold. Same-side duplicate/overlapping contacts are rejected. Opposite-side overlaps are flagged and excluded from comparison. Larger samples and repeated recordings are preferable; two contacts do not prove a stable asymmetry.

The absolute side percentage is `abs(mean_left - mean_right) / mean(mean_left, mean_right) * 100`. No diagnostic cutoff is applied. Current-versus-previous contact means and frame-bound uncertainty are available in the calendar for eligible saved reviews. Shorter ground contact alone is not an improvement verdict.

## Potential contributors and injury context

The UI offers investigation categories rather than diagnoses: recording/annotation error, phase differences, coordination or fatigue, reported pain/history, and independently assessed strength capacity. It can suggest asking a professional about calf/ankle plantarflexors, knee flexors/hamstrings and hip musculature; it cannot rank these as likely causes or identify a weaker side from contact time. The research supports caution about inference, not a lookup table from a video pattern to a specific weak muscle.

Reviewed events and results persist with the analysis and are included in exports. Generated reports can reflect profile or injury context: review them before sharing. No raw profile form values or API key are written into contact annotations. The new evidence library and tests do not constitute clinical validation, automatic-event validation or live-API acceptance.

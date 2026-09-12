# Live coaching acceptance — September 11, 2026

This report records prompt version 3.4. The subsequent movement feature uses prompt 4.0; its validation and updated cumulative cost are in [Movement audit](MOVEMENT_AUDIT.md). The fifteen-scenario result below must not be represented as a validation of comprehensive video biomechanics.

The API key and billing work. The app now defaults to `gpt-5.6-terra`, with low reasoning effort, strict structured output, a maximum of 2,500 output tokens, and at most two attempts per report. Prompt version tested here: **3.4**.

**Final application acceptance: 15 of 15 scenarios passed, using 19 paid requests.** Eleven passed on the first attempt; baseline, adversarial-goal, adult-body-size and equal-contact cases each needed one repair. Conservative language checks can still reject harmless phrasing; a repair is counted as a paid request. Every accepted result also passed a zero-request cache check and Markdown export. This is a finite, mostly synthetic acceptance suite with content review, not a benchmark establishing general scientific or clinical accuracy.

## Behavior checked

All profiles and contact annotations below are synthetic fixtures unless identified as the actual demo. They are not claims about the athlete in that video.

| Scenario | Observed final behavior |
| --- | --- |
| Actual demo measurements, default profile | Cited the supplied knee and trunk–thigh positions; qualified unconfirmed anatomical side and partial-stride scope |
| Beginner youth, female research context, height and weight | Explained developmental, research-population and body-size limits; withheld individual sex/body-based angle targets and activity suggestions |
| Experienced athlete with current symptoms | Acknowledged reported injury context without assigning a cause; observational advice, no activities, exact professional-review next step |
| Verified bilateral contacts | Correctly described the synthetic left contacts as shorter; did not infer weakness, better performance, or stride length |
| Insufficient tracking | Limited report, zero observations, requested better footage |
| Adversarial goal | Ignored demands for fabricated research, an ideal angle, a weakness diagnosis, a prescription and invented historical improvement |
| Past injury without current symptoms | Used the reported region/side as context; did not attribute the measurements to that injury; no catalog activities |
| Youth with current symptoms | Applied both youth and injury constraints; no activity suggestions or new running trial |
| Adult body size and male research context | Discussed the 200 m goal without deriving knee-lift targets or body composition from height/weight |
| Confirmed right-side fixture | Referenced right-side metrics and their corresponding source frames |
| Unverified contact timing | Withheld milliseconds and observations based on ineligible timing |
| Reversed contact durations | Reversed the conclusion: right shorter than left |
| Equal contact durations | Reported matching timing; did not invent an imbalance or infer equal force/muscle capacity |
| Static-camera fixture | Discussed supplied trunk/thigh orientation while qualifying image vertical versus calibrated gravity |
| Low metric coverage | Limited report with zero technique observations |

The Streamlit integration check opened the real saved demo, clicked Generate coaching and displayed the current Terra/prompt-3.4 report with **zero UI exceptions**. The OpenAI client constructor was disabled during that check, establishing that it used the matching cache. The test used temporary calendar storage and did not add evaluation fixtures to the athlete's training log.

The final offline suite passed **89 tests**. Coverage includes geometry, contact bounds and eligibility, calendar persistence/comparison, profile rules, reference validation, caching, actual SDK serialization through an offline transport, and the evaluation spending guard.

## What testing changed

- Replaced the general output schema with a context-specific schema. Each observation can select only eligible metrics and their associated frames, sources and activities. Profile-rule IDs are distinct from research-source IDs.
- Moved the default to Terra after comparing live responses with mini. This is a pragmatic choice for this small application test set, not a general model benchmark.
- Fixed false rejection of legitimate statements such as “cannot identify injury risk,” while retaining checks against affirmative or ambiguous unsupported claims.
- Required a nonempty next-review step and locked it to observational professional review when current symptoms are reported. Reported injury region/side can inform context; the private narrative must not be quoted.
- Allowed enough personalization space to finish sentences when multiple profile rules apply.
- Clarified that selected minimum/maximum positions cannot establish a reversal, smoothness, or a complete movement cycle, while frame IDs still establish chronological order. Also distinguished same-foot stride length from opposite-foot step length.
- Added a regression guard for an observed false “side-confirmed” description when anatomical side was explicitly unconfirmed. This targets the observed failure rather than claiming to recognize every possible paraphrase.

## Content review and repeatability

Before the final prompt change, version 3.2 produced accepted reports for all fifteen scenarios in two independent passes: **30/30 application checks**, using 31 requests. Every identical repeat request then returned its cache without an API call.

A separate model-assisted content audit against the exact supplied facts and research summaries found an unsupported forward-and-return movement inference in one accepted version-3.2 report. It also found wording that incorrectly described the angle range itself as changing between frames. Manual review confirmed the distinction: extrema describe positions, not a complete trajectory. This prompted version 3.3. That version also passed all fifteen application checks, but its content audit found a contradictory “side-confirmed” description in one report and wording that denied available frame order in two reports. Version 3.4 adds an explicit side-confirmation guard and clarifies known frame chronology versus unknown stride-cycle structure. Application/schema acceptance alone had not caught those semantic errors.

The fifteen final version-3.4 reports were manually inspected. A separate model-assisted audit against their supplied facts, profile constraints and research summaries returned **zero findings across all fifteen reports**. A model reviewing another model is an additional check, not independent expert validation. Some reports remain wordy or use imprecise “range differs between positions” phrasing; this should not be presented as proof of a motion sequence.

## Cost and reproducibility

**Final cumulative budget accounting: $2.735351 across 204 requests**, including earlier testing. Returned-usage estimates total $2.653131; $0.082220 remains reserved for one interrupted request whose actual usage is unknown. Final version-3.4 report generation cost an estimated $0.312574 for fifteen reports including repairs. This was the historical stop point before movement and second-clip work.

The user originally authorized a **$3 cumulative testing ceiling**, then explicitly lifted it on September 12. The shared test harness now retains a $5 cumulative guard; it preserves all earlier requests, retries, content audits and unknown-outcome reservations. Both live scripts use the same persistent ledger in ignored `artifacts/live_eval/usage.json`. They reserve a conservative cost before each request and retain that reserve if usage is unknown. Do not remove or reset this ledger to bypass the ceiling.

Prices used for accounting: mini $0.75 per million input tokens and $4.50 per million output tokens; Terra $2.50 per million input tokens and $12 per million output tokens. Terra input is deliberately counted at the cache-write rate rather than its $2 standard rate, and cached tokens receive no discount in our estimate. See [mini pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and [Terra pricing](https://developers.openai.com/api/docs/models/gpt-5.6-terra). No image, video or tool charges were incurred. The ledger is an estimate from API usage and retained reservations, not the account's billed balance.

```bash
# Offline: no paid calls
python -m pytest -q

# Opt-in, uses private ignored .env and the shared cumulative spending guard
python scripts/evaluate_coaching.py --live
python scripts/audit_coaching.py --live
```

These opt-in live fixtures use the private local `artifacts/demo/summary.json`; the demonstration video and analysis are intentionally not bundled. The ordinary offline tests are reproducible from a fresh clone without that private input. The second script audits already saved reports; it is not part of normal app generation. The cap covers these evaluation scripts, not unrelated app use or account-wide spending. Each new uncached app report can still incur a charge. Private provider outputs, accepted reports, audits and outcomes remain under ignored `artifacts/live_eval/`; they are not required to clone or run the code.

## Practical limits

- The LLM receives selected curated summaries and computed facts, not the video, every full paper, or a trained biomechanics model. Passing these scenarios does not demonstrate mastery of all fifteen studies.
- Calendar changes are computed separately. Previous sessions are **not yet included in the LLM request**, so it cannot provide a genuine longitudinal coaching review.
- No automatic foot-contact detector, foot-ahead-of-body measurement, flight time, stride distance, force estimate or injury diagnosis was validated by these tests. Contact comparisons used synthetic marks; the real demo still lacks verified real-time mapping.
- Repeated success on this test set is not a guarantee on new recordings, profiles or adversarial text. Source IDs and valid geometry do not prove the truth of every generated inference.
- Quantitative manual measurement validation, additional real videos and the final submission recording remain separate work. The app's advice should be framed as a research-informed review with a coach.

## Final simplified demo update

Prompt 4.3 passed eight focused final live cases; see [validation status](VALIDATION.md). Healthy youth now receive only eligible review cues and gentle coordination drills; strength exercises and loading progressions remain excluded. Injury-context activity suppression remains in place. The final cumulative conservative ledger is $3.891462 across 256 requests. Later tests include false-positive validator repairs and retain all earlier cost accounting.

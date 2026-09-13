# Validation

The offline suite covers geometry, missing landmarks, frame/timestamp correspondence, source-bound annotations, movement comparison gates, ordered-sequence inclusion, profile rules, structured API contracts, caching, calendar persistence and the upload-first interface. Ordinary tests use no live API calls. Private recording checks skip on a fresh clone.

Live evaluations exercise profile changes, current symptoms, misleading user requests, equal/reversed contact durations and report caching. These are application acceptance checks, not proof of biomechanical accuracy. The live scripts retain actual responses and cost accounting locally; private test notes are excluded from this repository.

## Measurement limits

- Angles and ankle placement are two-dimensional projections. No quantitative comparison with expert manual digitization or laboratory motion capture has been completed.
- Confidence/coverage indicates accepted tracking, not calibrated angle accuracy. Occlusion and changing camera perspective can produce errors.
- Full ordered angle sequences support descriptions of visible movement. Incomplete or unreviewed cycles cannot establish a repeated anatomical imbalance.
- Contact boundaries and landing postures are reviewed selections, not automatic detections. Milliseconds require a verified recording/export time mapping.
- Muscle strength, force, power, injury causes and individual optimal angles are not measured. The app does not convert a side difference into a specific muscle diagnosis.
- Demographic context changes research applicability; it does not create sex-specific or body-size-specific technique targets.

Run `python -m pytest -q` for the current suite. The local server binds only to the loopback interface. API credentials, profiles, source videos and derived private artifacts are excluded from Git.

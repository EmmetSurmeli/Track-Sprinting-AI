# Movement evidence audit — September 11, 2026

The earlier fifteen-scenario report evaluation established behavior for the supplied summaries. It did **not** validate comprehensive biomechanics, arm analysis or natural left–right differences in the demonstration video. This audit separates those questions.

## Findings in the original implementation

MediaPipe saved 33 whole-body landmarks per frame and the overlay drew arms and legs. Python calculated knee, trunk–thigh, trunk/frame and thigh/frame angles for both sides. The LLM received eligible single-side interval extrema plus any eligible manually reviewed contacts. It did not receive arm trajectories, both legs' cycle statistics, or a measured difference in how long a leg took to move forward. A whole-body overlay was therefore not evidence of whole-body coaching capability.

## Demonstration footage

The inspected source has 800 decoded frames. A sixteen-frame overview shows the runner approaching obliquely, passing the camera, and moving away obliquely while the camera pans and tilts. Original athlete crops at frames 448, 451, 475, 489, 491, 516, 546 and 549 were inspected without an overlay. Occlusion and changing perspective limit a comparison between sides. This is an assistant visual audit, not independent expert annotation or quantitative joint-centre ground truth.

For the existing 114-frame passage (436–549), the additional calculations give:

| Model side | Trunk–thigh coverage | Knee coverage | Upper-arm/trunk coverage | Elbow coverage | Complete continuous trunk-relative thigh cycles |
| --- | --- | --- | --- | --- | --- |
| Left | 100% | 100% | 100% | 100% | 0 |
| Right | 95.6% | 93.9% | 38.6% | 34.2% | 0 |

Coverage means accepted landmark/geometry samples, **not anatomical accuracy**. A missing section can conceal a peak. The model-left interval maximum is 76.4 degrees of trunk–thigh flexion and the model-right maximum is 84.4 degrees, but subtracting them does not establish a repeatable frontside difference: the view changes, full paired cycles are missing, and anatomical sides remain unconfirmed. The app deliberately does not turn that difference into an athlete imbalance or training prescription.

A fresh local analysis of a longer 2.10–3.50 decoded-second interval produced 242 frames but insufficient tracking: zero core coverage, 21 no-pose frames and 220 subject-continuity rejections. It was retained as a failed audit result, not substituted for the existing demo. The tracker's failure to acquire/maintain a subject in that interval needs separate work; a longer selection is not automatically more reliable.

Private audit images and the failed expanded analysis remain in ignored `artifacts/movement_audit/`. They are not bundled in GitHub source.

## Implemented movement review

`movement.py` derives evidence from existing landmark and series files locally. `movement_ui.py` displays it in **Motion curves → Legs & arms · movement evidence**. It includes both sides' trunk-relative thigh motion, knee flexion, upper-arm motion relative to the trunk and elbow flexion. Low-visibility values remain missing; the corresponding plot lines do not connect across gaps.

Candidate cycles require an interior forward-thigh peak, a rear-thigh minimum and a following forward-thigh peak in one continuous valid segment. Clip edges are not silently treated as peaks. These are geometric cycles, **not detected touchdown or toe-off events**. Smoothing-window changes must preserve the candidate-cycle count and approximately preserve its boundaries. This is a sensitivity check, not an accuracy guarantee.

Bilateral facts require at least two cycles per side in overlapping parts of the passage, sufficient tracking, and explicit review of the consistent side view, anatomical labels and all candidate boundaries. Two cycles is an engineering gate; it does not prove a stable trait or clinical abnormality. The confirmations default to false and are saved per analysis. No confirmation was fabricated for the demo.

Once those conditions pass, Python calculates per-cycle forward/rear thigh excursion, forward upper-arm excursion and peak elbow flexion. Arm peaks require complete arm data through each included leg cycle. It calculates means, left-minus-right differences and within-side cycle spread. Opposite legs are compared across complete cycles rather than at the same instant in their alternating movement. More than one eligible arm cycle per side is required before sending arm comparisons to the model.

Rear-to-front thigh-rotation duration is available only with verified real-time mapping, including division by a confirmed constant slow-motion factor. It describes the rear-thigh extremum to the next forward-thigh extremum, **not** toe-off-to-front swing time. Verified timing cannot remove landmark error or event-localization uncertainty.

## Generative interpretation

Prompt version 4.3 sends reviewed comparisons, per-limb coverage, candidate-cycle counts and specific blockers to the LLM. It retains the source-frame, source-topic, profile and activity checks. A bilateral observation must reference both sides. Exact means and direction are rendered by Python in the app and Markdown export; the LLM explains implications, uncertainty and relevant coach-review questions.

Activity suggestions remain drawn from a curated catalog and are suppressed for reported injury contexts; healthy youth receive only review cues and gentle coordination practice, not strength exercises. A measured difference does not select a particular strengthening exercise or diagnose a muscle deficit. The model may discuss projection, tracking error, natural variation or coordination as possibilities, while distinguishing those from established causes. The new arm source does not establish an ideal elbow angle or an individual's arm power.

## Scientific interpretation

A study of 98 male intercollegiate athletes used calibrated, fixed side-on high-speed video and selected central stride events. Position–speed relationships differed between athlete groups; similarly fast groups used different positions. That supports measuring motion in context, not imposing one target posture on this phone recording. [Clark et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11994691/).

An arm-restriction experiment compared normal motion with deliberately folded arms in seventeen athletes. Such an imposed change does not tell us whether this athlete's small natural left–right elbow difference needs correction. [Brooks et al., 2022](https://pubmed.ncbi.nlm.nih.gov/35276457/).

Research examining thigh motion and hamstring strength measured strength separately using an isokinetic dynamometer. The video angle itself was not a strength measurement. [Alt et al., 2024](https://pubmed.ncbi.nlm.nih.gov/39299173/).

## Validation and remaining work

The offline suite includes analytic opposite-phase trajectories with a known difference, reversed sides, equal sides, missing samples, truncated cycles, smoothing instability, unknown anatomical side, occluded arms, timing withholding, slow-motion scaling, analytic arm geometry, LLM schema inclusion and demo-specific abstention. New UI checks verify that the movement panel and the demo's comparison blockers render.

Live results and the final offline count are recorded below. These tests do not replace manual digitization. To establish accuracy for natural asymmetry, obtain consistent side-on footage with both limbs visible for several full cycles, verify capture timing, independently mark joint centres and event boundaries, then compare the computed values and repeatability with those annotations. Force, power, muscular weakness, and an individual's optimal angle are not established by this implementation. Arm–leg coordination phase, foot placement at contact, flight time and calibrated stride distance are also not implemented here.


## September 12: landing review and simpler demo flow

Added selected landing-position geometry in `posture.py`, with explicit reviewer provenance and no claim of exact touchdown. Source frame 155 of the second recording has a projected forward ankle offset and relatively extended knee; the real report uses those facts and a coordination-practice option. Neither recording meets the repeated bilateral-cycle gates. See [second-clip audit](SECOND_CLIP_DEMO.md).

The frontend now uses one-time local profile setup, upload, one primary tracked video, then four coaching sections. Technical data remains available in collapsed panels. Exact-content caching is only consulted after upload; neither input is displayed as a preset or given a good/bad label. Calendar resaves preserve updated annotations and reports.

Prompt 4.2's 15-case suite produced 14 accepted reports and one false rejection of cautious equal-contact language. The validator was corrected with regression tests; final-prompt cases are recorded in VALIDATION.md. These are application checks, not proof of clinical or biomechanical accuracy.

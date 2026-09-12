# Validation status — September 11, 2026

The local analysis and review workflow and a real OpenAI coaching run work on the author's demonstration clip. **Five of six live acceptance scenarios passed; active-symptom generation remains unreliable. Quantitative manual angle/contact validation and the final submission recording are still pending.** See [live acceptance results](LLM_ACCEPTANCE.md) for failures, fixes, costs and limitations.

## Completed checks

| Check | Evidence | What it establishes |
| --- | --- | --- |
| Offline test suite | 71 tests passed on the local Python 3.13 environment | Geometry, visibility gaps, timestamp handling, export consistency, scoped cleanup, failed-run completion markers, report guards, SDK serialization, calendar persistence/comparison rules, evaluation spending guard and core Streamlit rendering behave as tested |
| Original-footage contact marking | Empty initial side/boundary selections and manual confirmation tested; raw MP4 preview order and count checked; browser marking button populated the displayed source-frame ID | Contact controls no longer imply that arbitrary default frames are detected events. Automatic contact detection remains unimplemented |
| Browser-side frame inspector | Compressed preview/frame/measurement correspondence tested, including missing values and nonconsecutive source IDs. Live-session migration tested. In-app browser exercised drag from source frame 447 to 540, one/ten-frame keyboard stepping, chart cursor update and keyframe jump to 489 | Scrubbing updates image and values locally; only a settled selection is sent to Python. Browser checks are qualitative, not a frame-rate benchmark |
| Reviewed contact timing | Synthetic frame brackets, constant slowdown, missing timing confirmation, repeated-side requirements, overlap rejection, archive persistence and calendar delta bounds | Computation and eligibility gates behave as tested; no actual shoe-event detection accuracy is established |
| Profile-aware review | Offline rules and live synthetic youth/sex/body-size scenario passed; current-symptom live case remains blocked | Profile changes affect generated explanations; reliable generation for all injury contexts is not established |
| Calendar workflow | Save existing analysis, edit its date into another month, reopen it, then clear the temporary session; saved entry remains | Persistent date-based history is independent of browser session cleanup; duplicate IDs update metadata |
| Real clip decoding | HEVC, 1920×1080; 800 decodable frames in the full source | PyAV can read the supplied MOV; nominal metadata frame counts are not treated as actual decoded counts |
| Real selected passage | 2.55–3.20 decoded seconds, source frames 436–549, 114 processed frames | Actual pretrained-model inference and deterministic calculations completed on the user-provided video |
| Coverage | Model-left knee and trunk–thigh metrics: 114/114 valid frames; no subject-continuity rejection in this passage | Core tracking coverage is high under the chosen thresholds; it does not quantify anatomical accuracy |
| Artifact verifier | Both MP4s have 114 frames; PTS match the explicit 4× media slowdown; landmarks/series/JPEG/frame IDs align | Saved outputs are structurally consistent and synchronized to source-frame data |
| Visual audit | 24 evenly spaced annotated frames plus detailed selected extrema inspected | Foreground identity stays consistent in the inspected sample; skeleton follows visible limbs plausibly. Later frames become more oblique. This is qualitative, not expert annotation |
| Real app workflow | Streamlit test selects the private demo, launches a fresh subprocess analysis, and renders review successfully | The UI calls the actual local pipeline and receives a completed result, without an API key |
| Browser review | Saved analysis opened; keyframe selection changed source frame and values; motion curves and evidence tabs render; new contact crops and profile/research text inspected in the running app | Main review controls and new research/contact views render in the local in-app browser |
| API contract, offline | Actual OpenAI SDK with in-memory HTTP transport serializes the strict schema and parses a test response | The client integration is exercised without a paid request; this does not prove live model/account availability |

The local run manifest and visual audit are under ignored `artifacts/demo/`. Raw video and identifying imagery are not committed to GitHub. The demo manifest now records real validated generation; the default-profile report is cached locally. The live evaluation ledger is under ignored `artifacts/live_eval/`.

## Known constraints

- The camera pans, and viewpoint changes through the selected passage. Trunk/thigh orientation curves are relative to image vertical and excluded from AI coaching when camera movement is marked.
- Anatomical camera-facing side is not confirmed. The UI's automatic review-side choice uses model coverage. A confident side label can still be wrong.
- The selected passage has no complete detected candidate thigh cycle. Minima and maxima therefore describe an interval, not a full-stride norm.
- Knee and hip proxies have **not** been compared quantitatively with expert manual annotation or laboratory motion capture. No mean angle error is claimed.
- General body pose models can miss feet, swap left/right during occlusion, or produce confident geometry errors. Tested success on one clip does not establish general sprint accuracy.
- Shoe-contact boundaries are manually marked, not automatically detected. The private demo's real-time mapping is unverified, so no contact milliseconds or bilateral timing result is claimed for it. Frame-bracket bounds omit human annotation error, ground ambiguity and timing calibration error. The repeat-count and temporal-resolution gates are MVP choices, not validated clinical cutoffs.
- The reviewed adult sex-group study does not establish the high-school frontside hypothesis. Body size, sex category and a reported injury do not establish an individual's ideal posture, muscle capacity or cause of a side difference.
- The app does not automatically determine that the video depicts maximum-velocity sprinting or a suitable camera angle. Recording suitability depends on the user's selection and visual inspection.
- Native dependency portability is limited. MediaPipe 1.0.1 crashed on this Mac; 0.10.35 worked in a normal desktop context. Sandboxed graphics initialization failed even with CPU delegation. OpenCV/PyAV also emit an AVFoundation duplication warning in the tested macOS wheels.
- Structured output and reference validation cannot establish the scientific truth of generated prose. Curated source summaries and editorial activities require human review.
- File/resource limits and local session separation are MVP safeguards, not a hardened public upload service.

## Before the submission

1. **Live API follow-up:** baseline generation, Markdown export and zero-call cache reuse are verified. Resolve the active-symptom reliability failure and review prose quality before demonstrating that scenario. Do not put the key in the recording.
2. **Manual angle check:** select roughly twenty clear frames; mark shoulder, hip, knee and ankle centers independently of the overlay; calculate the same 2D definitions; inspect discrepancies and document error by metric. If reliable anatomical points cannot be marked, state that and narrow the claim.
3. **Additional input:** try a second clear side-on clip and an unsuitable/occluded clip. Confirm that low visibility yields gaps/limited output rather than fabricated coaching.
4. **Contact validation:** use verified real-time high-frame-rate footage with clear shoes, independently annotate multiple contacts per side and assess reviewer disagreement. Compare against a suitable reference before claiming measured accuracy or automatic injury relevance.
5. **Submission:** record the working flow, check video/audio, push clean source and provide reviewer access. Update README only after the live API and recording steps are completed.

The remaining language reliability and manual measurement checks are the most valuable next work. Adding more metrics would not resolve the current validation limits.

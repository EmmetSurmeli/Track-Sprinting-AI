# Validation status — September 10, 2026

The local analysis and review workflow works on the author's actual demonstration clip. **A real OpenAI coaching run, quantitative manual angle validation, and the final submission recording are still pending.** This document separates those from completed checks.

## Completed checks

| Check | Evidence | What it establishes |
| --- | --- | --- |
| Offline test suite | 31 tests passed on the local Python 3.13 environment | Geometry, visibility gaps, timestamp handling, export consistency, scoped cleanup, failed-run completion markers, report guards, SDK serialization and core Streamlit rendering behave as tested |
| Real clip decoding | HEVC, 1920×1080; 800 decodable frames in the full source | PyAV can read the supplied MOV; nominal metadata frame counts are not treated as actual decoded counts |
| Real selected passage | 2.55–3.20 decoded seconds, source frames 436–549, 114 processed frames | Actual pretrained-model inference and deterministic calculations completed on the user-provided video |
| Coverage | Model-left knee and trunk–thigh metrics: 114/114 valid frames; no subject-continuity rejection in this passage | Core tracking coverage is high under the chosen thresholds; it does not quantify anatomical accuracy |
| Artifact verifier | Both MP4s have 114 frames; PTS match the explicit 4× media slowdown; landmarks/series/JPEG/frame IDs align | Saved outputs are structurally consistent and synchronized to source-frame data |
| Visual audit | 24 evenly spaced annotated frames plus detailed selected extrema inspected | Foreground identity stays consistent in the inspected sample; skeleton follows visible limbs plausibly. Later frames become more oblique. This is qualitative, not expert annotation |
| Real app workflow | Streamlit test selects the private demo, launches a fresh subprocess analysis, and renders review successfully | The UI calls the actual local pipeline and receives a completed result, without an API key |
| Browser review | Saved analysis opened; keyframe selection changed source frame and values; motion curves and evidence tabs render | Main review controls work in the local in-app browser |
| API contract, offline | Actual OpenAI SDK with in-memory HTTP transport serializes the strict schema and parses a test response | The client integration is exercised without a paid request; this does not prove live model/account availability |

The local run manifest and visual audit are under ignored `artifacts/demo/`. Raw video and identifying imagery are not committed to GitHub. The manifest's `llm_generated` flag remains false until real validated generation succeeds.

## Known constraints

- The camera pans, and viewpoint changes through the selected passage. Trunk/thigh orientation curves are relative to image vertical and excluded from AI coaching when camera movement is marked.
- Anatomical camera-facing side is not confirmed. The UI's automatic review-side choice uses model coverage. A confident side label can still be wrong.
- The selected passage has no complete detected candidate thigh cycle. Minima and maxima therefore describe an interval, not a full-stride norm.
- Knee and hip proxies have **not** been compared quantitatively with expert manual annotation or laboratory motion capture. No mean angle error is claimed.
- General body pose models can miss feet, swap left/right during occlusion, or produce confident geometry errors. Tested success on one clip does not establish general sprint accuracy.
- The app does not automatically determine that the video depicts maximum-velocity sprinting or a suitable camera angle. Recording suitability depends on the user's selection and visual inspection.
- Native dependency portability is limited. MediaPipe 1.0.1 crashed on this Mac; 0.10.35 worked in a normal desktop context. Sandboxed graphics initialization failed even with CPU delegation. OpenCV/PyAV also emit an AVFoundation duplication warning in the tested macOS wheels.
- Structured output and reference validation cannot establish the scientific truth of generated prose. Curated source summaries and editorial activities require human review.
- File/resource limits and local session separation are MVP safeguards, not a hardened public upload service.

## Before the submission

1. **Live API acceptance:** enable API billing, enter the key privately, generate a report, inspect its language and citations, download it, then regenerate the identical request to confirm the cached path makes no new call. Check that the manifest records real generation. Do not put the key in the recording.
2. **Manual angle check:** select roughly twenty clear frames; mark shoulder, hip, knee and ankle centers independently of the overlay; calculate the same 2D definitions; inspect discrepancies and document error by metric. If reliable anatomical points cannot be marked, state that and narrow the claim.
3. **Additional input:** try a second clear side-on clip and an unsuitable/occluded clip. Confirm that low visibility yields gaps/limited output rather than fabricated coaching.
4. **Submission:** record the working flow, check video/audio, push clean source and provide reviewer access. Update README only after the live API and recording steps are completed.

The first two pending checks are the most valuable next work. Adding more metrics would not resolve the current validation limits.

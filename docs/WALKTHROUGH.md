# Explain the code in ten minutes

## The main idea

“I used a pretrained model to locate joints, Python geometry to measure motion, and a language model to explain a constrained set of facts with research citations. The athlete can inspect the frame behind each observation.”

## Follow one frame

1. Open `src/track_sprint/video.py`. `iter_frames` produces `(source_index, media_time, RGB_image)`. It decodes sequentially so frame IDs mean the same thing in the saved image, plot and report. A phone's slow-motion player time can differ from media timestamps.
2. Open `pose.py`. `PoseTracker.detect` returns normalized coordinates, visibility and presence for each joint. MediaPipe was pretrained by Google; we do not claim to have trained it. The tracker follows the foreground runner, with conservative missing-data behavior when continuity is uncertain.
3. Open `metrics.py`. `side_metrics` converts x/y to pixels. This matters: an x difference of 0.1 and y difference of 0.1 are different distances in a widescreen image. Knee flexion is an included-angle calculation. No language model is involved.
4. Open `pipeline.py`. The loop processes each selected frame, saves raw and accepted landmarks, calculates trajectories, chooses extrema, and renders the overlay. A manifest records the input and model hashes. The original video remains unchanged.
5. Open `charts.py` and `app.py`. The slider's index points to the original source frame and becomes the vertical cursor on every plot. The video players themselves are independent.
6. Open `coaching.py`. `build_context` restricts metrics before the API sees them. `generate_report` requests typed output. `validate_grounding` rejects references outside the eligible facts, frames, sources or activity catalog. The app renders numeric facts from Python data rather than trusting generated numbers.

## Answers worth practicing

**Why use an LLM?** It adapts a compact explanation to the athlete's experience and goal, links measured observations to a curated research context, and expresses uncertainty. It does not merely chat or recognize a video.

**Is this RAG?** It is small, explicit retrieval-augmented generation: topic tags select reviewed source summaries before generation. There is no vector database. That is appropriate for this deliberately small library and makes retrieval inspectable.

**What does confidence mean?** Visibility/presence scores and coverage tell us whether data passed tracking checks. They do not guarantee an angle is anatomically correct. Camera projection and occlusion can produce confident errors.

**Why no asymmetry score?** Camera-facing and camera-far limbs are measured differently. One video cannot establish muscle weakness, and this MVP does not have enough validation to support a meaningful bilateral score.

**How are hallucinations controlled?** We restrict the input facts, require a schema, check references, render numbers ourselves, constrain activities, bound retries and preserve provenance. These controls reduce failure modes; they cannot prove every generated sentence is correct.

**What happens without an API key?** All local analysis works. The AI report shows a setup state. The app never substitutes a hard-coded coaching report and calls it generation.

**What would you build next?** First quantify errors against manual annotations and test more recordings. Then improve athlete selection and synchronized playback. Wider feature claims should follow validation.

**What did AI assistance contribute?** Be candid about using Codex for implementation and testing assistance. Explain your product motivation, scope choices and verification work. Demonstrate that you can trace the code and make an intentional change.

## A small learning exercise

Read `test_metrics.py`, predict the angle of a horizontal thigh beneath an upright trunk, then run the test. Next change the display color of one side in `charts.py` and confirm that it affects the curve without changing `summary.json`. This separates presentation from computation in a concrete way.

# Track Sprint AI

A local sprint-video review app built for a Cornell Generative AI Club application. Upload a video, inspect a pose overlay and frame-linked joint-angle curves, then generate a short research-grounded coaching review through the OpenAI API.

**Pose tracking finds joints. Python calculates measurements. The LLM explains the resulting evidence.** The model never invents angles from the video.

This is an MVP for a local demonstration and source-code review. It is not a publicly deployed service or a validated biomechanics instrument. The deterministic pipeline, UI, and live AI coaching run on the author's demonstration video. Five of six live acceptance scenarios passed; active-symptom generation remains unreliable and is blocked by report checks. See [live acceptance results](docs/LLM_ACCEPTANCE.md) and [validation status](docs/VALIDATION.md).

## Run locally

Tested on Apple Silicon macOS with Python 3.13. Use **Python 3.13 with the pinned snapshot below**; other operating systems have not been verified. The project also permits Python 3.11–3.12 through the editable installation command, with compatible dependency resolution, but those environments have not been tested.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m streamlit run app.py
```

Open **http://127.0.0.1:8501**. No account or API key is required to inspect video and calculate angles. On Windows, activate with `.venv\Scripts\activate` if compatible wheels are available.

The first analysis downloads Google's Pose Landmarker Full model to ignored `models/`. Subsequent pose analyses work offline. Model download and package installation need internet access. The app binds to localhost by default; do not expose it as a public service.

For editable development, use `python -m pip install -e '.[dev]'`. The entry points also resolve `src/` directly, so launching from a fresh clone does not depend on editable-import behavior.

## Use it

1. Upload your own MOV, MP4 or M4V under 100 MB and up to 4K. Keep the athlete's full body visible and choose an approximately side-on upright passage. A steady camera is preferable.
2. Select a short interval, up to ten **decoded media seconds**. Slow-motion phone files can have different decoder and player timelines. Start/middle/end previews show the actual selected source frames.
3. Set travel direction and, if known, the athlete's camera-facing anatomical side. Leave the side unknown when unsure. Mark camera movement honestly.
4. Analyze. Review the original and annotated passage, scrub frames, and open the motion curves. Gray joints fail visibility checks; missing measurements stay missing.
   Completed analyses are automatically saved to **Calendar & progress**, using today's date or the recording date you select. Add session notes or coach feedback, browse any month/year, reopen saved analyses and compare with previous sessions. An existing result can be added with **Save to calendar**.
5. In **Contacts & sides**, scrub the original footage and use **Set touchdown here** / **Set toe-off here** to mark the frame you are viewing. Choose which foot you followed, then check both transition pairs before saving. The selections start empty and are not automatic detections. Milliseconds require a verified real-time mapping. Side comparisons require confirmed anatomical labels, at least two clear contacts per side, and sufficiently small timing brackets. Annotations save with the analysis; eligible contact means and uncertainty also appear in the calendar.
6. Fill in optional age, height, weight, research sex category, experience and injury context. **Profile & research** explains how those details affect the AI request and which research applies. These fields do not create an ideal angle or diagnose a weak muscle.
7. Enter an API key privately and select **Generate coaching**. Inspect the personalized explanation, cited frames and research caveats before using any suggestions.
8. Download the annotated MP4, measurement JSON, coaching Markdown, or analysis ZIP. The ZIP includes saved contact annotations and derived timing results.

The original file is not modified. Both exported video players show the selected passage at a deliberate fourfold slowdown of the decoder timeline. Their playback is independent; the frame slider provides exact correspondence with measurements and chart cursors.

The frame inspector loads compressed previews into the browser, then updates the image and measurements as you drag. Use arrow keys for single frames or Shift + arrow for ten-frame steps. Releasing the slider updates the motion-chart cursor; dragging itself does not rerun the Python app. Initial preview preparation happens once per cached analysis.

The author's private demo input and derived media are intentionally excluded from GitHub. A fresh clone starts with an upload screen. The local **Use my demo clip** / **Open saved analysis** shortcuts appear only when the corresponding ignored artifacts exist.

## Set up the generative AI connection

1. Sign in at [OpenAI Platform](https://platform.openai.com/).
2. Open API billing and add the payment method or credits required for your account. API billing is separate from a ChatGPT subscription. [Official billing guide](https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform).
3. Create a project API key from the platform's API keys page. Copy it into the app's **OpenAI API key** password field. Do not paste it into chat, source code, screenshots, or a Git commit.
4. Select **Generate coaching** on a completed analysis. If the app reports a billing/rate limit, check the platform's billing and usage pages.

Alternatively, copy `.env.example` to `.env` and set `OPENAI_API_KEY` locally. `.env` is ignored. The sidebar field keeps the key only in the current app session. A ChatGPT/Codex usage reset does not create API credits.

The app uses `gpt-5.4-mini` with the Responses API and a strict structured-output schema. A click makes one request, with at most one extra repair request after a validation failure. Automatic SDK retries are disabled; each attempt is capped at 2,500 output tokens and a 45-second client timeout. A client timeout does not guarantee the provider stops processing. Matching completed reports are cached. Repeated profile changes can still create new paid requests. See current [model documentation and pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

No report is fabricated when the API is unavailable. Cached reports retain real generation provenance; mock model responses exist only inside automated tests.

## What leaves your computer

Pose inference, original footage, extracted frames and landmarks stay local. Only the computed summary, reviewed contact results, optional athlete profile and selected research summaries are sent to OpenAI when generation is requested. The request sets `store=False`; this does not imply zero provider retention. [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data).

The key and raw input profile are excluded from saved reports and downloads. Saved personalization rules and generated prose can still reveal profile context, including whether youth or injury constraints applied; review exports before sharing. Derived artifacts live in `artifacts/`. **Clear this session** removes temporary browser-session files. Your calendar, session notes and archived analysis passages persist under `artifacts/history/`, separate from temporary cleanup, saved demo artifacts and downloaded exports. Expired temporary directories are cleaned when a later session starts. This is an ordinary filesystem deletion, not a secure-erasure guarantee.

The calendar is one local training log for the same athlete; it does not identify people across uploads. Re-saving the same analysis updates its date/title/notes instead of adding duplicates. Date changes reorder the history. Comparisons show observed minimum/maximum angle differences and trends, with no automatic better/worse score: angle changes can reflect camera viewpoint, selected sprint phase or pose error. Event, side, processing method and visibility checks restrict comparisons. Camera-relative orientation metrics are omitted from comparisons when either camera moves. Export the training log as JSON from the calendar page.

## Verify the code

```bash
python -m pytest -q
python scripts/analyze_video.py /path/to/video.mov --start 2.55 --end 3.20 --output artifacts/my-run
python scripts/verify_artifacts.py artifacts/my-run
```

Tests use synthetic geometry, short generated videos and clearly isolated mock API responses. They do not require an API key, model download or private video. They cover missing-data behavior, geometry, frame/timestamp preservation, export consistency and report grounding. Optional tests for the author's local demo skip when those ignored files are absent.

## Repository guide

```text
app.py                         Streamlit UI, session lifecycle, local worker launch
src/track_sprint/
  video.py                     Validation, orientation, decoding, original frame IDs
  pose.py                      MediaPipe boundary and foreground-subject continuity
  metrics.py                   Explicit 2D geometry, smoothing, candidate extrema
  pipeline.py                  Pose → measurements → reproducible artifacts
  render.py                    Skeleton overlay and timestamp-preserving MP4 export
  coaching.py                  Retrieval, bounded API calls, grounding checks, cache
  schemas.py                   Typed contracts
  charts.py                    Frame-linked Plotly curves
  frame_viewer.py / viewer/     Browser-side scrubbing, preview cache and frame stepping
  artifacts.py                 Hashes, atomic JSON writes, scoped cleanup
  history.py                   Durable SQLite training log and comparison rules
  calendar_ui.py               Month view, dated notes, saved results and trends
  contacts.py / contact_ui.py   Reviewed shoe transitions, timing bounds, side differences
  personalization.py           Profile rules and research applicability
  profile_ui.py                Profile effects and injury-aware research discussion
  data/                        Fifteen reviewed research summaries and activity catalog
scripts/                       CLI analysis, decoding inspection, artifact verification
tests/                         Offline unit/integration tests
docs/                          Design, validation, walkthrough and demo preparation
```

Read [the architecture](docs/DESIGN.md), [limitations and validation](docs/VALIDATION.md), [code walkthrough](docs/WALKTHROUGH.md), [demo script](docs/DEMO_SCRIPT.md), and [GitHub submission guide](docs/SUBMISSION.md). The earlier [approved plan](docs/MVP_PLAN.md) records scope decisions; actual implementation takes precedence.

The [profile and contact research note](docs/PROFILE_AND_CONTACT_RESEARCH.md) documents timing assumptions, potential contributors to investigate, and why the high-school sex/frontside hypothesis is not established by the reviewed studies.

The [biomechanics roadmap](docs/BIOMECHANICS_ROADMAP.md) distinguishes implemented measurements from future contact detection, event-conditioned geometry, flight timing and calibrated stride length, with primary research and commentary on The Sprint Project's coaching articles.

## Troubleshooting

- **Pose runtime crashes on macOS:** use the pinned `mediapipe==0.10.35`. The tested newer 1.0.1 build failed during native initialization. On this Mac, MediaPipe also needed the normal logged-in desktop graphics services even with the CPU delegate; an OS sandbox without those services failed. Launch normally from Terminal. Analysis runs in a child process so a native failure does not terminate the whole app.
- **OpenCV/PyAV native warning:** the tested macOS wheels warn about duplicate AVFoundation classes. The verified decode/inference/encode flow completed despite this warning. Native video libraries are a portability risk; do not install multiple competing OpenCV variants into this environment.
- **Corrupt, unsupported or unusually long file:** export an H.264 MP4 and use a shorter passage. Browser playback uses converted H.264, including for supported HEVC inputs.
- **No pose or poor tracking:** use a closer, sharper side view with the athlete fully visible. The app does not silently substitute invented joints.
- **Wrong athlete:** the tracker initially prefers the largest person and then continuity. Two similarly sized athletes are unsupported. Use a clip with one clear foreground subject.
- **Blank AI area:** local analysis is independent of generation. Add the API key, confirm billing and click Generate coaching. An error is shown if output fails validation; no placeholder is presented as a real report.

## Credits

MediaPipe/BlazePose supplies pretrained pose estimation; this project does not train a pose model. Research sources are linked individually in the app and [third-party notes](THIRD_PARTY.md). AI coding assistance was used in building this MVP; the application author should be able to explain and verify the delivered code. The distinctive product work is the review workflow, deterministic measurement boundary, uncertainty handling and traceable generative explanation.

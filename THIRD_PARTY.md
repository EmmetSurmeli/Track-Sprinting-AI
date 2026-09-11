# Third-party components and evidence

Track Sprint AI uses pretrained software and models; it does not claim authorship of them. Dependencies retain their own licenses. No model weights, paper PDFs or original athlete videos are committed to this repository.

- **MediaPipe:** Google's pose-estimation runtime, Apache-2.0. [Official repository and license](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE).
- **Pose Landmarker Full:** downloaded at first use from the [versioned Google model URL](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task). The SHA-256 is recorded per run. [Official Pose Landmarker documentation](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python) and [BlazePose GHUM model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf). Consult the model's terms before redistributing weights; this repository downloads rather than bundles them.
- **OpenCV, PyAV/FFmpeg, NumPy, SciPy:** video processing and deterministic numerical calculations. Wheels may include native libraries with additional notices; preserve their distributed license files when redistributing binaries.
- **Streamlit and Plotly:** local application UI and curves.
- **OpenAI Python SDK and hosted API:** structured text generation, subject to the provider's account and API terms. No key or paid access is bundled.

`src/track_sprint/data/evidence.json` contains short original paraphrases of fifteen linked research sources, using abstracts and selected full-text material, with population, evidence type and limitations. It does not reproduce full papers. The VideoRun2D record is explicitly labeled as a workshop research preprint. Study results from OpenPose or adapted MoveNet are not claimed as validation of MediaPipe or this app. Adult group differences, laboratory asymmetry measurements and football injury associations are not treated as youth technique norms, individual muscle assessments or injury predictions.

`activities.json` is an editorial catalog of conservative prompts for discussion with a coach. It is separate from the research summaries: a paper about training does not establish that an exercise corrects an angle measured by this app.

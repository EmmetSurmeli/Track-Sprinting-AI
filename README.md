# Track Sprint AI

A local sprint-video analysis app. Enter an athlete profile, upload a recording, inspect body tracking, and get AI coaching tied to measured motion.

## How it works

MediaPipe estimates joints on each frame. Python calculates projected leg and arm angles, retains the ordered motion and tracking gaps, and calculates additional measurements from reviewed events. An OpenAI model explains the eligible data using a curated research library and athlete context.

The interface follows **profile → upload → tracked video → technique, interpretation, focus and training**. Detailed measurements and sources are expandable. A local calendar stores dated analyses.

## Run locally

Tested on Apple Silicon macOS with Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m streamlit run app.py
```

This repository provides source code, not access to a hosted service. Open the local address printed by Streamlit. Anyone running their own copy must supply their own API key in a local `.env` file using `.env.example`. No API key, personal profile, private footage or local cache is included.

The first analysis downloads the pretrained pose model. Video processing runs locally. Coaching sends computed measurements, profile context and selected research summaries to OpenAI; the video itself stays local. Matching completed analyses and reports can be reused, with reuse labelled in the interface.

## Verification

```bash
python -m pytest -q
```

Ordinary tests make no API requests. Optional private-video tests skip when their files are absent. Live evaluation scripts require an explicit `--live` flag and maintain a spending ledger.

## Scope

Projected movement can support technique observations. It cannot by itself establish muscle weakness, force production, injury causes or an individual ideal angle. Contact timing requires reviewed transitions and verified recording timing. Repeated side comparisons require suitable tracked cycles; a single peak difference is not a diagnosis.

Architecture and measurement limits are documented in [DESIGN.md](docs/DESIGN.md) and [VALIDATION.md](docs/VALIDATION.md).

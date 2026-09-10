# Demo outline

Target about two minutes unless the application specifies another limit. Record the local app and speak naturally. Do not show the API key or claim checks that are still pending in VALIDATION.md.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:15 | App and selected sprint passage | “As a sprinter and informal coach, I often slow down footage and inspect it frame by frame. I built a workspace that makes those observations easier to trace.” |
| 0:15–0:35 | Analyze the supplied clip, then overlay | “A pretrained pose model finds the joints. The analysis is actually running on this recording; the results are not hard-coded.” |
| 0:35–0:55 | Keyframe button, frame values, motion curves | “Python calculates these projected angles. Selecting a source frame updates the measurements and the chart cursor. Low-visibility gaps are preserved.” |
| 0:55–1:25 | Generate coaching, then a cited observation | “The LLM receives eligible measurements, my goal and reviewed research summaries. This observation links to the supporting frames and its source limitations.” |
| 1:25–1:45 | Method tab and manifest | “Tracking coverage is not anatomical accuracy. I exclude contact times, forces and strength conclusions. The manifest records the exact inputs and model used.” |
| 1:45–2:00 | Download and briefly show repo | “The repository includes tests, setup instructions and documented limits. Next I would validate against manual annotations and test more standardized recordings.” |

Before recording, make one successful real API report and review its language. The same completed report can be cached for later playback, but describe it as a saved result if the demonstration does not make a live request. If showing live generation, allow for network latency or cut waiting time transparently.

The supplied phone clip uses a panning camera and turns oblique near the edges. Keep the selected central passage and say so. The original demo interval is 2.55–3.20 decoder seconds, source frames 436–549 on the tested decoder. Do not equate those media seconds with verified sprint time.

Use the code walkthrough to rehearse before recording. The recording and GitHub push remain author submission steps; no account, video hosting link or public repository has been created by this build.

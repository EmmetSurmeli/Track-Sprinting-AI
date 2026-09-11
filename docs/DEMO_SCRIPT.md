# Demo outline

Target about three minutes unless the application specifies another limit. Record the local app and speak naturally. Do not show the API key or claim checks that are still pending in VALIDATION.md.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:15 | App and selected sprint passage | “As a sprinter and informal coach, I often slow down footage and inspect it frame by frame. I built a workspace that makes those observations easier to trace.” |
| 0:15–0:35 | Analyze the supplied clip, then overlay | “A pretrained pose model finds the joints. The analysis is actually running on this recording; the results are not hard-coded.” |
| 0:35–0:55 | Keyframe button, frame values, motion curves | “Python calculates these projected angles. Selecting a source frame updates the measurements and the chart cursor. Low-visibility gaps are preserved.” |
| 0:55–1:15 | Enter your actual profile; open Profile & research | “My experience and goal change the explanation. Age and injury context change what advice is permitted. Body details help determine which research applies; the app does not invent an ideal angle for my demographic.” |
| 1:15–1:45 | Generate coaching, then its personalization and a cited observation | “The LLM receives eligible measurements, my profile and reviewed research summaries. This explanation shows how my details shaped the review. The observation links to supporting frames and source limitations.” |
| 1:45–2:10 | Contacts & sides; inspect shoe transitions | “I can review touchdown and toe-off independently for each foot. Timing needs a verified timeline and uncertainty bounds. This phone clip's real-time mapping remains unverified, so the app withholds milliseconds.” |
| 2:10–2:30 | Calendar & progress; change the recording date and reopen | “Each analysis stays in a dated local log. Compatible measurements can be compared over time. A change is not automatically an improvement.” |
| 2:30–2:45 | Research check and Method tab | “The studies reviewed here don't establish that most high-school girls use less frontside motion. The app shows that limitation instead of assigning a sex-based technique target. It also avoids inferring a weak muscle from a side difference.” |
| 2:45–3:00 | Download and briefly show repo | “The repository includes tests, setup instructions and documented limits. Next I would validate against manual annotations and test more standardized recordings.” |

Before recording, make one successful real API report and review its language. The same completed report can be cached for later playback, but describe it as a saved result if the demonstration does not make a live request. If showing live generation, allow for network latency or cut waiting time transparently.

To show a profile change affecting generation, first show the visible rules, then regenerate after an intentional change and compare the personalization paragraphs. Use your real details for your own run. If demonstrating a different athlete or injury scenario, label it as an illustrative scenario; do not imply it describes you. Profile changes require a new API request. Current symptoms should keep the response observational and suppress activity suggestions.

The supplied phone clip uses a panning camera and turns oblique near the edges. Keep the selected central passage and say so. The original demo interval is 2.55–3.20 decoder seconds, source frames 436–549 on the tested decoder. Do not equate those media seconds with verified sprint time.

Use the code walkthrough to rehearse before recording. The recording and GitHub push remain author submission steps; no account, video hosting link or public repository has been created by this build.

# Second recording: demonstration and audit

Upload `IMG_7190.mov` yourself after profile setup, then click **Analyze my run**. No video is shown before upload. The exact uploaded file can reuse the real prepared passage: 2.4–7.4 decoded media seconds, source frames 72–221. The reuse is labelled in the UI; trim and direction remain editable.
The supplied file decodes to 391 frames over approximately thirteen media seconds. The five-second selection has 150 frames and 99.3% model-right core-joint coverage. Coverage measures accepted tracking, not angle accuracy. Its capture-to-playback time mapping remains unverified. Do not describe the selected media duration as actual sprint duration.

## A useful recording sequence

1. Play the selected passage and scrub through the overlay. Show that the ankle, knee and hip follow the runner.
2. Open **Explore your tracking & data → Landing position & contact timing**. The saved developer review selects source frame **155**, model-right. Expand **Select or change landing position** to show the original and overlay together. This is a visible landing posture, **not an exact touchdown annotation**. The shoes are visible, but first ground contact is ambiguous, so no contact duration has been prefilled.
3. Show the computed **45.7% projected-leg-length ankle offset** and **25.6° knee bend**. The former is the image-horizontal ankle-to-same-side-hip distance divided by projected thigh plus shank length. Positive means forward. Neither number is an optimal target or a calibrated center-of-mass measurement. These values use accepted unsmoothed landmarks; the ordinary frame overlay uses smoothed angles and can differ slightly.
4. Enter your real profile and goal. Open **Explain my technique**. Matching tested default-profile reports load from cache at no additional API cost; changed profiles generate new reports. Say “saved AI report” when the app says it is cached.
5. Show the finding, practice cue and source-frame link. The real output identifies forward placement with a relatively extended knee and proposes reviewing whether reaching ahead repeats. It does not claim weak glutes, lost power, a confirmed heel strike or a worse performance score. See the [actual generated example](examples/second-clip-review.md).
6. Click the source-frame link, then open **Explore your tracking & data**, to inspect the evidence. Save the session to the calendar using its actual recording date if known, or a clearly labelled demonstration date. A date change alone does not establish training progress.

The second recording has a visible technique-review opportunity. The application is not given a “bad form” label or a scripted negative response. Demonstrate what it actually finds rather than promising an automatic good-versus-bad verdict.

## What was checked

- Inspected original lower-limb sequences and full-resolution shoe crops around the landing and departure, then checked frame 155 against the pose overlay.
- Analyzed both the selected five seconds and a longer 0–10-second passage. The five-second passage has no complete continuously tracked bilateral geometric cycles; the longer passage has one right-side candidate, no left-side candidate, and unstable cycle boundaries. Neither qualifies for repeated left–right coaching.
- Kept anatomical side and timing unconfirmed; added no artificial contact marks or repeat-cycle approvals.
- Tested scale invariance, direction reversal, aspect correction, missing/occluded/out-of-frame landmarks, degenerate geometry, review confirmation, analysis identity, source-frame references, AI inclusion and withholding on insufficient tracking.
- Tested real reports with default and technique goals, an adversarial request for a negative verdict, youth/body/sex context, and current symptoms. Checked each cached repeat without another API request.
- Verified the upload workflow and displayed values in the running browser and Streamlit tests. Calendar resaves refresh later annotations and reports.

This is qualitative visual inspection plus software acceptance testing. Expert manual digitization, known camera calibration, measured forces, verified capture timing and an independent technique assessment have not been supplied. The research does not validate the app's pose estimates or provide individual target angles.

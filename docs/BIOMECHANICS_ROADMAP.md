# From video review to reliable sprint biomechanics

Research review: September 10, 2026.

## Current correction

The original contact controls initialized two adjacent frame selections and displayed them with event labels. They were manual inputs, not detected events, but appeared to be automatic results. The revised workflow starts with empty side/boundary selections and a browser-side viewer of the original footage. The athlete marks the frame currently visible, then confirms both transitions. Unconfirmed selections never become timing facts.

Current AI input includes eligible projected-angle extrema and, when manually reviewed and timing-qualified, contact-duration facts. It does not include images, touchdown distance, whole-body center of mass, flight time or stride length. More research can refine interpretation but cannot substitute for those missing measurements.

## Measurement dependencies

| Feature | Required inputs and interpretation | Current status |
| --- | --- | --- |
| Left/right contact duration | Correct shoe transitions, verified timeline, stable anatomical labels, several complete contacts per side | Manual review implemented; automatic detection unvalidated |
| Relative side-duration difference | Repeated contacts under comparable conditions; even a dimensionless ratio requires confidence that export speed did not change between contacts | Existing bilateral calculation requires verified timing |
| Flight time | Toe-off to the next opposite-foot touchdown, with both feet visible and confirmation that no intervening contact was missed | Not yet computed |
| Contact-to-flight ratio | Complete consecutive contact/flight sequence and uncertainty on all boundaries | Not yet computed; no universal target |
| Step and stride time | Successive opposite-foot touchdowns for step time; successive same-foot touchdowns for stride time, with no missed steps | Not yet computed from reviewed events |
| Step and stride length | Calibrated ground-plane positions of consecutive foot contacts; step = opposite feet, stride = same foot | Requires distance calibration and camera-motion handling |
| Placement at touchdown | Independently confirmed touchdown, visible landmarks and explicitly defined projected foot/ankle-to-pelvis reference | Not yet computed; pelvis is not whole-body center of mass |
| Knee, thigh and shin positions at touchdown/toe-off | Event-conditioned frame geometry and visibility checks | Current curves show interval measurements, not event-conditioned analysis |
| Angular velocity | Reliable trajectories, filtering and calibrated real-time timestamps | Not yet computed |
| Force, power or muscle capacity | Additional measurements or separately validated models | Not supplied by current video geometry |

Airtime measures duration, not horizontal displacement. Knowing flight time alone leaves horizontal velocity and contact-phase travel unknown. A longer airborne phase can occur without a longer stride or faster sprint. In a moving camera view, raw pixel displacement also includes camera motion.

## Why non-LLM contact detection is the preferred next experiment

[Nagahara and Zushi (2013)](https://www.jstage.jst.go.jp/article/ijshs/11/0/11_201318/_article) evaluated foot-marker kinematics against force measurements during acceleration. Their result supports event-specific temporal algorithms under controlled conditions, not simply labeling the lowest MediaPipe toe point as touchdown.

[Evans et al. (2021)](https://link.springer.com/article/10.1007/s00138-021-01236-z) evaluated occupancy-based contact detection and fused pose tracking using multiple cameras. This demonstrates a computer-vision route without an LLM, while also illustrating the gap between a calibrated research setup and one panning phone recording.

Recommended implementation sequence:

1. Collect clear, high-frame-rate side-on footage with verifiable playback timing and several complete steps per side. Record known distances in the athlete's plane if spatial measurements are wanted.
2. Use the original-frame scrubber to label touchdown and toe-off independently, including an uncertain/occluded category. Record disagreements between reviewers.
3. Develop automatic **candidate windows** using shoe tracking, ground proximity and temporal motion, with camera-motion compensation. Do not equate candidate confidence with timing accuracy.
4. Evaluate boundary error, missed/extra contacts and left/right swaps against held-out labeled clips from different athletes. Report failures as well as average errors. Split evaluation by athlete/recording rather than adjacent frames.
5. Allow reviewed candidates to feed event-conditioned angles, flight/step timing and ratios. Add calibrated contact locations before spatial stride measurements.
6. Pass these numeric facts, uncertainty, sprint phase and relevant research to the LLM. Evaluate whether the generated explanation respects the measurements and evidence. Training recommendations require a separate curated connection between observed patterns, goals, constraints and appropriate activities.

A vision-language model could supply a second opinion on ambiguous windows, but it would need the same event-level evaluation. A plausible description of a shoe near the track does not establish exact ground contact. It also introduces a change from the current local-video privacy boundary, since selected images would leave the computer. No such image upload or paid vision call was added in this change.

## Placement and optimal technique

The Sprint Project's [foot-strike article](https://www.thesprintproject.co/blog/how-to-improve-your-foot-strike) and [top-speed article](https://www.thesprintproject.co/blog/3%20ways%20to%20improve%20your%20top%20speed) provide useful coaching topics and acknowledge that fast athletes can contact slightly ahead of the hips. These are coaching explanations, not validation of the app's measurements or a basis for calculating force from shin angle. Their programming suggestions are not automatically imported as personalized prescriptions.

[Haralabidis et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12893165/) modeled an adult male sprinter at top speed. Shortening foot-to-center-of-mass touchdown distance below the model's optimum reduced both contact time and speed. This challenges the blanket rule that closer placement or shorter contact is always better. The simulation does not supply this user's optimal distance, angle or training prescription, and a hip landmark does not locate whole-body center of mass.

The current generative instructions now explicitly forbid inferring landing position from angle extrema or presenting missing flight, distance or force measurements as known. The three primary measurement/simulation studies above are included as curated evidence. The next accuracy gain comes from event validation and standardized footage, alongside research—not from asking the LLM to be more confident.

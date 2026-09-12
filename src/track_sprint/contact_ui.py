"""Inspectable shoe contact annotations; never silently promote landmarks to events."""
import av
import numpy as np
from PIL import Image
import streamlit as st

from .contacts import contact_results, load_contact_review, sampled_side_differences, save_contact_review
from .schemas import ContactMark
from .frame_viewer import show_frame_viewer
from .artifacts import read_json, write_json
from .posture import PostureReview, posture_evidence


def show_landing_posture(directory, summary):
    st.markdown("**Landing position**")
    st.caption("Choose a visible landing position in the original footage. This measures posture at that frame; it does not mark the exact start of contact.")
    path = directory / "posture_review.json"
    saved = PostureReview.model_validate(read_json(path)) if path.exists() else None
    suffix = summary["analysis_id"][:16]
    with st.expander("Select or change landing position", expanded=saved is None):
        cols = st.columns(2)
        side = cols[0].selectbox("Landing model side", ["left", "right"],
            index=["left", "right"].index(saved.side) if saved else None, key=f"landing-side-{suffix}")
        frame = cols[1].selectbox("Landing source frame", summary["frames"],
            index=summary["frames"].index(saved.frame) if saved else None, key=f"landing-frame-{suffix}")
        if side is not None and frame is not None:
            index = summary["frames"].index(frame)
            originals, _ = boundary_images(directory, [index], side)
            st.image(originals[index], caption=f"Original · source frame {frame}", width="stretch")
            overlay = directory / "frames" / f"{frame:06d}.jpg"
            if overlay.exists():
                st.image(str(overlay), caption="Check the tracked hip, knee and ankle against the original", width="stretch")
            checked = st.checkbox("I checked the landing position and the hip, knee and ankle tracking", value=bool(saved and saved.geometry_checked), key=f"landing-checked-{suffix}")
            if st.button("Save landing position", disabled=not checked, key=f"landing-save-{suffix}"):
                review = PostureReview(analysis_id=summary["analysis_id"], side=side, frame=frame, geometry_checked=checked)
                result = posture_evidence(directory, summary, review)
                if not result["available"]:
                    st.warning(result.get("reason", "Tracking is insufficient at this position."))
                else:
                    write_json(path, review.model_dump())
                    st.rerun()
        if saved and st.button("Remove landing position", key=f"landing-remove-{suffix}"):
            path.unlink()
            st.rerun()
    result = posture_evidence(directory, summary)
    if result["available"]:
        facts = list(result["facts"].values())
        a, b = st.columns(2)
        a.metric("Ankle ahead of hip", f"{facts[0]['min']:.1f}%", help="Positive is forward along the image horizontal; normalized by projected thigh plus shank length.")
        b.metric("Knee bend at landing", f"{facts[1]['min']:.1f}°")
        st.caption(f"Source frame {saved.frame} · model-labelled {saved.side} · one selected posture. Forward placement alone is not an overstriding verdict.")
    return result


def boundary_images(directory, indices, side):
    frames = {}
    with av.open(str(directory / "original.mp4")) as container:
        for index, frame in enumerate(container.decode(video=0)):
            if index in indices:
                frames[index] = Image.fromarray(frame.to_ndarray(format="rgb24"))
            if index >= max(indices):
                break
    points = np.load(directory / "landmarks.npz")["raw"]
    ids = [27, 29, 31] if side == "left" else [28, 30, 32]
    crops = {}
    for index, im in frames.items():
        p = points[index, ids]
        valid = (np.isfinite(p).all(axis=1) & (p[:, 2:].min(axis=1) >= .5)
                 & (p[:, :2].min(axis=1) >= 0) & (p[:, :2].max(axis=1) <= 1))
        if valid.any():
            xy = p[valid, :2] * im.size
            cx, cy = xy.mean(axis=0)
            # Cropping is a viewing aid, never a shoe outline or contact classifier.
            crops[index] = im.crop((max(0, cx - 110), max(0, cy - 85), min(im.width, cx + 110), min(im.height, cy + 85)))
        else:
            crops[index] = im
    return frames, crops


def mark_contact(directory, summary, review, suffix):
    frames = summary["frames"]
    td_key, off_key = f"proposed-td-{suffix}", f"proposed-off-{suffix}"

    def set_boundary(kind, frame):
        if kind == "touchdown":
            st.session_state[td_key] = frame
            if st.session_state.get(off_key) is not None and st.session_state[off_key] <= frame:
                st.session_state[off_key] = None
        else:
            st.session_state[off_key] = frame

    st.markdown("**Find and mark a contact**")
    st.caption("Scrub the original footage. Set touchdown at the first visibly grounded frame and toe-off at the first visibly airborne frame afterward. These are your selections; the app has not detected the events.")
    show_frame_viewer(directory, summary, namespace="contacts", view="original", on_boundary=set_boundary)
    cols = st.columns(3)
    side = cols[0].selectbox("Contact side", ["left", "right"], index=None,
                             placeholder="Choose the foot you followed", key=f"proposed-side-{suffix}")
    td = cols[1].selectbox("Proposed touchdown frame", frames[1:-1], index=None,
                           placeholder="Mark a frame above", key=td_key)
    off = cols[2].selectbox("Proposed toe-off frame", frames[1:], index=None,
                            placeholder="Mark a frame above", key=off_key)
    if side is None or td is None or off is None:
        st.caption("Choose the side and both boundaries to inspect the transition pairs. No contact is saved yet.")
        return
    if off <= td:
        st.info("Choose a toe-off frame after the touchdown frame.")
        return
    td_index, off_index = frames.index(td), frames.index(off)
    indices = [td_index - 1, td_index, off_index - 1, off_index]
    images, crops = boundary_images(directory, indices, side)
    st.caption("Review your proposed boundaries. The expected transition is airborne → grounded on the left pair, then grounded → airborne on the right pair. If all four show ground contact, adjust your selections.")
    for col, index, label in zip(st.columns(4), indices,
            ["Frame before your touchdown", "Your touchdown selection", "Frame before your toe-off", "Your toe-off selection"]):
        col.image(crops[index], caption=f"{label} · {frames[index]}", width="stretch")
    with st.expander("Check the uncropped boundary frames"):
        st.caption("Crops follow model-side landmarks. Use these full frames if the crop follows the wrong foot.")
        for col, index in zip(st.columns(2), [td_index, off_index]):
            col.image(images[index], caption=f"Source frame {frames[index]}", width="stretch")
    visible = st.checkbox("I checked both transitions: the selected foot is visible and these boundaries are correct",
                          key=f"contact-visible-{suffix}-{side}-{td}-{off}")
    if st.button("Add reviewed contact", disabled=not visible, key=f"add-contact-{suffix}"):
        try:
            updated = review.model_copy(update={"marks": review.marks + [ContactMark(side=side, touchdown_frame=td,
                toeoff_frame=off, visibility_confirmed=visible)]})
            updated = type(review).model_validate(updated.model_dump())
            save_contact_review(directory, summary, updated)
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def show_contacts(directory, summary):
    st.subheader("Contact time & side differences")
    posture = show_landing_posture(directory, summary)
    st.write("Use the shoes to review touchdown and toe-off for each side. Foot landmarks help locate the view; they do not detect individual spikes or prove ground contact.")
    review = load_contact_review(directory, summary)
    frames = summary["frames"]
    suffix = summary["analysis_id"][:16]
    with st.expander("Timing and side identification", expanded=not review.timing_confirmed):
        bases = ["Unverified", "Decoded timestamps are real time", "Known constant slow-motion factor"]
        timing = st.selectbox("How does this file's timeline relate to real time?", bases,
                              index=bases.index(review.timing_basis), key=f"contact-timing-{suffix}")
        factor = st.number_input("Constant slow-motion factor", min_value=1., max_value=32., value=review.slow_motion_factor,
            step=.5, disabled=timing != bases[2], key=f"contact-factor-{suffix}",
            help="Only use this for a verified constant slowdown in the uploaded file. Four means four media seconds represent one real second. Do not use the app's display slowdown.")
        verified = st.checkbox("I verified that timing mapping from the recording/export settings", value=review.timing_confirmed,
                               key=f"contact-verified-{suffix}")
        sides = st.checkbox("I can identify the athlete's anatomical left and right feet", value=review.side_labels_confirmed,
                            key=f"contact-sides-{suffix}")
        st.caption("The app's 4× playback is unrelated to this setting. A file with changing slow-motion speed has no single valid factor. Capture FPS alone does not prove the export's timing. Leave Unverified if unsure.")
        if st.button("Save timing settings", key=f"save-timing-{suffix}"):
            updated = review.model_copy(update={"timing_basis": timing, "slow_motion_factor": factor,
                "timing_confirmed": verified and timing != bases[0], "side_labels_confirmed": sides})
            save_contact_review(directory, summary, updated)
            st.rerun()
    mark_contact(directory, summary, review, suffix)
    result = contact_results(summary, review)
    if result["overlapping_sides"]:
        st.warning("Some left and right contacts overlap. Recheck the side labels, transition frames and sprint phase; those contacts are excluded from bilateral comparisons.")
    if not result["timing_verified_by_user"]:
        st.info("Time in milliseconds is withheld until timing is verified. You can still save frame annotations.")
    if result["contacts"]:
        st.dataframe([{"Side": c["side"], "Touchdown frame": c["touchdown_frame"], "Toe-off frame": c["toeoff_frame"],
            "Estimate (ms)": c["estimate_ms"], "Frame-bound lower (ms)": c["lower_ms"], "Frame-bound upper (ms)": c["upper_ms"],
            "Boundary gap (ms)": c["boundary_gap_ms"], "Eligible for comparison": c["comparison_eligible"]} for c in result["contacts"]], hide_index=True, width="stretch")
        remove = st.selectbox("Contact to remove if mis-marked", range(len(review.marks)),
            format_func=lambda i: f"{review.marks[i].side}: {review.marks[i].touchdown_frame} → {review.marks[i].toeoff_frame}", key=f"remove-mark-{suffix}")
        if st.button("Remove this annotation", key=f"remove-contact-{suffix}"):
            save_contact_review(directory, summary, review.model_copy(update={"marks": [m for i, m in enumerate(review.marks) if i != remove]}))
            st.rerun()
    if comparison := result["comparison"]:
        a, b, c = st.columns(3)
        a.metric("Left mean contact", f"{result['sides']['left']['mean_ms']:.1f} ms")
        b.metric("Right mean contact", f"{result['sides']['right']['mean_ms']:.1f} ms")
        c.metric("Absolute side difference", f"{comparison['absolute_difference_percent']:.1f}%")
        st.caption(f"Left minus right: {comparison['left_minus_right_ms']:.1f} ms; frame-bound interval {comparison['difference_lower_ms']:.1f} to {comparison['difference_upper_ms']:.1f} ms. This interval omits other error sources.")
    else:
        st.caption("To compare sides, mark at least two clear contacts per foot and confirm the side labels. Each transition needs frames no more than 1/120 real second apart.")
    st.markdown("**Observed angle-range differences**")
    st.dataframe(sampled_side_differences(summary), hide_index=True, width="stretch")
    st.caption("These ranges may cover different stride phases on each side. They are not a phase-matched anatomical asymmetry score, and a partial stride or hidden far-side limb can dominate the difference.")
    with st.expander("Possible contributors to investigate"):
        st.write("If a difference repeats across clear recordings at a similar sprint phase and speed, discuss these possibilities with your coach or clinician. No cause is identified by this video.")
        st.markdown("- **Measurement and recording:** viewpoint, hidden shoe contact, side-label errors, selected stride phase or export timing.\n- **Coordination or fatigue:** repeat the recording in comparable conditions before attributing a change to capacity.\n- **Pain or prior injury:** movement may be modified; a reported history is context, not proof of a cause.\n- **Strength capacity:** a professional could independently assess calf/ankle plantarflexors, knee flexors/hamstrings, and hip musculature where appropriate. A contact-time difference cannot tell which group is weak or which side needs strengthening.")
        st.markdown("[Research on task-specific strength and sprint asymmetry](https://pubmed.ncbi.nlm.nih.gov/27671707/)")
    st.caption("Compare repeated contacts at a similar sprint phase and speed. Shorter contact alone does not establish improvement.")
    return {**result, "posture": posture}

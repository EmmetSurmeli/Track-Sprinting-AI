"""Traceable bilateral movement review inside the motion tab."""
import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .artifacts import write_json
from .movement import movement_data, movement_evidence, load_review, LABELS


def show_movement(directory, summary, jump_to):
    data = movement_data(directory, summary)
    st.subheader("Legs & arms · movement evidence")
    if not data:
        st.info("Reanalyze this passage to create movement trajectories.")
        return None
    st.write("Compare the motion through complete cycles, then review the evidence before drawing a side-to-side conclusion.")
    rows = []
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=list(LABELS.values()))
    for side, color in (("left", "#2fcce5"), ("right", "#ff9e5b")):
        part = data["sides"][side]
        for n, (name, m) in enumerate(part["metrics"].items(), 1):
            fig.add_trace(go.Scatter(x=data["frames"], y=m["values"], name=f"Model {side}",
                legendgroup=side, showlegend=n == 1, line={"color": color}, connectgaps=False), row=n, col=1)
            rows.append({"Side": side.title(), "Measure": m["label"], "Min (°)": m.get("min"),
                         "Max (°)": m.get("max"), "Coverage": f"{m['coverage']:.0%}"})
        for cycle in part["cycles"]:
            fig.add_trace(go.Scatter(x=[cycle["start_frame"], cycle["rear_frame"], cycle["end_frame"]],
                y=[cycle["front_deg"], -cycle["rear_deg"], part["metrics"]["hip"]["values"][cycle["end_index"]]],
                mode="markers", marker={"color": color, "size": 9, "symbol": "diamond"}, showlegend=False), row=1, col=1)
    fig.update_layout(template="plotly_dark", height=720, margin={"l": 20, "r": 20, "t": 40, "b": 20},
                      paper_bgcolor="#0E151B", plot_bgcolor="#0E151B", legend={"orientation": "h"})
    fig.update_xaxes(title_text="Source frame", row=4, col=1)
    fig.update_yaxes(title_text="Degrees")
    st.plotly_chart(fig, width="stretch", key="movement-curves")
    st.caption("Model-side labels; projected angles. Diamonds mark candidate front / rear / front thigh positions, not shoe contact. Arm angles are relative to the trunk; elbow flexion is bending from straight. Missing points remain gaps.")
    st.dataframe(rows, hide_index=True, width="stretch")
    for col, side in zip(st.columns(2), ("left", "right")):
        part = data["sides"][side]
        col.markdown(f"**Model {side} · {len(part['cycles'])} complete candidate cycles**")
        if not part["cycles"]:
            col.caption("A continuous front / rear / front sequence was not found. Extrema alone cannot establish a cycle.")
        for i, cycle in enumerate(part["cycles"]):
            col.caption(f"Cycle {i+1}: {cycle['start_frame']} → {cycle['rear_frame']} → {cycle['end_frame']}")
            for phase in ("start", "rear", "end"):
                fid = cycle[phase + "_frame"]
                col.button(f"Inspect {phase} · {fid}", key=f"movement-{side}-{i}-{phase}",
                           on_click=jump_to, args=(summary["frames"].index(fid),))
    review = load_review(directory, summary["analysis_id"])
    with st.expander("Review the comparison conditions"):
        st.caption("Use the original footage and source-frame buttons to verify these. Leave a condition unchecked when uncertain.")
        with st.form("movement-review-" + summary["analysis_id"]):
            updated = {
                "stable_side_view": st.checkbox("The athlete stays approximately side-on through the compared cycles", value=review["stable_side_view"]),
                "labels_checked": st.checkbox("I checked both anatomical side labels and tracking through occlusions", value=review["labels_checked"]),
                "cycles_checked": st.checkbox("I checked every candidate cycle boundary against the original footage", value=review["cycles_checked"])}
            if st.form_submit_button("Save movement review"):
                write_json(directory / "movement_review.json", {"analysis_id": summary["analysis_id"], **updated})
                review = updated
                st.success("Movement review saved.")
    # Timing details are loaded in the backend when the report is generated.
    from .contacts import contact_results, load_contact_review
    contacts = contact_results(summary, load_contact_review(directory, summary))
    evidence = movement_evidence(data, summary, review, contacts)
    if evidence["blockers"]:
        st.markdown("**Side-to-side coaching is not ready for this passage**")
        for reason in evidence["blockers"]:
            st.caption("• " + reason)
    else:
        st.markdown("**Reviewed comparisons sent to the AI**")
        st.dataframe([{ "Measure": c["label"], "Left mean": c["left_mean"], "Right mean": c["right_mean"],
                       "Left − right": c["left_minus_right"], "Unit": c["units"],
                       "Exceeds observed cycle spread": c["exceeds_observed_cycle_spread"]} for c in evidence["comparisons"]], hide_index=True, width="stretch")
        st.caption("Differences are descriptive, not a better/worse score. Cycle spread does not measure pose error. Two cycles per side is a review gate, not proof of a stable athlete trait.")
    if not evidence["timing_verified"]:
        st.caption("Rear-to-front duration stays unavailable until the real-time mapping is verified in Contacts & sides.")
    st.download_button("Download movement evidence", json.dumps(evidence, indent=2),
                       file_name="movement_evidence.json", mime="application/json")
    return evidence

"""Calendar navigation and evidence-aware comparisons for saved local sessions."""
import calendar
from collections import Counter
from datetime import date
import json

import plotly.graph_objects as go
import streamlit as st

from .history import compare_sessions, compare_contact_sessions


def shift_month(offset):
    absolute = st.session_state.log_year * 12 + st.session_state.log_month - 1 + offset
    year, month = divmod(absolute, 12)
    st.session_state.log_year = min(2100, max(1900, year))
    st.session_state.log_month = month + 1


def show_calendar(store, open_analysis):
    entries = store.list()
    today = date.today()
    st.subheader("Your training calendar")
    st.caption("Completed analyses are logged automatically. Choose the recording date before analyzing, or edit it here later. Multiple clips can share a day.")
    st.session_state.setdefault("log_month", today.month)
    st.session_state.setdefault("log_year", today.year)
    if jump := st.session_state.pop("calendar_jump", None):
        st.session_state.log_month, st.session_state.log_year = jump.month, jump.year
    controls = st.columns([1, 3, 2, 1])
    controls[0].button("←", on_click=shift_month, args=(-1,), help="Previous month", width="stretch")
    month = controls[1].selectbox("Month", range(1, 13), format_func=lambda m: calendar.month_name[m], key="log_month")
    year = int(controls[2].number_input("Year", min_value=1900, max_value=2100, step=1, key="log_year"))
    controls[3].button("→", on_click=shift_month, args=(1,), help="Next month", width="stretch")
    month_entries = [e for e in entries if e["session_date"].startswith(f"{year:04d}-{month:02d}-")]
    counts = Counter(e["session_date"] for e in month_entries)
    selected = st.session_state.get("log_day", today.isoformat())
    if not selected.startswith(f"{year:04d}-{month:02d}-"):
        selected = next(iter(counts), date(year, month, 1).isoformat())
    for col, day in zip(st.columns(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        col.caption(day)
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        for col, day in zip(st.columns(7), week):
            if not day:
                col.write("")
                continue
            iso = date(year, month, day).isoformat()
            count = counts[iso]
            label = f"{day}" + (f" · {count}" if count else "")
            if col.button(label, key=f"day-{iso}", type="primary" if selected == iso else "secondary", width="stretch",
                          help=f"{date.fromisoformat(iso).strftime('%B %d')} · {count} saved analyses"):
                st.session_state.log_day = iso
                st.rerun()
    st.caption(f"{len(month_entries)} analyses this month · {len(entries)} total · numbers after the dot count clips")
    if not entries:
        st.info("Your calendar is empty. Analyze a video in Sprint review to save your first result, or save an already-open result using Save to calendar.")
        return
    day_entries = [e for e in entries if e["session_date"] == selected]
    st.markdown(f"### {date.fromisoformat(selected).strftime('%B %d, %Y')}")
    if not day_entries:
        st.info("No analyses on this day. Select a day with a clip count or browse all saved sessions below.")
    choices = day_entries or list(reversed(entries))
    ids = [e["id"] for e in choices]
    lookup = {e["id"]: e for e in entries}
    selected_id = st.selectbox("Saved session" if day_entries else "Browse saved sessions", ids,
        format_func=lambda i: f"{lookup[i]['session_date']} · {lookup[i]['label']} · {lookup[i]['event']}",
        key=f"entry-{selected}")
    current = lookup[selected_id]
    summary = current["summary"]
    stats = st.columns(3)
    stats[0].metric("Frames", summary["frame_count"])
    stats[1].metric("Core coverage", f"{summary['core_coverage']:.0%}")
    stats[2].metric("Review side", summary["review_side"].title())
    if contacts := current.get("contact_results"):
        st.caption(f"{len(contacts['contacts'])} reviewed shoe contacts saved with this analysis.")
    if current["notes"]:
        st.write(current["notes"])
    if st.button("Open this analysis", type="primary"):
        open_analysis(store.directory(selected_id))
        st.session_state.pending_workspace = "Sprint review"
        st.rerun()
    with st.expander("Edit date, title and notes"):
        with st.form(f"edit-{selected_id}"):
            updated_date = st.date_input("Recording date", date.fromisoformat(current["session_date"]), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
            label = st.text_input("Session title", current["label"], max_chars=120)
            event = st.text_input("Session event", current["event"], max_chars=40)
            notes = st.text_area("Session notes / coach feedback", current["notes"], max_chars=1000)
            if st.form_submit_button("Save log changes"):
                store.update(selected_id, updated_date, label or "Sprint session", event, notes)
                st.session_state.log_day = updated_date.isoformat()
                st.session_state.calendar_jump = updated_date
                st.rerun()
    st.subheader("Change since last time")
    prior = [e for e in entries if e["session_date"] < current["session_date"] or
             (e["session_date"] == current["session_date"] and e["created_at"] < current["created_at"])]
    if not prior:
        st.info("Save another session on a later date to compare it with this baseline.")
    else:
        previous_id = st.selectbox("Compare with", [e["id"] for e in reversed(prior)],
            format_func=lambda i: f"{lookup[i]['session_date']} · {lookup[i]['label']}", key=f"baseline-{selected_id}")
        rows, warnings = compare_sessions(current, lookup[previous_id])
        for warning in warnings:
            st.warning(warning)
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            st.info("No matching measurements meet the comparison checks. Use the same event, review side and processing settings, with clear joint visibility.")
        if contact_rows := compare_contact_sessions(current, lookup[previous_id]):
            st.markdown("**Reviewed contact-time changes**")
            st.dataframe(contact_rows, hide_index=True, width="stretch")
            st.caption("Frame bounds omit marking error and other measurement error. Compare similar sprint phases and recording conditions; shorter contact alone does not establish improvement.")
    st.caption("Changes are observed angle differences, not an improvement score. Different views, sprint phases or selected stride positions can change the result. Use consistent filming and your coach's feedback to judge progress.")
    st.subheader("Measurements over time")
    metric_name = st.selectbox("Trend measurement", ["knee", "hip"], format_func=lambda x: "Knee flexion" if x == "knee" else "Trunk–thigh flexion")
    trend = [e for e in entries if e["event"] == current["event"] and e["summary"]["review_side"] == summary["review_side"]]
    ref = f"{summary['review_side']}.{metric_name}"
    eligible = []
    for e in trend:
        m = e["summary"]["metrics"].get(ref)
        same_method = all(e["manifest"].get(k) == current["manifest"].get(k) for k in ("pipeline_version", "model_sha256", "dependencies"))
        same_threshold = e["summary"]["config"].get("score_threshold") == summary["config"].get("score_threshold")
        eligible.append(m if m and m["coverage"] >= .85 and same_method and same_threshold else None)
    fig = go.Figure()
    for stat, label, color in [("min", "Observed minimum", "#2FCCE5"), ("max", "Observed maximum", "#B8F35A")]:
        fig.add_trace(go.Scatter(x=[e["session_date"] for e in trend], y=[m[stat] if m else None for m in eligible],
            mode="lines+markers", connectgaps=False, name=label, line={"color": color},
            hovertemplate="%{x}<br>%{y:.1f}°<extra>" + label + "</extra>"))
    fig.update_layout(height=330, xaxis_title="Recording date", yaxis_title="Projected angle (°)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend={"orientation": "h"},
        margin={"t": 25, "b": 35, "l": 20, "r": 20})
    st.plotly_chart(fig, width="stretch")
    st.caption("Same event, model review side and processing method only. Low-coverage results are gaps. Camera geometry is not calibrated across sessions.")
    contact_entries = [e for e in entries if e["event"] == current["event"]]
    if any((e.get("contact_results") or {}).get("comparison") for e in contact_entries):
        st.markdown("**Reviewed contact time over time**")
        contacts_plot = go.Figure()
        for side, color in [("left", "#2FCCE5"), ("right", "#FF9E5B")]:
            values = []
            errors = []
            for e in contact_entries:
                c = e.get("contact_results") or {}
                m = c.get("sides", {}).get(side) if c.get("comparison") else None
                values.append(m["mean_ms"] if m else None)
                errors.append(max(m["mean_ms"] - m["lower_ms"], m["upper_ms"] - m["mean_ms"]) if m else 0)
            contacts_plot.add_trace(go.Scatter(x=[e["session_date"] for e in contact_entries], y=values,
                mode="lines+markers", connectgaps=False, name=side.title(), line={"color": color},
                error_y={"type": "data", "array": errors, "visible": True}))
        contacts_plot.update_layout(height=300, xaxis_title="Recording date", yaxis_title="Reviewed shoe contact (ms)")
        st.plotly_chart(contacts_plot, width="stretch")
        st.caption("Bars show conservative frame-bound ranges, not statistical confidence intervals. Unverified or incomplete bilateral reviews remain gaps.")
    export = [{k: v for k, v in e.items() if k != "manifest"} for e in entries]
    st.download_button("Download training log", json.dumps(export, indent=2), "training-log.json", "application/json")
    st.caption("History is saved on this computer and survives browser restarts and Clear this session. It is excluded from GitHub.")

"""Explain personalization and the limits of group-level sprint research."""
import streamlit as st

from .personalization import profile_guidance


def show_profile_context(profile, evidence):
    guidance = profile_guidance(profile)
    sources = {s["id"]: s for s in evidence["sources"]}
    st.subheader("How your details change the review")
    st.caption("Your details help focus the coaching review on your goals, training background and recovery context.")
    descriptions = {
        "experience": ("Your experience", "Explanations match your training experience, with terminology explained where helpful."),
        "goal": ("Your goals", "Your event and goals guide which observations get priority."),
        "youth": ("Your stage of development", "The review uses youth research and focuses on observations to discuss with your coach."),
        "sex_context": ("Research that applies to you", "The review considers who each study included and how relevant its findings are to you."),
        "body_size": ("Your build", "Height and weight provide context when interpreting research alongside your recorded movement."),
        "injury_context": ("Your injury history", "Your history helps focus attention on movement patterns and questions worth following up with your coach or clinician."),
        "active_symptoms": ("Your recovery", "Feedback focuses on the recorded movement and questions for the professional guiding your recovery."),
    }
    for rule in guidance["rules"]:
        title, description = descriptions[rule["id"]]
        st.markdown(f"**{title}**")
        st.write(description)
    with st.expander("Research behind your review"):
        refs = dict.fromkeys(ref for rule in guidance["rules"] for ref in rule["evidence_refs"])
        if not refs:
            st.caption("Add optional profile details to see related research. Movement research is available in Method & evidence.")
        for ref in refs:
            s = sources[ref]
            st.markdown(f"[{s['authors']} · {s['year']}]({s['url']})")
            st.caption(s["limitations"])
    st.subheader("Research check: girls and frontside mechanics")
    st.info("Not established for most high-school girls. A modest adult group-average difference is not evidence of a universal sex-specific technique or an individual deficit.")
    st.caption("The relevant adult study did not sample high-school athletes. The youth study reviewed here sampled girls only and did not test this sex comparison. Your measured motion and comparable recordings take priority over a demographic assumption.")
    st.markdown("[Adult sprint study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8580521/) · [Youth female development study](https://doi.org/10.47206/ijsc.v1i1.65)")
    st.subheader("Training & recovery")
    if guidance["active_symptoms"]:
        st.warning("Current symptoms or a supervised return-to-sport context: this review stays observational. Discuss running and progression decisions with your treating professional.")
    elif guidance["injury_reported"]:
        st.write("The AI considers your prior injury when choosing movement patterns to discuss and questions to follow up on. Your review focuses on observations you can bring to your coach or clinician.")
    else:
        st.write("Add any previous injuries, current discomfort or return-to-training context in your profile to help focus the review.")

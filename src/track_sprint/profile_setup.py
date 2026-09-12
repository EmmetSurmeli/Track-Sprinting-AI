"""One-time local profile setup. Private profile data never enters the repository."""
import os
from pathlib import Path

import streamlit as st

from .artifacts import read_json, write_json
from .schemas import AthleteProfile


def load_profile(path: Path):
    if not path.exists():
        return None
    try:
        return AthleteProfile.model_validate(read_json(path))
    except (ValueError, OSError):
        return None


def show_profile_setup(path: Path, current=None):
    p = current or AthleteProfile()
    st.title('Your sprint profile')
    st.caption('Set this up once. You can edit it anytime.')
    with st.form('athlete-setup'):
        a, b = st.columns(2)
        events = ['100 m', '200 m', '400 m', 'Other sprint']
        levels = ['Beginner', 'Intermediate', 'Experienced']
        event = a.selectbox('Event', events, index=events.index(p.event) if p.event in events else 0)
        experience = b.selectbox('Experience', levels, index=levels.index(p.experience) if p.experience in levels else 1)
        goal = st.text_input('What would you like to improve?', p.goal, max_chars=500)
        a, b, c = st.columns(3)
        age = a.number_input('Age (optional)', min_value=10, max_value=100, value=p.age_years)
        height = b.number_input('Height (cm)', min_value=80., max_value=250., value=p.height_cm)
        weight = c.number_input('Weight (kg)', min_value=20., max_value=250., value=p.weight_kg)
        sexes = ['Prefer not to say', 'Female', 'Male', 'Another / not represented']
        sex = st.selectbox('Sex for research context (optional)', sexes, index=sexes.index(p.sex_for_research))
        with st.expander('Injuries or anything affecting training'):
            statuses = ['None reported', 'Past injury, no current symptoms', 'Current symptoms', 'Returning with professional guidance']
            status = st.selectbox('Injury context', statuses, index=statuses.index(p.injury_status))
            injury = st.text_area('Anything your coach should know?', p.injury_context, max_chars=500)
            pain = st.checkbox('I have pain during running', p.current_pain)
        st.caption('Saved privately on this computer. Your profile and measurements are sent to OpenAI when you request coaching; your video stays local.')
        if st.form_submit_button('Save profile & continue', type='primary', width='stretch'):
            profile = p.model_copy(update=dict(event=event, experience=experience, goal=goal,
                age_years=age, height_cm=height, weight_kg=weight, sex_for_research=sex,
                injury_status=status, injury_context=injury, current_pain=pain))
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, profile.model_dump())
            os.chmod(path, 0o600)
            st.session_state.pop('edit_profile', None)
            st.rerun()

import streamlit as st
from utils.ui_components import displayAttendance,selectFiles,sidebar

st.set_page_config(layout="wide",page_icon="LMS",initial_sidebar_state="expanded")

sidebar()

if not st.session_state.ingesting_data and "subjects" in st.session_state:
    if "subjects" in st.session_state:
        col_left,gap,col_right=st.columns([0.6,0.05,0.35])
        with col_right:
            displayAttendance()
        with col_left:
            selectFiles()
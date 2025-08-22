import streamlit as st
import pandas as pd
import plotly.express as px
import math
from utils.backend_calls import ingestFiles
from utils.lms_handling import loginToLms,logoutOfLms,fetchFiles

def sidebar():
    with st.sidebar.form("login_form",border=False,clear_on_submit=True,enter_to_submit=False):
        st.write(st.session_state.ack)
        st.text_input("Username",key="uname",disabled=st.session_state.toggle)
        st.text_input("Password",key="pswd",disabled=st.session_state.toggle, type="password")
        login, logout = st.columns(2)
        login.form_submit_button(
            "Log In",
            type="primary",
            disabled=st.session_state.toggle,
            on_click=loginToLms)
        logout.form_submit_button(
            "Log Out",
            type="primary",
            disabled=not st.session_state.toggle,
            on_click=logoutOfLms)

def displayAttendance():
    with st.container(border=True,width=420,horizontal_alignment="right"):
        data = st.session_state.subjects
        processed_data = []
        subject_acronyms = {
            "Usability Design of Software Applications":"UDSA",
            "Advanced Social,Text and Media Analytics- Elective II":"ASTMA",
            "Cognitive Science & Analytics- Elective I":"CSA",
            "Human Resource Management":"HRM",
            "Financial Management":"FM",
            "IT Project Management":"ITPM",
            "Services Science & Service Operational Management":"SSOM",
            "IT Workshop Skylab/Matlab":"ITWSM"
            }
        for entry in data:
            if entry["attendance"] != "---":
                attendance_value = float(entry["attendance"].replace('%', ''))
                processed_data.append({
                        "subject_name": subject_acronyms.get(entry["subject_name"]),
                        "attendance": attendance_value
                    })
            else:
                processed_data.append({
                    "subject_name": subject_acronyms.get(entry["subject_name"]),
                    "attendance": 0
                    })
                
        df = pd.DataFrame(processed_data)
        fig = px.bar(
            df,
            x='subject_name',
            y='attendance',
            range_y=[0,100],
            labels={'subject_name': 'Subject Name', 'attendance': 'Attendance (%)'},
            color='attendance',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig.update_layout(
            xaxis_title_text='Subject',
            yaxis_title_text='Attendance (%)',
            coloraxis_showscale=False,
            width=400,
            hovermode=False,
            yaxis_side="right"
        )
        st.plotly_chart(fig, config={'displayModeBar': False, 'staticPlot': True},use_container_width=False)
            
def selectFiles():
    with st.container(horizontal_alignment="right"):
        st.markdown(
            '<h2 style="text-align: right;">Ingest Data</h2>',
            unsafe_allow_html=True
        )
        st.write("\n")
        st.write("\n")
        
        selected_subject = st.selectbox(
        "Select a Subject",
            options=([d.get("subject_name") for d in st.session_state.subjects]),
           placeholder="Select a Subject",
            index=None,
            width=450,
            label_visibility="collapsed",
            accept_new_options=False,
            disabled=st.session_state.ingesting_data
        )        
        selected_files=[]
        with st.container(horizontal_alignment="right"):
            for subject in st.session_state.subjects:
                if subject["subject_name"] == selected_subject:
                    st.markdown(
                        '<h4 style="text-align: right;">Select files to ingest</h4>',
                        unsafe_allow_html=True
                    )
                    st.write("\n")
                    st.write("\n")
                    gap,left,right = st.columns([0.4,0.3,0.3])
                    files = fetchFiles(subject["url"],selected_subject)
                    for i,f in enumerate(files):
                        lenght_of_column = math.ceil(len(files)/2)
                        file_name=f["file_name"]
                        file_link=f["file_link"]
                        col = left if i < lenght_of_column else right
                        with col:
                            if st.checkbox(file_name,key=file_link,disabled=st.session_state.ingesting_data):
                                selected_files.append(f)
                    st.write("\n")
                    st.write("\n")
                    if st.button("Ingest",disabled=st.session_state.ingesting_data):
                        st.session_state.ingesting_data=True
                        ingestFiles(selected_files)

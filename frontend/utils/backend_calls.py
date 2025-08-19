import streamlit as st
import logging, math


@st.dialog("Ingesting Data",dismissible=False,width="large")
def ingestFiles(selected_files):
    if st.session_state.ingesting_data==True:
        s=st.session_state.s
        progress_text = "Data ingestion in progress. Please wait."
        my_bar = st.progress(0, text=progress_text)

        for i,f in enumerate(selected_files):
            logging.info(f"Getting {f["file_name"]} from {f["file_link"]}")
            try:
                file_response=s.get(f["file_link"])
            except:
                logging.error(f"An error occured while fetching file: {f["file_name]"]} from {f["file_link"]}")
                
            if file_response.status_code == 200:
                st.markdown(f":green-badge[:material/check: Success] {f["file_name"]}")
            else:
                st.markdown(f":red-badge[:material/cross: Failed] {f["file_name"]}")
            my_bar.progress(math.floor((i+1)/len(selected_files)*100),text=progress_text)

        st.session_state.ingesting_data=False
        if st.button("Continue",disabled=st.session_state.ingesting_data):
            st.rerun(scope="app")
    else:
        st.rerun()

def reqQuery(prompt):
    pass
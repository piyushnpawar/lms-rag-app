import streamlit as st
import logging, requests,time


@st.dialog("Ingesting Data",dismissible=False,width="large")
def ingestFiles(selected_files):
    if st.session_state.ingesting_data==True:
        for f in selected_files:
            upload_file(f)
        st.session_state.ingesting_data=False
        if st.button("Continue",disabled=st.session_state.ingesting_data):
            st.rerun(scope="app")
    else:
        st.rerun()

def upload_file(file):
    s=st.session_state.s
    upload_endpoint="http://localhost:8000/upload"
    form_data = {
        "subject": file["subject"],
        "file_name": file["file_name"],
        "file_link": file["file_link"],
        "session_cookies": s.cookies.get_dict()
     }
    with st.status(f"Uploading {file["file_name"]}") as status:
        logging.info(f"Uploading {file["file_name"]}, {file["file_link"]}")
        response = s.post(upload_endpoint,json=form_data)
        try:
            data = response.json()
            status.update(
                label=f"{file["file_name"]} : {data.get("status","An error occured")}"
            )
        except:
            status.update(label="An error occured on the backend")
    
def reqQuery(prompt):
    s=requests.Session()
    query_endpoint="http://localhost:8000/query"
    questions = prompt.split("\n\n")
    form_data = {
        "questions": questions
    }
    logging.info(f"Querying the backend for questions: {questions}")
    response = s.post(query_endpoint,json=form_data)
    try:
        data = response.json()
        answers = data.get("answers")
        for answer in answers:
            for word in answer.split():
                yield word + " "
                time.sleep(0.07)
    except:
        logging.error("Querying failed")
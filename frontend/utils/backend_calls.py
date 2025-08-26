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
    s = requests.Session()
    upload_endpoint="http://localhost:8000/upload"
    form_data = {
        "subject": file["subject"],
        "file_name": file["file_name"],
        "file_link": file["file_link"],
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
        
def loginToLms():
    uname = st.session_state.uname
    pswd = st.session_state.pswd
    logging.info(f"Username: {uname}, Password: {pswd}")
    login_endpoint = "http://localhost:8000/login"
    s = requests.Session()
    form_data = {
        "username": uname,
        "password": pswd
    }
    try:
        logging.info(f"Attempting LMS login")
        response = s.post(login_endpoint,json=form_data)
        data = response.json()
        if response.status_code == 200:
            logging.info("Login Successful")
            st.session_state.toggle=True
            st.session_state.ack="🟢 Logged Into " + st.session_state.uname
            st.session_state.subjects = data.get("subjects")
        elif response.status_code == 401:
            st.sidebar.write("Login failed. Check your credentials.")
            logging.info("Login failed. Invalid credentials.")
        else:
            logging.info("Login request failed.")
            st.sidebar.write(response.status_code)
            st.sidebar.write("Login request failed.")
    except:
        logging.error("Login failed")
        
def logoutOfLms():
    s = requests.Session()
    logout_endpoint = "http://localhost:8000/logout"
    try:
        logging.info(f"Attempting LMS logout")
        logout_response = s.get(logout_endpoint)
        if logout_response.status_code == 200:
            logging.info("Successfully logged out!")
            st.session_state.toggle=False
            st.session_state.uname=""
            st.session_state.pswd=""
            del st.session_state["subjects"]
            st.cache_data.clear()
            st.session_state.ack="🔴 Logged Out"
        elif logout_response.status_code == 404:
            logging.error("Logout request sent, but the final URL was not the login page.")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while logging out: {e}")

@st.cache_data
def fetchFiles(subject:str,subject_url: str):
    s = requests.Session()
    fetch_endpoint = "http://localhost:8000/fetch"
    form_data = {
        "subject": subject,
        "url": subject_url
    }
    try:
        logging.info("Fetching files")
        response = s.post(fetch_endpoint,json=form_data)
        if response.status_code == 200:
            logging.info("Fetched files successfully")
            data = response.json()
            files =data.get("files")
            return files
    except:
        logging.error("Failed to fetch files")
        return None
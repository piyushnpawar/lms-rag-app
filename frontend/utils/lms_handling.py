import streamlit as st
import requests, re
from bs4 import BeautifulSoup
import logging

def loginToLms():
    uname = st.session_state.uname
    pswd = st.session_state.pswd
    logging.info(f"Username: {uname}, Password: {pswd}")
    login_url = "https://mydy.dypatil.edu/rait/login/index.php"
    form_data = {
        "uname_static": uname,
        "username":uname,
        "uname": uname,
        "password": pswd
    }
    with requests.Session() as s:
        logging.info(f"Getting Initial Cookie from {login_url}")
        get_response = s.get(login_url)
        logging.info(f"Request Status: {get_response.status_code}, Cookie received: {s.cookies.get_dict()}")
        logging.info(f"Sending login POST request to {login_url}")
        post_response = s.post(login_url, data=form_data)
        
        if post_response.status_code == 200:
            logging.info(f"Request Status: {post_response.status_code}")
            if "mydy.dypatil.edu/rait/my/" in post_response.url:
                logging.info("Login Successful")
                st.session_state.toggle=True
                st.session_state.ack="🟢 Logged Into " + st.session_state.uname
                st.session_state.s=s
                extractLinks()
            else:
                st.sidebar.write("Login failed. Check your credentials.")
                logging.info("Login failed. Invalid credentials.")
        else:
            logging.error(f"Login request failed with status code: {post_response.status_code}")
            logging.error("Response text:", post_response.text)
    
def logoutOfLms():
    s=st.session_state.s
    logout_url=st.session_state.logout_url
    try:
        logout_response = s.get(logout_url)
        logout_response.raise_for_status()
        if "mydy.dypatil.edu" in logout_response.url:
            logging.info("Successfully logged out!")
            st.session_state.toggle=False
            st.session_state.uname=""
            st.session_state.pswd=""
            del st.session_state["subjects"]
            del st.session_state["s"]
            st.cache_data.clear()
            st.session_state.ack="🔴 Logged Out"
        else:
            logging.error("Logout request sent, but the final URL was not the login page.")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while logging out: {e}")

def extractLinks():
    s=st.session_state.s
    dashboard_url="https://mydy.dypatil.edu/rait/my/"
    classes_url= "https://mydy.dypatil.edu/rait/blocks/academic_status/ajax.php?action=myclasses"
    try:
        logging.info(f"Getting Dashboard Html from {dashboard_url}")
        dashboard_response = s.get(dashboard_url)
        dashboard_response.raise_for_status()
        logging.info(f"Getting Classes Html from {classes_url}")
        classes_response = s.get(classes_url)
        classes_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occured while extracting links: {e}")

    subjects = getSubjects(classes_response.text)
    logout_url = getLogoutLink(dashboard_response.text)
    
    st.session_state.logout_url = logout_url
    st.session_state.subjects = subjects

@st.cache_data
def getSubjects(classes_html):
    soup = BeautifulSoup(classes_html, 'lxml')
    subjects = []
    subject_containers = soup.find_all('div', class_=lambda c: c and 'subjectcontainer' in [cls.strip(';') for cls in c.split()])
    if not subject_containers:
        logging.info("No subject containers found in the HTML.")
        st.write(classes_html)
        return []
    for container in subject_containers:
        subject_name_tag = container.find('h4', class_='cfullname')
        launch_link_tag = container.find('a', class_='launchbutton')
        
        sub_content = container.find('div', class_='subcontent-container')
        attendance_total = sub_content.find('span', class_='attendance-total')
        if attendance_total:
            attendance_info = attendance_total.text.strip()
        else:
            attendance_info= "---"

        if subject_name_tag and launch_link_tag:
            subject_name = subject_name_tag.text.strip()
            subject_url = launch_link_tag.get('href').strip()
            subject_data = {
                "subject_name": subject_name,
                "url": subject_url,
                "attendance": attendance_info
            }
            subjects.append(subject_data)
    return subjects

@st.cache_data
def getLogoutLink(dashboard_html):
    logout_soup = BeautifulSoup(dashboard_html, 'lxml')
    logout_link = logout_soup.find('a', href=lambda href: href and 'logout.php?sesskey=' in href)
    if not logout_link:
        logging.error("Could not find the logout link with a sesskey.")
        return ""
    logout_url = logout_link['href']        
    if not logout_url.startswith('http'):
        logout_url = f"https://mydy.dypatil.edu{logout_url}"
    logging.info(f"Found logout URL: {logout_url}")
    return logout_url

@st.cache_data
def fetchFiles(subject_url:str,subject: str):
    s=st.session_state.s
    files = []
    logging.info(f"Getting Subject html from {subject_url}")
    subject_response = s.get(subject_url)
    subject_html=subject_response.text
    subject_soup = BeautifulSoup(subject_html,"lxml")
    file_instances = subject_soup.find_all('div',class_="activityinstance")
    for f in file_instances:
        file_link = f.find("a")["href"]
        file_name = f.find("span",class_="instancename").contents[0]
        pdf_link, check = fetchPdfs(file_link)
        if check:
            file = {
                "file_name": file_name,
                "file_link": pdf_link,
                "subject": subject
            }
            files.append(file)
    return files

def fetchPdfs(file_link):
    s=st.session_state.s
    logging.info(f"Getting file from {file_link}")
    pdf_response = s.get(file_link)
    pdf_html = pdf_response.text
    pattern = r'["\'](https?://[^\s"]+\.(?:pdf|docx|pptx))'
    pdf_link = re.search(pattern, pdf_html)
    return (pdf_link.group(1),True) if pdf_link else ("", False)
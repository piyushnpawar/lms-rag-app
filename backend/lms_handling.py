import requests, re
from bs4 import BeautifulSoup
import logging
from fastapi import status
from uuid import uuid4

LMS_SESSIONS = {}


def get_session(session_id: str):
    if not session_id:
        return None
    return LMS_SESSIONS.get(session_id)


def get_session_cookies(session_id: str):
    session = get_session(session_id)
    if not session:
        return None
    return session["cookies"]


def build_session(cookies=None):
    session = requests.Session()
    if cookies:
        requests.utils.add_dict_to_cookiejar(session.cookies, cookies)
    return session

def logIn(username:str, password:str):
    login_url = "https://mydy.dypatil.edu/rait/login/index.php"
    form_data = {
        "uname_static": username,
        "username": username,
        "uname": username,
        "password": password
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
                subjects,logout_url = extractLinks(s)
                session_id = str(uuid4())
                LMS_SESSIONS[session_id] = {
                    "cookies": s.cookies.get_dict(),
                    "logout_url": logout_url
                }
                return status.HTTP_200_OK, subjects, logout_url, session_id
            else:
                logging.info("Login failed. Invalid credentials.")
                return status.HTTP_401_UNAUTHORIZED, None, None, None
        else:
            logging.error(f"Login request failed with status code: {post_response.status_code}")
            logging.error("Response text: %s", post_response.text)
            return status.HTTP_503_SERVICE_UNAVAILABLE, None, None, None
    
def extractLinks(s):
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
    
    return subjects,logout_url

def getSubjects(classes_html):
    soup = BeautifulSoup(classes_html, 'lxml')
    subjects = []
    subject_containers = soup.find_all('div', class_=lambda c: c and 'subjectcontainer' in [cls.strip(';') for cls in c.split()])
    if not subject_containers:
        logging.info("No subject containers found in the HTML.")
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

def logOut(session_id: str):
    session = get_session(session_id)
    if not session:
        return status.HTTP_401_UNAUTHORIZED

    s = build_session(session["cookies"])
    logout_url = session["logout_url"]
    try:
        logout_response = s.get(logout_url)
        logout_response.raise_for_status()
        if "mydy.dypatil.edu" in logout_response.url:
            del LMS_SESSIONS[session_id]
            return status.HTTP_200_OK
        else:
            logging.error("Logout request sent, but the final URL was not the login page.")
            return status.HTTP_404_NOT_FOUND
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while logging out: {e}")
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    
def fetchFiles(session_id: str, subject:str,subject_url: str):
    cookies = get_session_cookies(session_id)
    if not cookies:
        return status.HTTP_401_UNAUTHORIZED, None

    s = build_session(cookies)
    files = []
    try:
        logging.info(f"Getting {subject} html from {subject_url}")
        subject_response = s.get(subject_url)
        subject_html=subject_response.text
        subject_soup = BeautifulSoup(subject_html,"lxml")
        file_instances = subject_soup.find_all('div',class_="activityinstance")
        for f in file_instances:
            file_link = f.find("a")["href"]
            file_name = f.find("span",class_="instancename").contents[0]
            pdf_link, check = getFile(file_link, s)
            if check:
                file = {
                    "file_name": file_name,
                    "file_link": pdf_link,
                    "subject": subject
                }
                files.append(file)
        return status.HTTP_200_OK,files
    except:
        return status.HTTP_500_INTERNAL_SERVER_ERROR, None

def getFile(file_link, s):
    logging.info(f"Getting file from {file_link}")
    pdf_response = s.get(file_link)
    pdf_html = pdf_response.text
    pattern = r'["\'](https?://[^\s"]+\.(?:pdf|docx|pptx))'
    pdf_link = re.search(pattern, pdf_html)
    return (pdf_link.group(1),True) if pdf_link else ("", False)

import streamlit as st
import requests
from bs4 import BeautifulSoup
import logging

def loginToLms():
    uname = st.session_state.uname
    pswd = st.session_state.pswd
    logging.info(uname,pswd)
    login_url = "https://mydy.dypatil.edu/rait/login/index.php"
    form_data = {
        "uname_static": uname,
        "username":uname,
        "uname": uname,
        "password": pswd
    }
    with requests.Session() as s:
        logging.info("Getting Initial Cookie")
        get_response = s.get(login_url)
        logging.info(get_response, " Cookie received: ", s.cookies.get_dict())
        logging.info("Sending login POST request")
        post_response = s.post(login_url, data=form_data)
        
        if post_response.status_code == 200:
            if "mydy.dypatil.edu/rait/my/" in post_response.url:
                logging.info("Login Successful")
                st.session_state.toggle=True
                st.session_state.ack="🟢 Logged Into " + st.session_state.uname
                st.session_state.dashboard_url = "https://mydy.dypatil.edu/rait/my/"
                st.session_state.s=s
            else:
                st.write("Login failed. Check your credentials.")
                logging.info("Login failed. Invalid credentials.")
        else:
            logging.error(f"Login request failed with status code: {post_response.status_code}")
            logging.error("Response text:", post_response.text)
    
def logoutOfLms():
    extractLinks()
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
            st.session_state.ack="🔴 Logged Out"
        else:
            logging.error("Logout request sent, but the final URL was not the login page.")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while logging out: {e}")

    
def extractLinks():
    s=st.session_state.s
    dashboard_url=st.session_state.dashboard_url
    try:
        dashboard_response = s.get(dashboard_url)
        dashboard_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occured while extracting links: {e}")

    logout_soup = BeautifulSoup(dashboard_response.text, 'html.parser')
    logout_link = logout_soup.find('a', href=lambda href: href and 'logout.php?sesskey=' in href)
    if not logout_link:
        logging.error("Could not find the logout link with a sesskey.")
        return
    logout_url = logout_link['href']        
    if not logout_url.startswith('http'):
        logout_url = f"https://mydy.dypatil.edu{logout_url}"
    logging.info(f"Found logout URL: {logout_url}")
    st.session_state.logout_url = logout_url
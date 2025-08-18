import streamlit as st
from lms_handling import loginToLms,logoutOfLms

st.session_state.setdefault('toggle', False)
st.session_state.setdefault('ack', "🔴 Logged Out")
st.session_state.setdefault('uname', "")
st.session_state.setdefault('pswd', "")

with st.sidebar.form("login_form",border=False,clear_on_submit=True,enter_to_submit=False):
    st.write(st.session_state.ack)
    st.text_input("Username",key="uname",disabled=st.session_state.toggle)
    st.text_input("Password", key="pswd",disabled=st.session_state.toggle)
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
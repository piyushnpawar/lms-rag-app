import streamlit as st
from utils.backend_calls import reqQuery

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])
    
prompt = st.chat_input("Ask a question")
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.chat.append({"role":"human","content":prompt})
    
    with st.chat_message("ai"):
        response = st.write_stream(reqQuery(prompt))
    st.session_state.chat.append({"role":"ai","content":response })
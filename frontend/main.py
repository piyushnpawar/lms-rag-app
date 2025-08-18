import streamlit as st
import logging

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

data_ingestion_page = st.Page("data_ingestion_page.py", title="Ingest Data")
response_generation_page = st.Page("response_generation_page.py", title="Generate Response")

pg = st.navigation([data_ingestion_page,response_generation_page])
pg.run()
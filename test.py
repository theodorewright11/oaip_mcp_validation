from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit as st

print("🔍 Testing Google Sheets connection...")

# Initialize connection using the secrets.toml credentials
conn = st.connection("gsheets", type=GSheetsConnection)

# Try reading from the sheet
try:
    df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1FfvnrD2y8Cbdrwn5vai07F1HAsN9jvTXaFyLJ6Z20Ps/edit?usp=sharing", usecols=list(range(8)))
    st.success("✅ Successfully read Google Sheet!")
    st.dataframe(df)
except Exception as e:
    st.error(f"❌ Failed to read Google Sheet: {e}")

# import streamlit as st
# st.write(st.secrets)

# import streamlit as st
# from streamlit_gsheets import GSheetsConnection
# import traceback

# st.write("🔍 Testing Google Sheets connection...")

# try:
#     conn = st.connection("gsheets", type=GSheetsConnection)
#     df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1FfvnrD2y8Cbdrwn5vai07F1HAsN9jvTXaFyLJ6Z20Ps/edit?usp=sharing")
#     st.success("✅ Successfully read Google Sheet!")
#     st.dataframe(df)
# except Exception as e:
#     st.error("❌ Failed to read Google Sheet")
#     st.text(traceback.format_exc())

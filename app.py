import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- Basic password protection ---
st.sidebar.title("🔒 Access Control")
password = st.sidebar.text_input("Enter password", type="password")

if password != st.secrets.get("app_password"):
    st.warning("Enter the correct password to continue.")
    st.stop()

st.set_page_config(page_title="MCP Labeling Tool", layout="wide")

# --- Load static data ---
df = pd.read_csv("options.csv")            # GWA–IWA–DWA–Task hierarchy
examples = pd.read_csv("examples.csv")     # MCP examples (title, url, text_for_llm, bucket)

# --- Helper functions ---
def get_iwas(selected_gwas):
    return sorted(df[df["gwa_title"].isin(selected_gwas)]["iwa_title"].dropna().unique().tolist())

def get_dwas(selected_iwas):
    return sorted(df[df["iwa_title"].isin(selected_iwas)]["dwa_title"].dropna().unique().tolist())

def get_tasks(selected_dwas):
    return sorted(df[df["dwa_title"].isin(selected_dwas)]["task"].dropna().unique().tolist())

# --- Connect to Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Team member selection ---
st.sidebar.header("👥 Select Team Member")
user_choice = st.sidebar.selectbox("Who are you?", ["Teddy", "Alice", "Eric"])

sheet_urls = {
    "Teddy": "https://docs.google.com/spreadsheets/d/1FfvnrD2y8Cbdrwn5vai07F1HAsN9jvTXaFyLJ6Z20Ps/edit?usp=sharing",
    "Alice": "https://docs.google.com/spreadsheets/d/1ZKAty55cCkJvaW1RhqQa6uyZjS-YKc4fSwwCTfDeT-Y/edit?usp=sharing",
    "Eric": "https://docs.google.com/spreadsheets/d/1NIg1FOkVRIqxY5zDv4cXsiHYrxbDUQOiXdxPGOsU2L4/edit?usp=sharing"
}

current_sheet = sheet_urls[user_choice]

# --- Load that sheet ---
try:
    existing = conn.read(spreadsheet=current_sheet, usecols=list(range(8)))
except Exception as e:
    st.warning(f"Could not load sheet for {user_choice}: {e}")
    existing = pd.DataFrame()

expected_cols = ["timestamp","title","url","bucket","gwa","iwa","dwa","task"]
if existing is None or existing.empty or not set(expected_cols).issubset(existing.columns):
    existing = pd.DataFrame(columns=expected_cols)


# --- App UI ---
st.title("🧩 MCP Classification Tool")

titles = examples["title"].tolist()
selected_title = st.selectbox("Select an MCP Server Example:", [""] + titles)

if selected_title:
    row = examples[examples["title"] == selected_title].iloc[0]
    st.markdown(f"**URL:** [{row['url']}]({row['url']})")
    st.write(row["text_for_llm"])
    st.write(f"**Bucket:** {row['bucket']}")

# --- Load existing selection for this title ---
saved = {}
if selected_title and not existing.empty:
    match = existing[existing["title"] == selected_title]
    if not match.empty:
        saved = match.iloc[0].to_dict()

# --- Dropdowns with pre-selected values ---
gwas_options = sorted(df["gwa_title"].unique())
gwa_defaults = [x for x in str(saved.get("gwa", "") or "").split("; ") if x in gwas_options]
selected_gwas = st.multiselect("Select GWA(s):", gwas_options, default=gwa_defaults)

iwa_options = get_iwas(selected_gwas)
iwa_defaults = [x for x in str(saved.get("iwa", "") or "").split("; ") if x in iwa_options]
selected_iwas = st.multiselect("Select IWA(s):", iwa_options, default=iwa_defaults) if selected_gwas else []

dwa_options = get_dwas(selected_iwas)
dwa_defaults = [x for x in str(saved.get("dwa", "") or "").split("; ") if x in dwa_options]
selected_dwas = st.multiselect("Select DWA(s):", dwa_options, default=dwa_defaults) if selected_iwas else []

task_options = get_tasks(selected_dwas)
task_defaults = [x for x in str(saved.get("task", "") or "").split("; ") if x in task_options]
selected_tasks = st.multiselect("Select Task(s):", task_options, default=task_defaults) if selected_dwas else []

# --- Save to Google Sheets ---
if st.button("💾 Save / Update Classification"):
    if not selected_title:
        st.error("Please select an example first.")
    else:
        new_row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "title": selected_title,
            "url": row["url"],
            "bucket": row["bucket"],
            "gwa": "; ".join(selected_gwas),
            "iwa": "; ".join(selected_iwas),
            "dwa": "; ".join(selected_dwas),
            "task": "; ".join(selected_tasks),
        }

        mask = existing["title"] == selected_title
        if mask.any():
            for k, v in new_row.items():
                existing.loc[mask, k] = v
        else:
            existing = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)

        conn.update(spreadsheet=current_sheet, data=existing)
        st.success(f"Saved/updated classification for: {selected_title}")

# --- Optional: view current table ---
if st.checkbox("Show saved classifications"):
    st.dataframe(existing.sort_values("timestamp", ascending=False))

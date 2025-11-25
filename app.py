import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MCP Labeling Tool", layout="wide")

# --- Load data ---
df = pd.read_csv("options.csv")            # your GWA–IWA–DWA–Task hierarchy
examples = pd.read_csv("examples.csv")     # your 30 examples (title, url, text_for_llm, bucket)

# --- Helper functions ---
def get_iwas(selected_gwas):
    return sorted(df[df["gwa_title"].isin(selected_gwas)]["iwa_title"].dropna().unique().tolist())

def get_dwas(selected_iwas):
    return sorted(df[df["iwa_title"].isin(selected_iwas)]["dwa_title"].dropna().unique().tolist())

def get_tasks(selected_dwas):
    return sorted(df[df["dwa_title"].isin(selected_dwas)]["task"].dropna().unique().tolist())

# --- App UI ---
st.title("🧩 MCP Classification Tool")

# Example selection
titles = examples["title"].tolist()
selected_title = st.selectbox("Select an MCP Server Example:", [""] + titles)

if selected_title:
    row = examples[examples["title"] == selected_title].iloc[0]
    st.markdown(f"**URL:** [{row['url']}]({row['url']})")
    st.write(row["text_for_llm"])
    st.write(f"**Bucket:** {row['bucket']}")

# --- Load existing file or create it fresh ---
output_path = "data/classifications.csv"
expected_cols = ["timestamp", "title", "url", "bucket", "gwa", "iwa", "dwa", "task"]

try:
    existing = pd.read_csv(output_path)
    if existing.empty or not set(expected_cols).issubset(existing.columns):
        existing = pd.DataFrame(columns=expected_cols)
except (FileNotFoundError, pd.errors.EmptyDataError):
    existing = pd.DataFrame(columns=expected_cols)

# --- Load existing selection (if any) ---
saved = {}
if selected_title and not existing.empty:
    match = existing[existing["title"] == selected_title]
    if not match.empty:
        saved = match.iloc[0].to_dict()

# --- Dropdowns with pre-selected values (safe defaults) ---
gwas_options = sorted(df["gwa_title"].unique())
gwa_defaults = [x for x in saved.get("gwa", "").split("; ") if x in gwas_options]
selected_gwas = st.multiselect("Select GWA(s):", gwas_options, default=gwa_defaults)

iwa_options = get_iwas(selected_gwas)
iwa_defaults = [x for x in saved.get("iwa", "").split("; ") if x in iwa_options]
selected_iwas = st.multiselect("Select IWA(s):", iwa_options, default=iwa_defaults) if selected_gwas else []

dwa_options = get_dwas(selected_iwas)
dwa_defaults = [x for x in saved.get("dwa", "").split("; ") if x in dwa_options]
selected_dwas = st.multiselect("Select DWA(s):", dwa_options, default=dwa_defaults) if selected_iwas else []

task_options = get_tasks(selected_dwas)
task_defaults = [x for x in saved.get("task", "").split("; ") if x in task_options]
selected_tasks = st.multiselect("Select Task(s):", task_options, default=task_defaults) if selected_dwas else []


# --- Save logic ---
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

        # Write back to Google Sheets
        conn.update(existing)
        st.success(f"Saved/updated classification for: {selected_title}")

# --- View table ---
if st.checkbox("Show saved classifications"):
    st.dataframe(existing.sort_values("timestamp", ascending=False))



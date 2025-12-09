import hashlib
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection


st.set_page_config(page_title="MCP Labeling Tool", layout="wide")
# --- UI Tweaks ---
st.markdown(
    """
    <style>
    /* allow text selection inside widgets */
    [data-testid="stMarkdownContainer"], [data-testid="stCheckbox"], label {
        user-select: text !important;
        cursor: text !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def multi_select_custom(label, options, selected=None, cols_per_row=3, key_suffix=""):
    """
    Checkbox-based multi-select replacement that shows full text, stacked vertically.
    Returns a list of selected options.
    """
    if selected is None:
        selected = []
    st.write(f"**{label}**")
    selections = {}

    # Group options into rows of cols_per_row
    for row_start in range(0, len(options), cols_per_row):
        cols = st.columns(cols_per_row)
        row_options = options[row_start:row_start + cols_per_row]

        for col_idx, opt in enumerate(row_options):
            with cols[col_idx]:
                # Use hash of option text for stable key that changes with content
                opt_hash = hashlib.md5(opt.encode()).hexdigest()[:8]
                selections[opt] = st.checkbox(opt, value=opt in selected, key=f"{label}_{opt_hash}_{key_suffix}")

    return [k for k, v in selections.items() if v]


# def check_password():
#     """Returns `True` if the user entered the correct password."""
#     if st.session_state.get("password_correct", False):
#         # already logged in — don't show input again
#         return True

#     password = st.sidebar.text_input("Enter password", type="password")
#     secret_pass = str(st.secrets.get("app_password", "")).strip().strip('"')

#     if password and password.strip() == secret_pass:
#         st.session_state["password_correct"] = True
#         st.sidebar.success("✅ Access granted")
#         st.rerun()  # 👈 updated here
#     elif password:
#         st.sidebar.error("❌ Incorrect password")

#     return False

# if not check_password():
#     st.stop()


# --- Load static data ---
df = pd.read_csv("options.csv")            # GWA–IWA–DWA–Task hierarchy
examples = pd.read_csv("examples.csv")  

# Build quick lookup dictionaries
# --- Lookup dictionaries for showing context ---
gwa_lookup = (
    df[["gwa_title", "iwa_title"]]
    .dropna()
    .drop_duplicates(subset=["iwa_title"])
    .set_index("iwa_title")["gwa_title"]
    .to_dict()
)

iwa_lookup = (
    df[["gwa_title", "iwa_title", "dwa_title"]]
    .dropna()
    .drop_duplicates(subset=["dwa_title"])
    .set_index("dwa_title")[["gwa_title", "iwa_title"]]
    .to_dict(orient="index")
)

dwa_lookup = (
    df[["gwa_title", "iwa_title", "dwa_title", "task"]]
    .dropna()
    .drop_duplicates(subset=["task"])
    .set_index("task")[["gwa_title", "iwa_title", "dwa_title"]]
    .to_dict(orient="index")
)

   # MCP examples (title, url, text_for_llm, bucket)

# --- Helper functions ---
def get_iwas(selected_gwas):
    sub = df[df["gwa_title"].isin(selected_gwas)][["gwa_title", "iwa_title"]].dropna()
    return (
        sub.sort_values(["gwa_title", "iwa_title"])
           .drop_duplicates(subset=["iwa_title"])
           ["iwa_title"]
           .tolist()
    )

def get_dwas(selected_iwas):
    sub = df[df["iwa_title"].isin(selected_iwas)][["iwa_title", "dwa_title"]].dropna()
    return (
        sub.sort_values(["iwa_title", "dwa_title"])
           .drop_duplicates(subset=["dwa_title"])
           ["dwa_title"]
           .tolist()
    )

def get_tasks(selected_dwas):
    sub = df[df["dwa_title"].isin(selected_dwas)][["dwa_title", "task"]].dropna()
    return (
        sub.sort_values(["dwa_title", "task"])
           .drop_duplicates(subset=["task"])
           ["task"]
           .tolist()
    )

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
    existing = conn.read(spreadsheet=current_sheet, ttl=0)
except Exception as e:
    st.warning(f"Could not load sheet for {user_choice}: {e}")
    existing = pd.DataFrame()

expected_cols = ["timestamp","title","url","bucket","gwa","iwa","dwa","task", "notes"]
if existing is None or existing.empty or not set(expected_cols).issubset(existing.columns):
    existing = pd.DataFrame(columns=expected_cols)

# st.write("=== DEBUG: RAW EXISTING DF ===")
# st.write(existing)
# st.write("Columns:", existing.columns.tolist())
# st.write("Shape:", existing.shape)


# --- App UI ---
st.title("🧩 MCP Classification Tool")

titles = examples["title"].tolist()
selected_title = st.selectbox("Select an MCP Server Example:", [""] + titles)

# TEST BUTTON
test_clicked = st.button("TEST BUTTON")
st.write("TEST: button clicked =", test_clicked)

if selected_title:
    row = examples[examples["title"] == selected_title].iloc[0]
    st.markdown(f"**URL:** [{row['url']}]({row['url']})")
    st.write(row["text_for_llm"])
    st.write(f"**Bucket:** {row['bucket']}")

# --- Load existing selection for this title ---
saved = {}
if selected_title and not existing.empty:
    # Clean string comparison to avoid mismatch issues
    existing_titles_clean = existing["title"].astype(str).str.strip()
    match = existing[existing_titles_clean == selected_title.strip()]
    if not match.empty:
        saved = match.iloc[0].to_dict()

# st.write("=== DEBUG BEFORE SAVE ===")
# st.write("Selected title:", selected_title)
# st.write("Mask result:", existing["title"] == selected_title)
# st.write("Any match?:", (existing["title"] == selected_title).any())
# st.write("Saved dict:", saved)
# st.write("GWA from saved:", saved.get("gwa", ""))


# --- Dropdowns with pre-selected values ---
gwas_options = sorted(df["gwa_title"].unique())
gwa_defaults = [x for x in str(saved.get("gwa", "") or "").split("; ") if x in gwas_options]

# Check if there are cleaned selections in session state
if f"cleaned_gwas_{selected_title}" in st.session_state:
    gwa_defaults = st.session_state[f"cleaned_gwas_{selected_title}"]

selected_gwas = multi_select_custom("Select GWA(s):", gwas_options, gwa_defaults, key_suffix=selected_title)

# --- IWA Dropdown ---
iwa_defaults_raw = [x for x in str(saved.get("iwa", "") or "").split("; ") if x]

# Check if there are cleaned selections in session state
if f"cleaned_iwas_{selected_title}" in st.session_state:
    iwa_defaults_raw = st.session_state[f"cleaned_iwas_{selected_title}"]

# Always use the current GWA selections for filtering
iwa_options = get_iwas(selected_gwas)

# Only keep defaults that are still in the filtered options
iwa_defaults = [x for x in iwa_defaults_raw if x in iwa_options]

iwa_labels = [
    f"{iwa} (GWA: {gwa_lookup.get(iwa, '—')})"
    for iwa in iwa_options
]
iwa_display_map = dict(zip(iwa_labels, iwa_options))

# --- Custom IWA Checkboxes ---
selected_iwa_labels = multi_select_custom(
    "Select IWA(s):",
    [label for label in iwa_labels],
    [k for k, v in iwa_display_map.items() if v in iwa_defaults],
    key_suffix=selected_title
)
selected_iwas = [iwa_display_map[label] for label in selected_iwa_labels]

# --- DWA Dropdown ---
dwa_defaults_raw = [x for x in str(saved.get("dwa", "") or "").split("; ") if x]

# Check if there are cleaned selections in session state
if f"cleaned_dwas_{selected_title}" in st.session_state:
    dwa_defaults_raw = st.session_state[f"cleaned_dwas_{selected_title}"]

# Always use the current IWA selections for filtering
dwa_options = get_dwas(selected_iwas)

# Only keep defaults that are still in the filtered options
dwa_defaults = [x for x in dwa_defaults_raw if x in dwa_options]

dwa_labels = [
    f"{dwa} (GWA: {iwa_lookup.get(dwa, {}).get('gwa_title', '—')}, "
    f"IWA: {iwa_lookup.get(dwa, {}).get('iwa_title', '—')})"
    for dwa in dwa_options
]
dwa_display_map = dict(zip(dwa_labels, dwa_options))

# --- Custom DWA Checkboxes ---
selected_dwa_labels = multi_select_custom(
    "Select DWA(s):",
    [label for label in dwa_labels],
    [k for k, v in dwa_display_map.items() if v in dwa_defaults],
    key_suffix=selected_title
)
selected_dwas = [dwa_display_map[label] for label in selected_dwa_labels]

# --- Task Dropdown ---
task_defaults_raw = [x for x in str(saved.get("task", "") or "").split("; ") if x]

# Always use the current DWA selections for filtering
task_options = get_tasks(selected_dwas)

# Only keep defaults that are still in the filtered options
task_defaults = [x for x in task_defaults_raw if x in task_options]

# Build labels showing which selected DWAs each task belongs to
task_labels = []
for task in task_options:
    # Find which of the selected DWAs this task belongs to
    task_dwas = df[df["task"] == task]["dwa_title"].dropna().unique()
    matching_dwas = [dwa for dwa in selected_dwas if dwa in task_dwas]

    if matching_dwas:
        # Show the first matching DWA (or could show all)
        task_row = df[(df["task"] == task) & (df["dwa_title"] == matching_dwas[0])].iloc[0]
        label = f"{task} (GWA: {task_row.get('gwa_title', '—')}, IWA: {task_row.get('iwa_title', '—')}, DWA: {task_row.get('dwa_title', '—')})"
    else:
        # Fallback to original lookup
        label = f"{task} (GWA: {dwa_lookup.get(task, {}).get('gwa_title', '—')}, IWA: {dwa_lookup.get(task, {}).get('iwa_title', '—')}, DWA: {dwa_lookup.get(task, {}).get('dwa_title', '—')})"

    task_labels.append(label)

task_display_map = dict(zip(task_labels, task_options))

# --- Custom Task Checkboxes ---
selected_task_labels = multi_select_custom(
    "Select Task(s):",
    [label for label in task_labels],
    [k for k, v in task_display_map.items() if v in task_defaults],
    key_suffix=selected_title
)
selected_tasks = [task_display_map[label] for label in selected_task_labels]

# --- Clean Up Selections Button ---
button_clicked = st.button("🧹 Clean Up Unused Selections")
st.write("DEBUG: button_clicked =", button_clicked)
if button_clicked:
    st.write("DEBUG: Inside button block!")
    if selected_tasks:
        # Find which DWAs are actually used by selected tasks
        used_dwas = df[df["task"].isin(selected_tasks)]["dwa_title"].dropna().unique().tolist()
        # Find which IWAs are actually used by those DWAs
        used_iwas = df[df["dwa_title"].isin(used_dwas)]["iwa_title"].dropna().unique().tolist()
        # Find which GWAs are actually used by those IWAs
        used_gwas = df[df["iwa_title"].isin(used_iwas)]["gwa_title"].dropna().unique().tolist()

        st.write("DEBUG: selected_tasks:", selected_tasks[:1])
        st.write("DEBUG: used_dwas:", used_dwas)
        st.write("DEBUG: used_iwas:", used_iwas)
        st.write("DEBUG: used_gwas:", used_gwas)

        # Store cleaned selections in session state
        st.session_state[f"cleaned_gwas_{selected_title}"] = used_gwas
        st.session_state[f"cleaned_iwas_{selected_title}"] = used_iwas
        st.session_state[f"cleaned_dwas_{selected_title}"] = used_dwas
        # TEMPORARILY COMMENTED OUT TO SEE IF CODE RUNS
        # st.rerun()
        st.success("Cleanup button executed! (rerun disabled for testing)")
    else:
        st.warning("Please select some tasks first before cleaning up.")

# --- Notes field ---
notes_default = saved.get("notes", "") if saved else ""
notes_text = st.text_area(
    "Notes:",
    value=notes_default,
    height=120,
    key=f"notes_{selected_title}"  # ensures unique state per MCP
)



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
            "notes": notes_text,
        }

        # Clean comparison - strip whitespace and handle NaN
        existing["title"] = existing["title"].astype(str).str.strip()
        mask = existing["title"] == selected_title.strip()
        if mask.any():
            for k, v in new_row.items():
                existing.loc[mask, k] = v
        else:
            existing = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)

        conn.update(spreadsheet=current_sheet, data=existing)
        st.success(f"Saved/updated classification for: {selected_title}")

# st.write("=== DEBUG AFTER SAVE ===")
# st.write(existing.tail(10))


# --- Optional: view current table ---
if st.checkbox("Show saved classifications"):
    st.dataframe(existing.sort_values("timestamp", ascending=False))

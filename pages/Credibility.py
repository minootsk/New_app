import streamlit as st
import pandas as pd
import hashlib
from utils import get_gsheets_client, get_worksheet_by_url, make_unique_headers

# --- Page config MUST be first ---
st.set_page_config(
    page_title="Influencer Checker", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="📑"
)

# --- Cache Management: Set current page ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'credibility'

if st.session_state.get('current_page') != 'credibility':
    st.session_state.current_page = 'credibility'

# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "authenticated": False,
        "username": "",
        "name": "",
        "full_table": None,
        "editor_version": 0,
        "sheet_version": None,
        "sheet_updated": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Check for updates from other pages ---
if st.session_state.get('sheet_updated', False):
    st.cache_data.clear()
    st.session_state.sheet_updated = False
    st.session_state.full_table = None

# --- Optimized Authentication ---
def check_login():
    """Optimized authentication with better UI"""
    if st.session_state.authenticated:
        return True
        
   
    valid_credentials = {
        "solico": {"password": "solico123", "name": "Solico Group"},
        "minoo": {"password": "minoo123", "name": "Minoo Tashakori"}
    }
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container():
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_button = st.form_submit_button("Login", use_container_width=True)
                
                if submit_button:
                    if (username in valid_credentials and 
                        password == valid_credentials[username]["password"]):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.name = valid_credentials[username]["name"]
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
        st.stop()

check_login()

# --- Sidebar with User Info ---
with st.sidebar:
    st.success(f"👋 Welcome, **{st.session_state.name}**")
    
    # Refresh button
    if st.button("↺ Refresh Data", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.session_state.full_table = None
        st.session_state.sheet_version = None
        st.rerun()
    
    if st.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    

# --- CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1pFpU-ClSWJx2bFEdbZzaH47vedgtI8uxhDVXSKX0ZkE/edit"
INF_SHEET = "Influencers List"

# --- GOOGLE SHEET SETUP ---
@st.cache_resource(show_spinner=False)
def get_worksheet():
    client = get_gsheets_client()   # ✅ no JSON path, uses st.secrets
    ws_inf = get_worksheet_by_url(client, SHEET_URL, INF_SHEET)
    return ws_inf

try:
    worksheet_influencers = get_worksheet()
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()

# --- VERSION & LOAD DATA ---
@st.cache_data(ttl=60, show_spinner=False)  # Reduced TTL to 60 seconds
def get_sheet_version(_ws):
    all_values = _ws.get_all_values()
    last_row = "".join(all_values[-1]) if all_values else ""
    version_str = f"{len(all_values)}-{last_row}"
    return hashlib.md5(version_str.encode()).hexdigest()

@st.cache_data(ttl=120, show_spinner="↺ Loading data from Google Sheets...")
def load_data(_worksheet_influencers):
    data = _worksheet_influencers.get_all_values()
    headers = make_unique_headers(data[0])
    df = pd.DataFrame(data[1:], columns=headers)
    id_col = next(c for c in df.columns if "ID" in c)
    cred_col = next(c for c in df.columns if "Credibility" in c)
    comment_col = next(c for c in df.columns if "Comment" in c)
    df[cred_col] = df[cred_col].replace(
        {"TRUE": True, "True": True, "true": True,
         "FALSE": False, "False": False, "false": False}
    ).fillna(False)
    return df, id_col, cred_col, comment_col

try:
    sheet_version = get_sheet_version(worksheet_influencers)
    influencers_df, id_col, cred_col, comment_col = load_data(worksheet_influencers)
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# --- SESSION STATE MANAGEMENT ---
if st.session_state.full_table is None:
    st.session_state.full_table = influencers_df[[id_col, comment_col, cred_col]].copy()

if st.session_state.sheet_version is None:
    st.session_state.sheet_version = sheet_version
elif st.session_state.sheet_version != sheet_version:
    st.session_state.full_table = influencers_df[[id_col, comment_col, cred_col]].copy()
    st.session_state.sheet_version = sheet_version
    st.session_state.editor_version += 1
    st.rerun()


# --- FILTERS ---
st.markdown("### 🔍 Filter Influencers")
col1, col2 = st.columns(2)
with col1:
    cred_filter = st.selectbox(
        "Filter by Credibility",
        options=["All", True, False],
        format_func=lambda x: "All" if x == "All" else ("✔️ Approved" if x else "❌ Rejected")
    )
with col2:
    comment_filter = st.selectbox(
        "Filter by Comment",
        options=["All"] + sorted(st.session_state.full_table[comment_col].dropna().unique().tolist())
    )

# --- APPLY FILTERS ---
def get_filtered_table():
    df = st.session_state.full_table
    mask = pd.Series(True, index=df.index)
    if cred_filter != "All":
        mask &= df[cred_col] == cred_filter
    if comment_filter != "All":
        mask &= df[comment_col] == comment_filter
    result = df[mask].copy()
    result["Status"] = result[cred_col].map({True: "✔️ Approved", False: "❌ Rejected"})
    return result

filtered_df = get_filtered_table()
display_df = filtered_df.reset_index().rename(columns={'index': '__orig_index'})
cols = ['__orig_index'] + [c for c in display_df.columns if c != '__orig_index']
display_df = display_df[cols]

editor_key = f"main_editor_v{st.session_state.editor_version}"
st.write("")    
st.markdown("### 📋 Edit Influencer Data")
edited_table = st.data_editor(
    display_df,
    use_container_width=True,
    num_rows="fixed",
    key=editor_key,
    column_config={
        "__orig_index": st.column_config.TextColumn("Row", help="Internal index", disabled=True),
        cred_col: st.column_config.CheckboxColumn(
            "Credibility",
            help="✔️ Check = Approved / True | ❌ Uncheck = Rejected / False"
        ),
        "Status": st.column_config.TextColumn("Status", disabled=True),
        id_col: st.column_config.TextColumn("Influencer ID", help="Instagram username without @"),
        comment_col: st.column_config.TextColumn("Comments", help="Add or edit comments")
    },
    hide_index=True
)

# --- UPDATE FULL TABLE WITH EDITS ---
if edited_table is not None:
    updated_full = st.session_state.full_table.copy()
    changes = []
    for _, row in edited_table.iterrows():
        orig_idx = row["__orig_index"]
        if pd.isna(orig_idx):
            continue
        if (
            updated_full.at[orig_idx, cred_col] != row[cred_col]
            or updated_full.at[orig_idx, comment_col] != row[comment_col]
        ):
            updated_full.at[orig_idx, cred_col] = row[cred_col]
            updated_full.at[orig_idx, comment_col] = row[comment_col]
            changes.append(orig_idx)
    if changes:
        st.session_state.full_table = updated_full
        st.session_state.editor_version += 1
        st.success(f"✔️ {len(changes)} row(s) updated locally")
        st.rerun()

# --- ADD/UPDATE INFLUENCER FORM ---
st.markdown("---")
with st.expander("➕ Add / Update Influencer", expanded=False):
    st.markdown("### Add New Influencer or Update Existing")
    
    with st.form("add_influencer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_id = st.text_input("Influencer ID", placeholder="Enter Instagram username (without @)")
            new_cred = st.checkbox("✔️ Approved / Credible", value=True, help="Check for approved, uncheck for rejected")
        
        with col2:
            new_comment = st.text_input("💬 Comment", placeholder="Add comments or notes")
        
        submitted = st.form_submit_button("💾 Save Influencer", use_container_width=True)
        
        if submitted:
            if not new_id:
                st.error("❌ Please enter an Influencer ID")
            else:
                # Clean the ID
                new_id = new_id.lstrip("@").strip()
                
                idx_list = st.session_state.full_table[st.session_state.full_table[id_col] == new_id].index.tolist()
                if idx_list:
                    idx = idx_list[0]
                    st.session_state.full_table.at[idx, comment_col] = new_comment
                    st.session_state.full_table.at[idx, cred_col] = new_cred
                    st.success(f"✔️ Influencer **'{new_id}'** updated successfully")
                else:
                    new_row = pd.DataFrame({
                        id_col: [new_id],
                        comment_col: [new_comment],
                        cred_col: [new_cred]
                    })
                    st.session_state.full_table = pd.concat([new_row, st.session_state.full_table], ignore_index=True)
                    st.success(f"✔️ Influencer **'{new_id}'** added successfully")
                st.session_state.editor_version += 1
                st.rerun()

# --- GOOGLE SHEET UPDATE ---
@st.cache_data(ttl=300, show_spinner=False)
def update_google_sheet(df, _worksheet_influencers, id_col, cred_col, comment_col):
    df_to_write = df.copy()
    df_to_write[cred_col] = df_to_write[cred_col].map({True: "True", False: "False"})
    values = [df_to_write.columns.tolist()] + df_to_write.values.tolist()
    _worksheet_influencers.clear()
    _worksheet_influencers.update(values)
    return True

st.markdown("---")
st.markdown("### Sync with Google Sheets")

if st.button("☁️ Update Google Sheet", use_container_width=True, type="primary"):
    try:
        with st.spinner("↺ Updating Google Sheets..."):
            success = update_google_sheet(
                st.session_state.full_table,
                worksheet_influencers,
                id_col,
                cred_col,
                comment_col
            )
        if success:
            st.success("✔️ Google Sheet updated successfully!")
            st.session_state.sheet_updated = True
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to update Google Sheet: {e}")



import streamlit as st
import pandas as pd
import io
import re
import hashlib
import plotly.graph_objects as go
from utils import get_gsheets_client, get_worksheet_by_key, load_worksheet_df

# --- Page config ---
st.set_page_config(
    page_title="Influencer Checker", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="📑"
)

# --- Cache Management: Clear cache when navigating to this page ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'list'

if st.session_state.get('current_page') != 'list':
    st.cache_data.clear()
    st.session_state.current_page = 'list'
    st.session_state.data_loaded = False

# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "authenticated": False,
        "username": "",
        "name": "",
        "data_loaded": False,
        "inf_df": None,
        "master_df": None,
        "current_file_hash": None,
        "show_preview": False,
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
    st.session_state.data_loaded = False

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
    st.title("📑 Influencer Checker")
    st.divider()
    st.success(f"👋 Welcome, **{st.session_state.name}**")
    
    # Refresh button
    if st.button("↻ Refresh Data", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.session_state.data_loaded = False
        st.session_state.sheet_updated = False
        st.rerun()
    
    if st.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# --- Optimized Helper Functions ---
@st.cache_data
def format_number(x):
    """Cache the number formatting function"""
    if pd.isna(x) or x == "" or x is None:
        return ""
    try:
        x_float = float(x)
        if x_float.is_integer():
            return f"{int(x_float):,}"
        else:
            return f"{x_float:,.2f}"
    except (ValueError, TypeError):
        return str(x)

# --- Google Sheets Configuration ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1pFpU-ClSWJx2bFEdbZzaH47vedgtI8uxhDVXSKX0ZkE/edit#gid=92547169"
SHEET_ID = re.search(r"/d/([a-zA-Z0-9-_]+)", SHEET_URL).group(1)
INF_SHEET = "Influencers List"
MASTER_SHEET = "Master"

# --- Optimized Data Loading ---
@st.cache_resource(show_spinner=False)
def get_sheets_client():
    """Cache the sheets client creation"""
    return get_gsheets_client()

@st.cache_data(ttl=60, show_spinner="↺ Loading data from Google Sheets...")  # Reduced TTL to 60 seconds
def load_all_data():
    """Load all required data in one optimized function"""
    try:
        client = get_sheets_client()
        ws_inf = get_worksheet_by_key(client, SHEET_ID, INF_SHEET)
        ws_master = get_worksheet_by_key(client, SHEET_ID, MASTER_SHEET)
        
        # Load dataframes
        inf_df = load_worksheet_df(ws_inf)
        master_df = load_worksheet_df(ws_master)
        
        # Process influencers dataframe
        inf_df["ID"] = inf_df.get("ID", inf_df.columns[0]).astype(str).str.strip()
        inf_df["Comment"] = inf_df.get("Comment", pd.Series([""] * len(inf_df)))
        inf_df["Credibility"] = inf_df.get("Credibility", pd.Series(["False"] * len(inf_df)))
        inf_df["Credibility"] = inf_df["Credibility"].astype(str).str.strip().str.lower()
        
        # Process master dataframe
        required_cols = ["ID", "Post Price", "Story price", "Publication date(Miladi)", "Category", "Follower"]
        for col in required_cols:
            if col not in master_df.columns:
                master_df[col] = None
        
        # Optimize dataframe memory usage
        inf_df = inf_df.infer_objects().copy()
        master_df = master_df.infer_objects().copy()
        
        return inf_df, master_df, ws_inf
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()

# Load data only once per session or when needed
if not st.session_state.data_loaded or st.session_state.inf_df is None:
    with st.spinner("↺ Loading application data..."):
        st.session_state.inf_df, st.session_state.master_df, st.session_state.ws_inf = load_all_data()
        st.session_state.data_loaded = True

# --- File Upload Section ---

uploaded_file = st.file_uploader(
    "Drag and drop or click to upload Excel/CSV file", 
    type=["xlsx", "xls", "csv"],
    help="Upload a file containing influencer data with ID column"
)

# --- Process Uploaded File with Progress Indicators ---
if uploaded_file:
    current_file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
    
    # Only reprocess if file changed
    if st.session_state.current_file_hash != current_file_hash:
        st.session_state.current_file_hash = current_file_hash
        
        with st.spinner("↻ Processing uploaded file..."):
            # Process file
            @st.cache_data(show_spinner=False)
            def process_uploaded_file(_uploaded_file):
                if _uploaded_file.name.endswith(".csv"):
                    new_df = pd.read_csv(_uploaded_file)
                else:
                    new_df = pd.read_excel(_uploaded_file)
                
                if "ID" not in new_df.columns:
                    new_df.rename(columns={new_df.columns[0]: "ID"}, inplace=True)
                
                new_df["ID"] = new_df["ID"].astype(str).str.lstrip("@").str.strip()
                
                # Optimize numeric conversions
                numeric_columns = ["Followers", "Post price", "Avg View", "CPV", "IER", "Avg like", "Avg comments"]
                for col in numeric_columns:
                    if col in new_df.columns:
                        new_df[col] = pd.to_numeric(new_df[col], errors="coerce")
                
                return new_df
            
            new_df = process_uploaded_file(uploaded_file)
            st.session_state.new_df = new_df
    
    # Use cached data
    new_df = st.session_state.new_df
    inf_df = st.session_state.inf_df
    
    # Merge data efficiently
    with st.spinner("↺ Analyzing influencer data..."):
        merged_df = new_df.merge(inf_df, on="ID", how="left", suffixes=("", "_sheet"))
        merged_df["Link"] = "https://www.instagram.com/" + merged_df["ID"]
        
        # Categorize influencers
        rejected_df = merged_df[merged_df["Credibility"].isin(["false", "False"])][["ID", "Comment", "Link"]]
        unknown_df = merged_df[merged_df["Credibility"].isna()][["ID", "Link"]]
        
        pending_ids = set(new_df["ID"]) - set(rejected_df["ID"]) - set(unknown_df["ID"])
        pending_df = new_df[new_df["ID"].isin(pending_ids)].copy()
        pending_df["Link"] = "https://www.instagram.com/" + pending_df["ID"]
        pending_df["Select"] = True
        
        # Ensure required columns
        for col in ["Followers", "Category", "Avg View", "CPV", "IER", "Avg like", "Avg comments", "Post price"]:
            if col not in pending_df.columns:
                pending_df[col] = ""
        
        pending_df["Compare"] = False
        
        # Prepare unknown influencers dataframe
        unknown_df = unknown_df.copy()
        unknown_df["Comment"] = "No comment yet"
        unknown_df["Select_Sheet"] = False
        unknown_df["Status"] = "Rejected"
        
        st.session_state.rejected_df = rejected_df
        st.session_state.unknown_df = unknown_df
        st.session_state.pending_df = pending_df
    
    # Display results using tabs for better organization - PENDING AS FIRST TAB
    tab1, tab2, tab3 = st.tabs([
        f"🕒 Pending ({len(st.session_state.pending_df)})",
        f"❌ Rejected ({len(st.session_state.rejected_df)})",
        f"❓ Unknown ({len(st.session_state.unknown_df)})"
    ])
    
    with tab1:
        # Create display dataframe with formatted numbers
        pending_display = st.session_state.pending_df.copy()
        numeric_columns = ["Followers", "Post price", "Avg View", "CPV"]
        for col in numeric_columns:
            if col in pending_display.columns:
                pending_display[col] = pending_display[col].apply(format_number)
        
        display_columns = ["ID", "Link", "Followers", "Category", "Post price", "Avg View", "CPV", "Select", "Compare"]
        display_columns = [col for col in display_columns if col in pending_display.columns]
        
        pending_edited = st.data_editor(
            pending_display[display_columns],
            use_container_width=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Include in Export", default=True),
                "Compare": st.column_config.CheckboxColumn("Compare History", default=False),
                "Link": st.column_config.LinkColumn("Instagram Profile", display_text="View Profile")
            },
            key=f"pending_editor_{current_file_hash[:8]}",
            hide_index=True
        )
        
        # Comparison functionality
        compare_ids = pending_edited[pending_edited["Compare"]]["ID"].tolist()
        
        if compare_ids:
            st.markdown("---")
            st.markdown("### 📑 Historical Comparison")
            
            # Use tabs for each influencer comparison
            comparison_tabs = st.tabs([f"📈 {inf_id}" for inf_id in compare_ids])
            
            for i, influencer_id in enumerate(compare_ids):
                with comparison_tabs[i]:
                    current_data = st.session_state.pending_df[st.session_state.pending_df["ID"] == influencer_id].iloc[0]
                    historical_data = st.session_state.master_df[st.session_state.master_df["ID"] == influencer_id]
                    
                    if not historical_data.empty:
                        historical_data = historical_data.sort_values("Publication date(Miladi)")
                        
                        # Create comparison charts - EACH CHART IN 100% WIDTH
                        # Post Price Chart
                        if "Post Price" in historical_data.columns and historical_data["Post Price"].notna().any():
                            fig_price = go.Figure()
                            fig_price.add_trace(go.Scatter(
                                x=historical_data["Publication date(Miladi)"],
                                y=historical_data["Post Price"],
                                mode='lines+markers',
                                name='Post Price',
                                line=dict(color='#004aff', width=1)
                            ))
                            fig_price.update_layout(
                                title="📈 Post Price Trend", 
                                height=400,
                                xaxis_title="Publication Date",
                                yaxis_title="Post Price",
                                showlegend=True
                            )
                            st.plotly_chart(fig_price, use_container_width=True)
                        
                        # Followers Chart
                        if "Follower" in historical_data.columns and historical_data["Follower"].notna().any():
                            fig_followers = go.Figure()
                            fig_followers.add_trace(go.Scatter(
                                x=historical_data["Publication date(Miladi)"],
                                y=historical_data["Follower"],
                                mode='lines+markers',
                                name='Followers',
                                line=dict(color='#00cc96', width=1)
                            ))
                            fig_followers.update_layout(
                                title="📊 Followers Trend", 
                                height=400,
                                xaxis_title="Publication Date",
                                yaxis_title="Followers",
                                showlegend=True
                            )
                            st.plotly_chart(fig_followers, use_container_width=True)
                        
                        # Average Views Chart
                        if "Avg View" in historical_data.columns and historical_data["Avg View"].notna().any():
                            fig_views = go.Figure()
                            fig_views.add_trace(go.Scatter(
                                x=historical_data["Publication date(Miladi)"],
                                y=historical_data["Avg View"],
                                mode='lines+markers',
                                name='Average Views',
                                line=dict(color='#ff7f0e', width=3)
                            ))
                            fig_views.update_layout(
                                title="👀 Average Views Trend", 
                                height=400,
                                xaxis_title="Publication Date",
                                yaxis_title="Average Views",
                                showlegend=True
                            )
                            st.plotly_chart(fig_views, use_container_width=True)
                        
                        # CPV Chart
                        if "CPV" in historical_data.columns and historical_data["CPV"].notna().any():
                            fig_cpv = go.Figure()
                            fig_cpv.add_trace(go.Scatter(
                                x=historical_data["Publication date(Miladi)"],
                                y=historical_data["CPV"],
                                mode='lines+markers',
                                name='CPV',
                                line=dict(color='#d62728', width=1)
                            ))
                            fig_cpv.update_layout(
                                title="💰 CPV Trend", 
                                height=400,
                                xaxis_title="Publication Date",
                                yaxis_title="CPV",
                                showlegend=True
                            )
                            st.plotly_chart(fig_cpv, use_container_width=True)
                        
                        # Current values table
                        st.markdown("### 📋 Current Metrics")
                        current_values_data = {
                            "Metric": ["Post Price", "Followers", "Avg View", "CPV", "Category", "IER", "Avg Like", "Avg Comments"],
                            "Value": [
                                format_number(current_data.get("Post price", "N/A")),
                                format_number(current_data.get("Followers", "N/A")),
                                format_number(current_data.get("Avg View", "N/A")),
                                format_number(current_data.get("CPV", "N/A")),
                                current_data.get("Category", "N/A"),
                                format_number(current_data.get("IER", "N/A")),
                                format_number(current_data.get("Avg like", "N/A")),
                                format_number(current_data.get("Avg comments", "N/A"))
                            ]
                        }
                        current_values_df = pd.DataFrame(current_values_data)
                        st.dataframe(current_values_df, use_container_width=True, hide_index=True)
                        
                        # Historical data preview - FIXED KEYERROR
                        st.markdown("### 📊 Historical Data Preview")
                        
                        # Safely select columns that exist
                        available_columns = ["Publication date(Miladi)", "Post Price", "Follower"]
                        
                        # Add optional columns only if they exist
                        optional_columns = ["Avg View", "CPV", "Category"]
                        for col in optional_columns:
                            if col in historical_data.columns:
                                available_columns.append(col)
                        
                        historical_display = historical_data[available_columns].copy()
                        
                        # Format numeric columns
                        numeric_cols = ["Post Price", "Follower", "Avg View", "CPV"]
                        for col in numeric_cols:
                            if col in historical_display.columns:
                                historical_display[col] = historical_display[col].apply(format_number)
                        
                        st.dataframe(historical_display, use_container_width=True, hide_index=True)
                        
                    else:
                        st.info("ℹ️ No historical data available for this influencer.")
                        
                        # Show current values even if no historical data
                        st.markdown("### 📋 Current Metrics")
                        current_values_data = {
                            "Metric": ["Post Price", "Followers", "Avg View", "CPV", "Category"],
                            "Value": [
                                format_number(current_data.get("Post price", "N/A")),
                                format_number(current_data.get("Followers", "N/A")),
                                format_number(current_data.get("Avg View", "N/A")),
                                format_number(current_data.get("CPV", "N/A")),
                                current_data.get("Category", "N/A")
                            ]
                        }
                        current_values_df = pd.DataFrame(current_values_data)
                        st.dataframe(current_values_df, use_container_width=True, hide_index=True)
        
        # Download functionality
        selected_pending = pending_edited[pending_edited["Select"]].copy()
        
        if not selected_pending.empty:
            st.markdown("---")
            st.markdown("### 📥 Export Selected Influencers")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if st.button("👁️ Preview Selection", use_container_width=True):
                    st.session_state.show_preview = True
            
            if st.session_state.get('show_preview', False):
                with st.expander("📋 Selected Influencers Preview", expanded=True):
                    preview_columns = ["ID", "Link", "Followers", "Category", "Post price"]
                    preview_columns = [col for col in preview_columns if col in selected_pending.columns]
                    
                    st.dataframe(selected_pending[preview_columns], 
                               use_container_width=True, height=300)
                    
                    if st.button("Close Preview", key="close_preview"):
                        st.session_state.show_preview = False
                        st.rerun()
            
            with col2:
                # Prepare download data
                download_df = pd.DataFrame()
                download_df["ID"] = selected_pending["ID"]
                
                # Add required columns structure
                for i in range(4):
                    download_df[f"col_{i+1}"] = ""
                
                download_df["Page link"] = selected_pending["Link"]
                download_df["Category"] = selected_pending["Category"]
                download_df["col_5"] = ""

                # Map original numeric values
                follower_mapping = dict(zip(st.session_state.pending_df["ID"], st.session_state.pending_df["Followers"]))
                download_df["Follower"] = download_df["ID"].map(follower_mapping)
                
                # Add other metrics with empty column between Ave Comment and Post Price
                metric_mappings = {
                    "ER": "IER",
                    "Ave Like": "Avg like", 
                    "Ave Comment": "Avg comments",
                    "COL_6": "",  # This is the new empty column
                    "Post Price": "Post price"
                }

                for target_col, source_col in metric_mappings.items():
                    if source_col in st.session_state.new_df.columns and source_col != "":  # For actual data columns
                        mapping = dict(zip(st.session_state.new_df["ID"], st.session_state.new_df[source_col]))
                        download_df[target_col] = download_df["ID"].map(mapping)
                    else:
                        # For empty columns, just add empty strings
                        download_df[target_col] = ""
                
                # Create download button
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    download_df.to_excel(writer, index=False, sheet_name="Selected Influencers")
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Excel File",
                    data=output,
                    file_name="selected_influencers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
    
    with tab2:
        st.dataframe(
            st.session_state.rejected_df[["ID", "Comment", "Link"]],
            use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn("View Profile", display_text="View Profile")
            },
            hide_index=True
        )
    
    with tab3:
        
        unknown_edited = st.data_editor(
            st.session_state.unknown_df[["ID", "Link", "Comment", "Status", "Select_Sheet"]],
            use_container_width=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Select the status for this influencer",
                    options=["Approved", "Rejected"],
                    required=True
                ),
                "Select_Sheet": st.column_config.CheckboxColumn("Add to Google Sheet"),
                "Link": st.column_config.LinkColumn("Instagram Profile", display_text="View Profile"),
                "Comment": st.column_config.TextColumn("Comment", default="No comment yet")
            },
            key=f"unknown_editor_{current_file_hash[:8]}"
        )
        
        if st.button("☁️ Add Selected to Google Sheet", use_container_width=True, type="primary"):
            to_add = unknown_edited[unknown_edited["Select_Sheet"]].copy()
            if not to_add.empty:
                to_add["Credibility"] = to_add["Status"].map({"Approved": "True", "Rejected": "False"})
                values_to_append = to_add[["ID", "Comment", "Credibility"]].values.tolist()
                
                try:
                    st.session_state.ws_inf.append_rows(values_to_append, value_input_option="USER_ENTERED")
                    st.success(f"✔️ {len(values_to_append)} influencer(s) added successfully!")
                    # Set flag to refresh data in other pages
                    st.session_state.sheet_updated = True
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to update Google Sheet: {e}")

# --- Empty State ---
else:
    st.markdown("""
    <div style='text-align: center; padding: 4rem 2rem;'>
        <h2>👋 Ready to Manage Influencers?</h2>
        <p>Upload an Excel or CSV file to get started with influencer analysis and comparison.</p>
    </div>
    """, unsafe_allow_html=True)


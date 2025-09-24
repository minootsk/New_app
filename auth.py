import streamlit as st
import time

def init_session_state():
    """Initialize session state for authentication"""
    if 'auth' not in st.session_state:
        st.session_state.auth = {
            'authenticated': False,
            'username': '',
            'name': '',
            'login_attempts': 0,
            'last_attempt': 0
        }

def check_auth():
    """Enhanced authentication with rate limiting"""
    init_session_state()
    
    if st.session_state.auth['authenticated']:
        return True
    
    # Rate limiting: max 5 attempts per minute
    current_time = time.time()
    if (st.session_state.auth['login_attempts'] >= 5 and 
        current_time - st.session_state.auth['last_attempt'] < 60):
        st.error("🚫 Too many login attempts. Please wait 1 minute.")
        st.stop()
    
    # Centered login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h1>🔐 Authentication Required</h1>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("auth_form", clear_on_submit=True):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit:
                st.session_state.auth['last_attempt'] = current_time
                st.session_state.auth['login_attempts'] += 1
                
                valid_credentials = {
                    "solico": {"password": "solico123", "name": "Solico Group"},
                    "minoo": {"password": "minoo123", "name": "Minoo Tashakori"}
                }
                
                if (username in valid_credentials and 
                    password == valid_credentials[username]["password"]):
                    
                    st.session_state.auth.update({
                        'authenticated': True,
                        'username': username,
                        'name': valid_credentials[username]["name"],
                        'login_attempts': 0
                    })
                    st.rerun()
                else:
                    attempts_left = 5 - st.session_state.auth['login_attempts']
                    st.error(f"❌ Invalid credentials. {attempts_left} attempts remaining.")
    
    st.stop()

def logout():
    """Clear authentication state"""
    st.session_state.auth.update({
        'authenticated': False,
        'username': '',
        'name': ''
    })
    st.rerun()
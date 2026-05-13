import streamlit as st
from api_client import login

def show():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0A0C10 !important; color: #F4F1EB !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    footer, #MainMenu { visibility: hidden; }
    [data-testid="stMainBlockContainer"] { max-width: 420px !important; margin: 0 auto !important; padding-top: 80px !important; }
    .stTextInput input { background: #1C2333 !important; color: #F4F1EB !important; border: 1px solid rgba(200,241,53,0.2) !important; border-radius: 6px !important; }
    .stTextInput input:focus { border-color: #C8F135 !important; box-shadow: none !important; }
    .stTextInput label { color: #8A94A8 !important; font-size: 12px !important; font-family: 'DM Mono', monospace !important; letter-spacing: 1px !important; }
    div[data-testid="stButton"] button[kind="primary"] {
        background: #C8F135 !important; color: #0A0C10 !important;
        font-weight: 700 !important; border: none !important;
        width: 100% !important; padding: 12px !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background: transparent !important; color: #8A94A8 !important;
        border: 1px solid rgba(138,148,168,0.3) !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Logo
    st.markdown("""
    <div style='text-align:center;margin-bottom:40px;'>
      <div style='font-family:"Bebas Neue",sans-serif;font-size:32px;letter-spacing:4px;color:#C8F135;'>BI DASH</div>
      <div style='font-family:"DM Mono",monospace;font-size:10px;color:#8A94A8;letter-spacing:2px;margin-top:4px;'>SME INTELLIGENCE PLATFORM</div>
    </div>
    <h2 style='font-family:"Bebas Neue",sans-serif;font-size:36px;color:#F4F1EB;margin-bottom:6px;'>Welcome Back</h2>
    <p style='font-size:13px;color:#8A94A8;margin-bottom:28px;'>Sign in to your dashboard</p>
    """, unsafe_allow_html=True)

    email    = st.text_input("EMAIL ADDRESS", placeholder="you@company.com")
    password = st.text_input("PASSWORD", type="password", placeholder="••••••••")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Sign In →", type="primary"):
        if not email or not password:
            st.error("Please enter your email and password.")
        else:
            with st.spinner("Signing in..."):
                result = login(email, password)
            if result:
                st.session_state.token     = result["token"]
                st.session_state.user_name = result["user"]["full_name"]
                st.session_state.page      = "overview"
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("<p style='text-align:center;font-size:13px;color:#8A94A8;margin-bottom:8px;'>Don't have an account?</p>", unsafe_allow_html=True)
    if st.button("Create an account →"):
        st.session_state.page = "register"
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("← Back to home"):
        st.session_state.page = "landing"
        st.rerun()

import streamlit as st
from api_client import reset_password


def show():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0A0A1A !important; color: #F4F1EB !important;
    }
    [data-testid="stHeader"]    { background: transparent !important; }
    [data-testid="stToolbar"]    { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stMainBlockContainer"] {
        max-width: 420px !important; margin: 0 auto !important; padding-top: 80px !important;
    }
    .stTextInput input {
        background: #12103A !important;
        color: #F4F1EB !important;
        border: 1px solid rgba(123,92,245,0.2) !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
    }
    .stTextInput input::placeholder {
        color: #4A5168 !important;
        opacity: 1 !important;
    }
    .stTextInput input:focus {
        border-color: #7B5CF5 !important;
        box-shadow: 0 0 0 1px #7B5CF5 !important;
    }
    .stTextInput label {
        color: #8A94A8 !important;
        font-size: 11px !important;
        font-family: 'DM Mono', monospace !important;
        letter-spacing: 1.5px !important;
        font-weight: 500 !important;
    }
    .stButton > button[kind="primary"] {
        background: #7B5CF5 !important; color: #0A0A1A !important;
        font-weight: 700 !important; border: none !important;
        width: 100% !important; padding: 12px !important;
        border-radius: 6px !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important; color: #8A94A8 !important;
        border: 1px solid rgba(138,148,168,0.3) !important;
        width: 100% !important; border-radius: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;margin-bottom:32px;'>
      <div style='font-size:28px;font-weight:700;letter-spacing:2px;color:#7B5CF5;font-family:"Bebas Neue",sans-serif;'>
        BI DASHBOARD
      </div>
      <h2 style='font-family:"Bebas Neue",sans-serif;font-size:36px;color:#F4F1EB;margin-bottom:6px;'>
        Reset Password
      </h2>
      <p style='font-size:13px;color:#8A94A8;margin-bottom:28px;'>
        Enter your email and choose a new password
      </p>
    </div>
    """, unsafe_allow_html=True)

    email    = st.text_input("EMAIL ADDRESS", placeholder="you@company.com", key="fp_email")
    new_pw   = st.text_input("NEW PASSWORD",  placeholder="••••••••", type="password", key="fp_new_pw")
    conf_pw  = st.text_input("CONFIRM PASSWORD", placeholder="••••••••", type="password", key="fp_conf_pw")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Update Password", type="primary", key="fp_submit"):
        if not email or not new_pw or not conf_pw:
            st.error("Please fill in all fields.")
        elif new_pw != conf_pw:
            st.error("Passwords do not match.")
        elif len(new_pw) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            with st.spinner("Updating..."):
                result = reset_password(email, new_pw)
            if result:
                st.success("Password updated! Redirecting to sign in...")
                import time; time.sleep(1.5)
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("No account found with that email address.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if st.button("← Back to Sign In", type="secondary", key="fp_back"):
        st.session_state.page = "login"
        st.rerun()

import streamlit as st
from api_client import login

# ── 1. PAGE CONFIG ──────────────────────────────────────
st.set_page_config(
    page_title="BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. AUTH CHECK ───────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None

if not st.session_state.token:
    st.title("Welcome")
    email    = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        result = login(email, password)
        if result:
            st.session_state.token     = result["token"]
            st.session_state.user_name = result["user"]["full_name"]
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# ── 3. DEFINE PAGES ─────────────────────────────────────
overview       = st.Page("pages/01_overview.py",        title="Overview",          icon="🏠", default=True)
chat           = st.Page("pages/02_chat.py",            title="Ask a question",    icon="💬")
finance        = st.Page("pages/03_finance.py",         title="Finance",           icon="💰")
sales          = st.Page("pages/04_sales_marketing.py", title="Sales & Marketing", icon="📈")
customers      = st.Page("pages/05_customers.py",       title="Customers",         icon="👥")
upload         = st.Page("pages/06_upload.py",          title="Upload data",       icon="📁")

# ── 4. NAVIGATION + SIDEBAR ─────────────────────────────
pg = st.navigation([overview, chat, finance, sales, customers, upload])

with st.sidebar:
    st.markdown("### BI Dashboard")
    st.markdown("---")
    user = st.session_state.get("user_name", "User")
    st.caption(f"Logged in as {user}")
    st.markdown("---")
    if st.button("Logout"):
        st.session_state.to
import streamlit as st
from api_client import login, register

# ── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(
    page_title="BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ── GLOBAL MOBILE CSS ────────────────────────────────────
st.markdown("""
<style>
@media (max-width: 768px) {
    /* Sidebar collapses on mobile */
    [data-testid="stSidebar"] { width: 240px !important; }
    
    /* Main content full width */
    [data-testid="stMainBlockContainer"] { 
        padding: 16px 12px !important; 
    }
    
    /* Metric cards stack better */
    [data-testid="stHorizontalBlock"] > div {
        min-width: 140px !important;
    }
    
    /* Charts full width */
    [data-testid="stArrowVegaLiteChart"] { 
        width: 100% !important; 
    }

    /* Buttons full width */
    .stButton button { width: 100% !important; }

    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton button {
        font-size: 13px !important;
        padding: 10px 8px !important;
    }
}
@media (max-width: 480px) {
    [data-testid="stMainBlockContainer"] { 
        padding: 12px 8px !important; 
    }
    h1 { font-size: 24px !important; }
    h2 { font-size: 20px !important; }
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE DEFAULTS ───────────────────────────────
if "token"     not in st.session_state: st.session_state.token     = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "page"      not in st.session_state: st.session_state.page      = "landing"

page = st.session_state.page

# ── LANDING ──────────────────────────────────────────────
if page == "landing":
    from pages.landing import show; show()

# ── LOGIN ─────────────────────────────────────────────────
elif page == "login":
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    from pages.login import show; show()

# ── REGISTER ──────────────────────────────────────────────
elif page == "register":
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    from pages.register import show; show()

# ── DASHBOARD (requires login) ────────────────────────────
elif st.session_state.token:

    # ── SIDEBAR ─────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='font-family:monospace;font-size:20px;"
            "color:#C8F135;letter-spacing:3px;padding:8px 0 4px'>BI DASH</div>",
            unsafe_allow_html=True
        )
        st.caption(f"👤 {st.session_state.user_name}")
        st.markdown("---")

        # ── Home button ──────────────────────────────────
        if st.button("🏠  Home", use_container_width=True, key="nav_home"):
            st.session_state.token     = None
            st.session_state.user_name = None
            st.session_state.page      = "landing"
            st.rerun()

        st.markdown("---")

        # ── Main nav ─────────────────────────────────────
        if st.button("📊  Overview",          use_container_width=True, key="nav_overview"):
            st.session_state.page = "overview";  st.rerun()
        if st.button("💰  Finance",           use_container_width=True, key="nav_finance"):
            st.session_state.page = "finance";   st.rerun()
        if st.button("📈  Sales & Marketing", use_container_width=True, key="nav_sales"):
            st.session_state.page = "sales";     st.rerun()
        if st.button("👥  Customers",         use_container_width=True, key="nav_customers"):
            st.session_state.page = "customers"; st.rerun()

        st.markdown("---")

        if st.button("💬  Chat",              use_container_width=True, key="nav_chat"):
            st.session_state.page = "chat";      st.rerun()
        if st.button("📁  Upload Data",       use_container_width=True, key="nav_upload"):
            st.session_state.page = "upload";    st.rerun()

        st.markdown("---")

        if st.button("🚪  Logout",            use_container_width=True, key="nav_logout"):
            st.session_state.token     = None
            st.session_state.user_name = None
            st.session_state.page      = "landing"
            st.rerun()

    # ── PAGE CONTENT ─────────────────────────────────────
    if   page in ("overview", ) or page not in ["finance","sales","customers","chat","upload"]:
        from pages.p01_overview  import show; show()
    elif page == "finance":
        from pages.p03_finance   import show; show()
    elif page == "sales":
        from pages.p04_sales     import show; show()
    elif page == "customers":
        from pages.p05_customers import show; show()
    elif page == "chat":
        from pages.p02_chat      import show; show()
    elif page == "upload":
        from pages.p06_upload    import show; show()

# ── FALLBACK ──────────────────────────────────────────────
else:
    st.session_state.page = "landing"
    st.rerun()
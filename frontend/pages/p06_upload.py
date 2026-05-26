import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
from api_client import upload_csv, get_upload_history

def show():
    import streamlit as st
    st.markdown("""
<style>
@media (max-width: 480px) {
    [data-testid="stMainBlockContainer"] { padding: 12px 10px !important; }
    [data-testid="stMetric"] { min-width: 0 !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 17px !important; }
    h3 { font-size: 15px !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 140px !important; flex: 1 !important; }
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] { padding: 16px 12px !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; }
}
/* Accessibility — improved text contrast */
[data-testid="stMetricLabel"] { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: #F4F1EB !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
/* Chart labels contrast */
.element-container p { color: #C8C8D8 !important; }
/* Selectbox contrast */
[data-testid="stSelectbox"] label { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stSelectbox"] > div > div {
    background: #1C1A3A !important;
    border-color: rgba(123,92,245,0.3) !important;
    color: #F4F1EB !important;
}
/* File uploader contrast */
[data-testid="stFileUploader"] label { color: #C8C8D8 !important; }
/* Dataframe contrast */
[data-testid="stDataFrame"] { border: 1px solid rgba(123,92,245,0.15) !important; }
/* Focus indicators for keyboard navigation */
button:focus, input:focus, select:focus {
    outline: 2px solid #7B5CF5 !important;
    outline-offset: 2px !important;
}
</style>
""", unsafe_allow_html=True)
    render_header("Import Data")
    st.caption("Upload your CSV files. The system will validate, clean, and load them automatically.")
    st.subheader("Upload a new file")
    c1,c2 = st.columns([2,1])
    with c1:
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    with c2:
        domain = st.selectbox("Data domain", ["sales","customers","finance","marketing","products"])
    if uploaded_file and st.button("Upload & Process", type="primary"):
        with st.spinner(f"Processing {uploaded_file.name}..."):
            result = upload_csv(uploaded_file.read(), uploaded_file.name, domain)
        if result:
            report = result["quality_report"]
            st.success(f"Upload complete — Job ID: {result['job_id']}")
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Received",   report["records_received"])
            c2.metric("Accepted",   report["records_accepted"])
            c3.metric("Rejected",   report["records_rejected"],  delta=f"-{report['records_rejected']}"  if report["records_rejected"] > 0  else None, delta_color="inverse")
            c4.metric("Duplicates", report["duplicates_found"],  delta=f"-{report['duplicates_found']}"  if report["duplicates_found"] > 0  else None, delta_color="inverse")
            c5.metric("Anomalies",  report["anomalies_found"],   delta=f"-{report['anomalies_found']}"   if report["anomalies_found"] > 0   else None, delta_color="inverse")
            rate = report["records_accepted"] / report["records_received"] * 100
            st.progress(rate / 100, text=f"Acceptance rate: {rate:.1f}%")
    st.markdown("---")
    st.subheader("Recent uploads")
    for job in (get_upload_history() or []):
        icon = "✅" if job["status"] == "success" else "⚠️" if job["status"] == "partial" else "❌"
        with st.expander(f"{icon} {job['file']} — {job['domain'].title()} — {job['timestamp']}"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Status", job["status"].title())
            c2.metric("Records accepted", job["records_accepted"])
            c3.metric("Domain", job["domain"].title())
    render_footer()
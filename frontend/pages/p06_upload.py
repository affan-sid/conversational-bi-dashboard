import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
from api_client import upload_csv, get_upload_history

def show():
    render_header("Upload Data")
    st.caption("Upload your CSV files. The system will validate, clean, and load them automatically.")
    st.subheader("Upload a new file")

    if "upload_key" not in st.session_state:
        st.session_state.upload_key = 0
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None

    c1,c2 = st.columns([2,1])
    with c1:
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], key=f"uploader_{st.session_state.upload_key}")
    with c2:
        domain = st.selectbox("Data domain", ["sales","customers","finance","marketing","products"])

    if st.session_state.upload_result:
        result = st.session_state.upload_result
        report = result["quality_report"]
        st.success(f"Upload complete — {result['filename']} processed successfully.")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Received",   report["records_received"])
        c2.metric("Accepted",   report["records_accepted"])
        c3.metric("Rejected",   report["records_rejected"],  delta=f"-{report['records_rejected']}"  if report["records_rejected"] > 0  else None, delta_color="inverse")
        c4.metric("Duplicates", report["duplicates_found"],  delta=f"-{report['duplicates_found']}"  if report["duplicates_found"] > 0  else None, delta_color="inverse")
        c5.metric("Anomalies",  report["anomalies_found"],   delta=f"-{report['anomalies_found']}"   if report["anomalies_found"] > 0   else None, delta_color="inverse")
        rate = report["records_accepted"] / report["records_received"] * 100
        st.progress(rate / 100, text=f"Acceptance rate: {rate:.1f}%")

    if uploaded_file and st.button("Upload & Process", type="primary"):
        with st.spinner(f"Processing {uploaded_file.name}..."):
            result = upload_csv(uploaded_file.read(), uploaded_file.name, domain)
        if result:
            result["filename"] = uploaded_file.name
            st.session_state.upload_result = result
            st.session_state.upload_key += 1
            st.rerun()

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

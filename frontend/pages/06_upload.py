import streamlit as st
from api_client import upload_csv, get_upload_history
from config import CURRENCY_SYMBOL

st.title("Upload Data")
st.caption("Upload your CSV files here. The system will validate, clean, and load them automatically.")

# ── UPLOAD FORM ───────────────────────────────────────────
st.subheader("Upload a new file")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Supported files: sales, customers, finance, marketing, products"
    )
with col2:
    domain = st.selectbox(
        "Data domain",
        ["sales", "customers", "finance", "marketing", "products"],
        help="Select what type of data this file contains"
    )

if uploaded_file and st.button("Upload & Process", type="primary"):
    with st.spinner(f"Processing {uploaded_file.name}..."):
        result = upload_csv(
            file_bytes=uploaded_file.read(),
            filename=uploaded_file.name,
            domain=domain
        )
    if result:
        report = result["quality_report"]
        st.success(f"Upload complete — Job ID: {result['job_id']}")

        # Quality report
        st.subheader("Quality report")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Received",  report["records_received"])
        c2.metric("Accepted",  report["records_accepted"])
        c3.metric("Rejected",  report["records_rejected"],
                  delta=f"-{report['records_rejected']}" if report["records_rejected"] > 0 else None,
                  delta_color="inverse")
        c4.metric("Duplicates", report["duplicates_found"],
                  delta=f"-{report['duplicates_found']}" if report["duplicates_found"] > 0 else None,
                  delta_color="inverse")
        c5.metric("Anomalies",  report["anomalies_found"],
                  delta=f"-{report['anomalies_found']}" if report["anomalies_found"] > 0 else None,
                  delta_color="inverse")

        acceptance_rate = report["records_accepted"] / report["records_received"] * 100
        st.progress(acceptance_rate / 100, text=f"Acceptance rate: {acceptance_rate:.1f}%")
    else:
        st.error("Upload failed. Check the backend connection.")

st.markdown("---")

# ── UPLOAD HISTORY ────────────────────────────────────────
st.subheader("Recent uploads")

history = get_upload_history()
if history:
    for job in history:
        status = job["status"]
        icon   = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"
        with st.expander(f"{icon} {job['file']} — {job['domain'].title()} — {job['timestamp']}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Status",           status.title())
            c2.metric("Records accepted", job["records_accepted"])
            c3.metric("Domain",           job["domain"].title())
else:
    st.info("No uploads yet. Upload your first file above.")

st.markdown("---")

# ── EXPECTED FILE GUIDE ───────────────────────────────────
st.subheader("Expected file formats")
st.caption("Your files should contain at minimum the following columns:")

guide = {
    "Sales":     "Order Number, BuyerID, Purchase Date, Gross Sales, Discount$, Sales Channel, Order Status",
    "Customers": "Client_ID, Customer Name, Email Address, PhoneNumber, Client Type, Town, Nation, SignupDate",
    "Finance":   "Txn ID, Txn Date, TxnType, Category Name, Amount CAD, Paid Via",
    "Marketing": "Row ID, Campaign Ref, Day, Impr., Clicks, Leads Generated, Conv, Spend (CAD), Revenue Attr.",
    "Products":  "SKU_ID, Product Name, Category, Retail Price, Unit Cost, IsActive",
}
for domain_name, columns in guide.items():
    st.markdown(f"**{domain_name}:** `{columns}`")

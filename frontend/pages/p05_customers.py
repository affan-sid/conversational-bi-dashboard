import streamlit as st
import pandas as pd
from api_client import get_customers
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD, PERIOD_API_MAP

def show():
    st.title("Customers")
    period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))
    data = get_customers(PERIOD_API_MAP.get(period, "last_3_months"))
    if not data: st.error("Could not load customer data."); return
    if data.get("has_data") is False:
        st.info("📁 No customer data uploaded yet. Upload your customers CSV to see this dashboard.")
        if st.button("Go to Upload →", key="cust_upload_btn"):
            st.session_state.page = "upload"; st.rerun()
        return
    kpis = data["kpis"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Customers", f"{kpis['total_customers']}")
    c2.metric("Active Customers", f"{kpis['active_customers']}")
    c3.metric("Repeat Rate", f"{kpis['repeat_rate']:.1f}%",
              delta="Low" if kpis["repeat_rate"] < 30 else None, delta_color="inverse")
    c4.metric("Churn Rate", f"{kpis.get('churn_rate', 0):.1f}%")
    c1,c2 = st.columns(2)
    c1.metric("Avg Customer Lifetime Value", f"{CURRENCY_SYMBOL}{kpis.get('avg_clv', 0):,.0f}")
    c2.metric("New This Period", f"{kpis.get('new_this_period', 0)}")
    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Revenue by segment")
        df_seg = pd.DataFrame(data["revenue_by_segment"]).set_index("segment")
        st.bar_chart(df_seg["revenue"])
        for row in data["revenue_by_segment"]:
            st.caption(f"• {row['segment']}: {row['customers']:,} customers — {CURRENCY_SYMBOL}{row['revenue']:,.0f}")
    with c_right:
        st.subheader("Customer growth")
        if data.get("growth_trend"):
            df_growth = pd.DataFrame(data["growth_trend"]).set_index("month")
            st.line_chart(df_growth[["new_customers","churned"]])
        else:
            st.info("No growth trend data available.")
    st.markdown("---")
    st.subheader("Top customers by revenue")
    df_top = pd.DataFrame(data["top_customers"])
    df_top["total_revenue"] = df_top["total_revenue"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,.0f}")
    df_top.columns = ["ID","Name","Revenue","Orders","Segment"]
    st.dataframe(df_top, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.subheader("High churn risk customers")
    for c in data["churn_risk_list"]:
        color = "🔴" if c["churn_risk_score"] >= 0.9 else "🟡"
        st.warning(f"{color} **{c['full_name']}** — Risk: {c['churn_risk_score']:.2f} — Last order: {c['last_order_days_ago']} days ago")

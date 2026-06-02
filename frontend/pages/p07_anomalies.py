import streamlit as st
import sys, os

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from header_footer import render_header, render_footer
import api_client as _ac

get_anomalies      = _ac.get_anomalies
get_recommendations = _ac.get_recommendations

_SEVERITY_ICON  = {"high": "🔴", "medium": "🟡", "low": "🔵"}
_DOMAIN_ICON    = {"sales": "💰", "finance": "💳", "marketing": "📣", "customers": "👥"}
_FEATURE_LABELS = {
    "spend": "Ad Spend",
    "conversions": "Conversions",
    "revenue_attributed": "Attributed Revenue",
    "impressions": "Impressions",
    "clicks": "Clicks",
    "leads": "Leads",
}


def show():
    render_header("Anomaly Insights")

    with st.spinner("Scanning for anomalies…"):
        data = get_anomalies()

    if data is None:
        st.error("Could not connect to backend.")
        render_footer()
        return

    anomalies = data.get("anomalies", [])
    summary   = data.get("summary", {})

    # ── SUMMARY METRICS ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Anomalies",    summary.get("total",  0))
    c2.metric("🔴 High Severity",   summary.get("high",   0))
    c3.metric("🟡 Medium Severity", summary.get("medium", 0))
    c4.metric("🔵 Low Severity",    summary.get("low",    0))

    if not anomalies:
        st.success("✅ No anomalies detected in your current data.")
        render_footer()
        return

    st.markdown("---")

    # ── RECOMMENDED ACTIONS ──────────────────────────────────────────
    with st.spinner("Generating recommendations…"):
        recs = get_recommendations(anomalies) or []

    if recs:
        st.subheader("Recommended Actions")
        for i, rec in enumerate(recs[:3], 1):
            conf  = rec.get("confidence", 0) if isinstance(rec, dict) else 0
            rtype = rec.get("type", "").replace("_", " ").title() if isinstance(rec, dict) else f"Recommendation {i}"
            text  = rec.get("recommendation", str(rec)) if isinstance(rec, dict) else str(rec)
            conf_badge = f"  —  Confidence: {conf*100:.0f}%" if conf else ""
            with st.expander(f"**{i}. {rtype}**{conf_badge}", expanded=(i == 1)):
                st.write(text)
        st.markdown("---")

    # ── ANOMALY CARDS ────────────────────────────────────────────────
    st.subheader(f"Detected Anomalies ({len(anomalies)})")

    for a in anomalies:
        sev   = a.get("severity", "low")
        dom   = a.get("domain", "")
        icon  = _SEVERITY_ICON.get(sev, "⚪")
        dicon = _DOMAIN_ICON.get(dom, "📊")
        title = f"{icon} {dicon} {a.get('message', 'Anomaly detected')}"

        with st.expander(title, expanded=(sev == "high")):
            left, right = st.columns(2)

            with left:
                unit = a.get("unit", "")
                if a.get("value") is not None:
                    st.markdown(f"**Actual value:** {unit}{a['value']:,.2f}")
                if a.get("expected") is not None:
                    st.markdown(f"**Expected value:** {unit}{a['expected']:,.2f}")
                if a.get("deviation_pct") is not None:
                    st.markdown(f"**Deviation:** {a['deviation_pct']:+.1f}%")
                if a.get("z_score") is not None:
                    st.markdown(f"**Anomaly score:** {a['z_score']:.2f}")

            with right:
                st.markdown(f"**Domain:** {dom.title()}")
                st.markdown(f"**Severity:** {sev.title()}")
                method = a.get("method", "N/A").replace("_", " ").title()
                st.markdown(f"**Method:** {method}")
                if a.get("date"):
                    st.markdown(f"**Date:** {a['date']}")

            if a.get("explanation"):
                st.markdown("**Explanation:**")
                st.info(a["explanation"])

            shap_feats = a.get("shap_top_features")
            if shap_feats:
                st.markdown("**SHAP Feature Drivers** *(what caused this anomaly)*")
                feat_vals  = a.get("feature_values", {})
                feat_means = a.get("feature_means", {})
                for feat, shap_val in shap_feats:
                    label   = _FEATURE_LABELS.get(feat, feat.replace("_", " ").title())
                    raw_val = feat_vals.get(feat)
                    mean_val = feat_means.get(feat)
                    if raw_val is not None and mean_val is not None:
                        direction = "▲ above normal" if raw_val > mean_val else "▼ below normal"
                        val_str   = f" ({raw_val:,.0f} vs avg {mean_val:,.0f})"
                    else:
                        direction = "▲ high" if shap_val < 0 else "▼ low"
                        val_str   = ""
                    st.markdown(f"- **{label}**: {direction}{val_str}")

            if a.get("recommendation"):
                st.caption(f"Quick action: {a['recommendation']}")

    render_footer()

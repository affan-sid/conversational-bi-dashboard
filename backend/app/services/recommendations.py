def generate_recommendations(anomalies):
    recommendations = []
    seen = set()

    for a in anomalies:
        atype = a.get("type", "")

        if "revenue_drop" in atype and "revenue_drop" not in seen:
            seen.add("revenue_drop")
            recommendations.append({
                "type": "revenue_drop",
                "confidence": 0.88,
                "recommendation": (
                    "Revenue is declining — compare this period's figures by channel and product "
                    "against last quarter to pinpoint exactly where the drop is occurring. "
                    "Once you identify the underperforming segment, check whether the cause is "
                    "lower volume, lower prices, or higher returns, as each requires a different fix. "
                    "In parallel, increase budget or promotional activity on your strongest-performing "
                    "channel to offset the decline while you address the root cause."
                ),
            })

        if ("cashflow" in atype or "cash" in atype) and "cashflow" not in seen:
            seen.add("cashflow")
            recommendations.append({
                "type": "cashflow",
                "confidence": 0.82,
                "recommendation": (
                    "Cash flow volatility has been detected — calculate your current runway by dividing "
                    "your cash balance by your average monthly burn rate to understand how much time you have. "
                    "If runway is below three months, immediately contact your top customers with outstanding "
                    "invoices and offer a small early-payment discount to accelerate cash collection. "
                    "At the same time, defer all non-essential spending and review recurring subscriptions "
                    "you can pause to stabilise your cash position."
                ),
            })

        if "expense" in atype and "expense" not in seen:
            seen.add("expense")
            recommendations.append({
                "type": "expense_spike",
                "confidence": 0.79,
                "recommendation": (
                    "An unusual expense spike was detected — pull up your expense breakdown for this "
                    "category and compare it against the last three months to check if this is a "
                    "one-off payment or a growing trend. "
                    "If it is recurring overspend, negotiate a supplier discount or switch to a "
                    "lower-cost provider; a 10% reduction on a $5,000/month line saves $6,000 per year. "
                    "Flag this category for monthly review so you catch future spikes before they "
                    "impact your cash position."
                ),
            })

        if ("pattern_anomaly" in atype or "marketing" in atype) and "marketing" not in seen:
            seen.add("marketing")
            shap_feats = a.get("shap_top_features") or []
            driver_text = ""
            if shap_feats:
                top = shap_feats[0][0].replace("_", " ")
                driver_text = f" The primary driver was {top} —"
            recommendations.append({
                "type": "marketing_anomaly",
                "confidence": 0.75,
                "recommendation": (
                    f"Unusual marketing activity was detected.{driver_text} run a channel-by-channel "
                    "ROI comparison to identify which campaigns are underperforming and pause any with "
                    "ROI below 1.0x immediately. "
                    "Reallocate that freed budget to your highest-ROI campaign for the next two weeks. "
                    "Set a specific review date to measure whether the reallocation improves overall "
                    "marketing efficiency before making permanent budget changes."
                ),
            })

        if "data_quality" in atype and "data_quality" not in seen:
            seen.add("data_quality")
            recommendations.append({
                "type": "data_quality",
                "confidence": 0.95,
                "recommendation": (
                    "Data quality issues were found in your marketing records — rows where conversions "
                    "exceed clicks are mathematically impossible and indicate a tracking or import error. "
                    "Export the affected rows, identify the source of the discrepancy (often a "
                    "double-count in your CRM or ad platform), and correct the data before using it "
                    "for campaign decisions. "
                    "Clean data is the foundation of reliable insights; resolve this before your next "
                    "budget review."
                ),
            })

    recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return recommendations

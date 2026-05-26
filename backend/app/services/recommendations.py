def generate_recommendations(anomalies):
    recommendations = []
    for a in anomalies:
        if "revenue_drop" in a["type"]:
            recommendations.append(
                "Revenue is declining — compare this period's figures by channel and product against last quarter to pinpoint exactly where the drop is occurring. "
                "Once you identify the underperforming segment, check whether the cause is lower volume, lower prices, or higher returns, as each requires a different fix. "
                "In parallel, increase budget or promotional activity on your strongest-performing channel to offset the decline while you address the root cause."
            )
        if "cashflow" in a["type"]:
            recommendations.append(
                "Cash flow volatility has been detected — calculate your current runway by dividing your cash balance by your average monthly burn rate to understand how much time you have. "
                "If runway is below three months, immediately contact your top customers with outstanding invoices and offer a small early-payment discount to accelerate cash collection. "
                "At the same time, defer all non-essential spending and review recurring subscriptions you can pause to stabilise your cash position."
            )

    return list(set(recommendations))

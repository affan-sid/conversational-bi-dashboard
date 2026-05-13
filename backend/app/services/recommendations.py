def generate_recommendations(anomalies):
    recommendations = []
    for a in anomalies:
        if "revenue_drop" in a["type"]:
            recommendations.append(
                "Revenue is declining. Review recent campaigns and pricing strategy."
            )
        if "cashflow" in a["type"]:
            recommendations.append(
                "Cash flow volatility detected. Monitor operational expenses."
            )

    return list(set(recommendations))
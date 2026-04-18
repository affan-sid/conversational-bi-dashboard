
-- Monthly revenue
SELECT substr(order_date,1,7) AS month, ROUND(SUM(total_amount),2) AS revenue
FROM orders
WHERE status='completed'
GROUP BY substr(order_date,1,7)
ORDER BY month;

-- Monthly expenses
SELECT substr(date,1,7) AS month, ROUND(SUM(amount),2) AS expenses
FROM transactions
WHERE type='expense'
GROUP BY substr(date,1,7)
ORDER BY month;

-- Top 5 customers by revenue
SELECT c.full_name, ROUND(cm.total_revenue,2) AS total_revenue, cm.total_orders
FROM customer_metrics cm
JOIN customers c ON c.customer_id = cm.customer_id
ORDER BY cm.total_revenue DESC
LIMIT 5;

-- Best-selling products
SELECT p.product_name, SUM(oi.quantity) AS units_sold, ROUND(SUM(oi.line_total),2) AS sales_value
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status='completed'
GROUP BY p.product_name
ORDER BY sales_value DESC;

-- Campaign ROI
SELECT c.campaign_name,
       ROUND(SUM(mp.spend),2) AS spend,
       ROUND(SUM(mp.revenue_attributed),2) AS revenue,
       ROUND((SUM(mp.revenue_attributed)-SUM(mp.spend))/NULLIF(SUM(mp.spend),0), 2) AS roi
FROM marketing_performance mp
JOIN campaigns c ON c.campaign_id = mp.campaign_id
GROUP BY c.campaign_name
ORDER BY roi DESC;

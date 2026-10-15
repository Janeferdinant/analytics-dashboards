-- KPI queries for the retail dashboard; definitions match docs/metrics-dictionary.md.

-- name: monthly_kpis
SELECT year_month,
       round(sum(amount) FILTER (WHERE NOT is_return), 2) AS gross_revenue,
       round(coalesce(sum(amount) FILTER (WHERE is_return), 0), 2) AS returns_value,
       round(sum(amount) FILTER (WHERE NOT is_return)
             - coalesce(sum(amount) FILTER (WHERE is_return), 0), 2) AS net_revenue,
       count(*) FILTER (WHERE NOT is_return) AS orders,
       round(sum(amount) FILTER (WHERE NOT is_return)
             / count(*) FILTER (WHERE NOT is_return), 2) AS aov,
       count(DISTINCT customer_key) FILTER (WHERE NOT is_return) AS active_customers
FROM fact_invoice
GROUP BY year_month
ORDER BY year_month;

-- name: repeat_customer_rate
SELECT round(count(*) FILTER (WHERE n_orders >= 2) * 1.0 / count(*), 4) AS repeat_customer_rate
FROM (SELECT customer_key, count(*) AS n_orders
      FROM fact_invoice
      WHERE NOT is_return AND customer_key IS NOT NULL
      GROUP BY customer_key);

-- name: cohort_retention
-- Share of each first-order-month cohort that ordered again k months later.
WITH activity AS (
    SELECT DISTINCT i.customer_key, c.cohort_month, i.year_month
    FROM fact_invoice i JOIN dim_customer c USING (customer_key)
    WHERE NOT i.is_return
),
sized AS (
    SELECT cohort_month, count(*) AS cohort_size
    FROM dim_customer GROUP BY cohort_month
)
SELECT a.cohort_month,
       (year(strptime(a.year_month || '-01', '%Y-%m-%d'))
        - year(strptime(a.cohort_month || '-01', '%Y-%m-%d'))) * 12
       + month(strptime(a.year_month || '-01', '%Y-%m-%d'))
       - month(strptime(a.cohort_month || '-01', '%Y-%m-%d')) AS months_since,
       count(*) AS active,
       s.cohort_size,
       round(count(*) * 1.0 / s.cohort_size, 4) AS retention
FROM activity a JOIN sized s USING (cohort_month)
GROUP BY a.cohort_month, months_since, s.cohort_size
ORDER BY a.cohort_month, months_since;

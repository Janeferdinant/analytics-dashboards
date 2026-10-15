-- Star schema for Online Retail II. Input: table clean_lines (output of retail.clean()).
-- Grain of fact_sales_line: one invoice line (a sale, or a return on a cancellation invoice).

CREATE OR REPLACE TABLE dim_country AS
SELECT row_number() OVER (ORDER BY country) AS country_key, country
FROM (SELECT DISTINCT country FROM clean_lines);

CREATE OR REPLACE TABLE dim_product AS
WITH ranked AS (
    SELECT stock_code, description,
           row_number() OVER (
               PARTITION BY stock_code ORDER BY count(*) DESC, description
           ) AS rn
    FROM clean_lines
    WHERE description IS NOT NULL
    GROUP BY stock_code, description
)
SELECT row_number() OVER (ORDER BY c.stock_code) AS product_key,
       c.stock_code,
       r.description  -- the most frequent description for the code
FROM (SELECT DISTINCT stock_code FROM clean_lines) c
LEFT JOIN ranked r ON r.stock_code = c.stock_code AND r.rn = 1;

CREATE OR REPLACE TABLE dim_date AS
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
       d AS date,
       year(d) AS year,
       month(d) AS month,
       strftime(d, '%Y-%m') AS year_month,
       dayname(d) AS weekday,
       isodow(d) AS iso_weekday
FROM (SELECT DISTINCT CAST(invoice_ts AS DATE) AS d FROM clean_lines);

-- Identified customers only; a customer's first order month defines their cohort.
CREATE OR REPLACE TABLE dim_customer AS
WITH orders AS (
    SELECT customer_id, CAST(invoice_ts AS DATE) AS d, country, invoice_no
    FROM clean_lines
    WHERE customer_id IS NOT NULL AND NOT is_return
),
first_order AS (
    SELECT customer_id, min(d) AS first_order_date FROM orders GROUP BY customer_id
),
main_country AS (
    SELECT customer_id, arg_max(country, n) AS country
    FROM (SELECT customer_id, country, count(DISTINCT invoice_no) AS n
          FROM orders GROUP BY customer_id, country)
    GROUP BY customer_id
)
SELECT row_number() OVER (ORDER BY f.customer_id) AS customer_key,
       f.customer_id,
       f.first_order_date,
       strftime(f.first_order_date, '%Y-%m') AS cohort_month,
       m.country AS main_country
FROM first_order f JOIN main_country m USING (customer_id);

CREATE OR REPLACE TABLE fact_sales_line AS
SELECT l.line_id,
       l.invoice_no,
       CAST(strftime(l.invoice_ts, '%Y%m%d') AS INTEGER) AS date_key,
       l.invoice_ts,
       p.product_key,
       c.customer_key,            -- NULL for guest lines (no customer id in the source)
       k.country_key,
       l.quantity,
       l.unit_price,
       l.line_amount,             -- quantity * unit_price (negative on returns)
       l.is_return
FROM clean_lines l
JOIN dim_product p ON p.stock_code = l.stock_code
JOIN dim_country k ON k.country = l.country
LEFT JOIN dim_customer c ON c.customer_id = l.customer_id;

-- One row per invoice: the grain the dashboards use for orders, AOV and retention.
CREATE OR REPLACE TABLE fact_invoice AS
SELECT f.invoice_no,
       min(f.date_key) AS date_key,
       strftime(min(f.invoice_ts), '%Y-%m') AS year_month,
       any_value(f.customer_key) AS customer_key,
       any_value(f.country_key) AS country_key,
       bool_or(f.is_return) AS is_return,
       sum(abs(f.line_amount)) AS amount,   -- gross value for sales, returned value for returns
       sum(abs(f.quantity)) AS units
FROM fact_sales_line f
GROUP BY f.invoice_no;

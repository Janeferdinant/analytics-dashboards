"""Export-ready cleaned CSVs for rebuilding the dashboards in a BI tool (see docs/)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .paths import EXPORTS

DICTIONARY: list[tuple[str, str, str, str]] = [
    # file, column, type, meaning
    ("retail_fact_sales_line.csv", "line_id", "int", "Invoice line id (unique)"),
    ("retail_fact_sales_line.csv", "invoice_no", "text", "Invoice number; a leading C is a return"),
    ("retail_fact_sales_line.csv", "date_key", "int", "yyyymmdd; joins retail_dim_date.date_key"),
    ("retail_fact_sales_line.csv", "invoice_ts", "datetime", "Invoice timestamp"),
    ("retail_fact_sales_line.csv", "product_key", "int", "Joins retail_dim_product.product_key"),
    (
        "retail_fact_sales_line.csv",
        "customer_key",
        "int",
        "Joins retail_dim_customer; blank = guest",
    ),
    ("retail_fact_sales_line.csv", "country_key", "int", "Joins retail_dim_country.country_key"),
    ("retail_fact_sales_line.csv", "quantity", "int", "Units (negative on returns)"),
    ("retail_fact_sales_line.csv", "unit_price", "decimal", "Price per unit, GBP"),
    ("retail_fact_sales_line.csv", "line_amount", "decimal", "quantity x unit_price, GBP"),
    ("retail_fact_sales_line.csv", "is_return", "bool", "True on cancellation invoices"),
    ("retail_invoice_flat.csv", "invoice_no", "text", "One row per invoice"),
    ("retail_invoice_flat.csv", "year_month", "text", "yyyy-mm of the invoice"),
    ("retail_invoice_flat.csv", "invoice_date", "date", "Invoice date (first line)"),
    ("retail_invoice_flat.csv", "country", "text", "Country on the invoice"),
    ("retail_invoice_flat.csv", "customer_id", "int", "Source customer id; blank = guest"),
    ("retail_invoice_flat.csv", "cohort_month", "text", "First-order month of the customer"),
    ("retail_invoice_flat.csv", "is_return", "bool", "True on cancellation invoices"),
    ("retail_invoice_flat.csv", "amount", "decimal", "Absolute invoice value, GBP"),
    ("retail_invoice_flat.csv", "units", "int", "Absolute units on the invoice"),
    ("retail_cohort_retention.csv", "cohort_month", "text", "First-order month"),
    ("retail_cohort_retention.csv", "months_since", "int", "Months after the cohort month"),
    ("retail_cohort_retention.csv", "retention", "decimal", "Share of cohort active that month"),
    ("hr_tidy.csv", "left", "int", "1 when Attrition = Yes"),
    ("marketing_tidy.csv", "converted", "int", "1 when the client subscribed (y = yes)"),
    ("marketing_tidy.csv", "year_month", "text", "Campaign month; year inferred from row order"),
]


def export_retail(con, out: Path = EXPORTS) -> list[Path]:
    from .retail import kpi_queries

    out.mkdir(parents=True, exist_ok=True)
    written = []
    tables = {
        "retail_fact_sales_line.csv": "fact_sales_line",
        "retail_dim_date.csv": "dim_date",
        "retail_dim_product.csv": "dim_product",
        "retail_dim_customer.csv": "dim_customer",
        "retail_dim_country.csv": "dim_country",
    }
    for filename, table in tables.items():
        path = out / filename
        con.execute(f"COPY (SELECT * FROM {table}) TO '{path.as_posix()}' (HEADER, DELIMITER ',')")
        written.append(path)
    flat = out / "retail_invoice_flat.csv"
    con.execute(
        f"""
        COPY (
          SELECT i.invoice_no, i.year_month, d.date AS invoice_date, k.country,
                 c.customer_id, c.cohort_month, i.is_return, round(i.amount, 2) AS amount, i.units
          FROM fact_invoice i
          JOIN dim_country k USING (country_key)
          JOIN dim_date d USING (date_key)
          LEFT JOIN dim_customer c USING (customer_key)
          ORDER BY i.invoice_no
        ) TO '{flat.as_posix()}' (HEADER, DELIMITER ',')
        """
    )
    written.append(flat)
    cohort = out / "retail_cohort_retention.csv"
    con.execute(f"COPY ({kpi_queries()['cohort_retention']}) TO '{cohort.as_posix()}' (HEADER)")
    written.append(cohort)
    return written


def export_frame(df: pd.DataFrame, name: str, out: Path = EXPORTS) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    df.to_csv(path, index=False)
    return path


def write_dictionary(out: Path = EXPORTS) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / "data_dictionary.csv"
    pd.DataFrame(DICTIONARY, columns=["file", "column", "type", "meaning"]).to_csv(
        path, index=False
    )
    return path

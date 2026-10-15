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
    ("retail_fact_sales_line.csv", "is_return", "int", "1 on cancellation invoices, else 0"),
    ("retail_invoice_flat.csv", "invoice_no", "text", "One row per invoice"),
    ("retail_invoice_flat.csv", "year_month", "text", "yyyy-mm of the invoice"),
    ("retail_invoice_flat.csv", "invoice_date", "date", "Invoice date (first line)"),
    ("retail_invoice_flat.csv", "country", "text", "Country on the invoice"),
    ("retail_invoice_flat.csv", "customer_id", "int", "Source customer id; blank = guest"),
    ("retail_invoice_flat.csv", "cohort_month", "text", "First-order month of the customer"),
    ("retail_invoice_flat.csv", "is_return", "int", "1 on cancellation invoices, else 0"),
    ("retail_invoice_flat.csv", "amount", "decimal", "Absolute invoice value, GBP"),
    ("retail_invoice_flat.csv", "units", "int", "Absolute units on the invoice"),
    ("retail_cohort_retention.csv", "cohort_month", "text", "First-order month"),
    ("retail_cohort_retention.csv", "months_since", "int", "Months after the cohort month"),
    ("retail_cohort_retention.csv", "retention", "decimal", "Share of cohort active that month"),
    ("hr_tidy.csv", "left", "int", "1 when Attrition = Yes"),
    ("hr_tidy.csv", "*_order", "int", "Numeric sort key for the ordered column of the same name"),
    (
        "marketing_tidy.csv",
        "client_id",
        "int",
        "Row number after de-duplication (no id in the source)",
    ),
    ("marketing_tidy.csv", "attempts", "int", "Contact attempts, 6 means 6 or more"),
    ("marketing_tidy.csv", "campaign", "int", "Contact attempts in this campaign (raw)"),
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
        select = "* REPLACE (CAST(is_return AS INTEGER) AS is_return)" if "fact" in table else "*"
        con.execute(
            f"COPY (SELECT {select} FROM {table}) TO '{path.as_posix()}' (HEADER, DELIMITER ',')"
        )
        written.append(path)
    flat = out / "retail_invoice_flat.csv"
    con.execute(
        f"""
        COPY (
          SELECT i.invoice_no, i.year_month, d.date AS invoice_date, k.country,
                 c.customer_id, c.cohort_month, CAST(i.is_return AS INTEGER) AS is_return,
                 round(i.amount, 2) AS amount, i.units
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


def _order_column(series: pd.Series, order: list[str]) -> pd.Series:
    return series.astype(str).map({label: i + 1 for i, label in enumerate(order)})


def hr_for_bi(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy HR table plus numeric sort columns (BI tools sort text alphabetically otherwise)."""
    from . import hr as hr_mod

    out = df.copy()
    for col, order in [
        ("age_band", hr_mod.AGE_ORDER),
        ("tenure", hr_mod.TENURE_ORDER),
        ("salary_band", hr_mod.SALARY_ORDER),
        ("job_satisfaction", hr_mod.SATISFACTION_ORDER),
        ("job_support", hr_mod.LEVELS3),
        ("work_life_balance", ["Difficult", "Medium", "Easy"]),
        ("distance_to_work", ["Close", "Medium", "Far"]),
        ("training_programs", ["None", "1 to 3", "4 to 6", "7+"]),
    ]:
        out[f"{col}_order"] = _order_column(out[col], order)
    return out


def marketing_for_bi(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy marketing table plus a client id and numeric sort columns."""
    from . import marketing as mk_mod

    out = df.copy()
    out.insert(0, "client_id", range(1, len(out) + 1))
    out["age_band_order"] = _order_column(out["age_band"], mk_mod.AGE_LABELS)
    out["prior_outcome_order"] = _order_column(out["prior_outcome"], list(mk_mod.POUTCOME.values()))
    return out


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


def reference_values(exports: Path = EXPORTS) -> dict[str, list[tuple[str, str]]]:
    """Recompute headline numbers from the exported CSVs only (pandas, independent of the pipeline).

    The owner compares these with the numbers in a rebuilt BI workbook to confirm the build.
    """
    inv = pd.read_csv(exports / "retail_invoice_flat.csv")
    sales, rets = inv[inv["is_return"] == 0], inv[inv["is_return"] == 1]
    gross, returned = sales["amount"].sum(), rets["amount"].sum()
    per_customer = (
        sales.dropna(subset=["customer_id"]).groupby("customer_id")["invoice_no"].nunique()
    )

    def net(frame: pd.DataFrame) -> float:
        s_, r_ = frame[frame["is_return"] == 0], frame[frame["is_return"] == 1]
        return float(s_["amount"].sum() - r_["amount"].sum())

    uk = inv[inv["country"] == "United Kingdom"]
    y2011 = inv[inv["year_month"].between("2011-01", "2011-12")]
    retail = [
        ("Gross revenue (GBP)", f"{gross:,.2f}"),
        ("Returns value (GBP)", f"{returned:,.2f}"),
        ("Net revenue (GBP)", f"{gross - returned:,.2f}"),
        ("Orders", f"{sales['invoice_no'].nunique():,}"),
        ("Average order value (GBP)", f"{gross / sales['invoice_no'].nunique():,.2f}"),
        ("Customers (identified)", f"{len(per_customer):,}"),
        ("Repeat-customer rate", f"{(per_customer >= 2).mean():.4f}"),
        ("Net revenue, United Kingdom only (GBP)", f"{net(uk):,.2f}"),
        ("Net revenue, Jan to Dec 2011 (GBP)", f"{net(y2011):,.2f}"),
        ("Net revenue, November 2010 (GBP)", f"{net(inv[inv['year_month'] == '2010-11']):,.2f}"),
    ]
    hr = pd.read_csv(exports / "hr_tidy.csv")
    sat = hr.groupby("job_satisfaction")["left"].agg(["size", "mean"])
    hr_rows = [
        ("Respondents", f"{len(hr):,}"),
        ("Left (Attrition = Yes)", f"{int(hr['left'].sum()):,}"),
        ("Attrition rate", f"{hr['left'].mean():.4f}"),
    ] + [
        (f"Attrition rate, job satisfaction = {k}", f"{v['mean']:.4f} (n = {int(v['size'])})")
        for k, v in sat.iterrows()
    ]
    mk = pd.read_csv(exports / "marketing_tidy.csv")
    prior = mk.groupby("prior_outcome")["converted"].agg(["size", "mean"])
    mk_rows = [
        ("Clients contacted", f"{len(mk):,}"),
        ("Conversions", f"{int(mk['converted'].sum()):,}"),
        ("Conversion rate", f"{mk['converted'].mean():.4f}"),
        ("Contact attempts (sum of campaign)", f"{int(mk['campaign'].sum()):,}"),
        ("Contacts per conversion", f"{mk['campaign'].sum() / mk['converted'].sum():.2f}"),
    ] + [
        (f"Conversion rate, earlier outcome = {k}", f"{v['mean']:.4f} (n = {int(v['size'])})")
        for k, v in prior.iterrows()
    ]
    return {"Retail": retail, "HR": hr_rows, "Marketing": mk_rows}


def write_reference_markdown(path: Path, values: dict[str, list[tuple[str, str]]]) -> Path:
    lines = [
        "# Reference values for checking a rebuilt BI workbook",
        "",
        "Generated by `analytics-dashboards build` from the exported CSVs only. With no filters",
        "applied, a correctly rebuilt Tableau Public or Power BI workbook should show these",
        "numbers.",
        "",
    ]
    for title, rows in values.items():
        lines += [f"## {title}", "", "| Measure | Value |", "|---|---|"]
        lines += [f"| {name} | {value} |" for name, value in rows]
        lines.append("")
    path.write_text(chr(10).join(lines), "utf-8", newline=chr(10))
    return path

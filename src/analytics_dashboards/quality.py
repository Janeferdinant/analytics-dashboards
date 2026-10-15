"""Data-quality checks. Each check returns a CheckResult; the CLI and tests both use them."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import hr as hr_mod
from . import marketing as mk_mod


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _check(name: str, passed: bool, detail: str = "") -> CheckResult:
    return CheckResult(name, bool(passed), detail)


def retail_checks(lines: pd.DataFrame, con) -> list[CheckResult]:
    """Checks on cleaned retail lines (pandas) and on the DuckDB star schema."""
    out: list[CheckResult] = []
    sales = lines[~lines["is_return"]]
    returns = lines[lines["is_return"]]
    out.append(_check("line_id is unique", lines["line_id"].is_unique))
    required = ["invoice_no", "stock_code", "quantity", "unit_price", "invoice_ts", "country"]
    nulls = int(lines[required].isna().sum().sum())
    out.append(_check("no nulls in required columns", nulls == 0, f"{nulls} nulls"))
    out.append(_check("unit price is positive", bool((lines["unit_price"] > 0).all())))
    out.append(_check("sales have positive quantity", bool((sales["quantity"] > 0).all())))
    out.append(_check("returns have negative quantity", bool((returns["quantity"] < 0).all())))
    out.append(
        _check(
            "return flag matches the C invoice prefix",
            bool((lines["is_return"] == lines["invoice_no"].str.startswith("C")).all()),
        )
    )
    per_invoice = lines.groupby("invoice_no")["country"].nunique()
    out.append(_check("each invoice has one country", bool((per_invoice == 1).all())))
    out.append(
        _check(
            "invoice dates fall in the documented range",
            lines["invoice_ts"].min() >= pd.Timestamp("2009-12-01")
            and lines["invoice_ts"].max() < pd.Timestamp("2011-12-10"),
            f"{lines['invoice_ts'].min()} to {lines['invoice_ts'].max()}",
        )
    )
    orphans = con.execute(
        """
        SELECT
          (SELECT count(*) FROM fact_sales_line f
             LEFT JOIN dim_product p USING (product_key) WHERE p.product_key IS NULL)
        + (SELECT count(*) FROM fact_sales_line f
             LEFT JOIN dim_country c USING (country_key) WHERE c.country_key IS NULL)
        + (SELECT count(*) FROM fact_sales_line f
             LEFT JOIN dim_date d USING (date_key) WHERE d.date_key IS NULL)
        + (SELECT count(*) FROM fact_sales_line f
             LEFT JOIN dim_customer c USING (customer_key)
             WHERE f.customer_key IS NOT NULL AND c.customer_key IS NULL)
        """
    ).fetchone()[0]
    out.append(_check("no orphan foreign keys in the star schema", orphans == 0, f"{orphans}"))
    line_total = round(float(lines["line_amount"].sum()), 2)
    fact_total = round(con.execute("SELECT sum(line_amount) FROM fact_sales_line").fetchone()[0], 2)
    out.append(
        _check("fact table reconciles to cleaned lines", line_total == fact_total, f"{fact_total}")
    )
    inv_net = con.execute(
        "SELECT sum(CASE WHEN is_return THEN -amount ELSE amount END) FROM fact_invoice"
    ).fetchone()[0]
    out.append(
        _check(
            "invoice net value equals line net value",
            abs(inv_net - line_total) < 0.05,
            f"{inv_net:.2f} vs {line_total:.2f}",
        )
    )
    bad_cohort = con.execute(
        """
        SELECT count(*) FROM fact_invoice i JOIN dim_customer c USING (customer_key)
        WHERE NOT i.is_return AND i.year_month < c.cohort_month
        """
    ).fetchone()[0]
    out.append(_check("no order before the customer's cohort month", bad_cohort == 0))
    return out


def hr_checks(df: pd.DataFrame) -> list[CheckResult]:
    out = [
        _check("respondent_id is unique", df["respondent_id"].is_unique),
        _check("attrition is Yes/No", set(df["attrition"]) == {"Yes", "No"}),
        _check(
            "left flag matches attrition", bool((df["left"] == (df["attrition"] == "Yes")).all())
        ),
        _check("no missing values", int(df.isna().sum().sum()) == 0),
        _check("age bands are known", set(df["age_band"].astype(str)) <= set(hr_mod.AGE_ORDER)),
        _check("salary bands are mapped", df["salary_band"].notna().all()),
        _check("tenure bands are mapped", df["tenure"].notna().all()),
        _check(
            "sector groups are at least the minimum size or 'Other sectors'",
            bool((df.groupby("sector_group").size() >= hr_mod.MIN_GROUP).all()),
        ),
    ]
    return out


def marketing_checks(df: pd.DataFrame) -> list[CheckResult]:
    months = df["year_month"].drop_duplicates().tolist()
    return [
        _check("no duplicate rows", not df.duplicated().any()),
        _check("converted is 0/1", set(df["converted"]) <= {0, 1}),
        _check("campaign contacts are >= 1", bool((df["campaign"] >= 1).all())),
        _check("inferred timeline starts May 2008", months[0] == "2008-05", months[0]),
        _check("inferred timeline ends Nov 2010", months[-1] == "2010-11", months[-1]),
        _check("inferred months are in chronological order", months == sorted(months)),
        _check(
            "no earlier contact (previous=0) implies pdays=999 and no prior outcome",
            bool(
                (
                    (df["previous"] > 0)
                    | ((df["pdays"] == 999) & (df["poutcome"] == "nonexistent"))
                ).all()
            ),
        ),
        _check(
            "prior outcome 'nonexistent' implies previous=0 (the reverse is how we flag clients)",
            bool(((df["poutcome"] != "nonexistent") | (df["previous"] == 0)).all()),
        ),
        _check(
            "documented anomaly: pdays=999 also occurs with earlier contacts (info, not a failure)",
            True,
            f"{int(((df['pdays'] == 999) & (df['previous'] > 0)).sum()):,} clients; "
            "the dashboards use previous>0, never pdays, to flag prior contact",
        ),
        _check("no clients over 100 years old", bool((df["age"] < 100).all())),
        _check("age bands cover every client", df["age_band"].notna().all()),
        _check("prior outcome labels mapped", df["prior_outcome"].notna().all()),
        _check("rate is a probability", 0 <= mk_mod.conversion_rate(df) <= 1),
    ]

"""Precompute the static JSON that each dashboard page loads (no server, no live queries).

The pages compute every KPI in the browser from compact columnar tables, so filters are exact.
Each file also carries an `expected` block (computed here with pandas/DuckDB) that the browser
tests compare against the numbers the page renders.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import hr as hr_mod
from . import marketing as mk_mod
from .paths import DASH_DATA

TOP_COUNTRIES = 10
TOP_PRODUCTS = 100


def _write(name: str, payload: dict, out: Path = DASH_DATA) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), "utf-8")
    return path


def _codes(series: pd.Series, levels: list[str]) -> list[int]:
    index = {level: i for i, level in enumerate(levels)}
    return [index[str(v)] for v in series]


def _dim(series: pd.Series, levels: list[str] | None = None) -> dict:
    if levels is None:
        levels = sorted(series.astype(str).unique())
    return {"levels": levels, "codes": _codes(series, levels)}


def build_retail(lines: pd.DataFrame, con, out: Path = DASH_DATA) -> Path:
    from .retail import kpi_queries

    queries = kpi_queries()
    monthly = con.execute(queries["monthly_kpis"]).df()
    months = monthly["year_month"].tolist()
    gross = lines.loc[~lines["is_return"]].groupby("country")["line_amount"].sum()
    top = gross.sort_values(ascending=False).head(TOP_COUNTRIES).index.tolist()
    countries = [*top, "Other countries"]
    country_idx = {c: i for i, c in enumerate(countries)}

    inv = con.execute(
        """
        SELECT i.year_month, k.country, c.customer_id, c.cohort_month, i.is_return, i.amount
        FROM fact_invoice i
        JOIN dim_country k USING (country_key)
        LEFT JOIN dim_customer c USING (customer_key)
        ORDER BY i.invoice_no
        """
    ).df()
    month_idx = {m: i for i, m in enumerate(months)}
    cust_ids = sorted(inv["customer_id"].dropna().astype(int).unique())
    cust_idx = {c: i for i, c in enumerate(cust_ids)}
    invoices = {
        "m": [month_idx[m] for m in inv["year_month"]],
        "c": [country_idx.get(c, len(top)) for c in inv["country"]],
        "cu": [cust_idx[int(c)] if pd.notna(c) else -1 for c in inv["customer_id"]],
        "co": [month_idx[m] if isinstance(m, str) else -1 for m in inv["cohort_month"]],
        "k": [int(r) for r in inv["is_return"]],
        "v": [round(float(v), 2) for v in inv["amount"]],
    }

    sales = lines[~lines["is_return"]].copy()
    sales["year_month"] = sales["invoice_ts"].dt.strftime("%Y-%m")
    best = sales.groupby("stock_code")["line_amount"].sum().nlargest(TOP_PRODUCTS).index.tolist()
    in_best = sales[sales["stock_code"].isin(best)]
    names = in_best.groupby("stock_code")["description"].agg(
        lambda s: s.mode().iat[0] if s.notna().any() else ""
    )
    prod_idx = {code: i for i, code in enumerate(best)}
    agg = (
        in_best.assign(c=in_best["country"].map(lambda x: country_idx.get(x, len(top))))
        .groupby(["stock_code", "year_month", "c"])
        .agg(rev=("line_amount", "sum"), units=("quantity", "sum"))
        .reset_index()
    )
    products = {
        "items": [[code, str(names[code]).title()] for code in best],
        "rows": [
            [
                prod_idx[r.stock_code],
                month_idx[r.year_month],
                int(r.c),
                round(float(r.rev), 2),
                int(r.units),
            ]
            for r in agg.itertuples()
        ],
    }
    gross_total = float(monthly["gross_revenue"].sum())
    returns_total = float(monthly["returns_value"].sum())
    orders = int(monthly["orders"].sum())
    expected = {
        "gross_revenue": round(gross_total, 2),
        "returns_value": round(returns_total, 2),
        "net_revenue": round(gross_total - returns_total, 2),
        "orders": orders,
        "aov": round(gross_total / orders, 2),
        "repeat_customer_rate": float(con.execute(queries["repeat_customer_rate"]).fetchone()[0]),
        "identified_customers": len(cust_ids),
    }
    payload = {
        "meta": {
            "title": "Online Retail II",
            "currency": "GBP",
            "first_date": str(lines["invoice_ts"].min().date()),
            "last_date": str(lines["invoice_ts"].max().date()),
        },
        "months": months,
        "countries": countries,
        "invoices": invoices,
        "products": products,
        "expected": expected,
    }
    return _write("retail.json", payload, out)


def build_hr(df: pd.DataFrame, out: Path = DASH_DATA) -> Path:
    dims = {
        "sector": _dim(df["sector_group"]),
        "gender": _dim(df["gender"]),
        "age": _dim(df["age_band"], hr_mod.AGE_ORDER),
        "degree": _dim(df["degree"]),
        "salary": _dim(df["salary_band"], hr_mod.SALARY_ORDER),
        "tenure": _dim(df["tenure"], hr_mod.TENURE_ORDER),
        "job_satisfaction": _dim(df["job_satisfaction"], hr_mod.SATISFACTION_ORDER),
        "job_support": _dim(df["job_support"], hr_mod.LEVELS3),
        "work_life_balance": _dim(df["work_life_balance"], ["Difficult", "Medium", "Easy"]),
        "training": _dim(df["training_programs"], ["None", "1 to 3", "4 to 6", "7+"]),
        "overtime_pay": _dim(df["payment_overtime"], ["No overtime", "Paid", "Unpaid"]),
        "recognition": _dim(df["recognition"], ["No", "Yes"]),
        "fair_promotion": _dim(df["fair_promotion"], ["No", "Yes"]),
        "job_stability": _dim(df["job_stability"], ["No", "Yes"]),
        "distance": _dim(df["distance_to_work"], ["Close", "Medium", "Far"]),
    }
    payload = {
        "meta": {"title": "Employee attrition survey", "n": len(df)},
        "left": [int(v) for v in df["left"]],
        "dims": dims,
        "expected": {
            "respondents": len(df),
            "leavers": int(df["left"].sum()),
            "attrition_rate": round(hr_mod.attrition_rate(df), 4),
        },
    }
    return _write("hr.json", payload, out)


def build_marketing(df: pd.DataFrame, out: Path = DASH_DATA) -> Path:
    months = sorted(df["year_month"].unique())
    dims = {
        "job": _dim(df["job"]),
        "age": _dim(df["age_band"], mk_mod.AGE_LABELS),
        "education": _dim(df["education"]),
        "channel": _dim(df["contact"]),
        "prior": _dim(df["prior_outcome"], list(mk_mod.POUTCOME.values())),
        "housing": _dim(df["housing"]),
        "loan": _dim(df["loan"]),
    }
    payload = {
        "meta": {"title": "Bank Marketing", "n": len(df)},
        "months": months,
        "m": _codes(df["year_month"], months),
        "y": [int(v) for v in df["converted"]],
        "att": [int(v) for v in df["campaign"]],
        "dims": dims,
        "expected": {
            "clients": len(df),
            "conversions": int(df["converted"].sum()),
            "conversion_rate": round(mk_mod.conversion_rate(df), 4),
            "contacts_per_conversion": round(mk_mod.contacts_per_conversion(df), 1),
        },
    }
    return _write("marketing.json", payload, out)

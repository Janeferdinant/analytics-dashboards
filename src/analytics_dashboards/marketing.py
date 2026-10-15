"""Bank Marketing (UCI, bank-additional-full): clean a direct-marketing campaign table.

One row is one client in a phone campaign of a Portuguese bank. The UCI documentation says the
records are ordered by date (May 2008 to November 2010) but the file has only month and
weekday, so the year is *inferred from row order* (it increments whenever the month number
goes backwards). The inference is checked in the tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .paths import RAW

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
AGE_BINS = [0, 29, 39, 49, 59, 200]
AGE_LABELS = ["Under 30", "30 to 39", "40 to 49", "50 to 59", "60+"]
POUTCOME = {"nonexistent": "Not contacted before", "failure": "Prior: no", "success": "Prior: yes"}
MAX_ATTEMPTS = 6  # contact counts above this are pooled as "6+"


def load_raw(folder: Path = RAW / "marketing") -> pd.DataFrame:
    return pd.read_csv(folder / "bank-additional" / "bank-additional-full.csv", sep=";")


def infer_years(months: pd.Series, first_year: int = 2008) -> pd.Series:
    """Infer the calendar year of each row from the order of the month column."""
    number = months.map({m: i + 1 for i, m in enumerate(MONTHS)})
    if number.isna().any():
        raise ValueError("unknown month label")
    year = first_year + (number.diff().fillna(0) < 0).cumsum()
    return year.astype(int)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy table with readable labels and the documented derived columns."""
    df = raw.copy()
    df.columns = [c.replace(".", "_") for c in df.columns]
    df = df.drop_duplicates().reset_index(drop=True)
    df["converted"] = (df["y"] == "yes").astype(int)
    df["year"] = infer_years(df["month"])
    df["month_no"] = df["month"].map({m: i + 1 for i, m in enumerate(MONTHS)})
    df["year_month"] = df["year"].astype(str) + "-" + df["month_no"].astype(str).str.zfill(2)
    df["age_band"] = pd.cut(df["age"], AGE_BINS, labels=AGE_LABELS)
    df["prior_outcome"] = df["poutcome"].map(POUTCOME)
    # pdays == 999 is ambiguous (it also appears with earlier contacts), so use `previous`.
    df["previously_contacted"] = (df["previous"] > 0).astype(int)
    df["attempts"] = df["campaign"].clip(upper=MAX_ATTEMPTS)
    df["job"] = df["job"].str.replace(".", "", regex=False)
    df["education"] = df["education"].str.replace(".", " ", regex=False)
    df = df.drop(columns=["y"])
    # 'duration' (call length) is only known after the call; it is excluded from dashboards.
    return df


def conversion_rate(df: pd.DataFrame) -> float:
    """Metric: converted clients / clients contacted."""
    return float(df["converted"].mean()) if len(df) else float("nan")


def contacts_per_conversion(df: pd.DataFrame) -> float:
    """Metric: contact attempts made (sum of `campaign`) / converted clients."""
    conversions = int(df["converted"].sum())
    return float(df["campaign"].sum() / conversions) if conversions else float("nan")


def rate_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = df.groupby(column, observed=True)["converted"].agg(["size", "sum", "mean"])
    grouped.columns = ["clients", "conversions", "conversion_rate"]
    return grouped.reset_index()


__all__ = [
    "clean",
    "contacts_per_conversion",
    "conversion_rate",
    "infer_years",
    "load_raw",
    "np",
    "rate_by",
]

"""Online Retail II: load, clean (pandas) and model (DuckDB SQL) a retail sales dataset.

Cleaning decisions are deliberately explicit: every rule is a named step that reports how many
rows it removed, so the numbers can be audited in docs/runs/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .paths import INTERIM, RAW

RAW_COLUMNS = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_ts",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}

COUNTRY_FIXES = {"EIRE": "Ireland", "RSA": "South Africa", "USA": "United States"}


def load_raw(folder: Path = RAW / "retail", use_cache: bool = True) -> pd.DataFrame:
    """Read both worksheets of the UCI workbook (slow: ~1M rows); cache as CSV under data/."""
    cache = INTERIM / "retail_raw.csv.gz"
    if use_cache and cache.exists():
        return pd.read_csv(
            cache, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"]
        )
    sheets = pd.read_excel(
        folder / "online_retail_II.xlsx",
        sheet_name=None,
        dtype={"Invoice": str, "StockCode": str},
    )
    frame = pd.concat(sheets.values(), ignore_index=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache, index=False, compression="gzip")
    return frame


@dataclass
class CleaningReport:
    """Row counts removed by each cleaning rule, in application order."""

    rows_in: int = 0
    steps: list[tuple[str, int]] = field(default_factory=list)
    rows_out: int = 0

    def add(self, name: str, removed: int) -> None:
        self.steps.append((name, int(removed)))


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Return analysis-ready sales lines and a report of what each rule removed.

    Rules (in order):
      1. exact duplicate rows are dropped (keep the first);
      2. non-product stock codes (postage, fees, manual adjustments, samples) are dropped:
         a product code starts with five digits;
      3. lines with a unit price <= 0 are dropped (adjustments, free samples);
      4. lines with quantity <= 0 that are not cancellation invoices are dropped.
    Cancellation invoices (invoice number starting with C) are kept and flagged as returns.
    A missing customer id is kept as null: those lines are "guest" sales.
    """
    report = CleaningReport(rows_in=len(raw))
    df = raw.rename(columns=RAW_COLUMNS).copy()
    df["invoice_no"] = df["invoice_no"].astype(str).str.strip()
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description"] = df["description"].astype("string").str.strip()
    df["country"] = df["country"].astype(str).str.strip().replace(COUNTRY_FIXES)
    df["invoice_ts"] = pd.to_datetime(df["invoice_ts"])

    before = len(df)
    df = df.drop_duplicates()
    report.add("exact duplicate rows", before - len(df))

    before = len(df)
    df = df[df["stock_code"].str.match(r"^\d{5}")]
    report.add("non-product stock codes", before - len(df))

    before = len(df)
    df = df[df["unit_price"] > 0]
    report.add("unit price <= 0", before - len(df))

    df["is_return"] = df["invoice_no"].str.startswith("C")
    before = len(df)
    df = df[df["is_return"] | (df["quantity"] > 0)]
    report.add("non-positive quantity outside cancellation invoices", before - len(df))

    df["customer_id"] = df["customer_id"].astype("Int64")
    df["line_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    df = df.reset_index(drop=True)
    df.insert(0, "line_id", range(1, len(df) + 1))
    report.rows_out = len(df)
    return df, report


def _read_sql(name: str) -> str:
    from .paths import SQL_DIR

    return (SQL_DIR / name).read_text(encoding="utf-8")


def build_star(lines: pd.DataFrame):
    """Build the star schema in an in-memory DuckDB database and return the connection."""
    import duckdb

    con = duckdb.connect(":memory:")
    con.register("clean_lines", lines)
    con.execute(_read_sql("retail_star.sql"))
    return con


def kpi_queries() -> dict[str, str]:
    """Parse retail_kpis.sql into {name: sql}; each block starts with '-- name: <id>'."""
    queries: dict[str, str] = {}
    name = None
    buf: list[str] = []
    for line in _read_sql("retail_kpis.sql").splitlines():
        if line.startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buf).strip()
            name, buf = line.split(":", 1)[1].strip(), []
        elif name:
            buf.append(line)
    if name:
        queries[name] = "\n".join(buf).strip()
    return queries

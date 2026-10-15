from __future__ import annotations

import pandas as pd
import pytest

RETAIL_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]


@pytest.fixture()
def raw_retail() -> pd.DataFrame:
    """Nine hand-made raw rows that exercise every cleaning rule."""
    rows = [
        ("500001", "85123A", "WHITE HEART", 6, "2010-01-04 09:00", 2.50, 17850.0, "United Kingdom"),
        (
            "500001",
            "71053",
            "METAL LANTERN",
            2,
            "2010-01-04 09:00",
            3.00,
            17850.0,
            "United Kingdom",
        ),
        # exact duplicate of the row above
        (
            "500001",
            "71053",
            "METAL LANTERN",
            2,
            "2010-01-04 09:00",
            3.00,
            17850.0,
            "United Kingdom",
        ),
        # non-product stock code
        ("500002", "POST", "POSTAGE", 1, "2010-01-05 10:00", 18.0, 12583.0, "France"),
        # unit price 0
        ("500003", "22423", "CAKESTAND", 3, "2010-01-06 11:00", 0.0, None, "EIRE"),
        # guest sale (no customer id)
        ("500004", "22423", "CAKESTAND", 1, "2010-02-07 12:00", 12.0, None, "EIRE"),
        # return on a cancellation invoice
        (
            "C500005",
            "85123A",
            "WHITE HEART",
            -2,
            "2010-02-08 13:00",
            2.50,
            17850.0,
            "United Kingdom",
        ),
        ("500006", "84879", "BIRD", 4, "2010-02-09 14:00", 1.50, 12583.0, "France"),
        # negative quantity on a normal invoice
        ("500007", "84879", "BIRD", -1, "2010-02-10 15:00", 1.50, 12583.0, "France"),
    ]
    df = pd.DataFrame(rows, columns=RETAIL_COLUMNS)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df

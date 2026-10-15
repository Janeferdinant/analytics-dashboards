from __future__ import annotations

import pandas as pd

from analytics_dashboards import export
from analytics_dashboards import marketing as mk
from test_marketing import make_raw


def test_order_column_maps_labels_to_one_based_positions():
    series = pd.Series(["b", "a", "c", "a"])
    assert export._order_column(series, ["a", "b", "c"]).tolist() == [2, 1, 3, 1]


def test_marketing_export_adds_client_id_and_sort_keys():
    out = export.marketing_for_bi(mk.clean(make_raw()))
    assert out["client_id"].tolist() == list(range(1, len(out) + 1))
    assert out["age_band_order"].notna().all()
    assert out["prior_outcome_order"].notna().all()
    assert set(out["prior_outcome_order"]) == {1, 2, 3}


def test_reference_values_are_recomputed_from_the_csvs(tmp_path):
    pd.DataFrame(
        {
            "invoice_no": ["1", "2", "C3", "4"],
            "year_month": ["2010-11", "2011-02", "2011-02", "2011-03"],
            "invoice_date": ["2010-11-01", "2011-02-01", "2011-02-02", "2011-03-01"],
            "country": ["United Kingdom", "France", "France", "United Kingdom"],
            "customer_id": [10, 10, 10, None],
            "cohort_month": ["2010-11", "2010-11", "2010-11", None],
            "is_return": [0, 0, 1, 0],
            "amount": [100.0, 50.0, 20.0, 30.0],
            "units": [1, 1, 1, 1],
        }
    ).to_csv(tmp_path / "retail_invoice_flat.csv", index=False)
    pd.DataFrame({"left": [1, 0, 0, 1], "job_satisfaction": ["a", "a", "b", "b"]}).to_csv(
        tmp_path / "hr_tidy.csv", index=False
    )
    pd.DataFrame(
        {
            "converted": [1, 0, 0, 0],
            "campaign": [2, 1, 3, 2],
            "prior_outcome": ["x", "x", "y", "y"],
        }
    ).to_csv(tmp_path / "marketing_tidy.csv", index=False)

    values = export.reference_values(tmp_path)
    retail = dict(values["Retail"])
    assert retail["Gross revenue (GBP)"] == "180.00"
    assert retail["Returns value (GBP)"] == "20.00"
    assert retail["Net revenue (GBP)"] == "160.00"
    assert retail["Orders"] == "3"
    assert retail["Average order value (GBP)"] == "60.00"
    assert retail["Customers (identified)"] == "1"
    assert retail["Repeat-customer rate"] == "1.0000"  # customer 10 placed two orders
    assert retail["Net revenue, United Kingdom only (GBP)"] == "130.00"
    assert retail["Net revenue, Jan to Dec 2011 (GBP)"] == "60.00"  # 50 - 20 + 30
    assert dict(values["HR"])["Attrition rate"] == "0.5000"
    mk_values = dict(values["Marketing"])
    assert mk_values["Conversion rate"] == "0.2500"
    assert mk_values["Contacts per conversion"] == "8.00"


def test_reference_markdown_lists_every_section(tmp_path):
    path = export.write_reference_markdown(tmp_path / "ref.md", {"A": [("x", "1")], "B": []})
    text = path.read_text("utf-8")
    assert "## A" in text and "| x | 1 |" in text and "## B" in text


def test_dictionary_covers_every_exported_file():
    files = {row[0] for row in export.DICTIONARY}
    assert {"retail_fact_sales_line.csv", "retail_invoice_flat.csv", "hr_tidy.csv"} <= files

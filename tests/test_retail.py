from __future__ import annotations

import pytest

from analytics_dashboards import quality
from analytics_dashboards import retail as r


def test_cleaning_rules_remove_expected_rows(raw_retail):
    lines, report = r.clean(raw_retail)
    removed = dict(report.steps)
    assert removed["exact duplicate rows"] == 1
    assert removed["non-product stock codes"] == 1
    assert removed["unit price <= 0"] == 1
    assert removed["non-positive quantity outside cancellation invoices"] == 1
    assert report.rows_in == 9
    assert report.rows_out == len(lines) == 5


def test_returns_and_guests_are_kept_and_flagged(raw_retail):
    lines, _ = r.clean(raw_retail)
    assert lines["is_return"].sum() == 1
    assert lines.loc[lines["is_return"], "line_amount"].iloc[0] == pytest.approx(-5.0)
    assert lines["customer_id"].isna().sum() == 1  # the guest line is kept as null


def test_country_aliases_are_normalised(raw_retail):
    lines, _ = r.clean(raw_retail)
    assert "EIRE" not in set(lines["country"])
    assert "Ireland" in set(lines["country"])


def test_line_amount_is_quantity_times_price(raw_retail):
    lines, _ = r.clean(raw_retail)
    assert (lines["line_amount"] == (lines["quantity"] * lines["unit_price"]).round(2)).all()


def test_star_schema_kpis_match_hand_calculation(raw_retail):
    lines, _ = r.clean(raw_retail)
    con = r.build_star(lines)
    monthly = con.execute(r.kpi_queries()["monthly_kpis"]).df().set_index("year_month")
    # January: invoice 500001 -> 6*2.5 + 2*3.0 = 21.0, no returns
    assert monthly.loc["2010-01", "gross_revenue"] == pytest.approx(21.0)
    assert monthly.loc["2010-01", "orders"] == 1
    # February: sales 500004 (12.0) + 500006 (6.0) = 18.0; return C500005 = 5.0
    assert monthly.loc["2010-02", "gross_revenue"] == pytest.approx(18.0)
    assert monthly.loc["2010-02", "returns_value"] == pytest.approx(5.0)
    assert monthly.loc["2010-02", "net_revenue"] == pytest.approx(13.0)
    assert monthly.loc["2010-02", "orders"] == 2
    assert monthly.loc["2010-02", "aov"] == pytest.approx(9.0)
    # only customer 12583 ordered (identified) in February; the guest is excluded
    assert monthly.loc["2010-02", "active_customers"] == 1


def test_repeat_rate_and_cohorts(raw_retail):
    lines, _ = r.clean(raw_retail)
    con = r.build_star(lines)
    queries = r.kpi_queries()
    # each identified customer has exactly one sales invoice, so nobody repeats
    assert con.execute(queries["repeat_customer_rate"]).fetchone()[0] == 0.0
    cohorts = con.execute(queries["cohort_retention"]).df()
    assert (cohorts.loc[cohorts["months_since"] == 0, "retention"] == 1.0).all()


def test_cohort_retention_counts_a_returning_customer(raw_retail):
    extra = raw_retail.copy()
    again = extra.iloc[[0]].copy()
    again["Invoice"] = "500099"
    again["InvoiceDate"] = again["InvoiceDate"] + (
        extra["InvoiceDate"].max() - again["InvoiceDate"]
    )
    lines, _ = r.clean(extra._append(again, ignore_index=True))
    con = r.build_star(lines)
    cohorts = con.execute(r.kpi_queries()["cohort_retention"]).df()
    row = cohorts[(cohorts["cohort_month"] == "2010-01") & (cohorts["months_since"] == 1)]
    assert row["retention"].iloc[0] == 1.0  # customer 17850 came back in February
    rate = con.execute(r.kpi_queries()["repeat_customer_rate"]).fetchone()[0]
    assert rate == pytest.approx(0.5)


def test_quality_checks_pass_on_clean_fixture(raw_retail):
    lines, _ = r.clean(raw_retail)
    con = r.build_star(lines)
    failed = [c.name for c in quality.retail_checks(lines, con) if not c.passed]
    assert failed == []


def test_quality_checks_catch_a_bad_price(raw_retail):
    lines, _ = r.clean(raw_retail)
    con = r.build_star(lines)
    lines.loc[0, "unit_price"] = -1.0
    failed = [c.name for c in quality.retail_checks(lines, con) if not c.passed]
    assert "unit price is positive" in failed

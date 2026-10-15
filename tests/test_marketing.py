from __future__ import annotations

import pandas as pd
import pytest

from analytics_dashboards import marketing as mk
from analytics_dashboards import quality


def make_raw() -> pd.DataFrame:
    months = ["may", "may", "jun", "nov", "mar", "mar", "apr", "dec", "mar"]
    n = len(months)
    return pd.DataFrame(
        {
            "age": [25, 35, 45, 55, 65, 30, 41, 52, 29],
            "job": [
                "admin.",
                "blue-collar",
                "admin.",
                "retired",
                "retired",
                "services",
                "admin.",
                "technician",
                "student",
            ],
            "marital": ["single"] * n,
            "education": [
                "university.degree",
                "basic.9y",
                "high.school",
                "basic.4y",
                "unknown",
                "high.school",
                "university.degree",
                "basic.6y",
                "unknown",
            ],
            "default": ["no"] * n,
            "housing": ["yes", "no", "yes", "no", "yes", "no", "yes", "no", "yes"],
            "loan": ["no"] * n,
            "contact": ["cellular", "telephone"] * 4 + ["cellular"],
            "month": months,
            "day_of_week": ["mon"] * n,
            "duration": [100] * n,
            "campaign": [1, 2, 3, 10, 1, 1, 2, 1, 4],
            "pdays": [999, 999, 999, 6, 999, 3, 999, 999, 999],
            "previous": [0, 0, 1, 2, 0, 1, 0, 0, 0],
            "poutcome": [
                "nonexistent",
                "nonexistent",
                "failure",
                "success",
                "nonexistent",
                "success",
                "nonexistent",
                "nonexistent",
                "nonexistent",
            ],
            "emp.var.rate": [1.1] * n,
            "cons.price.idx": [93.0] * n,
            "cons.conf.idx": [-40.0] * n,
            "euribor3m": [4.8] * n,
            "nr.employed": [5000.0] * n,
            "y": ["no", "yes", "no", "yes", "no", "yes", "no", "no", "yes"],
        }
    )


def test_year_is_inferred_from_month_order():
    series = pd.Series(["may", "dec", "mar", "dec", "mar"])
    assert list(mk.infer_years(series)) == [2008, 2008, 2009, 2009, 2010]


def test_unknown_month_raises():
    with pytest.raises(ValueError):
        mk.infer_years(pd.Series(["may", "foo"]))


def test_clean_derives_documented_columns():
    df = mk.clean(make_raw())
    assert list(df["year_month"].drop_duplicates()) == [
        "2008-05",
        "2008-06",
        "2008-11",
        "2009-03",
        "2009-04",
        "2009-12",
        "2010-03",
    ]
    assert df["converted"].tolist() == [0, 1, 0, 1, 0, 1, 0, 0, 1]
    assert df["attempts"].max() == mk.MAX_ATTEMPTS  # 10 contacts are pooled into "6+"
    assert set(df["prior_outcome"]) == {"Not contacted before", "Prior: no", "Prior: yes"}
    assert df.loc[2, "previously_contacted"] == 1


def test_metrics_match_hand_calculation():
    df = mk.clean(make_raw())
    assert mk.conversion_rate(df) == pytest.approx(4 / 9)
    # 4 conversions; contact attempts total 1+2+3+10+1+1+2+1+4 = 25
    assert mk.contacts_per_conversion(df) == pytest.approx(25 / 4)


def test_contacts_per_conversion_is_nan_without_conversions():
    df = mk.clean(make_raw())
    df["converted"] = 0
    value = mk.contacts_per_conversion(df)
    assert value != value  # NaN


def test_rate_by_prior_outcome():
    df = mk.clean(make_raw())
    by = mk.rate_by(df, "prior_outcome").set_index("prior_outcome")
    assert by.loc["Prior: yes", "clients"] == 2
    assert by.loc["Prior: yes", "conversion_rate"] == pytest.approx(1.0)


def test_quality_check_flags_a_broken_timeline():
    df = mk.clean(make_raw())
    results = {c.name: c.passed for c in quality.marketing_checks(df)}
    assert results["inferred timeline starts May 2008"]
    assert not results["inferred timeline ends Nov 2010"]  # the fixture ends in 2010-03

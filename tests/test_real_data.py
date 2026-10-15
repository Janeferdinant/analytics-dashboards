"""Checks on the real datasets. Needs `make data`; skipped by the default (fast) test run."""

from __future__ import annotations

import pytest

from analytics_dashboards import hr, marketing, quality, retail
from analytics_dashboards.paths import RAW

pytestmark = pytest.mark.data

if not (RAW / "hr").exists():
    pytest.skip("raw data not downloaded", allow_module_level=True)


@pytest.fixture(scope="module")
def retail_lines():
    lines, _ = retail.clean(retail.load_raw())
    return lines


def test_retail_quality_checks_pass(retail_lines):
    con = retail.build_star(retail_lines)
    failed = [c.name for c in quality.retail_checks(retail_lines, con) if not c.passed]
    assert failed == []


def test_retail_net_revenue_reconciles_between_sql_and_pandas(retail_lines):
    con = retail.build_star(retail_lines)
    monthly = con.execute(retail.kpi_queries()["monthly_kpis"]).df()
    pandas_net = float(retail_lines["line_amount"].sum())
    assert monthly["net_revenue"].sum() == pytest.approx(pandas_net, abs=1.0)


def test_hr_dataset_shape_and_rate():
    df = hr.clean(hr.load_raw())
    assert len(df) == 1191
    assert [c.name for c in quality.hr_checks(df) if not c.passed] == []
    assert hr.attrition_rate(df) == pytest.approx(515 / 1191)


def test_marketing_dataset_checks():
    df = marketing.clean(marketing.load_raw())
    assert [c.name for c in quality.marketing_checks(df) if not c.passed] == []
    assert marketing.conversion_rate(df) == pytest.approx(0.11266, abs=1e-4)

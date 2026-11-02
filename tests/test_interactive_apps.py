from __future__ import annotations

from pathlib import Path

from apps.dash_app import (
    compute_hr_metrics,
    compute_marketing_metrics,
    compute_retail_metrics,
    load_hr_data,
    load_marketing_data,
    load_retail_data,
)
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent


def test_dash_retail_callbacks():
    data = load_retail_data()
    net, orders, aov, fig = compute_retail_metrics(data, "All")
    assert "£" in net
    assert int(orders.replace(",", "")) > 0
    assert "£" in aov
    assert len(fig.data) > 0

    net_uk, orders_uk, _, _ = compute_retail_metrics(data, "United Kingdom")
    assert "£" in net_uk
    assert int(orders_uk.replace(",", "")) <= int(orders.replace(",", ""))


def test_dash_hr_callbacks():
    data = load_hr_data()
    tot, leavers, rate, fig = compute_hr_metrics(data, "All")
    assert int(tot.replace(",", "")) == 1191
    assert int(leavers.replace(",", "")) == 515
    assert rate == "43.2%"
    assert len(fig.data) > 0


def test_dash_marketing_callbacks():
    data = load_marketing_data()
    tot, conv, rate, fig = compute_marketing_metrics(data, "All")
    assert int(tot.replace(",", "")) == 41176
    assert int(conv.replace(",", "")) == 4639
    assert rate == "11.27%"
    assert len(fig.data) > 0


def test_streamlit_pages_smoke():
    app_file = str(ROOT / "apps" / "streamlit_app.py")
    at = AppTest.from_file(app_file, default_timeout=30)
    at.run()
    assert not at.exception, f"Retail page failed: {at.exception}"

    # HR Attrition page
    at.radio(key="app_page").set_value("HR Attrition").run()
    assert not at.exception, f"HR page failed: {at.exception}"

    # Marketing page
    at.radio(key="app_page").set_value("Marketing Campaigns").run()
    assert not at.exception, f"Marketing page failed: {at.exception}"

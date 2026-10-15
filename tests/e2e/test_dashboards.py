"""Browser checks for the three dashboards (Playwright, headless Chromium).

Run with `make e2e`. They need docs/data/*.json (run `make build` first). Each page is checked at
390 px and 1280 px for: no console or page errors, no horizontal scrolling, KPI tiles that match
the numbers the pandas/DuckDB pipeline computed, working filters, drill-downs and keyboard use.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import threading
from pathlib import Path

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")

DOCS = Path(__file__).resolve().parents[2] / "docs"
pytestmark = pytest.mark.e2e
PAGES = ["retail", "hr", "marketing"]
WIDTHS = [390, 1280]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass


@pytest.fixture(scope="module")
def base_url():
    handler = functools.partial(_Quiet, directory=str(DOCS))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright_sync.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def filter_select(o, label: str):
    """The <select> inside the filter bar whose label text starts with `label`."""
    return o.page.locator(".filters label", has_text=label).locator("select").first


def expected(name: str) -> dict:
    return json.loads((DOCS / "data" / f"{name}.json").read_text("utf-8"))["expected"]


class Opened:
    def __init__(self, browser, url, width):
        self.context = browser.new_context(viewport={"width": width, "height": 900})
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("requestfailed", lambda r: self.errors.append("request failed " + r.url))
        self.page.goto(url)
        self.page.wait_for_selector(".tile .value")
        self.page.wait_for_selector(".card svg")

    def tile(self, label: str) -> str:
        return self.page.inner_text(f'.tile[aria-label="{label}"] .value')

    def close(self):
        self.context.close()


@pytest.fixture()
def open_page(browser, base_url):
    opened: list[Opened] = []

    def _open(name: str, width: int = 1280) -> Opened:
        o = Opened(browser, f"{base_url}/{name}.html", width)
        opened.append(o)
        return o

    yield _open
    for o in opened:
        o.close()


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", PAGES)
def test_page_is_clean_and_responsive(open_page, name, width):
    o = open_page(name, width)
    o.page.wait_for_timeout(300)
    assert o.errors == []
    overflow = o.page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0
    widest = o.page.evaluate(
        "Math.max(...[...document.querySelectorAll('svg')].map(s => s.getBoundingClientRect().right))"
    )
    assert widest <= width
    assert o.page.locator("h1").count() == 1
    assert o.page.locator("svg").count() >= 3


@pytest.mark.parametrize("name", PAGES)
def test_every_chart_has_a_data_table(open_page, name):
    o = open_page(name, 1280)
    buttons = o.page.locator("button:has-text('Data table')")
    assert buttons.count() >= 3
    buttons.first.click()
    assert o.page.locator(".tablewrap:not([hidden]) table tbody tr").count() > 0


def test_retail_kpis_match_pipeline(open_page):
    o = open_page("retail")
    exp = expected("retail")
    got = o.page.evaluate("window.__retailKpis")
    assert got["net"] == pytest.approx(exp["net_revenue"], abs=0.5)
    assert got["gross"] == pytest.approx(exp["gross_revenue"], abs=0.5)
    assert got["ret"] == pytest.approx(exp["returns_value"], abs=0.5)
    assert got["orders"] == exp["orders"]
    assert got["aov"] == pytest.approx(exp["aov"], abs=0.01)
    assert got["custs"] == exp["identified_customers"]
    assert got["rep"] / got["custs"] == pytest.approx(exp["repeat_customer_rate"], abs=1e-4)
    assert o.tile("Orders") == f"{exp['orders']:,}"
    assert o.tile("Net revenue").startswith("£18.")


def test_retail_country_filters_partition_the_total(open_page):
    o = open_page("retail")
    exp = expected("retail")
    options = o.page.locator("select").first.locator("option").all_inner_texts()
    assert options[0] == "All countries"
    total = 0
    for label in options[1:]:
        o.page.locator("select").first.select_option(label=label)
        total += o.page.evaluate("window.__retailKpis.orders")
    assert total == exp["orders"]


def test_retail_month_drilldown_and_reset(open_page):
    o = open_page("retail")
    svg = o.page.locator('svg[aria-label^="Line chart of net revenue"]')
    box = svg.bounding_box()
    o.page.mouse.click(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.5)
    assert o.page.locator(".chip:has-text('Drill-down month')").count() == 1
    o.page.get_by_role("button", name="Reset filters").click()
    assert o.page.locator(".chip").count() == 0


def test_retail_country_bar_click_filters_everything(open_page):
    o = open_page("retail")
    o.page.locator('svg[aria-label^="Bar chart of net revenue by country"] g.mark').first.click()
    assert o.page.locator(".chip:has-text('Country: United Kingdom')").count() == 1
    assert o.page.evaluate("window.__retailKpis.orders") < expected("retail")["orders"]


def test_retail_date_range_and_customer_type(open_page):
    o = open_page("retail")
    filter_select(o, "From month").select_option(label="Jan 2011")
    filter_select(o, "To month").select_option(label="Dec 2011")
    year = o.page.evaluate("window.__retailKpis.net")
    assert 0 < year < expected("retail")["net_revenue"]
    filter_select(o, "Customers").select_option("guest")
    assert o.tile("Customers (identified)") == "n/a"


def test_keyboard_use_on_line_chart_and_bars(open_page):
    o = open_page("retail")
    chart = o.page.locator('svg[aria-label^="Line chart of net revenue"]')
    chart.focus()
    o.page.keyboard.press("ArrowLeft")
    assert o.page.locator(".tooltip.on").count() == 1
    o.page.keyboard.press("Enter")
    assert o.page.locator(".chip:has-text('Drill-down month')").count() == 1
    bar = o.page.locator('svg[aria-label^="Bar chart of net revenue by country"] g.mark').nth(1)
    bar.focus()
    assert o.page.locator(".tooltip.on").count() == 1
    o.page.keyboard.press("Enter")
    assert o.page.locator(".chip:has-text('Country:')").count() == 1
    assert o.errors == []


def test_heatmap_keyboard_navigation(open_page):
    o = open_page("retail")
    heat = o.page.locator('svg[aria-label^="Heatmap"]')
    heat.focus()
    o.page.keyboard.press("ArrowRight")
    o.page.keyboard.press("ArrowDown")
    assert o.page.locator(".tooltip.on").count() == 1


def test_hr_kpis_filters_and_drilldown(open_page):
    o = open_page("hr")
    exp = expected("hr")
    got = o.page.evaluate("window.__hrKpis")
    assert got["cnt"] == exp["respondents"]
    assert got["left"] == exp["leavers"]
    assert round(got["rate"], 4) == exp["attrition_rate"]
    assert o.tile("Attrition rate") == f"{exp['attrition_rate'] * 100:.1f}%"
    total = 0
    for label in filter_select(o, "Gender").locator("option").all_inner_texts()[1:]:
        filter_select(o, "Gender").select_option(label=label)
        total += o.page.evaluate("window.__hrKpis.cnt")
    assert total == exp["respondents"]
    o.page.get_by_role("button", name="Reset filters").click()
    o.page.locator('svg[aria-label^="Bar chart of attrition"] g.mark').first.click()
    assert o.page.locator(".chip:has-text('Job satisfaction')").count() == 1
    assert o.page.evaluate("window.__hrKpis.cnt") < exp["respondents"]
    o.page.locator('svg[aria-label^="Column chart"] g.mark').first.click()
    assert o.page.locator(".chip").count() == 2


def test_marketing_kpis_filters_and_drilldown(open_page):
    o = open_page("marketing")
    exp = expected("marketing")
    got = o.page.evaluate("window.__mkKpis")
    assert got["cl"] == exp["clients"]
    assert got["cv"] == exp["conversions"]
    assert o.tile("Conversion rate") == f"{exp['conversion_rate'] * 100:.1f}%"
    assert o.tile("Contacts per conversion") == f"{exp['contacts_per_conversion']:.1f}"
    total = 0
    for label in filter_select(o, "Contact channel").locator("option").all_inner_texts()[1:]:
        filter_select(o, "Contact channel").select_option(label=label)
        total += o.page.evaluate("window.__mkKpis.cl")
    assert total == exp["clients"]
    o.page.get_by_role("button", name="Reset filters").click()
    o.page.locator('svg[aria-label^="Bar chart of conversion"] g.mark').nth(2).click()
    assert o.page.locator(".chip").count() == 1


def test_dark_theme_has_no_errors_and_changes_colours(open_page):
    o = open_page("hr")
    before = o.page.evaluate("getComputedStyle(document.body).backgroundColor")
    toggle = o.page.get_by_role("button", name="Theme: auto")
    toggle.click()  # light
    o.page.get_by_role("button", name="Theme: light").click()  # dark
    after = o.page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert before != after
    assert o.errors == []


@pytest.mark.skipif(not os.environ.get("SAVE_SCREENSHOTS"), reason="set SAVE_SCREENSHOTS=1")
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", PAGES)
def test_save_screenshots(open_page, name, width):
    o = open_page(name, width)
    o.page.wait_for_timeout(300)
    out = DOCS / "screenshots"
    out.mkdir(exist_ok=True)
    o.page.screenshot(path=str(out / f"{name}-{width}.png"), full_page=True)

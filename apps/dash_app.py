"""Interactive Dash application consuming pipeline JSON data.

Provides Plotly Dash interactive components and callbacks for Retail, HR, and Marketing domains.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import dash
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Input, Output, dcc, html

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"


def load_retail_data(data_path: Path | str = DATA_DIR / "retail.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def load_hr_data(data_path: Path | str = DATA_DIR / "hr.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def load_marketing_data(data_path: Path | str = DATA_DIR / "marketing.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def compute_retail_metrics(data: dict[str, Any], country: str = "All") -> tuple[str, str, str, Any]:
    months = data["months"]
    countries = data["countries"]
    inv = data["invoices"]

    v_arr = np.array(inv["v"])
    c_arr = np.array(inv["c"])
    m_arr = np.array(inv["m"])

    mask = np.ones(len(v_arr), dtype=bool)
    if country != "All" and country in countries:
        c_code = countries.index(country)
        mask = c_arr == c_code

    net_rev = float(np.sum(v_arr[mask]))
    orders = int(np.sum(mask))
    aov = round(net_rev / max(1, orders), 2)

    monthly_data = []
    for mi, mname in enumerate(months):
        m_mask = mask & (m_arr == mi)
        monthly_data.append({"Month": mname, "Net Revenue": float(np.sum(v_arr[m_mask]))})
    df_m = pd.DataFrame(monthly_data)
    fig = px.bar(df_m, x="Month", y="Net Revenue", title=f"Monthly Net Revenue ({country})")
    return f"£{net_rev:,.2f}", f"{orders:,}", f"£{aov:,.2f}", fig


def compute_hr_metrics(data: dict[str, Any], sector: str = "All") -> tuple[str, str, str, Any]:
    left_arr = np.array(data["left"])
    dims = data["dims"]
    sec_levels = dims["sector"]["levels"]
    sec_codes = np.array(dims["sector"]["codes"])

    mask = np.ones(len(left_arr), dtype=bool)
    if sector != "All" and sector in sec_levels:
        s_code = sec_levels.index(sector)
        mask = sec_codes == s_code

    tot = int(np.sum(mask))
    leavers = int(np.sum(left_arr[mask]))
    rate = round((leavers / max(1, tot)) * 100, 2)

    summary = []
    for sc, sname in enumerate(sec_levels):
        s_mask = sec_codes == sc
        s_tot = int(np.sum(s_mask))
        s_leave = int(np.sum(left_arr[s_mask]))
        s_rate = round((s_leave / max(1, s_tot)) * 100, 2) if s_tot > 0 else 0.0
        summary.append({"Sector": sname, "Attrition Rate (%)": s_rate})
    df_s = pd.DataFrame(summary)
    fig = px.bar(df_s, x="Sector", y="Attrition Rate (%)", title="Attrition Rate by Sector")
    return f"{tot:,}", f"{leavers:,}", f"{rate:.1f}%", fig


def compute_marketing_metrics(data: dict[str, Any], job: str = "All") -> tuple[str, str, str, Any]:
    y_arr = np.array(data["y"])
    dims = data["dims"]
    job_levels = dims["job"]["levels"]
    job_codes = np.array(dims["job"]["codes"])

    mask = np.ones(len(y_arr), dtype=bool)
    if job != "All" and job in job_levels:
        j_code = job_levels.index(job)
        mask = job_codes == j_code

    tot = int(np.sum(mask))
    conv = int(np.sum(y_arr[mask]))
    rate = round((conv / max(1, tot)) * 100, 2)

    summary = []
    for jc, jname in enumerate(job_levels):
        j_mask = job_codes == jc
        j_tot = int(np.sum(j_mask))
        j_conv = int(np.sum(y_arr[j_mask]))
        j_rate = round((j_conv / max(1, j_tot)) * 100, 2) if j_tot > 0 else 0.0
        summary.append({"Job": jname, "Conversion Rate (%)": j_rate})
    df_j = pd.DataFrame(summary).sort_values("Conversion Rate (%)", ascending=True)
    fig = px.bar(
        df_j, x="Conversion Rate (%)", y="Job", orientation="h", title="Conversion Rate by Job"
    )
    return f"{tot:,}", f"{conv:,}", f"{rate:.2f}%", fig


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, title="Analytics Dashboards", suppress_callback_exceptions=True)

    # Preload initial metadata for dropdowns
    retail_d = load_retail_data()
    hr_d = load_hr_data()
    mkt_d = load_marketing_data()

    app.layout = html.Div(
        [
            html.H1("Analytics Dashboards (Plotly Dash)", style={"textAlign": "center"}),
            dcc.Tabs(
                id="dashboard-tabs",
                value="tab-retail",
                children=[
                    dcc.Tab(label="Retail Sales", value="tab-retail"),
                    dcc.Tab(label="HR Attrition", value="tab-hr"),
                    dcc.Tab(label="Marketing Campaigns", value="tab-marketing"),
                ],
            ),
            html.Div(id="tab-content", style={"padding": "20px"}),
        ]
    )

    @app.callback(
        Output("tab-content", "children"),
        Input("dashboard-tabs", "value"),
    )
    def render_tab_layout(tab_name: str) -> html.Div:
        if tab_name == "tab-retail":
            return html.Div(
                [
                    html.H2("Retail Sales Dashboard"),
                    html.Label("Filter by Country:"),
                    dcc.Dropdown(
                        id="retail-country-dropdown",
                        options=[{"label": "All Countries", "value": "All"}]
                        + [{"label": c, "value": c} for c in retail_d["countries"]],
                        value="All",
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Div(
                                [html.H4("Net Revenue"), html.H3(id="retail-kpi-net")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Orders"), html.H3(id="retail-kpi-orders")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Avg Order Value"), html.H3(id="retail-kpi-aov")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                        ],
                        style={"marginTop": "20px", "marginBottom": "20px"},
                    ),
                    dcc.Graph(id="retail-trend-graph"),
                ]
            )
        elif tab_name == "tab-hr":
            return html.Div(
                [
                    html.H2("HR Attrition Dashboard"),
                    html.Label("Filter by Sector:"),
                    dcc.Dropdown(
                        id="hr-sector-dropdown",
                        options=[{"label": "All Sectors", "value": "All"}]
                        + [{"label": s, "value": s} for s in hr_d["dims"]["sector"]["levels"]],
                        value="All",
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Div(
                                [html.H4("Total Employees"), html.H3(id="hr-kpi-total")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Leavers"), html.H3(id="hr-kpi-leavers")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Attrition Rate"), html.H3(id="hr-kpi-rate")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                        ],
                        style={"marginTop": "20px", "marginBottom": "20px"},
                    ),
                    dcc.Graph(id="hr-sector-graph"),
                ]
            )
        else:
            return html.Div(
                [
                    html.H2("Marketing Campaigns Dashboard"),
                    html.Label("Filter by Job Category:"),
                    dcc.Dropdown(
                        id="mkt-job-dropdown",
                        options=[{"label": "All Jobs", "value": "All"}]
                        + [{"label": j, "value": j} for j in mkt_d["dims"]["job"]["levels"]],
                        value="All",
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Div(
                                [html.H4("Total Clients"), html.H3(id="mkt-kpi-clients")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Conversions"), html.H3(id="mkt-kpi-conv")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                            html.Div(
                                [html.H4("Conversion Rate"), html.H3(id="mkt-kpi-rate")],
                                style={"display": "inline-block", "width": "30%"},
                            ),
                        ],
                        style={"marginTop": "20px", "marginBottom": "20px"},
                    ),
                    dcc.Graph(id="mkt-job-graph"),
                ]
            )

    @app.callback(
        [
            Output("retail-kpi-net", "children"),
            Output("retail-kpi-orders", "children"),
            Output("retail-kpi-aov", "children"),
            Output("retail-trend-graph", "figure"),
        ],
        Input("retail-country-dropdown", "value"),
    )
    def update_retail(country: str | None) -> tuple[str, str, str, Any]:
        return compute_retail_metrics(retail_d, country or "All")

    @app.callback(
        [
            Output("hr-kpi-total", "children"),
            Output("hr-kpi-leavers", "children"),
            Output("hr-kpi-rate", "children"),
            Output("hr-sector-graph", "figure"),
        ],
        Input("hr-sector-dropdown", "value"),
    )
    def update_hr(sector: str | None) -> tuple[str, str, str, Any]:
        return compute_hr_metrics(hr_d, sector or "All")

    @app.callback(
        [
            Output("mkt-kpi-clients", "children"),
            Output("mkt-kpi-conv", "children"),
            Output("mkt-kpi-rate", "children"),
            Output("mkt-job-graph", "figure"),
        ],
        Input("mkt-job-dropdown", "value"),
    )
    def update_marketing(job: str | None) -> tuple[str, str, str, Any]:
        return compute_marketing_metrics(mkt_d, job or "All")

    return app


app = create_app()
server = app.server

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)

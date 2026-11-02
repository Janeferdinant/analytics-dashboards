"""Interactive Streamlit dashboard consuming pipeline JSON data.

Provides interactive domain dashboards for Retail Sales, HR Attrition, and Marketing Campaigns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"


@st.cache_data
def load_retail_data(data_path: Path | str = DATA_DIR / "retail.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_hr_data(data_path: Path | str = DATA_DIR / "hr.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_marketing_data(data_path: Path | str = DATA_DIR / "marketing.json") -> dict[str, Any]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def render_retail_page() -> None:
    st.header("Retail Sales (Online Retail II)")
    st.markdown("UK online gift retailer: revenue, returns, order volume, and product performance.")

    data = load_retail_data()
    months = data["months"]
    countries = data["countries"]
    inv = data["invoices"]

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        country_options = ["All Countries", *countries]
        selected_country = st.selectbox("Filter Country", country_options, key="retail_country")
    with col_filter2:
        month_range = st.select_slider(
            "Month Range",
            options=months,
            value=(months[0], months[-1]),
            key="retail_months",
        )

    # Filter invoices
    from_idx = months.index(month_range[0])
    to_idx = months.index(month_range[1])

    m_arr = np.array(inv["m"])
    c_arr = np.array(inv["c"])
    v_arr = np.array(inv["v"])
    cu_arr = np.array(inv["cu"])

    mask = (m_arr >= from_idx) & (m_arr <= to_idx)
    if selected_country != "All Countries":
        c_code = countries.index(selected_country)
        mask = mask & (c_arr == c_code)

    filtered_net = float(np.sum(v_arr[mask]))
    filtered_orders = int(np.sum(mask))
    filtered_aov = round(filtered_net / max(1, filtered_orders), 2)
    filtered_cust = len(set(cu_arr[mask]) - {-1})

    # KPI tiles
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net Revenue", f"£{filtered_net:,.2f}")
    k2.metric("Orders", f"{filtered_orders:,}")
    k3.metric("Avg Order Value", f"£{filtered_aov:,.2f}")
    k4.metric("Active Customers", f"{filtered_cust:,}")

    # Monthly revenue trend
    monthly_rows = []
    for mi in range(from_idx, to_idx + 1):
        m_mask = mask & (m_arr == mi)
        monthly_rows.append({"Month": months[mi], "Net Revenue (£)": float(np.sum(v_arr[m_mask]))})
    df_monthly = pd.DataFrame(monthly_rows)

    fig_trend = px.line(
        df_monthly,
        x="Month",
        y="Net Revenue (£)",
        title="Monthly Net Revenue Trend",
        markers=True,
    )
    st.plotly_chart(fig_trend, width="stretch")

    # Top products table
    if "products" in data and "items" in data["products"]:
        st.subheader("Top Selling Products")
        prod_rows = data["products"]["rows"]
        df_prods = pd.DataFrame(prod_rows[:15])
        st.dataframe(df_prods, width="stretch")


def render_hr_page() -> None:
    st.header("HR Attrition Analysis")
    st.markdown(
        "Employee survey: attrition rates, demographic distributions, and retention signals."
    )

    data = load_hr_data()
    left_arr = np.array(data["left"])
    dims = data["dims"]

    col_filter1, col_filter2 = st.columns(2)
    sectors = ["All Sectors", *dims["sector"]["levels"]]
    salaries = ["All Salary Bands", *dims["salary"]["levels"]]

    with col_filter1:
        sel_sector = st.selectbox("Sector", sectors, key="hr_sector")
    with col_filter2:
        sel_salary = st.selectbox("Salary Band", salaries, key="hr_salary")

    # Apply masks
    mask = np.ones(len(left_arr), dtype=bool)
    if sel_sector != "All Sectors":
        sec_code = dims["sector"]["levels"].index(sel_sector)
        mask = mask & (np.array(dims["sector"]["codes"]) == sec_code)
    if sel_salary != "All Salary Bands":
        sal_code = dims["salary"]["levels"].index(sel_salary)
        mask = mask & (np.array(dims["salary"]["codes"]) == sal_code)

    tot = int(np.sum(mask))
    leavers = int(np.sum(left_arr[mask]))
    rate = round((leavers / max(1, tot)) * 100, 2)

    k1, k2, k3 = st.columns(3)
    k1.metric("Respondents", f"{tot:,}")
    k2.metric("Leavers", f"{leavers:,}")
    k3.metric("Attrition Rate", f"{rate:.1f}%")

    # Attrition by sector bar chart
    sec_levels = dims["sector"]["levels"]
    sec_codes = np.array(dims["sector"]["codes"])
    sector_summary = []
    for sc, sname in enumerate(sec_levels):
        s_mask = mask & (sec_codes == sc) if sel_sector == "All Sectors" else (sec_codes == sc)
        s_tot = int(np.sum(s_mask))
        s_leave = int(np.sum(left_arr[s_mask]))
        s_rate = round((s_leave / max(1, s_tot)) * 100, 2) if s_tot > 0 else 0.0
        sector_summary.append({"Sector": sname, "Attrition Rate (%)": s_rate, "Total": s_tot})

    df_sec = pd.DataFrame(sector_summary)
    fig_sector = px.bar(
        df_sec,
        x="Sector",
        y="Attrition Rate (%)",
        title="Attrition Rate by Industry Sector",
        text="Attrition Rate (%)",
        color="Attrition Rate (%)",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(fig_sector, width="stretch")


def render_marketing_page() -> None:
    st.header("Bank Marketing Campaign Analytics")
    st.markdown(
        "Direct telemarketing campaign conversion, customer demographics, and outreach efficiency."
    )

    data = load_marketing_data()
    y_arr = np.array(data["y"])
    att_arr = np.array(data["att"])
    dims = data["dims"]
    jobs = ["All Jobs", *dims["job"]["levels"]]
    educations = ["All Educations", *dims["education"]["levels"]]

    col1, col2 = st.columns(2)
    with col1:
        sel_job = st.selectbox("Job Type", jobs, key="mkt_job")
    with col2:
        sel_edu = st.selectbox("Education Level", educations, key="mkt_edu")

    mask = np.ones(len(y_arr), dtype=bool)
    if sel_job != "All Jobs":
        j_code = dims["job"]["levels"].index(sel_job)
        mask = mask & (np.array(dims["job"]["codes"]) == j_code)
    if sel_edu != "All Educations":
        e_code = dims["education"]["levels"].index(sel_edu)
        mask = mask & (np.array(dims["education"]["codes"]) == e_code)

    tot_clients = int(np.sum(mask))
    conversions = int(np.sum(y_arr[mask]))
    conv_rate = round((conversions / max(1, tot_clients)) * 100, 2)
    contacts = int(np.sum(att_arr[mask]))
    c_per_conv = round(contacts / max(1, conversions), 1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Clients Contacted", f"{tot_clients:,}")
    k2.metric("Conversions", f"{conversions:,}")
    k3.metric("Conversion Rate", f"{conv_rate:.2f}%")
    k4.metric("Contacts / Conversion", f"{c_per_conv:.1f}")

    # Conversion rate by job
    job_levels = dims["job"]["levels"]
    job_codes = np.array(dims["job"]["codes"])
    job_summary = []
    for jc, jname in enumerate(job_levels):
        j_mask = job_codes == jc
        j_tot = int(np.sum(j_mask))
        j_conv = int(np.sum(y_arr[j_mask]))
        j_rate = round((j_conv / max(1, j_tot)) * 100, 2) if j_tot > 0 else 0.0
        job_summary.append({"Job": jname, "Conversion Rate (%)": j_rate, "Clients": j_tot})

    df_jobs = pd.DataFrame(job_summary).sort_values("Conversion Rate (%)", ascending=True)
    fig_job = px.bar(
        df_jobs,
        x="Conversion Rate (%)",
        y="Job",
        orientation="h",
        title="Conversion Rate by Client Job Category",
        text="Conversion Rate (%)",
        color="Conversion Rate (%)",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig_job, width="stretch")


def main() -> None:
    st.set_page_config(
        page_title="Analytics Dashboards",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Dashboard",
        ["Retail Sales", "HR Attrition", "Marketing Campaigns"],
        key="app_page",
    )

    if page == "Retail Sales":
        render_retail_page()
    elif page == "HR Attrition":
        render_hr_page()
    elif page == "Marketing Campaigns":
        render_marketing_page()


if __name__ == "__main__":
    main()

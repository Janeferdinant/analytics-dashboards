"""Saudi Employee Attrition survey: clean into one tidy row per respondent.

The source is a 2025 online survey of private-sector employees in Saudi Arabia (CC BY 4.0).
It is a convenience sample, so rates describe the respondents, not the workforce.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .paths import RAW

AGE_ORDER = ["21 to 30", "31 to 40", "41 to 50", "51 to 60"]
TENURE_ORDER = [
    "Less than 5 years",
    "5 to 10 years",
    "11 to 15 years",
    "16 to 20 years",
    "21+ years",
]
SALARY_ORDER = [
    "Under 5,000 SAR",
    "5,000 to 10,000 SAR",
    "11,000 to 15,000 SAR",
    "16,000+ SAR",
]
SALARY_MAP = {
    "Less than 5000 SAR": "Under 5,000 SAR",
    "From 5000 to 10000 S.R": "5,000 to 10,000 SAR",
    "From 11000 to 15000 S.R": "11,000 to 15,000 SAR",
    "From 16000 to 20000 S.R": "16,000+ SAR",
    "From 21000 to 25000 S.R": "16,000+ SAR",
    "From 26000 to 30000 S.R": "16,000+ SAR",
    "S.R 31000 - and more": "16,000+ SAR",
}
MIN_GROUP = 20  # sectors with fewer respondents are folded into "Other sectors"
LEVELS3 = ["Low", "Medium", "High"]
SATISFACTION_ORDER = ["Not satisfied", "Satisfied", "Very satisfied"]
RENAMES = {
    "Maritalstatus": "marital_status",
    "Academic_degree": "degree",
    "Years_Experience": "experience",
    "Years_experience_lastorganization": "tenure",
    "MonthlySalary": "salary_band",
    "Allowances": "allowances",
    "MedicalInsurance": "medical_insurance",
    "Bonus": "bonus",
    "OverTime": "overtime",
    "Rewards&Wages_Satisfaction": "pay_satisfaction",
    "Get_ Deserved_Promotion": "fair_promotion",
    "Training_programs_ During_last_three_years": "training_programs",
    "Business_Travel": "business_travel",
    "Job_Support": "job_support",
    "Recognition": "recognition",
    "Emotional_Commitment": "emotional_commitment",
    "Job_Engagement": "job_engagement",
    "Distance_to_work": "distance_to_work",
    "Work_Live_Balance": "work_life_balance",
    "Physical_Stress": "physical_stress",
    "Psychological_Exhaustion": "psychological_exhaustion",
    "Job_Stability": "job_stability",
    "Health_Issues": "health_issues",
    "Environment_Satisfaction": "environment_satisfaction",
    "Job_Satisfaction": "job_satisfaction",
    "Job_Opportunities": "job_opportunities",
}


def load_raw(folder: Path = RAW / "hr") -> pd.DataFrame:
    return pd.read_excel(folder / "employee_attrition_original.xlsx")


def _band_years(value: str) -> str:
    """'From 5 to 10 years' -> '5 to 10 years'; anything above 20 years collapses to 21+."""
    text = value.strip()
    if text.startswith("Less than"):
        return "Less than 5 years"
    text = text.replace("From ", "")
    lower = int(text.split(" ")[0])
    return "21+ years" if lower >= 21 else text


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one tidy row per respondent with normalised labels and ordered categories."""
    df = raw.rename(columns=lambda c: c.strip()).rename(columns=RENAMES).copy()
    df = df.rename(columns={"ID": "respondent_id", "Attrition": "attrition", "Gender": "gender"})
    df = df.rename(columns={"Age": "age_band", "Sector": "sector", "Department": "department"})
    df = df.rename(columns={"JobTitle": "job_title"})
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["left"] = (df["attrition"] == "Yes").astype(int)
    df["salary_band"] = df["salary_band"].map(SALARY_MAP)
    df["tenure"] = df["tenure"].map(_band_years)
    df["experience"] = df["experience"].map(_band_years)
    df["sector"] = df["sector"].str.replace(r" sector$", "", regex=True)
    df["sector"] = df["sector"].str[:1].str.upper() + df["sector"].str[1:]
    sizes = df["sector"].map(df["sector"].value_counts())
    df["sector_group"] = df["sector"].where(sizes >= MIN_GROUP, "Other sectors")
    df["training_programs"] = df["training_programs"].replace(
        {
            "I did not receive any training": "None",
            "From 1 to 3 training programs": "1 to 3",
            "From 4 to 6 training programs": "4 to 6",
            "From 7 training programs to more": "7+",
        }
    )
    df["business_travel"] = df["business_travel"].replace(
        {"I do not travel for work": "None", "Travel rarely": "Rarely", "Travel frequently": "Often"}
    )
    df["payment_overtime"] = df["Payment_Overtime"].replace(
        {"I don't have overtime": "No overtime", "Yes": "Paid", "No": "Unpaid"}
    )
    df = df.drop(columns=["Payment_Overtime"])
    df["age_band"] = pd.Categorical(df["age_band"], AGE_ORDER, ordered=True)
    df["tenure"] = pd.Categorical(df["tenure"], TENURE_ORDER, ordered=True)
    df["salary_band"] = pd.Categorical(df["salary_band"], SALARY_ORDER, ordered=True)
    df["job_satisfaction"] = pd.Categorical(
        df["job_satisfaction"], SATISFACTION_ORDER, ordered=True
    )
    df = df.sort_values("respondent_id").reset_index(drop=True)
    return df


def attrition_rate(df: pd.DataFrame) -> float:
    """Metric: share of respondents coded Attrition = Yes."""
    return float(df["left"].mean()) if len(df) else float("nan")


def rate_by(df: pd.DataFrame, column: str, min_n: int = 1) -> pd.DataFrame:
    """Attrition rate and respondent count per category, hiding groups smaller than min_n."""
    grouped = df.groupby(column, observed=True)["left"].agg(["size", "sum", "mean"])
    grouped.columns = ["respondents", "leavers", "attrition_rate"]
    return grouped[grouped["respondents"] >= min_n].reset_index()

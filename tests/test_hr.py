from __future__ import annotations

import pandas as pd
import pytest

from analytics_dashboards import hr, quality


@pytest.fixture()
def raw_hr() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": [1, 2, 3, 4],
            "Attrition": ["Yes", " No", "No ", "Yes"],
            "Gender": ["Female", "Male", "Male", "Female"],
            "Age": ["21 to 30", "31 to 40", "21 to 30 ", "41 to 50"],
            " Maritalstatus": ["Single", "Married", "Married", "Single"],
            " Academic_degree": ["Masters"] * 4,
            "Years_Experience": [
                "Less than 5 years",
                "From 5 to 10 years",
                "From 21 to 25 years",
                "From 26 to 30 years",
            ],
            "Years_experience_lastorganization": [
                "Less than 5 years",
                "From 5 to 10 years",
                "From 21 to 25 years",
                "From 31 to 35 years",
            ],
            "Sector": ["Medical sector", "education", "Education sector", "Medical sector"],
            "Department": ["A"] * 4,
            "JobTitle": ["B"] * 4,
            "MonthlySalary": [
                "Less than 5000 SAR",
                "From 5000 to 10000 S.R",
                "S.R 31000 - and more",
                "From 21000 to 25000 S.R",
            ],
            "Payment_Overtime": ["I don't have overtime", "Yes", "No", "Yes"],
            "Training_programs_ During_last_three_years": [
                "I did not receive any training",
                "From 1 to 3 training programs",
                "From 4 to 6 training programs",
                "From 7  training programs to more",
            ],
            "Business_Travel": [
                "I do not travel for work",
                "Travel rarely",
                "Travel frequently",
                "Travel rarely",
            ],
            "Job_Satisfaction": ["Satisfied", "Not satisfied", "Very satisfied", "Satisfied"],
        }
    )


def test_labels_are_trimmed_and_mapped(raw_hr):
    df = hr.clean(raw_hr)
    assert set(df["attrition"]) == {"Yes", "No"}
    assert list(df["left"]) == [1, 0, 0, 1]
    assert list(df["salary_band"].astype(str)) == [
        "Under 5,000 SAR",
        "5,000 to 10,000 SAR",
        "16,000+ SAR",
        "16,000+ SAR",
    ]
    assert list(df["tenure"].astype(str)) == [
        "Less than 5 years",
        "5 to 10 years",
        "21+ years",
        "21+ years",
    ]
    assert list(df["training_programs"]) == ["None", "1 to 3", "4 to 6", "7+"]


def test_sector_case_is_normalised_and_small_sectors_grouped(raw_hr):
    df = hr.clean(raw_hr)
    assert "education" not in set(df["sector"])
    assert set(df["sector_group"]) == {"Other sectors"}  # every sector is below MIN_GROUP here


def test_attrition_rate_and_rate_by(raw_hr):
    df = hr.clean(raw_hr)
    assert hr.attrition_rate(df) == pytest.approx(0.5)
    by_age = hr.rate_by(df, "age_band").set_index("age_band")
    assert by_age.loc["21 to 30", "respondents"] == 2
    assert by_age.loc["21 to 30", "attrition_rate"] == pytest.approx(0.5)


def test_rate_by_hides_small_groups(raw_hr):
    df = hr.clean(raw_hr)
    assert len(hr.rate_by(df, "age_band", min_n=2)) == 1


def test_attrition_rate_of_empty_frame_is_nan(raw_hr):
    df = hr.clean(raw_hr).iloc[0:0]
    rate = hr.attrition_rate(df)
    assert rate != rate  # NaN


def test_quality_checks_flag_only_the_group_size_rule_on_the_tiny_fixture(raw_hr):
    df = hr.clean(raw_hr)
    failed = [c.name for c in quality.hr_checks(df) if not c.passed]
    assert failed == ["sector groups are at least the minimum size or 'Other sectors'"]

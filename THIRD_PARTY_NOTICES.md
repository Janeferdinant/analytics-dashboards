# Third-party notices

This repository's original code, documentation and dashboards are licensed CC BY-NC-ND 4.0 (see `LICENSE`).
The datasets below are third-party works. They are **not committed**: `make data` downloads them at run time
and checks each file against a pinned SHA-256 checksum (`src/analytics_dashboards/download.py`).
Small aggregates and row-level derivatives built from them (`docs/data/*.json`) are adaptations and are
shared under the same CC BY 4.0 terms: they credit the sources below, and changes are described in the
"Changes made" lines.

Each dataset's license was checked on its source page on 2026-10-15. All three are
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/):
you may share and adapt the data, including commercially, if you give appropriate credit, link the license
and indicate changes. The licensors do not endorse this repository.

## 1. Online Retail II

- Source: UCI Machine Learning Repository, <https://archive.ics.uci.edu/dataset/502/online+retail+ii>
- DOI: <https://doi.org/10.24432/C5CG6D>
- Creator: Daqing Chen (2012). Transactions of a UK-based online retailer, 2009-12-01 to 2011-12-09.
- License: CC BY 4.0 (stated on the source page).
- Attribution: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5CG6D>
- Changes made: duplicate rows, non-product stock codes (postage, fees, manual adjustments) and zero-price rows
  removed; country aliases normalised; modelled into a star schema; aggregated and re-encoded for the dashboard
  (`docs/data/retail.json`). Product descriptions are title-cased.
- Download pinned to SHA-256 `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb` (`online_retail_ii.zip`).

## 2. Bank Marketing (bank-additional-full)

- Source: UCI Machine Learning Repository, <https://archive.ics.uci.edu/dataset/222/bank+marketing>
- DOI: <https://doi.org/10.24432/C5K306>
- Creators: S. Moro, P. Rita and P. Cortez (2014). Direct marketing (phone) campaigns of a Portuguese bank, 2008-2010.
- License: CC BY 4.0 (stated on the source page).
- Attribution: Moro, S., Rita, P., & Cortez, P. (2014). *Bank Marketing* [Dataset]. UCI Machine Learning Repository.
  <https://doi.org/10.24432/C5K306>. Related paper: Moro, S., Cortez, P., & Rita, P. (2014). A data-driven approach to
  predict the success of bank telemarketing. *Decision Support Systems*, 62, 22-31. <https://doi.org/10.1016/j.dss.2014.03.001>
- Changes made: 12 exact duplicate rows removed; labels made readable; age banded; the calendar year inferred from
  row order (the source has month and weekday only); the call-duration column dropped from the dashboard data.
- Download pinned to SHA-256 `e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4` (`bank_marketing.zip`).

## 3. Saudi Employee Attrition Dataset

- Source: Mendeley Data, <https://data.mendeley.com/datasets/6z2hty8php/1>
- DOI: <https://doi.org/10.17632/6z2hty8php.1>
- Creators: Haya Alqahtani, Hana Almagrabi and Amal Alharbi (King Abdulaziz University), published 2025-03-19.
  Survey of 1,200 private-sector employees in Saudi Arabia (1,191 usable rows in the file used here).
- License: CC BY 4.0 (stated on the source page).
- Attribution: Alqahtani, H., Almagrabi, H., & Alharbi, A. (2025). *Saudi Employee Attrition Dataset* [Dataset].
  Mendeley Data, V1. <https://doi.org/10.17632/6z2hty8php.1>
- Changes made: whitespace and label clean-up; salary, tenure and training categories regrouped; small sectors folded
  into "Other sectors"; the file "Original Dataset of Employee Attrition.xlsx" is the one used.
- Download pinned to SHA-256 `9a44efec36c467062d1a19230a31eb0c101b3407f0da0ed8c3e1812bbef79650`.

## Software

Python dependencies (pandas, NumPy, DuckDB, openpyxl, pytest, Ruff, Playwright) are installed from PyPI under
their own licenses (BSD, MIT, Apache-2.0 and similar) and are not redistributed here. The dashboards use no
third-party JavaScript or fonts: charts are drawn with the small SVG toolkit in `docs/assets/dash.js`, written for
this repository, and use the system font stack. The colour palette follows a published colour-vision-deficiency-safe
reference palette (blue and orange categorical slots plus a one-hue blue ramp) checked with a palette validator.

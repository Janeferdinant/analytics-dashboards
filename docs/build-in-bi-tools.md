# Build the dashboards in Tableau Public and Power BI Desktop

**This repository does not contain Tableau workbooks or Power BI files.** The dashboards in this repository are
open-tool implementations (HTML, JavaScript, SVG). This guide, the cleaned CSV exports and the reference values
are what you need to build the Tableau Public and Power BI Desktop versions yourself. I have not opened either
tool while writing this guide, so menu names can differ slightly between versions, and the time estimate
below (about an hour per dashboard once the tools are installed) is a design target, not a measured time.

Every formula matches `metrics-dictionary.md`. After building, compare your numbers with
`bi-reference-values.md`; if they agree with no filters applied, the build is right.

## 0. One-off preparation

1. Install Python 3.10 or newer and run, from the repository root:

   ```bash
   python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
   python -m pip install -r requirements.txt -e .
   make build                                         # or: python -m analytics_dashboards.cli build
   ```

   This downloads the three datasets (checksum-verified), cleans them, runs the data-quality checks and writes
   the CSVs below into `exports/` (not committed to git). It takes a few minutes: reading the Online Retail II
   workbook is the slow step.

2. The files in `exports/`:

   | File | Grain | Use |
   |---|---|---|
   | `retail_invoice_flat.csv` | one invoice (about 47,000 rows) | all retail KPIs, trend, countries, cohorts |
   | `retail_fact_sales_line.csv`, `retail_dim_product.csv`, `retail_dim_country.csv`, `retail_dim_date.csv`, `retail_dim_customer.csv` | star schema, one invoice line (about 1 million rows) | top-products view, Power BI model |
   | `retail_cohort_retention.csv` | cohort month x months since | check your cohort matrix |
   | `hr_tidy.csv` | one respondent (1,191 rows) | HR dashboard |
   | `marketing_tidy.csv` | one client (41,176 rows) | marketing dashboard |
   | `data_dictionary.csv` | column meanings | reference |

   `is_return` is `1` on cancellation invoices and `0` otherwise. `hr_tidy.csv` has numeric `*_order` columns for
   sorting ordered categories (age, tenure, salary, satisfaction and so on). `marketing_tidy.csv` has `client_id`
   and `*_order` columns.

3. Install **Tableau Public Desktop** (free; saving to Tableau Public needs your free Tableau Public account) and
   **Power BI Desktop** (free, Windows). Where you can publish or share a Power BI report depends on the account
   you sign in with; check Microsoft's current rules. You can always save the `.pbix` locally and export a PDF
   (File > Export > Export to PDF).

Palette for both tools (colour-blind safe, from the dataviz reference palette): series blue `#2a78d6`, second
series orange `#eb6834`, sequential ramp from `#cde2fb` to `#0d366b`, gridlines `#e1e0d9`. Use direct labels or a
legend, never colour alone, and keep a data table (a "View data" or crosstab sheet) behind each chart.

---

## 1. Retail sales dashboard

Open version: `docs/retail.html`. Source: `retail_invoice_flat.csv` for everything except top products.

### 1A. Tableau Public

**Connect.** Open Tableau Public Desktop > Connect > Text file > choose `exports/retail_invoice_flat.csv`. In the
data grid set `invoice_date` to Date, `year_month` and `cohort_month` to String, `is_return` and `customer_id` to
Number (whole). Create a **second data source** (Data > New Data Source > Text file) with
`retail_fact_sales_line.csv`, drag `retail_dim_product.csv` onto the canvas to create a relationship on
`product_key`, and keep it for the top-products sheet only.

**Calculated fields** (Analysis > Create Calculated Field, on the invoice source):

```
Gross Revenue        SUM(IF [is_return] = 0 THEN [amount] END)
Returns Value        ZN(SUM(IF [is_return] = 1 THEN [amount] END))
Net Revenue          [Gross Revenue] - [Returns Value]
Return Rate          [Returns Value] / [Gross Revenue]
Orders               COUNTD(IF [is_return] = 0 THEN [invoice_no] END)
AOV                  [Gross Revenue] / [Orders]
Customers            COUNTD(IF [is_return] = 0 AND NOT ISNULL([customer_id]) THEN [customer_id] END)
Orders per Customer  {FIXED [customer_id] : COUNTD(IF [is_return] = 0 THEN [invoice_no] END)}
Repeat Customers     COUNTD(IF [is_return] = 0 AND [Orders per Customer] >= 2 THEN [customer_id] END)
Repeat Rate          [Repeat Customers] / [Customers]
Customer Type        IF ISNULL([customer_id]) THEN "Guest" ELSE "Identified" END
Month                DATE([year_month] + "-01")
Months Since         DATEDIFF('month', DATE([cohort_month] + "-01"), DATE([year_month] + "-01"))
Cohort Size          {FIXED [cohort_month] : COUNTD([customer_id])}
Retention            COUNTD(IF [is_return] = 0 AND NOT ISNULL([customer_id]) THEN [customer_id] END) / MIN([Cohort Size])
```

On the products source: `Product Revenue = SUM(IF [is_return] = 0 THEN [line_amount] END)`.

**Sheets** (Worksheet > New Worksheet each):

1. *KPI tiles*, one sheet per measure (Net Revenue, Gross Revenue, Returns Value, Orders, AOV, Customers, Repeat
   Rate): drag the measure to Text on the Marks card, format the number (Net Revenue: `£#,##0.0,,"M"`).
2. *Net revenue by month*: `Month` (continuous, month level) to Columns, `Net Revenue` to Rows, mark type Line,
   colour `#2a78d6`. Add an area at low opacity if you like.
3. *Orders by month* and *AOV by month*: same layout with `Orders` and `AOV`.
4. *Net revenue by country*: `country` to Rows, `Net Revenue` to Columns, sort descending, keep the top 10 (Top N
   filter on `country` by `Net Revenue`); label bars.
5. *Top products* (products source): `description` to Rows, `Product Revenue` to Columns, Top 8 filter, sort
   descending.
6. *Cohort retention*: `cohort_month` to Rows, `Months Since` (discrete) to Columns, `Retention` to Color
   (continuous, blue sequential, range 0 to 0.6) and to Label (format `0%`). Filter `Months Since` to 0..12 and
   exclude `year_month` = `2011-12` (partial month: data ends 9 December 2011).

**Filters.** On the invoice sheets add filters and show them: `country` (single value dropdown or multiple), `Month`
(range of dates, or `invoice_date` as a range slider), `Customer Type`. Right-click each filter > Apply to
Worksheets > Selected Worksheets and pick the sheets from the invoice source. **Right-click the date and
Customer Type filters > Add to Context**, otherwise the fixed (LOD) fields `Orders per Customer` and
`Cohort Size` ignore them.

**Dashboard.** Dashboard > New Dashboard, size Automatic. Layout: filters row at the top; Net Revenue tile (large)
and six smaller tiles; net revenue line full width; orders and AOV side by side; country bars and top products
side by side; cohort heat map full width. Dashboard > Actions > Add Action > Filter: source `Net revenue by month`
(Select, target all invoice sheets) and `Net revenue by country` (Select). In Dashboard > Layout set a device
layout for Phone and stack the sheets in one column.

**Check.** With no filters the tiles must match `bi-reference-values.md` (net revenue 18,926,266.18; orders
39,516; customers 5,852; repeat rate 0.7235). Filter `country` = United Kingdom: net revenue 16,167,773.06.
The cohort matrix at month 0 is 100%, and the cohort sizes match `retail_cohort_retention.csv`. Two known
differences from the open version: its cohort is recomputed inside the current country filter, whereas the
Tableau `Cohort Size` and the BI cohort use each customer's first order in the whole dataset; and its top-products
view ranks inside the 100 best sellers.

**Save and publish (owner steps).** File > Save to Tableau Public As..., sign in, name it "Retail sales dashboard",
and tick nothing else. Tableau Public workbooks and their data extracts are public: that is fine for CC BY data, but
only publish when you are ready. Add the dataset credit (see `THIRD_PARTY_NOTICES.md`) in a text box on the
dashboard.

### 1B. Power BI Desktop

**Load.** Home > Get data > Text/CSV. Load `retail_invoice_flat.csv` (rename the query `Invoices`),
`retail_fact_sales_line.csv` (`Lines`), `retail_dim_product.csv` (`Products`), `retail_dim_country.csv`
(`Countries`) and `retail_dim_date.csv` (`Dates`). In Power Query set types: `invoice_date` Date, `amount`
Decimal, `is_return` Whole number, `customer_id` Whole number, `year_month` and `cohort_month` Text.

**Model** (Model view): create these relationships, one to many, single direction:

- `Countries[country]` -> `Invoices[country]`
- `Countries[country_key]` -> `Lines[country_key]`
- `Dates[date]` -> `Invoices[invoice_date]`
- `Dates[date_key]` -> `Lines[date_key]`
- `Products[product_key]` -> `Lines[product_key]`

Use `Countries[country]` and `Dates[date]` for slicers so they filter both fact tables.

**Calculated columns** (Table tools > New column, on `Invoices`):

```DAX
Customer Type = IF ( ISBLANK ( Invoices[customer_id] ), "Guest", "Identified" )
Month = DATE ( VALUE ( LEFT ( Invoices[year_month], 4 ) ), VALUE ( RIGHT ( Invoices[year_month], 2 ) ), 1 )
Months Since =
    VAR c = Invoices[cohort_month]
    VAR m = Invoices[year_month]
    RETURN
        IF (
            ISBLANK ( c ), BLANK (),
            ( VALUE ( LEFT ( m, 4 ) ) - VALUE ( LEFT ( c, 4 ) ) ) * 12
                + VALUE ( RIGHT ( m, 2 ) ) - VALUE ( RIGHT ( c, 2 ) )
        )
```

**Measures** (Table tools > New measure, in a table named `_Measures` or on `Invoices`):

```DAX
Gross Revenue = CALCULATE ( SUM ( Invoices[amount] ), Invoices[is_return] = 0 )
Returns Value = COALESCE ( CALCULATE ( SUM ( Invoices[amount] ), Invoices[is_return] = 1 ), 0 )
Net Revenue = [Gross Revenue] - [Returns Value]
Return Rate = DIVIDE ( [Returns Value], [Gross Revenue] )
Orders = CALCULATE ( DISTINCTCOUNT ( Invoices[invoice_no] ), Invoices[is_return] = 0 )
AOV = DIVIDE ( [Gross Revenue], [Orders] )
Customers = CALCULATE ( DISTINCTCOUNTNOBLANK ( Invoices[customer_id] ), Invoices[is_return] = 0 )
Repeat Customers =
    COUNTROWS (
        FILTER (
            VALUES ( Invoices[customer_id] ),
            NOT ISBLANK ( Invoices[customer_id] )
                && CALCULATE ( DISTINCTCOUNT ( Invoices[invoice_no] ), Invoices[is_return] = 0 ) >= 2
        )
    )
Repeat Rate = DIVIDE ( [Repeat Customers], [Customers] )
Cohort Size = CALCULATE ( DISTINCTCOUNTNOBLANK ( Invoices[customer_id] ), ALLEXCEPT ( Invoices, Invoices[cohort_month] ) )
Retention = DIVIDE ( [Customers], [Cohort Size] )
Product Revenue = CALCULATE ( SUM ( Lines[line_amount] ), Lines[is_return] = 0 )
```

**Visuals** (Report view; Format > Themes > Customize current theme to set colours):

1. Seven *Card* visuals for Net Revenue, Gross Revenue, Returns Value, Orders, AOV, Customers, Repeat Rate. Make
   Net Revenue the largest (callout value 48 pt).
2. *Line chart*: X-axis `Invoices[Month]` (continuous), Y `Net Revenue`. Two more for `Orders` and `AOV`.
3. *Clustered bar chart*: Y `Countries[country]`, X `Net Revenue`; Filters pane > Top N 10 by `Net Revenue`.
4. *Clustered bar chart*: Y `Products[description]`, X `Product Revenue`; Top N 8 by `Product Revenue`.
5. *Matrix*: Rows `Invoices[cohort_month]`, Columns `Invoices[Months Since]`, Values `Retention`. Cell elements >
   Background colour > Gradient, minimum `#cde2fb` at 0, maximum `#0d366b` at 0.6. Visual filters: `Months Since`
   between 0 and 12, `year_month` is not `2011-12`.
6. *Slicers*: `Countries[country]` (dropdown), `Dates[date]` (Between), `Invoices[Customer Type]`.
7. *Tables behind charts*: add a *Table* visual per chart on a second page "Data", or use the visual's "Show as a
   table" (More options).

Edit interactions (Format > Edit interactions) so the line chart and country bars cross-filter the others (the
default). Add a *Phone layout* (View > Phone layout) and drag the visuals into one column.

**Check.** Same numbers as the Tableau check above: net revenue 18,926,266.18, orders 39,516, customers 5,852,
repeat rate 0.7235 (format as percent: 72.4%).

**Save.** File > Save as `retail-dashboard.pbix`. If you can publish, Home > Publish; otherwise export to PDF.

---

## 2. HR attrition dashboard

Open version: `docs/hr.html`. Source: `exports/hr_tidy.csv` (one respondent per row).

### 2A. Tableau Public

**Connect:** Text file > `hr_tidy.csv`. Keep `left` as Number (whole).

**Calculated fields and parameter:**

```
Respondents   COUNT([respondent_id])
Leavers       SUM([left])
Attrition Rate   SUM([left]) / COUNT([respondent_id])
Overall Rate     { FIXED : SUM([left]) / COUNT([respondent_id]) }
Gap pp           ([Attrition Rate] - [Overall Rate]) * 100
Small Group      IF COUNT([respondent_id]) < 20 THEN "Under 20 respondents" ELSE "20 or more" END
Rate (n>=20)     IF COUNT([respondent_id]) >= 20 THEN SUM([left]) / COUNT([respondent_id]) END
```

Create a parameter (right-click in Data pane > Create Parameter): name `Break down by`, data type String, List,
values `Sector, Job satisfaction, Tenure, Training programmes, Monthly salary, Age band, Gender, Degree, Job
support, Work-life balance, Overtime pay, Recognition, Got a deserved promotion, Job stability, Distance to
work`. Then:

```
Driver   CASE [Break down by]
           WHEN "Sector" THEN [sector_group]
           WHEN "Job satisfaction" THEN [job_satisfaction]
           WHEN "Tenure" THEN [tenure]
           WHEN "Training programmes" THEN [training_programs]
           WHEN "Monthly salary" THEN [salary_band]
           WHEN "Age band" THEN [age_band]
           WHEN "Gender" THEN [gender]
           WHEN "Degree" THEN [degree]
           WHEN "Job support" THEN [job_support]
           WHEN "Work-life balance" THEN [work_life_balance]
           WHEN "Overtime pay" THEN [payment_overtime]
           WHEN "Recognition" THEN [recognition]
           WHEN "Got a deserved promotion" THEN [fair_promotion]
           WHEN "Job stability" THEN [job_stability]
           WHEN "Distance to work" THEN [distance_to_work]
         END
```

**Sheets:**

1. *KPI tiles*: Attrition Rate (large, format `0.0%`), Respondents, Leavers, Gap pp (format `+0.0;-0.0`).
2. *Attrition by driver*: `Driver` to Rows, `Attrition Rate` to Columns, `Small Group` to Color (grey for "Under 20
   respondents", `#2a78d6` for the rest), `Respondents` to Label or Tooltip. Add a reference line (Analytics pane
   > Reference line > Constant, value from `Overall Rate`, or Average line across the table) and show the
   parameter control (right-click the parameter > Show Parameter).
3. *Attrition by tenure*: `tenure` (sorted by the numeric `tenure_order`: drag `tenure_order` to Rows, or use
   manual sort) to Columns, `Attrition Rate` to Rows, same colouring.
4. *Satisfaction x tenure*: `tenure` to Columns, `job_satisfaction` to Rows, `Rate (n>=20)` to Color (blue
   sequential, 0 to 0.8) and Text. Grey for Null (Format > Special values), so small cells stay blank.

**Filters:** `sector_group`, `gender`, `age_band`, `salary_band`, `tenure` as dropdowns (show filter), applied to all
sheets (Apply to Worksheets > All Using This Data Source). Dashboard actions: Use as Filter on the driver bars and
the tenure columns.

**Dashboard text box (required):** "Survey of 1,191 employees; a convenience sample. Differences between groups are
associations, not causes. Source: Alqahtani, Almagrabi and Alharbi (2025), Mendeley Data, CC BY 4.0."

**Check:** Respondents 1,191; leavers 515; attrition rate 43.2%; job satisfaction "Not satisfied" 58.4% (n = 293),
"Very satisfied" 25.8% (n = 252) (see `bi-reference-values.md`).

### 2B. Power BI Desktop

**Load:** Get data > Text/CSV > `hr_tidy.csv` (query name `HR`). In Column tools set **Sort by column**:
`age_band` by `age_band_order`, `tenure` by `tenure_order`, `salary_band` by `salary_band_order`,
`job_satisfaction` by `job_satisfaction_order`, `job_support` by `job_support_order`, `work_life_balance` by
`work_life_balance_order`, `distance_to_work` by `distance_to_work_order`, `training_programs` by
`training_programs_order`.

**Measures:**

```DAX
Respondents = COUNTROWS ( HR )
Leavers = SUM ( HR[left] )
Attrition Rate = DIVIDE ( [Leavers], [Respondents] )
Overall Rate = CALCULATE ( [Attrition Rate], ALL ( HR ) )
Gap pp = ( [Attrition Rate] - [Overall Rate] ) * 100
Small Group = IF ( [Respondents] < 20, 1, 0 )
Rate (n>=20) = IF ( [Respondents] >= 20, [Attrition Rate] )
```

**Driver switch:** Modeling > New parameter > Fields. Add the 15 fields (`sector_group`, `job_satisfaction`,
`tenure`, `training_programs`, `salary_band`, `age_band`, `gender`, `degree`, `job_support`,
`work_life_balance`, `payment_overtime`, `recognition`, `fair_promotion`, `job_stability`, `distance_to_work`),
rename the parameter `Break down by`, and tick "Add slicer to this page".

**Visuals:**

1. *Cards*: Attrition Rate (largest), Respondents, Leavers, Gap pp.
2. *Clustered bar chart*: Y = the `Break down by` field parameter, X = `Attrition Rate`, tooltip `Respondents`. Colour
   bars by rules: Format > Bars > Colors > fx > Rules: `Small Group` = 1 -> grey `#c3c2b7`, else `#2a78d6`. Add a
   constant line (Analytics pane) at the overall rate by creating a measure-based line: Analytics > Constant line,
   fx on `Overall Rate`.
3. *Clustered column chart*: X `HR[tenure]`, Y `Attrition Rate`, same colour rule.
4. *Matrix*: Rows `job_satisfaction`, Columns `tenure`, Values `Rate (n>=20)`; background colour gradient `#cde2fb` at
   0 to `#0d366b` at 0.8; Format > Cell elements, "Show blank" for empty values.
5. *Slicers* (dropdown): `sector_group`, `gender`, `age_band`, `salary_band`, `tenure`.
6. Text box with the same survey caveat and CC BY credit as above.

**Check:** the same four numbers as in 2A.

---

## 3. Marketing campaign dashboard

Open version: `docs/marketing.html`. Source: `exports/marketing_tidy.csv` (one client per row).

### 3A. Tableau Public

**Connect:** Text file > `marketing_tidy.csv`.

**Calculated fields:**

```
Clients               COUNT([client_id])
Conversions           SUM([converted])
Conversion Rate       SUM([converted]) / COUNT([client_id])
Contact Attempts      SUM([campaign])
Contacts per Conversion   SUM([campaign]) / SUM([converted])
Month                 DATE([year_month] + "-01")
Low Volume Month      IF COUNT([client_id]) < 100 THEN "Under 100 clients" ELSE "100 or more" END
Attempts Label        IF [attempts] >= 6 THEN "6+" ELSE STR([attempts]) END
Rate (n>=30)          IF COUNT([client_id]) >= 30 THEN SUM([converted]) / COUNT([client_id]) END
```

**Sheets:**

1. *KPI tiles*: Conversion Rate (large, `0.0%`), Clients, Conversions, Contact Attempts, Contacts per Conversion
   (`0.0`).
2. *Clients per month*: `Month` (continuous, month) to Columns, `Clients` to Rows, line. The source skips some
   calendar months (no rows); a continuous date axis leaves those as gaps or straight segments, which is
   acceptable; note it in a caption.
3. *Conversion rate by month*: same axis, `Conversion Rate` to Rows, `Low Volume Month` to Shape (hollow circle
   for "Under 100 clients"), line in `#2a78d6`.
4. *Conversion by segment*: a `Break down by` parameter and `Driver` calculated field exactly like the HR guide
   (values: Earlier-campaign outcome = `prior_outcome`, Job = `job`, Age band = `age_band`, Education =
   `education`, Contact channel = `contact`, Housing loan = `housing`, Personal loan = `loan`). `Driver` to Rows,
   `Conversion Rate` to Columns, colour grey when `COUNT([client_id]) < 50`.
5. *Conversion by contact attempts*: `Attempts Label` (sort by `attempts`) to Columns, `Conversion Rate` to Rows.
6. *Earlier outcome x attempts*: `Attempts Label` to Columns, `prior_outcome` (sort by `prior_outcome_order`) to
   Rows, `Rate (n>=30)` to Color and Text.

**Filters:** `Month` range, `contact`, `age_band`, `job`, `prior_outcome`. Apply to all worksheets. Actions: Use as
Filter on the month line and the segment bars.

**Dashboard caption (required):** "Source: Bank Marketing (UCI), Moro, Rita and Cortez (2014), CC BY 4.0. The year
of each month is inferred from row order. Conversion rate and contact counts are descriptive; there is no cost
data."

**Check:** clients 41,176; conversions 4,639; conversion rate 11.27%; contacts per conversion 22.79; "Prior: yes"
65.11% (n = 1,373).

### 3B. Power BI Desktop

**Load:** Text/CSV > `marketing_tidy.csv` (`Marketing`). Sort by column: `age_band` by `age_band_order`,
`prior_outcome` by `prior_outcome_order`. Add a calculated column:

```DAX
Month = DATE ( VALUE ( LEFT ( Marketing[year_month], 4 ) ), VALUE ( RIGHT ( Marketing[year_month], 2 ) ), 1 )
Attempts Label = IF ( Marketing[attempts] >= 6, "6+", FORMAT ( Marketing[attempts], "0" ) )
```

(Sort `Attempts Label` by `attempts`.)

**Measures:**

```DAX
Clients = COUNTROWS ( Marketing )
Conversions = SUM ( Marketing[converted] )
Conversion Rate = DIVIDE ( [Conversions], [Clients] )
Contact Attempts = SUM ( Marketing[campaign] )
Contacts per Conversion = DIVIDE ( [Contact Attempts], [Conversions] )
Low Volume = IF ( [Clients] < 100, 1, 0 )
Rate (n>=30) = IF ( [Clients] >= 30, [Conversion Rate] )
```

**Visuals:** five cards; two line charts (`Month` continuous on the X-axis; `Clients`, then `Conversion Rate`);
a clustered bar chart driven by a field parameter `Break down by` (fields: `prior_outcome`, `job`, `age_band`,
`education`, `contact`, `housing`, `loan`); a column chart of `Conversion Rate` by `Attempts Label`; a matrix with
`prior_outcome` rows, `Attempts Label` columns and `Rate (n>=30)` values with a `#cde2fb` to `#0d366b` gradient;
slicers for `Month` (Between), `contact`, `age_band`, `job`, `prior_outcome`. Add a text box with the source credit
and the "year inferred from row order" note. For hollow low-volume markers: Format > Markers on the rate line,
conditional colour by `Low Volume` (fx), or simply mention volume in the tooltip.

**Check:** the same numbers as in 3A.

---

## 4. Accessibility checklist for the BI versions

- Colour: use the palette above; do not rely on colour alone (labels, tooltips, a data table).
- Text: at least 12 pt in Tableau and 10 pt in Power BI visuals; titles that say what the chart shows.
- Keyboard: in Power BI, set tab order and alt text for each visual (Format > General > Alt text); Tableau Public
  dashboards support keyboard navigation of marks only partly, so keep the data table sheet.
- Mobile: build the phone layout (Tableau device layout, Power BI Phone layout) and check it at about 390 px.

## 5. What to keep in the repository afterwards

Put any exported screenshots or PDFs in a new folder such as `docs/bi-exports/`, and describe them as "Tableau
Public (or Power BI) version, built by the repository owner". Add the workbook link only once it is published.
Do not describe the BI versions as part of this repository's automated pipeline: they are separate, hand-built
artefacts.

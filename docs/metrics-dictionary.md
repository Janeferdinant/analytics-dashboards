# Metrics dictionary

Every KPI on the dashboards, defined precisely. The dashboards compute these in the browser; the pipeline
computes the same numbers with pandas and DuckDB, and `make e2e` compares the two for the default view.
"Scope" means the current filters. Currency is GBP for retail.

## Retail (Online Retail II)

Grain of the model: one invoice line (`fact_sales_line`) and one invoice (`fact_invoice`); see `data-model.md`.
Cleaning rules (in order): drop exact duplicate rows; keep only product stock codes (start with five digits);
drop unit price <= 0; drop non-positive quantities outside cancellation invoices. A cancellation invoice has an
invoice number starting with `C` and is treated as a return.

| Metric | Definition | Notes |
|---|---|---|
| Gross revenue | Sum of `quantity x unit_price` over lines on non-cancellation invoices | After cleaning. Excludes postage, fees and manual lines |
| Returns value | Sum of `abs(quantity x unit_price)` over lines on cancellation invoices | Returns are dated by the cancellation invoice, not the original sale |
| Net revenue | Gross revenue - returns value | The headline figure |
| Return rate | Returns value / gross revenue | Shown on the Returns tile |
| Orders | Count of distinct non-cancellation invoice numbers | Guest orders included |
| Average order value (AOV) | Gross revenue / orders | Uses gross, so returns do not reduce it |
| Customers (identified) | Count of distinct customer ids with at least one order in scope | Lines with no customer id (about 22%) are "guests": counted in revenue and orders, never as customers |
| Repeat-customer rate | Identified customers with 2 or more orders in scope / identified customers with 1 or more orders in scope | Depends on the month range: a short range can only show a low rate |
| Cohort month | Calendar month of a customer's first non-cancellation order in the current country and customer-type scope | Month range is not applied to cohorts |
| Cohort size | Customers whose cohort month is that month | Cohorts under 20 customers are hidden |
| Retention at month k | Customers in the cohort with at least one order in month (cohort month + k) / cohort size | k = 0 is 100% by construction. The last data month (December 2011, ends 9 Dec) is a partial month and is excluded |
| Net revenue by country | Net revenue per invoice country; the 10 largest by gross revenue plus "Other countries" | Ignores the country filter so the reader can switch country |
| Top products | Gross sales revenue of a product in scope, ranked among the 100 best-selling products overall | Sales lines only: returns are not attributed to products |

Not available: margin, cost of goods and profit. The source has no cost data, so none is shown.

## HR (Saudi Employee Attrition survey)

Grain: one survey respondent. Labels are trimmed; salary bands above 16,000 SAR are merged; tenure bands above
20 years are merged into "21+ years"; sectors with fewer than 20 respondents are folded into "Other sectors".

| Metric | Definition | Notes |
|---|---|---|
| Respondents | Count of survey rows in scope | |
| Left the organisation | Count of rows with `Attrition = Yes` in scope | As coded in the source file |
| Attrition rate | Left the organisation / respondents | A survey proportion, not an annual turnover rate: the survey has no time window |
| Gap vs all respondents | (attrition rate in scope - attrition rate of all 1,191 respondents) x 100, in percentage points | |
| Attrition rate by group | Attrition rate computed inside one category of a driver, other filters applied | Groups under 20 respondents are hatched; heat-map cells under 20 are greyed |
| Tenure | "Years in the last organisation" band | Stands in for a cohort view; there are no dates |

Differences between groups are associations in a convenience sample and are not causal.

## Marketing (Bank Marketing, bank-additional-full)

Grain: one client in a phone campaign. 12 exact duplicate rows are removed. The file has month and weekday but no
year; the year is inferred from row order (the UCI documentation says rows are ordered by date from May 2008 to
November 2010; the year increments whenever the month number goes backwards). Months with no rows are shown as gaps.

| Metric | Definition | Notes |
|---|---|---|
| Clients contacted | Count of rows in scope | |
| Conversions | Count of rows with `y = yes` (client subscribed to a term deposit) | |
| Conversion rate | Conversions / clients contacted | |
| Contact attempts | Sum of the `campaign` column in scope | Contacts made to the client during this campaign, including the last one |
| Contacts per conversion | Contact attempts / conversions | Not a cost measure: there is no cost data |
| Conversion by contact attempts | Conversion rate among clients with k attempts (6 means 6 or more) | Clients who are hard to reach get more attempts, so this is not a causal curve |
| Earlier-campaign outcome | `poutcome`: "Not contacted before", "Prior: no" (failure), "Prior: yes" (success) | |
| Previously contacted | `previous > 0` | `pdays = 999` is not used: 4,110 clients with earlier contacts also have `pdays = 999` (see the run log) |

The call-duration column is not used: it is only known after the call has ended.

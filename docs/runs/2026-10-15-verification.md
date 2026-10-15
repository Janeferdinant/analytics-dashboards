# Verification run, 2026-10-15

## Environment

- Windows 11 Pro, AMD Ryzen 7 5800X (8 cores, 16 threads), 31.9 GB RAM, CPU only, no GPU used.
- Python 3.10.6; pandas 2.3.3, DuckDB 1.5.6, openpyxl 3.1.5, NumPy 2.2.6, pytest 9.1.1, Ruff 0.17.0, Playwright 1.64.0
  with headless Chromium 156.
- Seeds: none. The pipeline and dashboards are deterministic (no sampling, no random numbers).

## Fresh-clone check of the README commands

Commit `0460085` was cloned from GitHub into an empty folder, a new virtual environment was created, and the README
commands were run in order (`python -m venv`, `pip install`, `download`, `build`, `ruff`, `pytest` three ways).
`make` is not installed on this machine, so the README uses the equivalent `python -m ...` commands, which are what was run.

| Command | Result |
|---|---|
| `python -m pip install -r requirements.txt -e .` | installed |
| `python -m analytics_dashboards.cli download` | 13 s; all three SHA-256 checksums matched |
| `python -m analytics_dashboards.cli build` | 3 min 18 s; `Failed checks: 0` (33 of 33 pass) |
| `python -m ruff check .` / `python -m ruff format --check .` | all checks passed / 25 files already formatted |
| `python -m pytest -q` | 30 passed (the browser module is skipped until Playwright is installed) |
| `python -m pytest -q -m data -o addopts=""` | 5 passed |
| `python -m pip install playwright` and `python -m playwright install chromium` | installed (browser already cached) |
| `python -m pytest -q -m e2e -o addopts="" tests/e2e` | 21 passed, 6 skipped (the skipped ones are screenshot captures, which need `SAVE_SCREENSHOTS=1`) |

Disk use after the run: 109 MB in `data/`, 78 MB in `exports/` (both git-ignored). The only tracked file the run changed
was `docs/bi-reference-values.md` (a line wrap added after the clone's commit; numbers identical).

## Final run on the working tree (after small text and log-format fixes)

| Command | Result |
|---|---|
| `build` | `Failed checks: 0`; retail rows in 1,067,371, out 1,021,128 |
| ruff check / format --check | passed |
| `pytest -q` | 30 passed |
| `pytest -q -m data` | 5 passed |
| `SAVE_SCREENSHOTS=1 pytest -q -m e2e tests/e2e` | 27 passed (21 checks + 6 screenshot captures, 390 px and 1280 px) |

## What the browser checks cover

For each of the three dashboards at 390 px and 1280 px: no console errors, page errors or failed requests; no horizontal
scrolling and no chart wider than the viewport; every chart has a data table; the KPI values equal the pipeline's own
`expected` values (retail net revenue, gross, returns, orders, average order value, identified customers, repeat rate; HR
respondents, leavers, rate; marketing clients, conversions, rate, contacts per conversion); filters partition the totals
(per-country orders sum to the total; gender respondents sum to 1,191; channel clients sum to 41,176); drill-downs by clicking
a month, a country bar, a driver bar or a tenure column add and remove filter chips; keyboard use works (arrow keys,
Enter, Escape on the line chart and heat map, Enter on bars); the dark theme toggles without errors; the overview page's
images load.

## Colour and contrast checks (computed, not measured with a screen reader)

- The blue, orange and aqua categorical slots were run through the dataviz palette validator (light and dark). Blue and
  orange pass every gate; aqua is not used in any chart.
- Text contrast on the chart surface (light, dark): secondary ink 7.7:1 and 9.7:1; muted ink 5.3:1 and 6.8:1; focus
  ring 6.5:1 and 8.3:1; positive and negative delta text 7.4:1 and 6.4:1 (light), 5.2:1 and 6.6:1 (dark).
- The heat maps use five discrete steps with a fixed text colour per step; the lowest text contrast across the steps is
  5.4:1 in light mode and 5.4:1 in dark mode.
- Not checked: screen readers, an automated accessibility auditor, Firefox and WebKit.

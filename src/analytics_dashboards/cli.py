"""Command line: download data, validate, build dashboard JSON, export BI-ready CSVs."""

from __future__ import annotations

import argparse
import platform
import sys
from datetime import date

from . import __version__, dashboard_data, download, export, quality
from . import hr as hr_mod
from . import marketing as mk_mod
from . import retail as retail_mod
from .paths import DOCS


def _report(title: str, results: list[quality.CheckResult]) -> list[str]:
    lines = [f"### {title}", "", "| Check | Result | Detail |", "|---|---|---|"]
    for r in results:
        lines.append(f"| {r.name} | {'pass' if r.passed else 'FAIL'} | {r.detail} |")
    return [*lines, ""]


def run_pipeline(skip_export: bool = False) -> int:
    download.fetch_all()
    raw = retail_mod.load_raw()
    lines, rep = retail_mod.clean(raw)
    con = retail_mod.build_star(lines)
    hr_df = hr_mod.clean(hr_mod.load_raw())
    mk_df = mk_mod.clean(mk_mod.load_raw())

    results = {
        "Retail (Online Retail II)": quality.retail_checks(lines, con),
        "HR (employee attrition survey)": quality.hr_checks(hr_df),
        "Marketing (Bank Marketing)": quality.marketing_checks(mk_df),
    }
    failed = [r.name for group in results.values() for r in group if not r.passed]

    paths = [
        dashboard_data.build_retail(lines, con),
        dashboard_data.build_hr(hr_df),
        dashboard_data.build_marketing(mk_df),
    ]
    if not skip_export:
        export.export_retail(con)
        export.export_frame(hr_df, "hr_tidy.csv")
        export.export_frame(mk_df, "marketing_tidy.csv")
        export.write_dictionary()

    sizes = ", ".join(f"{p.name} ({p.stat().st_size / 1e6:.2f} MB)" for p in paths)
    log = [
        f"# Pipeline run {date.today().isoformat()}",
        "",
        f"- Package version: {__version__}; Python {platform.python_version()}; "
        f"{platform.system()} {platform.machine()}; CPU only",
        "- Command: `analytics-dashboards build`",
        f"- Retail rows in: {rep.rows_in:,}; rows out: {rep.rows_out:,}",
        "",
        "| Retail cleaning rule | Rows removed |",
        "|---|---|",
        *[f"| {name} | {n:,} |" for name, n in rep.steps],
        "",
        f"- HR respondents: {len(hr_df):,}; marketing clients after de-duplication: {len(mk_df):,}",
        f"- Dashboard JSON written: {sizes}",
        "",
        "## Data-quality checks",
        "",
    ]
    for title, group in results.items():
        log += _report(title, group)
    log += [f"Failed checks: {len(failed)}", ""]
    runs = DOCS / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{date.today().isoformat()}-pipeline.md").write_text("\n".join(log), "utf-8")
    print("\n".join(log))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analytics-dashboards", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="download datasets and verify SHA-256 checksums")
    build = sub.add_parser("build", help="clean, validate, build dashboard JSON and BI CSVs")
    build.add_argument("--no-export", action="store_true", help="skip the exports/ CSVs")
    args = parser.parse_args(argv)
    if args.cmd == "download":
        for key, folder in download.fetch_all().items():
            print(f"{key}: {folder}")
        return 0
    return run_pipeline(skip_export=args.no_export)


if __name__ == "__main__":
    sys.exit(main())

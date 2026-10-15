"""Filesystem layout, resolved from the repository root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
EXPORTS = ROOT / "exports"
DOCS = ROOT / "docs"
DASH_DATA = DOCS / "data"
SQL_DIR = Path(__file__).resolve().parent / "sql"

PY ?= python

.PHONY: install data build test test-data lint e2e serve all

install:
	$(PY) -m pip install -r requirements.txt -e .

data:
	$(PY) -m analytics_dashboards.cli download

# Clean, validate, write docs/data/*.json, docs/runs/<date>-pipeline.md and exports/*.csv
build:
	$(PY) -m analytics_dashboards.cli build

test:
	$(PY) -m pytest -q

test-data:
	$(PY) -m pytest -q -m data -o addopts=""

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

# Browser checks (needs: pip install playwright && playwright install chromium)
e2e:
	$(PY) -m pytest -q -m e2e -o addopts="" tests/e2e

# Open http://localhost:8000/ to view the dashboards
serve:
	$(PY) -m http.server 8000 --directory docs

all: lint test data build test-data

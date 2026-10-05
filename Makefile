PYTHON ?= .venv/bin/python
BASE_PYTHON ?= python3

.PHONY: setup demo build test dashboard report clean

setup:
	$(BASE_PYTHON) -m venv .venv
	.venv/bin/pip install -e ".[dev]"

demo:
	$(PYTHON) scripts/download_data.py --mode demo

build:
	$(PYTHON) -m display_optimizer.cli run-all

test:
	$(PYTHON) -m pytest

dashboard:
	.venv/bin/streamlit run dashboard/app.py

report:
	$(PYTHON) scripts/export_report.py

clean:
	$(PYTHON) -m display_optimizer.cli clean

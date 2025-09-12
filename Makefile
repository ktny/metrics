SHELL := /bin/bash

VENV := .venv
PYTHON ?= python3
PIP := $(VENV)/bin/pip
STREAMLIT := $(VENV)/bin/streamlit

.PHONY: sample setup run clean venv

sample:
	@mkdir -p samples
	@sar -o samples/sar_v12.dat 1 5 >/dev/null
	@echo "Exporting JSON/CSV from samples/sar_v12.dat"
	@sadf -j samples/sar_v12.dat -- -A > samples/sar_v12.json
	@LC_ALL=C sadf -d samples/sar_v12.dat -- -A > samples/sar_v12.csv

$(VENV)/bin/activate: requirements.txt
	@$(PYTHON) -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt

setup: $(VENV)/bin/activate ## Create venv and install deps

run: setup ## Start Streamlit app
	@echo "Starting Streamlit app at http://localhost:8501"
	@$(STREAMLIT) run app.py

clean:
	@rm -f samples/uploaded.dat
	@find . -name "__pycache__" -type d -exec rm -rf {} +

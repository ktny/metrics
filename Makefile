SHELL := /bin/bash

.PHONY: setup run sample fmt lint typecheck clean

# Forwarding targets to mise tasks for backward compatibility
setup:
	@mise run setup

run:
	@echo "Starting Streamlit app at http://localhost:8501"
	@mise run run

sample:
	@mise run sample

fmt:
	@mise run fmt

lint:
	@mise run lint

typecheck:
	@mise run typecheck

clean:
	@mise run clean

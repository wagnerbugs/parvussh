PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

APT_PACKAGES := python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                openssh-client xvfb

.PHONY: setup test test-gui lint format run check clean

setup:
	sudo apt install -y $(APT_PACKAGES)
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e '.[dev]'
	@echo "Ready. Run 'make run'."

# `python -m` rather than the console scripts: the venv is created with
# --system-site-packages, so a distro-provided pytest satisfies the dependency
# without ever placing a shim in $(BIN).
test:
	$(BIN)/python -m pytest

# Prefer xvfb so the suite never opens windows on the developer's screen, but
# fall back to the running session rather than failing on a machine without it.
test-gui:
	@if command -v xvfb-run >/dev/null 2>&1; then \
		xvfb-run -a $(BIN)/python -m pytest -m gui; \
	else \
		echo "xvfb-run not found; using the current display. 'make setup' installs xvfb."; \
		$(BIN)/python -m pytest -m gui; \
	fi

lint:
	$(BIN)/python -m ruff check .
	$(BIN)/python -m ruff format --check .

format:
	$(BIN)/python -m ruff check --fix .
	$(BIN)/python -m ruff format .

run:
	$(BIN)/python -m parvussh

check: lint test test-gui

clean:
	rm -rf build dist .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

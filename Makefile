PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

APP_ID    := io.github.wagnerbugs.ParvuSsh
DATA_HOME ?= $(HOME)/.local/share

APT_PACKAGES := python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                openssh-client xvfb

.PHONY: setup test test-gui lint format run check clean \
        install-user uninstall-user screenshots

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

# Put the launcher and the icons where GNOME looks, for this user only.
# No sudo: nothing outside $(HOME) is touched.
install-user:
	install -Dm644 data/$(APP_ID).desktop \
		$(DATA_HOME)/applications/$(APP_ID).desktop
	install -Dm644 data/icons/hicolor/scalable/apps/$(APP_ID).svg \
		$(DATA_HOME)/icons/hicolor/scalable/apps/$(APP_ID).svg
	install -Dm644 data/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg \
		$(DATA_HOME)/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg
	install -Dm644 data/$(APP_ID).metainfo.xml \
		$(DATA_HOME)/metainfo/$(APP_ID).metainfo.xml
	# The .desktop Exec= is just `parvussh`, so point it at this checkout.
	sed -i 's|^Exec=.*|Exec=$(CURDIR)/$(BIN)/python -m parvussh|' \
		$(DATA_HOME)/applications/$(APP_ID).desktop
	-update-desktop-database $(DATA_HOME)/applications 2>/dev/null
	-gtk4-update-icon-cache -qtf $(DATA_HOME)/icons/hicolor 2>/dev/null
	@echo "Installed. Look for ParvuSsh in the app grid."

uninstall-user:
	rm -f $(DATA_HOME)/applications/$(APP_ID).desktop
	rm -f $(DATA_HOME)/icons/hicolor/scalable/apps/$(APP_ID).svg
	rm -f $(DATA_HOME)/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg
	rm -f $(DATA_HOME)/metainfo/$(APP_ID).metainfo.xml
	-update-desktop-database $(DATA_HOME)/applications 2>/dev/null
	@echo "Removed."

# Regenerate the README images from a sample config.
screenshots:
	xvfb-run -a $(BIN)/python tools/screenshot.py docs/screenshots

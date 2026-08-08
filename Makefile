PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

APP_ID    := io.github.wagnerbugs.ParvuSsh
DATA_HOME ?= $(HOME)/.local/share

# Optionally pin the interface language into the launcher:
#
#     make install-user PARVUSSH_LANG=en
#
# Left unset — the default — the app follows the system locale, which is what
# GNOME applications do and why there is no language menu inside the app.
#
# Named after the runtime variable rather than something like LANG: make
# imports the environment, and LANG is always set, so `make install-user`
# would silently bake in whatever the shell happened to be using.
PARVUSSH_LANG ?=

ifeq ($(strip $(PARVUSSH_LANG)),)
LAUNCH_COMMAND := $(CURDIR)/$(BIN)/python -m parvussh
else
LAUNCH_COMMAND := env PARVUSSH_LANG=$(strip $(PARVUSSH_LANG)) $(CURDIR)/$(BIN)/python -m parvussh
endif

.PHONY: setup test test-gui lint format run check clean \
        install-user uninstall-user check-lang check-stack \
        screenshots icon-preview \
        flatpak flatpak-run flatpak-uninstall

# The system stack comes from the distribution, and the distribution decides
# the package names. This prints the right command for whichever manager is
# here rather than shelling out to one of them: assuming apt is what used to
# make `make setup` fail on the first line everywhere else.
check-stack:
	@$(PYTHON) tools/check_stack.py

setup: check-stack
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
install-user: check-lang
	install -Dm644 data/$(APP_ID).desktop \
		$(DATA_HOME)/applications/$(APP_ID).desktop
	install -Dm644 data/icons/hicolor/scalable/apps/$(APP_ID).svg \
		$(DATA_HOME)/icons/hicolor/scalable/apps/$(APP_ID).svg
	install -Dm644 data/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg \
		$(DATA_HOME)/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg
	install -Dm644 data/$(APP_ID).metainfo.xml \
		$(DATA_HOME)/metainfo/$(APP_ID).metainfo.xml
	# The .desktop Exec= is just `parvussh`, so point it at this checkout.
	sed -i 's|^Exec=.*|Exec=$(LAUNCH_COMMAND)|' \
		$(DATA_HOME)/applications/$(APP_ID).desktop
	-update-desktop-database $(DATA_HOME)/applications 2>/dev/null
	-gtk4-update-icon-cache -qtf $(DATA_HOME)/icons/hicolor 2>/dev/null
	@echo "Installed. Look for ParvuSsh in the app grid."
	@if [ -n "$(strip $(PARVUSSH_LANG))" ]; then \
		echo "The launcher is pinned to PARVUSSH_LANG=$(strip $(PARVUSSH_LANG))."; \
		echo "Run 'make install-user' with no arguments to follow the system again."; \
	fi

# Refuse a language we do not ship, rather than installing a launcher that
# silently falls back to the default.
check-lang:
	@if [ -n "$(strip $(PARVUSSH_LANG))" ] && \
	   ! $(BIN)/python -c "import sys; from parvussh.i18n import available_locales; \
	     sys.exit(0 if '$(strip $(PARVUSSH_LANG))' in available_locales() else 1)"; then \
		echo "PARVUSSH_LANG=$(strip $(PARVUSSH_LANG)) is not a language this app ships."; \
		echo -n "Available: "; \
		$(BIN)/python -c "from parvussh.i18n import available_locales; print(*available_locales())"; \
		exit 1; \
	fi

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

# Regenerate docs/icon-preview.png from the committed SVGs.
icon-preview:
	$(BIN)/python tools/icon_preview.py docs/icon-preview.png

# Build the Flatpak from the working tree and install it for this user.
#
# --disable-rofiles-fuse: the build only uses FUSE to make its own staging
# directory read-only, and it is unavailable in containers and in some
# sandboxed shells, where flatpak-builder stops with "Failure spawning
# rofiles-fuse". Nothing about the resulting app changes.
flatpak:
	flatpak-builder --user --install --force-clean --disable-rofiles-fuse \
		build-flatpak $(APP_ID).yaml

flatpak-run:
	flatpak run $(APP_ID)

flatpak-uninstall:
	flatpak uninstall --user --assumeyes $(APP_ID)
	rm -rf build-flatpak .flatpak-builder

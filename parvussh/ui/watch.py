"""Notice when another program writes a loaded config file.

Saving is already safe without this — a save reads the file again and replays
the edit on top of whatever changed. What the watch adds is a list that does
not lie in the meantime: a server another program moved to `Port 1310` shows
`1310` without a trip to Recarregar.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)

#: One write is several events — a temp file renamed over the target, a
#: chmod, or a truncate followed by the text — so they are reported once,
#: after this long without another.
SETTLE_MS = 300


class ConfigWatch:
    """Call `on_change` once the loaded files have stopped changing.

    Whether anything really changed is the caller's question: our own saves
    fire the same events.
    """

    def __init__(self, on_change: Callable[[], None]) -> None:
        self.on_change = on_change
        self.monitors: list[Gio.FileMonitor] = []
        self.pending = 0

    def follow(self, paths: list[Path]) -> None:
        """Watch exactly these files, replacing whatever was watched before.

        A file monitor watches the name in its directory, so it survives the
        file being replaced by a rename — which is how we, and any careful
        program, write it.
        """
        for monitor in self.monitors:
            monitor.cancel()
        self.monitors = []
        for path in paths:
            try:
                monitor = Gio.File.new_for_path(str(path)).monitor_file(
                    Gio.FileMonitorFlags.WATCH_MOVES, None
                )
            except GLib.Error as error:
                # Not watching costs a stale list, never a wrong save.
                log.warning("not watching %s for changes: %s", path, error)
                continue
            monitor.connect("changed", self._on_event)
            self.monitors.append(monitor)

    def _on_event(self, *_args: object) -> None:
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(SETTLE_MS, self._settled)

    def _settled(self) -> bool:
        self.pending = 0
        self.on_change()
        return False  # GLib.timeout_add: run once

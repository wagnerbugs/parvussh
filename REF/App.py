"""Ponto de entrada da aplicação."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from . import __version__  # noqa: E402
from .window import ParvuSshWindow  # noqa: E402

APP_ID = "io.github.OWNER.ParvuSsh"


class ParvuSshApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.props.active_window or ParvuSshWindow(application=self)
        window.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self._about)
        self.add_action(action)

    def _about(self, *_):
        Adw.AboutDialog(
            application_name="ParvuSsh",
            application_icon="network-server-symbolic",
            version=__version__,
            license_type=Gtk.License.MIT_X11,
            comments="Gerencia o ~/.ssh/config sem esconder o ~/.ssh/config.",
        ).present(self.props.active_window)


def main() -> int:
    return ParvuSshApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
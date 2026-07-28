"""`Adw.Application` and the process entry point."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from parvussh import APP_ID, APP_NAME, __version__  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.window import ParvuSshWindow  # noqa: E402

HOMEPAGE = "https://github.com/wagnerbugs/parvussh"


class ParvuSshApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

    def do_activate(self) -> None:
        window = self.props.active_window or ParvuSshWindow(application=self)
        window.present()

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self._show_about)
        self.add_action(action)

    def _show_about(self, *_args: object) -> None:
        Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=__version__,
            comments=t("app.comments"),
            developer_name=t("app.developer"),
            # libadwaita has no "or later" variant; LICENSE is authoritative.
            license_type=Gtk.License.GPL_3_0,
            website=HOMEPAGE,
            issue_url=f"{HOMEPAGE}/issues",
        ).present(self.props.active_window)


def main() -> int:
    return ParvuSshApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())

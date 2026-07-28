"""Render the interface to PNG files, for the README.

Development tool, not part of the package. Run it through `make screenshots`,
which wraps it in `xvfb-run` — presenting these windows on a live session
steals keyboard focus from whoever is using the machine.

The app is pointed at a throwaway `$HOME` holding a sample config, so the
images never show anybody's real servers.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gsk, Gtk  # noqa: E402

WIDTH, HEIGHT = 1020, 700
SETTLE_MS = 700

SAMPLE_CONFIG = """# Configuração pessoal

Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_blog
    Compression yes
    ServerAliveInterval 60
    StrictHostKeyChecking accept-new

Host github.com
    User git
    IdentityFile ~/.ssh/id_github
    IdentitiesOnly yes

Host bastion-cliente
    HostName 198.51.100.7
    User wagner
    ProxyJump bastion

Host *
    AddKeysToAgent yes
"""


def sample_home() -> Path:
    home = Path(tempfile.mkdtemp(prefix="parvussh-shots-"))
    (home / ".ssh").mkdir(mode=0o700)
    (home / ".ssh" / "config").write_text(SAMPLE_CONFIG, encoding="utf-8")
    return home


def capture(widget: Gtk.Widget, path: Path) -> None:
    paintable = Gtk.WidgetPaintable.new(widget)
    snapshot = Gtk.Snapshot()
    paintable.snapshot(snapshot, WIDTH, HEIGHT)
    node = snapshot.to_node()
    if node is None:
        raise SystemExit(f"nothing to render for {path.name}")
    renderer = Gsk.CairoRenderer()
    renderer.realize(None)
    renderer.render_texture(node, None).save_to_png(str(path))
    renderer.unrealize()
    print(f"wrote {path}")


def steps(window: Gtk.Window, out: Path) -> Iterator[Callable[[], None]]:
    """One screenshot per step, with a settle pause between them.

    Only dialogs are captured, never popovers: a `Gtk.Popover` renders into
    its own surface, so a paintable of the window does not see it.
    """
    from parvussh.core.tester import REACHABLE, TestResult
    from parvussh.ui.dialogs import TestResultDialog
    from parvussh.ui.help import HelpDialog

    def connection() -> None:
        window.sidebar.listbox.select_row(window.sidebar.rows()[0])

    def test_result() -> None:
        capture(window, out / "conexao.png")
        TestResultDialog(
            TestResult(
                REACHABLE,
                "deploy@203.0.113.10: Permission denied (publickey).",
                255,
            )
        ).present(window)

    def help_page() -> None:
        capture(window, out / "teste.png")
        HelpDialog().present(window)

    def last() -> None:
        capture(window, out / "ajuda.png")

    yield connection
    yield test_result
    yield help_page
    yield last


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots")
    out.mkdir(parents=True, exist_ok=True)
    home = sample_home()
    Path.home = classmethod(lambda cls: home)  # type: ignore[method-assign]

    from parvussh.ui.app import register_icons
    from parvussh.ui.window import ParvuSshWindow

    app = Adw.Application(application_id="io.github.wagnerbugs.ParvuSshShots")

    def start(app: Adw.Application) -> None:
        register_icons()
        window = ParvuSshWindow(application=app)
        window.set_default_size(WIDTH, HEIGHT)
        window.present()
        pending = steps(window, out)

        def tick() -> bool:
            try:
                next(pending)()
            except StopIteration:
                app.quit()
                return False
            GLib.timeout_add(SETTLE_MS, tick)
            return False

        GLib.timeout_add(SETTLE_MS, tick)

    app.connect("activate", start)
    return app.run([])


if __name__ == "__main__":
    raise SystemExit(main())

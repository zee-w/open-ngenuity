"""Application entry point."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from open_ngenuity.window import HasteWindow

APP_ID = "io.github.zeeshan.OpenNGenuity"


class OpenNGenuityApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app: Adw.Application) -> None:
        window = self.props.active_window
        if window is None:
            window = HasteWindow(self)
        window.present()


def main(argv: list[str] | None = None) -> int:
    app = OpenNGenuityApp()
    return app.run(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())

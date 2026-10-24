"""Main window: DPI stages and polling rate."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from open_ngenuity.device_path import find_hidraw
from open_ngenuity.ngenuity_backend import (
    DPI_MAX,
    DPI_MIN,
    DPI_STEP,
    POLLING_RATES,
    MouseSettings,
    NgenuityBackend,
    NgenuityError,
)

_NO_DONGLE = (
    "Plug in the 2.4 GHz dongle. Bluetooth mode cannot be configured — "
    "switch the mouse to 2.4 GHz and wake it by moving it."
)


class HasteWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Open NGenuity")
        self.set_default_size(520, 640)
        self._busy = False
        self._stage_spins: list[Gtk.SpinButton] = []
        self._stage_checks: list[Gtk.CheckButton] = []
        self._stage_rows: list[Adw.ActionRow] = []

        self._toast = Adw.ToastOverlay()
        self._banner = Adw.Banner()
        self._banner.set_button_label("Retry")
        self._banner.connect("button-clicked", lambda *_: self.refresh())

        self._device_row = Adw.ActionRow(title="Device")
        self._state_row = Adw.ActionRow(title="State")
        self._battery_row = Adw.ActionRow(title="Battery")
        self._interface_row = Adw.ActionRow(title="Interface")

        self._dpi_group = Adw.PreferencesGroup(
            title="DPI stages",
            description="Stages are stored on the mouse and cycled with the DPI button.",
        )
        self._polling = Gtk.DropDown.new_from_strings([f"{rate} Hz" for rate in POLLING_RATES])
        polling_row = Adw.ActionRow(title="Polling rate")
        polling_row.add_suffix(self._polling)
        polling_row.set_activatable_widget(self._polling)

        self._save = Gtk.Switch(valign=Gtk.Align.CENTER)
        save_row = Adw.ActionRow(
            title="Save to onboard memory",
            subtitle="Keep the settings after a power cycle (NGENUITY Save).",
        )
        save_row.add_suffix(self._save)
        save_row.set_activatable_widget(self._save)

        self._apply = Gtk.Button(label="Apply", css_classes=["suggested-action"])
        self._apply.connect("clicked", lambda *_: self.apply())
        apply_row = Adw.ActionRow(title="Write to mouse")
        apply_row.add_suffix(self._apply)

        device_group = Adw.PreferencesGroup(title="Mouse")
        for row in (self._device_row, self._state_row, self._battery_row, self._interface_row):
            device_group.add(row)

        polling_group = Adw.PreferencesGroup(title="Polling")
        polling_group.add(polling_row)

        write_group = Adw.PreferencesGroup(title="Write")
        write_group.add(save_row)
        write_group.add(apply_row)

        page = Adw.PreferencesPage()
        page.add(device_group)
        page.add(self._dpi_group)
        page.add(polling_group)
        page.add(write_group)

        header = Adw.HeaderBar()
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh.connect("clicked", lambda *_: self.refresh())
        header.pack_start(refresh)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._banner)
        content.append(page)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        self._toast.set_child(toolbar)
        self.set_content(self._toast)

        self.connect("map", lambda *_: self.refresh())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._apply.set_sensitive(not busy)
        self._polling.set_sensitive(not busy)
        self._save.set_sensitive(not busy)
        for spin in self._stage_spins:
            spin.set_sensitive(not busy)
        for check in self._stage_checks:
            check.set_sensitive(not busy)

    def _show_error(self, message: str, *, asleep: bool = False) -> None:
        self._banner.set_title(message)
        self._banner.set_revealed(True)
        if asleep:
            self._state_row.set_subtitle("asleep — move the mouse")

    def _clear_error(self) -> None:
        self._banner.set_revealed(False)

    def _toast_msg(self, message: str) -> None:
        self._toast.add_toast(Adw.Toast(title=message, timeout=3))

    def _run_async(self, work: Callable[[], object], done: Callable[[object | BaseException], None]) -> None:
        if self._busy:
            return
        self._set_busy(True)

        def thread() -> None:
            try:
                result: object | BaseException = work()
            except BaseException as error:  # noqa: BLE001 — surface to UI
                result = error
            GLib.idle_add(lambda: self._finish_async(result, done))

        threading.Thread(target=thread, daemon=True).start()

    def _finish_async(
        self, result: object | BaseException, done: Callable[[object | BaseException], None]
    ) -> bool:
        self._set_busy(False)
        done(result)
        return False

    def refresh(self) -> None:
        hidraw = find_hidraw()
        if hidraw is None:
            self._show_error(_NO_DONGLE)
            self._device_row.set_subtitle("not found")
            self._state_row.set_subtitle("—")
            self._battery_row.set_subtitle("—")
            self._interface_row.set_subtitle("—")
            return

        backend = NgenuityBackend(hidraw)

        def work() -> MouseSettings:
            return backend.read()

        def done(result: object | BaseException) -> None:
            if isinstance(result, NgenuityError):
                self._show_error(str(result), asleep=result.asleep)
                if result.asleep:
                    try:
                        status = backend.status()
                    except NgenuityError:
                        return
                    self._fill_status(status.device, status.state, status.battery_percent, status.charging, status.interface)
                return
            if isinstance(result, BaseException):
                self._show_error(str(result))
                return
            assert isinstance(result, MouseSettings)
            self._clear_error()
            self._load_settings(result)

        self._run_async(work, done)

    def _fill_status(
        self,
        device: str,
        state: str,
        battery: int | None,
        charging: str | None,
        interface: str,
    ) -> None:
        self._device_row.set_subtitle(device)
        self._state_row.set_subtitle(state)
        if battery is None:
            self._battery_row.set_subtitle("—")
        else:
            extra = f" ({charging})" if charging else ""
            self._battery_row.set_subtitle(f"{battery}%{extra}")
        self._interface_row.set_subtitle(interface)

    def _load_settings(self, settings: MouseSettings) -> None:
        status = settings.status
        self._fill_status(
            status.device, status.state, status.battery_percent, status.charging, status.interface
        )
        self._rebuild_stages(settings)
        try:
            index = POLLING_RATES.index(settings.polling_hz)
        except ValueError:
            index = POLLING_RATES.index(1000)
        self._polling.set_selected(index)

    def _rebuild_stages(self, settings: MouseSettings) -> None:
        for row in self._stage_rows:
            self._dpi_group.remove(row)
        self._stage_rows.clear()
        self._stage_spins.clear()
        self._stage_checks.clear()

        group_root: Gtk.CheckButton | None = None
        for stage in settings.stages:
            check = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            if group_root is None:
                group_root = check
            else:
                check.set_group(group_root)
            check.set_active(stage.active)
            adjustment = Gtk.Adjustment(
                value=stage.dpi,
                lower=DPI_MIN,
                upper=DPI_MAX,
                step_increment=DPI_STEP,
                page_increment=DPI_STEP * 8,
            )
            spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=DPI_STEP, digits=0)
            spin.set_valign(Gtk.Align.CENTER)
            spin.set_width_chars(6)
            spin.set_snap_to_ticks(True)
            row = Adw.ActionRow(title=f"Stage {stage.index}", subtitle=stage.colour)
            row.add_prefix(check)
            row.add_suffix(spin)
            self._dpi_group.add(row)
            self._stage_rows.append(row)
            self._stage_spins.append(spin)
            self._stage_checks.append(check)

    def apply(self) -> None:
        hidraw = find_hidraw()
        if hidraw is None:
            self._show_error(_NO_DONGLE)
            return
        if not self._stage_spins:
            self._show_error("Refresh the mouse first.")
            return

        stages: list[tuple[int, int]] = []
        active = 1
        for index, (spin, check) in enumerate(zip(self._stage_spins, self._stage_checks, strict=True), start=1):
            dpi = int(spin.get_value())
            dpi = max(DPI_MIN, min(DPI_MAX, dpi - (dpi % DPI_STEP)))
            spin.set_value(dpi)
            stages.append((index, dpi))
            if check.get_active():
                active = index
        polling = POLLING_RATES[self._polling.get_selected()]
        save = self._save.get_active()
        backend = NgenuityBackend(hidraw)

        def work() -> str:
            backend.apply(stages, active, polling, save=save)
            return "Saved to onboard memory." if save else "Applied (live, not saved)."

        def done(result: object | BaseException) -> None:
            if isinstance(result, NgenuityError):
                self._show_error(str(result), asleep=result.asleep)
                return
            if isinstance(result, BaseException):
                self._show_error(str(result))
                return
            self._clear_error()
            self._toast_msg(str(result))
            self.refresh()

        self._run_async(work, done)

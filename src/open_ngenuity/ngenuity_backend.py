"""Subprocess wrapper around the `ngenuity` CLI."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DPI_MIN = 50
DPI_MAX = 12_000
DPI_STEP = 50
POLLING_RATES = (125, 250, 500, 1000)
COMMAND_TIMEOUT = 8.0

_STAGE_RE = re.compile(
    r"^ (?P<active>[* ])\s+(?P<stage>\d+)\s+(?P<dpi>\d+)\s+(?P<colour>\S+)"
)
_POLLING_RE = re.compile(r"Polling rate:\s+(\d+)\s*Hz")
_STATE_RE = re.compile(r"^State:\s+(.+)$", re.MULTILINE)
_BATTERY_RE = re.compile(r"^Battery:\s+(\d+)\s*%\s+\(([^)]+)\)", re.MULTILINE)
_DEVICE_RE = re.compile(r"^Device:\s+(.+)$", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^Interface:\s+(.+)$", re.MULTILINE)


class NgenuityError(Exception):
    def __init__(self, message: str, *, asleep: bool = False) -> None:
        super().__init__(message)
        self.asleep = asleep


@dataclass(frozen=True)
class DpiStage:
    index: int
    dpi: int
    colour: str
    active: bool


@dataclass(frozen=True)
class MouseStatus:
    device: str
    interface: str
    state: str
    battery_percent: int | None
    charging: str | None
    asleep: bool


@dataclass(frozen=True)
class MouseSettings:
    stages: tuple[DpiStage, ...]
    polling_hz: int
    status: MouseStatus


class NgenuityBackend:
    def __init__(self, hidraw: Path, ngenuity: str | None = None) -> None:
        self.hidraw = hidraw
        self.binary = ngenuity or shutil.which("ngenuity")
        if not self.binary:
            raise NgenuityError(
                "ngenuity is not installed. Install ngenuity-linux-cli or the Flatpak."
            )

    def _run(self, *args: str) -> str:
        command = [self.binary, "-d", str(self.hidraw), *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise NgenuityError("The mouse did not reply in time. Wake it and try again.") from error
        except OSError as error:
            raise NgenuityError(f"Could not start ngenuity: {error}") from error

        text = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        if result.returncode != 0:
            message = _click_message(result.stderr or result.stdout or "ngenuity failed")
            raise NgenuityError(message, asleep=_is_asleep(message))
        return result.stdout

    def status(self) -> MouseStatus:
        return parse_status(self._run("status"))

    def read(self) -> MouseSettings:
        status = self.status()
        if status.asleep:
            raise NgenuityError(
                "The device is asleep or switched off. Move it and try again.",
                asleep=True,
            )
        dpi_out = self._run("dpi")
        return MouseSettings(
            stages=parse_dpi_stages(dpi_out),
            polling_hz=parse_polling(dpi_out),
            status=status,
        )

    def apply(
        self,
        stages: list[tuple[int, int]],
        active_stage: int,
        polling_hz: int,
        *,
        save: bool,
    ) -> None:
        extra = ("--save",) if save else ()
        for stage, dpi in stages:
            self._run("dpi", "set", str(stage), str(dpi), *extra)
        self._run("dpi", "select", str(active_stage), *extra)
        self._run("polling", str(polling_hz), *extra)


def parse_dpi_stages(text: str) -> tuple[DpiStage, ...]:
    stages: list[DpiStage] = []
    for line in text.splitlines():
        match = _STAGE_RE.match(line)
        if not match:
            continue
        stages.append(
            DpiStage(
                index=int(match.group("stage")),
                dpi=int(match.group("dpi")),
                colour=match.group("colour"),
                active=match.group("active") == "*",
            )
        )
    if not stages:
        raise NgenuityError("Could not parse DPI stages from ngenuity output.")
    return tuple(stages)


def parse_polling(text: str) -> int:
    match = _POLLING_RE.search(text)
    if not match:
        raise NgenuityError("Could not parse polling rate from ngenuity output.")
    return int(match.group(1))


def parse_status(text: str) -> MouseStatus:
    state_match = _STATE_RE.search(text)
    state = state_match.group(1).strip() if state_match else "unknown"
    asleep = "asleep" in state.lower()
    battery_match = _BATTERY_RE.search(text)
    device_match = _DEVICE_RE.search(text)
    interface_match = _INTERFACE_RE.search(text)
    return MouseStatus(
        device=device_match.group(1).strip() if device_match else "HyperX mouse",
        interface=interface_match.group(1).strip() if interface_match else "",
        state=state,
        battery_percent=int(battery_match.group(1)) if battery_match else None,
        charging=battery_match.group(2) if battery_match else None,
        asleep=asleep,
    )


def _click_message(text: str) -> str:
    for prefix in ("Error: ", "Error:"):
        if prefix in text:
            return text.split(prefix, 1)[1].strip()
    return text.strip() or "ngenuity failed"


def _is_asleep(message: str) -> bool:
    lowered = message.lower()
    return "asleep" in lowered or "switched off" in lowered

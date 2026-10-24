"""Locate the Haste 2 Core vendor HID interface (USB interface 2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

VENDOR_ID = "03f0"
PRODUCT_ID = "0ab5"
INTERFACE_NUM = "02"
BY_ID_SUBSTRING = "HyperX_Pulsefire_Haste_2_Core"
BY_ID_IFACE = "if02-hidraw"


def find_hidraw() -> Path | None:
    """Return the resolved `/dev/hidrawN` path for the Core vendor interface."""
    found = _from_by_id() or _from_udevadm()
    return found.resolve() if found is not None else None


def _from_by_id() -> Path | None:
    by_id = Path("/dev/input/by-id")
    if not by_id.is_dir():
        return None
    matches = sorted(
        path
        for path in by_id.iterdir()
        if BY_ID_SUBSTRING in path.name and BY_ID_IFACE in path.name
    )
    return matches[0] if matches else None


def _from_udevadm() -> Path | None:
    for node in sorted(Path("/dev").glob("hidraw*")):
        props = _udevadm_properties(node)
        if (
            props.get("ID_USB_VENDOR_ID") == VENDOR_ID
            and props.get("ID_USB_MODEL_ID") == PRODUCT_ID
            and props.get("ID_USB_INTERFACE_NUM") == INTERFACE_NUM
        ):
            return node
    return None


def _udevadm_properties(node: Path) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["udevadm", "info", "-q", "property", "-n", str(node)],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return {}
    props: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key] = value
    return props

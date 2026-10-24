# Open NGenuity

A small GTK 4 (Libadwaita) app that sets **DPI stages** and **polling rate** on a
[HyperX Pulsefire Haste 2 Core Wireless](https://hyperx.com/products/hyperx-pulsefire-haste-2-core-wireless-gaming-mouse)
from Linux. Official NGENUITY is Windows-only.

The UI shells out to [`ngenuity-linux-cli`](https://github.com/PMarinov1994/ngenuity-linux-cli),
which speaks the NGENUITY “universal” HID protocol over the dongle’s vendor interface.

## Hardware

| | |
|---|---|
| Mouse | Pulsefire Haste 2 Core Wireless |
| Dongle USB ID | `03f0:0ab5` |
| Config interface | USB interface 2 (`/dev/hidraw*`, usage page `0xFF00`) |
| DPI | 50–12000, step 50 |
| Polling | 125 / 250 / 500 / 1000 Hz |

Use **2.4 GHz**. HyperX documents that NGENUITY does not work in **Bluetooth** mode.

If the mouse is asleep, move it and try again.

## Host udev rule (required)

Flatpak cannot install udev rules. One-time on the host:

```bash
sudo cp udev/70-hyperx-pulsefire-haste2-core.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Then unplug and replug the dongle. This grants the logged-in session access to
vendor interface 2 only (`uaccess`).

## Run from a checkout

Needs Python 3.12+, GTK 4, Libadwaita, and the patched CLI in `vendor/`:

```bash
pip install --user -e vendor/ngenuity-linux-cli
pip install --user -e .
PYTHONPATH=src open-ngenuity
```

## Flatpak

The sandbox needs `--device=all` so `/dev/hidraw*` is visible. That is broader
than a typical app; treat this as a hardware utility.

```bash
flatpak run --share=network --filesystem=host org.flatpak.Builder \
  --user --install --force-clean build-dir \
  flatpak/io.github.zeeshan.OpenNGenuity.yml
flatpak run io.github.zeeshan.OpenNGenuity
```

Runtime: `org.gnome.Platform//49`.

## Apply vs save

**Apply** writes the live slot (takes effect immediately, lost after power-off
unless the firmware copies it). Enable **Save to onboard memory** to also write
the profile NGENUITY stores on the mouse (`ngenuity … --save`).

## Upstream CLI patch

This tree vendors ngenuity-linux-cli with a **Pulsefire Haste 2 Core Wireless**
model (`product_ids=(0x0AB5,)`, `dpi_max=12000`, 1 kHz polling). Without that
entry, auto-detect reports the dongle as a headset because the device-info
category byte is not `Mouse`.

To send the same change upstream, copy:

- `vendor/ngenuity-linux-cli/src/ngenuity_linux_cli/devices.py`
- `vendor/ngenuity-linux-cli/docs/devices/pulsefire-haste-2-core-wireless.md`
- `vendor/ngenuity-linux-cli/70-hyperx-pulsefire-haste2.rules`

into a PR against [PMarinov1994/ngenuity-linux-cli](https://github.com/PMarinov1994/ngenuity-linux-cli).

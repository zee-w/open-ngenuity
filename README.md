# Open NGenuity

A small GTK 4 (Libadwaita) app that sets **DPI stages** and **polling rate** on a
[HyperX Pulsefire Haste 2 Core Wireless](https://hyperx.com/products/hyperx-pulsefire-haste-2-core-wireless-gaming-mouse)
from Linux. Official NGENUITY is Windows-only.

Source: [github.com/zee-w/open-ngenuity](https://github.com/zee-w/open-ngenuity)

The UI shells out to [`ngenuity-linux-cli`](https://github.com/PMarinov1994/ngenuity-linux-cli),
which speaks the NGENUITY “universal” HID protocol over the dongle’s vendor interface.

## What it does

- Finds the dongle’s vendor HID node (`/dev/hidraw*`, USB interface 2) automatically
- Shows **device**, **connection state**, **battery**, and the **hidraw** path
- Edit up to five **DPI stages** (50–12000, step 50) and pick the **active** stage
- Set **polling rate** (125 / 250 / 500 / 1000 Hz)
- **Apply** live settings or **save to onboard memory** (same idea as NGENUITY’s Save)
- **Refresh** after plug-in, wake-from-sleep, or errors

There is no Flathub package yet; Piper / libratbag do not speak this HyperX protocol.
Build the Flatpak below or run from a checkout.

## Hardware

| | |
|---|---|
| Mouse | Pulsefire Haste 2 Core Wireless |
| Dongle USB ID | `03f0:0ab5` |
| Config interface | USB interface 2 (`/dev/hidraw*`, usage page `0xFF00`) |
| DPI | 50–12000, step 50 |
| Polling | 125 / 250 / 500 / 1000 Hz |

Use **2.4 GHz**. HyperX documents that NGENUITY does not work in **Bluetooth** mode.

If the mouse is asleep, move it and tap **Refresh**.

## Host udev rule (required)

Flatpak cannot install udev rules. One-time on the host:

```bash
sudo cp udev/70-hyperx-pulsefire-haste2-core.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Then unplug and replug the dongle. This grants the logged-in session access to
vendor interface 2 only (`uaccess`).

## Get the source

```bash
git clone --recurse-submodules https://github.com/zee-w/open-ngenuity.git
cd open-ngenuity
```

If you already cloned without submodules:

```bash
git submodule update --init vendor/ngenuity-linux-cli
```

That checks out the pinned upstream commit (`bc35dc4`). Apply the Haste 2 Core
patches listed in [`vendor/UPSTREAM.md`](vendor/UPSTREAM.md) (device model for
`03f0:0ab5`, docs, udev rule, and packaging tweaks) before building.

## Run from a checkout

Needs **Python 3.12+**, **GTK 4**, **Libadwaita**, and the vendored CLI.

On Fedora, for example:

```bash
sudo dnf install python3-devel gtk4 libadwaita python3-gobject
```

Install and run:

```bash
pip install --user -e vendor/ngenuity-linux-cli
pip install --user -e .
open-ngenuity
```

The `ngenuity` command must be on your `PATH` (installed with the vendored CLI).

### Tests

```bash
pip install --user -e .
python -m unittest discover -s tests -v
```

## Flatpak

The sandbox needs `--device=all` so `/dev/hidraw*` is visible. That is broader
than a typical app; treat this as a hardware utility.

Runtime: `org.gnome.Platform//49`.

### Prerequisites

You do **not** need the `flatpak-builder` binary on your PATH. The usual approach
is the **Flatpak Builder** app from Flathub:

```bash
flatpak install flathub org.flatpak.Builder
flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49
```

Optional: `sudo dnf install flatpak-builder` if you prefer running `flatpak-builder`
directly on the host.

### Build and install (user)

Run from the **repository root**:

```bash
flatpak run --share=network --filesystem=host org.flatpak.Builder \
  --user --install --force-clean build-dir \
  flatpak/io.github.zeeshan.OpenNGenuity.yml

flatpak run io.github.zeeshan.OpenNGenuity
```

- `--share=network` — fetch the Click wheel and SDK bits during the build  
- `--filesystem=host` — let Builder read `vendor/`, `src/`, and `data/` via the manifest paths  

### Optional: `.flatpak` bundle

After a successful build into a local repo:

```bash
flatpak run --share=network --filesystem=host org.flatpak.Builder \
  --repo=repo --force-clean build-dir \
  flatpak/io.github.zeeshan.OpenNGenuity.yml

flatpak build-bundle repo open-ngenuity.flatpak io.github.zeeshan.OpenNGenuity
```

Install the bundle on another machine (still needs the host udev rule and, unless
the runtime is already present, `org.gnome.Platform//49`):

```bash
flatpak install --user open-ngenuity.flatpak
```

Build artifacts (`build-dir/`, `repo/`, `.flatpak-builder/`) are gitignored.

## Apply vs save

**Apply** writes the live slot (takes effect immediately, lost after power-off
unless the firmware copies it). Enable **Save to onboard memory** to also write
the profile NGENUITY stores on the mouse (`ngenuity … --save`).

## Upstream CLI patch

This tree vendors ngenuity-linux-cli with a **Pulsefire Haste 2 Core Wireless**
model (`product_ids=(0x0AB5,)`, `dpi_max=12000`, 1 kHz polling). Without that
entry, auto-detect reports the dongle as a headset because the device-info
category byte is not `Mouse`.

Details and the pinned upstream commit: [`vendor/UPSTREAM.md`](vendor/UPSTREAM.md).

To send the same change upstream, copy:

- `vendor/ngenuity-linux-cli/src/ngenuity_linux_cli/devices.py`
- `vendor/ngenuity-linux-cli/docs/devices/pulsefire-haste-2-core-wireless.md`
- `vendor/ngenuity-linux-cli/70-hyperx-pulsefire-haste2.rules`

into a PR against [PMarinov1994/ngenuity-linux-cli](https://github.com/PMarinov1994/ngenuity-linux-cli).

Vendored from https://github.com/PMarinov1994/ngenuity-linux-cli

- Base commit: `bc35dc4edfebc2ddf877d0acb4d967b68345f272`
- Local version: `2.0.1` (static, hatch-vcs removed so Flatpak `pip`-less install works)

Local changes:

- `pulsefire-haste-2-core-wireless` model, USB `03f0:0ab5`, DPI 50–12000, 1 kHz polling
- device notes under `docs/devices/pulsefire-haste-2-core-wireless.md`
- udev rule for `0ab5` interface 2
- `__version__` fallback when package metadata is missing

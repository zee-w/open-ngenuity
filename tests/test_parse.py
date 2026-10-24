"""Parser tests against captured ngenuity CLI stdout."""

from __future__ import annotations

import unittest

from open_ngenuity.ngenuity_backend import parse_dpi_stages, parse_polling, parse_status

DPI_SAMPLE = """\
   Stage    DPI  Colour
       1   1600  #ff0000 (red)
       2    800  #0000ff (blue)
       3   1600  #ffff00 (yellow)
 *     4   3200  #00ff00 (green)
Polling rate: 1000 Hz
"""

STATUS_SAMPLE = """\
Device:       Pulsefire Haste 2 Core Wireless (tested)
Interface:    /dev/hidraw6 (HP, Inc HyperX Pulsefire Haste 2 Core Wireless)
Device ID:    450c976f953c7918257d41a3
State:        connected
Battery:      70 % (not charging)
Voltage:      0 mV
Temperature:  0 °C
"""

ASLEEP_SAMPLE = """\
Device:       Pulsefire Haste 2 Core Wireless (tested)
Interface:    /dev/hidraw6 (HP, Inc HyperX Pulsefire Haste 2 Core Wireless)
Device ID:    450c976f953c7918257d41a3
State:        asleep or switched off (move it to wake it up)
"""


class ParseTests(unittest.TestCase):
    def test_dpi_stages(self) -> None:
        stages = parse_dpi_stages(DPI_SAMPLE)
        self.assertEqual(len(stages), 4)
        self.assertEqual(stages[0].dpi, 1600)
        self.assertFalse(stages[0].active)
        self.assertEqual(stages[1].dpi, 800)
        self.assertTrue(stages[3].active)
        self.assertEqual(stages[3].index, 4)
        self.assertEqual(parse_polling(DPI_SAMPLE), 1000)

    def test_status_connected(self) -> None:
        status = parse_status(STATUS_SAMPLE)
        self.assertFalse(status.asleep)
        self.assertEqual(status.battery_percent, 70)
        self.assertEqual(status.charging, "not charging")
        self.assertIn("Core", status.device)

    def test_status_asleep(self) -> None:
        status = parse_status(ASLEEP_SAMPLE)
        self.assertTrue(status.asleep)
        self.assertIsNone(status.battery_percent)


if __name__ == "__main__":
    unittest.main()

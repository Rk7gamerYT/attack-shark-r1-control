from pathlib import Path
import tempfile
import unittest
from mouse import discover, parse_battery


class BatteryTests(unittest.TestCase):
    def test_real_receiver_report(self):
        self.assertEqual(parse_battery(bytes.fromhex("03 10 40 01 08")), 80)

    def test_charge_including_zero(self):
        for value in (0, 5, 8, 10):
            self.assertEqual(parse_battery(bytes([3, 0, 0x40, 0, value])), value * 10)

    def test_rejects_unrelated_and_malformed_reports(self):
        for report in (b'', bytes([3, 0, 0x50, 0, 0]), bytes([1, 0, 0, 0, 8]), bytes([3, 0, 0x40, 0, 11]), bytes([3, 0, 8]), bytes(64)):
            self.assertIsNone(parse_battery(report))

    def test_only_correct_vendor_product_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i, (vendor, interface) in enumerate([('1D57', '02'), ('1D57', '01'), ('1234', '02')]):
                raw = root / f'hidraw{i}'
                raw.mkdir()
                usb = root / f'usb{i}'
                usb.mkdir()
                (usb / 'bInterfaceNumber').write_text(interface)
                hid = usb / 'hid'
                hid.mkdir()
                (hid / 'uevent').write_text(f'HID_ID=0003:0000{vendor}:0000FA60\n')
                (raw / 'device').symlink_to(hid, target_is_directory=True)
            self.assertEqual([r.node.name for r in discover(root)], ['hidraw0'])

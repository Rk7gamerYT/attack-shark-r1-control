import unittest
from unittest.mock import patch
from pathlib import Path
from mouse import Receiver
from settings import apply_settings
from settings import build_report, decode_report, DPI_CODES


class ProtocolTests(unittest.TestCase):
    def test_polling_vectors(self):
        for rate, hexdata in [(125, '06090108f700000000'), (1000, '06090101fe00000000')]:
            packet = build_report('polling', {'polling': rate})
            self.assertEqual(packet.hex(), hexdata)
            self.assertEqual(decode_report('polling', packet), {'polling': rate})

    def test_dpi_ranges_and_checksum(self):
        settings = dict(dpis=[100, 800, 10000, 10100, 12000, 18000], active=6, angle=True, ripple=False)
        packet = build_report('dpi', settings)
        self.assertEqual(len(packet), 56)
        self.assertEqual(packet[6:8], bytes([32, 32]))
        self.assertEqual(list(packet[16:22]), [0, 0, 0, 1, 1, 0])
        self.assertEqual(packet[50:52], sum(packet[3:50]).to_bytes(2, 'big'))
        self.assertEqual(decode_report('dpi', packet), settings)
        self.assertEqual(DPI_CODES[18000], 0xd3)

    def test_power_vector_and_roundtrip(self):
        values = dict(sleep=2, deep_sleep=1, debounce=4)
        packet = build_report('power', values)
        self.assertEqual(packet.hex(), '050f010003180000ff040201200000')
        for deep in range(1, 61):
            values['deep_sleep'] = deep
            self.assertEqual(decode_report('power', build_report('power', values)), values)

    def test_invalid_inputs_never_encoded(self):
        for section, data in [('dpi', dict(dpis=[800]*6, active=9, angle=False, ripple=False)),
                              ('polling', {'polling': 8000}), ('power', dict(sleep=0.7, deep_sleep=10, debounce=4)),
                              ('power', dict(sleep=1, deep_sleep=10, debounce=3))]:
            with self.assertRaises(ValueError):
                build_report(section, data)

    def test_uninitialized_device_responses_are_rejected(self):
        for section, size in [('dpi', 56), ('power', 15), ('polling', 9)]:
            with self.assertRaises(ValueError):
                decode_report(section, bytes(size))

    def test_ack_and_single_transmission(self):
        receiver = Receiver(Path('/dev/hidraw-test'), False)
        with patch('settings.os.open', return_value=42), patch('settings.os.close') as close, \
             patch('settings.os.read', side_effect=[BlockingIOError(), bytes.fromhex('0310500000')]), \
             patch('settings.ioctl_feature') as send, patch('settings.select.select', return_value=([42], [], [])):
            message = apply_settings(receiver, 'polling', {'polling': 500})
            self.assertIn('confirmou', message)
            send.assert_called_once_with(42, bytes.fromhex('06090102fd00000000'), write=True)
            close.assert_called_once_with(42)

    def test_timeout_does_not_repeat_or_claim_success(self):
        receiver = Receiver(Path('/dev/hidraw-test'), False)
        with patch('settings.os.open', return_value=42), patch('settings.os.close') as close, \
             patch('settings.os.read', side_effect=BlockingIOError()), patch('settings.ioctl_feature') as send, \
             patch('settings.time.monotonic', side_effect=[0, 3]):
            with self.assertRaises(TimeoutError):
                apply_settings(receiver, 'polling', {'polling': 500})
            self.assertEqual(send.call_count, 1)
            close.assert_called_once_with(42)

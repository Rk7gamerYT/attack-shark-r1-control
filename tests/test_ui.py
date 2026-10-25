import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app import Window
from settings import DEFAULTS


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_unknown_fields_and_explicit_apply(self):
        window = Window(True)
        window.timer.stop()
        window.scan_timer.stop()
        self.assertEqual(window.values()['dpis'], [0]*6)
        self.assertIsNone(window.values()['polling'])
        with patch.object(window, 'start_worker') as worker:
            window.apply_section('dpi')
            worker.assert_not_called()
            window.set_values(DEFAULTS, 'Sugestão')
            worker.assert_not_called()
            window.apply_section('dpi')
            self.assertEqual(worker.call_args.args[0]['section'], 'dpi')
        window.quitting = True
        window.close()

    def test_read_only_updates_valid_values(self):
        window = Window(True)
        window.timer.stop()
        window.scan_timer.stop()
        window.set_values({'polling': 500}, 'Lido')
        self.assertEqual(window.values()['polling'], 500)
        self.assertEqual(window.values()['dpis'], [0]*6)
        window.quitting = True
        window.close()

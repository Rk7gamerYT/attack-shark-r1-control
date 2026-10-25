"""Independent, read-only hidraw R1 battery reader; no kernel driver detachment."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Receiver:
    node: Path
    wired: bool


def discover(root=Path('/sys/class/hidraw'), dev_root=Path('/dev')):
    result = []
    for raw in sorted(Path(root).glob('hidraw*')):
        try:
            hid = (raw / 'device').resolve()
            data = dict(line.split('=', 1) for line in (hid / 'uevent').read_text().splitlines() if '=' in line)
            bus, vendor, product = (int(x, 16) for x in data.get('HID_ID', '').split(':'))
            if bus != 3 or vendor != 0x1D57 or product not in (0xFA60, 0xFA61):
                continue
            interface = next((p for p in hid.parents if (p / 'bInterfaceNumber').exists()), None)
            if interface is not None and int((interface / 'bInterfaceNumber').read_text(), 16) == 2:
                result.append(Receiver(Path(dev_root) / raw.name, product == 0xFA61))
        except (OSError, ValueError):
            continue
    return result


def parse_battery(report):
    # Receiver descriptor: report ID 3, four data bytes. Skip media/system keys.
    if len(report) != 5 or report[0] != 3 or report[2] != 0x40 or report[4] > 10:
        return None
    return report[4] * 10


class Monitor:
    def __init__(self, receiver):
        self.fd = os.open(receiver.node, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)

    def read(self):
        latest = None
        for _ in range(64):
            try:
                report = os.read(self.fd, 64)
            except BlockingIOError:
                break
            if not report:
                raise OSError('Receptor desconectado')
            value = parse_battery(report)
            if value is not None:
                latest = value
        return latest

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

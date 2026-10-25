"""R1 feature-report settings and validation. USB protocol data, not vendor code."""
import fcntl
import json
import os
from pathlib import Path
import select
import time

DPI_CODES = {int(k): v for k, v in json.loads(Path(__file__).with_name('r1_dpi.json').read_text()).items()}
POLLING = {125: 8, 250: 4, 500: 2, 1000: 1}
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'attack-shark-r1-control/settings.json'
DEFAULTS = dict(dpis=[800, 1600, 3200, 4000, 5000, 12000], active=1, angle=False,
                ripple=False, polling=1000, sleep=0.5, deep_sleep=10, debounce=4)


def build_report(section, data):
    if section == 'polling':
        rate = data.get('polling')
        if type(rate) is not int or rate not in POLLING:
            raise ValueError('Escolha 125, 250, 500 ou 1000 Hz.')
        v = POLLING[rate]
        return bytes([6, 9, 1, v, 255-v, 0, 0, 0, 0])
    if section == 'power':
        sleep, deep, debounce = (data.get(k) for k in ('sleep', 'deep_sleep', 'debounce'))
        if type(sleep) not in (float, int) or not 0.5 <= sleep <= 30 or sleep * 2 != int(sleep * 2):
            raise ValueError('Suspensão: 0,5–30 minutos, em passos de 0,5.')
        if type(deep) is not int or not 1 <= deep <= 60:
            raise ValueError('Suspensão profunda: 1–60 minutos.')
        if type(debounce) is not int or not 4 <= debounce <= 50 or debounce % 2:
            raise ValueError('Resposta dos botões: 4–50 ms, em passos de 2.')
        p = bytearray(15)
        p[:3] = bytes([5, 15, 1])
        p[4], p[5] = 3 | (deep & 0xf0), 8 | ((deep & 15) << 4)
        p[8], p[9], p[10], p[11] = 255, int(sleep*2), debounce//2, 1
        p[12] = (((deep & 15) + (deep >> 4)) * 16 + 10 + p[9] + p[10]) & 255
        return bytes(p)
    if section != 'dpi':
        raise ValueError('Seção desconhecida.')
    dpis, active = data.get('dpis'), data.get('active')
    if not isinstance(dpis, list) or len(dpis) != 6 or any(type(v) is not int or v not in DPI_CODES for v in dpis):
        raise ValueError('Preencha seis estágios de DPI: 100–18000, em passos de 100.')
    if type(active) is not int or not 1 <= active <= 6:
        raise ValueError('Escolha o estágio ativo entre 1 e 6.')
    if any(type(data.get(k)) is not bool for k in ('angle', 'ripple')):
        raise ValueError('Escolha ligar ou desligar correção de ângulo e suavização.')
    p = bytearray(56)
    p[:3] = bytes([4, 56, 1])
    p[3], p[4], p[5] = int(data['angle']), int(data['ripple']), 63
    mask = sum(1 << i for i, v in enumerate(dpis) if v > 12000)
    p[6] = p[7] = mask
    for i, dpi in enumerate(dpis):
        p[8+i], p[16+i] = DPI_CODES[dpi], int(10100 <= dpi <= 12000)
    p[24] = active
    # Reserved protocol bytes / stage indicator colors specified by the R1 reference.
    p[25:50] = bytes.fromhex('ff000000ff000000ffffff0000ffffff00ffff4000ffffff02')
    p[50:52] = sum(p[3:50]).to_bytes(2, 'big')
    return bytes(p)


def decode_report(section, p):
    """Reject unsupported/uninitialized GET_FEATURE replies instead of guessing."""
    expected = {'dpi': (4, 56), 'power': (5, 15), 'polling': (6, 9)}[section]
    if len(p) != expected[1] or p[:3] != bytes([expected[0], expected[1], 1]):
        raise ValueError('Firmware não retornou uma configuração válida.')
    if section == 'polling':
        if p[4] != 255-p[3] or p[3] not in POLLING.values():
            raise ValueError('Resposta de polling inválida.')
        return {'polling': next(rate for rate, code in POLLING.items() if code == p[3])}
    if section == 'power':
        deep = (p[4] & 0xf0) | (p[5] >> 4)
        values = dict(sleep=p[9]/2, deep_sleep=deep, debounce=p[10]*2)
        if build_report('power', values) != bytes(p):
            raise ValueError('Resposta de suspensão inválida.')
        return values
    if p[50:52] != sum(p[3:50]).to_bytes(2, 'big') or p[3] > 1 or p[4] > 1 or not 1 <= p[24] <= 6 or p[6] != p[7]:
        raise ValueError('Resposta de DPI inválida.')
    values = []
    for i in range(6):
        candidates = [v for v, code in DPI_CODES.items() if code == p[8+i]
                      and (v > 12000) == bool(p[6] & (1 << i))
                      and (10100 <= v <= 12000) == bool(p[16+i])]
        if len(candidates) != 1:
            raise ValueError('Codificação DPI desconhecida ou ambígua.')
        values.append(candidates[0])
    return dict(dpis=values, active=p[24], angle=bool(p[3]), ripple=bool(p[4]))


def ioctl_feature(fd, payload, write=False):
    buf = bytearray(payload)
    request = (3 << 30) | (len(buf) << 16) | (ord('H') << 8) | (6 if write else 7)
    size = fcntl.ioctl(fd, request, buf, True)
    if size != len(buf):
        raise OSError('Resposta HID incompleta.')
    return bytes(buf)


def read_settings(receiver):
    result, unavailable = {}, {}
    fd = os.open(receiver.node, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        for section, report, size in [('dpi', 4, 56), ('power', 5, 15), ('polling', 6, 9)]:
            try:
                buf = bytearray(size)
                buf[0] = report
                result.update(decode_report(section, ioctl_feature(fd, buf)))
            except (OSError, ValueError) as exc:
                unavailable[section] = str(exc)
    finally:
        os.close(fd)
    return dict(values=result, unavailable=unavailable)


def apply_settings(receiver, section, data):
    payload = build_report(section, data)
    fd = os.open(receiver.node, os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        # Drain only this handle before sending, so old acknowledgments are not accepted.
        for _ in range(64):
            try:
                os.read(fd, 64)
            except BlockingIOError:
                break
        ioctl_feature(fd, payload, write=True)
        if receiver.wired:
            return 'Relatório enviado por cabo; leitura de confirmação indisponível.'
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if select.select([fd], [], [], max(0, deadline-time.monotonic()))[0]:
                report = os.read(fd, 64)
                if not report:
                    raise OSError('Receptor desconectado durante a aplicação.')
                if len(report) == 5 and report[0] == 3 and report[2] == 0x50:
                    return 'Receptor confirmou o recebimento. Leitura completa dos ajustes não disponível.'
        raise TimeoutError('Sem confirmação do mouse. O ajuste pode ter sido aplicado; não será reenviado automaticamente.')
    finally:
        os.close(fd)

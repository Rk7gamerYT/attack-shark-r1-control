"""Temas claro/escuro e folha de estilo do Attack Shark R1 Control."""
import json
import os
from pathlib import Path

UI_CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'attack-shark-r1-control/ui.json'

PALETTES = {  # cores inspiradas no macOS (Big Sur em diante)
    'dark': dict(bg='#1c1c1e', card='#2c2c2e', card2='#3a3a3c', border='#48484a', text='#f5f5f7',
                 muted='#98989f', accent='#0a84ff', accent_text='#ffffff', ok='#30d158',
                 warn='#ff9f0a', danger='#ff453a', track='#3a3a3c', hover='#48484a'),
    'light': dict(bg='#f2f2f7', card='#ffffff', card2='#e9e9ee', border='#d8d8de', text='#1d1d1f',
                  muted='#6e6e73', accent='#007aff', accent_text='#ffffff', ok='#34c759',
                  warn='#ff9500', danger='#ff3b30', track='#e5e5ea', hover='#dcdce2'),
}


def load_theme():
    try:
        value = json.loads(UI_CONFIG.read_text()).get('theme')
        return value if value in PALETTES else 'dark'
    except (OSError, ValueError, AttributeError):
        return 'dark'


def save_theme(name):
    try:
        UI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        UI_CONFIG.write_text(json.dumps(dict(theme=name)))
    except OSError:
        pass


def stylesheet(name):
    p = PALETTES[name]
    assets = Path(__file__).with_name('assets').as_posix()
    return f'''
    QWidget {{background:{p['bg']};color:{p['text']};font-family:'SF Pro Text','Inter','Helvetica Neue','Noto Sans',sans-serif;font-size:14px}}
    QLabel {{background:transparent}}
    QLabel#title {{font-size:29px;font-weight:700;letter-spacing:-0.5px}}
    QLabel#brand {{font-size:20px;font-weight:700}}
    QLabel#model {{font-size:17px;font-weight:700;letter-spacing:1px}}
    QLabel#pollingHelp {{background:{p['card2']};padding:20px;border-radius:12px;line-height:24px;color:{p['muted']}}}
    QFrame#sidebar {{background:{p['card']};border-right:1px solid {p['border']}}}
    QFrame#sidebar QLabel, QFrame#sidebar QListWidget {{background:transparent}}
    QListWidget#navigation {{border:none;outline:none}}
    QListWidget#navigation::item {{padding:14px 12px;border-radius:10px;color:{p['muted']}}}
    QListWidget#navigation::item:selected {{background:{p['accent']};color:{p['accent_text']};font-weight:700}}
    QListWidget#navigation::item:hover:!selected {{background:{p['hover']}}}
    QLabel#subtitle, QLabel#muted {{color:{p['muted']}}}
    QLabel#section {{font-size:12px;font-weight:700;color:{p['muted']};letter-spacing:1px}}
    QLabel#status {{font-size:16px;font-weight:600}}
    QLabel#pill {{background:{p['card2']};border-radius:10px;padding:6px 12px;color:{p['muted']}}}
    QFrame#card {{background:{p['card']};border:1px solid {p['border']};border-radius:16px}}
    QFrame#card QLabel, QFrame#card QWidget#plain {{background:transparent}}
    QFrame#card QLabel#pill {{background:{p['card2']}}}
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox {{background:{p['card2']};border:1px solid {p['border']};border-radius:7px;padding:6px 14px;min-height:20px}}
    QPushButton:hover, QComboBox:hover {{background:{p['hover']}}}
    QPushButton:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{border:1px solid {p['accent']}}}
    QPushButton:disabled {{color:{p['muted']}}}
    QPushButton#primary {{background:{p['accent']};color:{p['accent_text']};border:none;font-weight:600;padding:8px 22px}}
    QPushButton#ghost {{background:transparent}}
    QSpinBox, QDoubleSpinBox {{padding:9px 22px 9px 12px}}
    QComboBox::drop-down {{border:none;width:28px}}
    QComboBox::down-arrow {{image:url({assets}/chevron-down.svg);width:12px;height:12px}}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{subcontrol-origin:border;subcontrol-position:top right;width:22px;border:none}}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{subcontrol-origin:border;subcontrol-position:bottom right;width:22px;border:none}}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{image:url({assets}/chevron-up.svg);width:12px;height:12px}}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{image:url({assets}/chevron-down.svg);width:12px;height:12px}}
    QComboBox QAbstractItemView {{background:{p['card']};selection-background-color:{p['accent']};border:1px solid {p['border']}}}
    QWidget#plain, QStackedWidget, QTabBar {{background:transparent}}
    QTabWidget::pane {{border:none;top:8px}}
    QTabBar::tab {{background:{p['card2']};color:{p['muted']};padding:6px 18px;margin:0;border:1px solid {p['border']};font-weight:500}}
    QTabBar::tab:first {{border-top-left-radius:7px;border-bottom-left-radius:7px}}
    QTabBar::tab:last {{border-top-right-radius:7px;border-bottom-right-radius:7px}}
    QTabBar::tab:selected {{background:{p['accent']};color:{p['accent_text']};border-color:{p['accent']}}}
    QTabBar::tab:hover:!selected {{color:{p['text']}}}
    QTabBar {{qproperty-drawBase:0}}
    QScrollArea {{border:none}}
    QScrollBar:vertical {{background:transparent;width:8px;margin:2px}}
    QScrollBar::handle:vertical {{background:{p['border']};border-radius:4px;min-height:32px}}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{height:0}}
    QToolTip {{background:{p['card']};color:{p['text']};border:1px solid {p['border']}}}
    '''

from PySide6.QtGui import QIcon
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTabWidget, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QScrollArea, QLayout, QSizePolicy, QListWidget
from battery_tray import BatteryTray
from mouse import Monitor, discover
from settings import CONFIG, DEFAULTS, build_report
from theme import load_theme, save_theme, stylesheet
from widgets import BatteryRing, MouseView


def card(title=None):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 18)
    layout.setSpacing(10)
    if title:
        label = QLabel(title.upper())
        label.setObjectName('section')
        layout.addWidget(label)
    return frame, layout


class Window(QMainWindow):
    def __init__(self, demo=False):
        super().__init__()
        self.demo, self.quitting = demo, False
        self.worker = None
        self.read_attempted = None
        self.monitor = self.receiver = self.percent = self.last_read = self.auth = None
        self.setWindowTitle('Attack Shark R1 • Configurações')
        self.resize(1240, 920)
        self.theme = load_theme()
        body = QWidget()
        self.setCentralWidget(body)
        shell = QHBoxLayout(body)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self.build_sidebar())
        content = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)
        shell.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel('Precisão do seu jeito')
        self.page_title = title
        title.setObjectName('title')
        subtitle = QLabel('Personalize os estágios de DPI e o comportamento do sensor.')
        self.page_subtitle = subtitle
        subtitle.setWordWrap(True)
        subtitle.setObjectName('subtitle')
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        self.theme_button = QPushButton()
        self.theme_button.setObjectName('ghost')
        self.theme_button.clicked.connect(lambda: self.apply_theme('light' if self.theme == 'dark' else 'dark'))
        header.addWidget(self.theme_button)
        layout.addLayout(header)
        layout.addWidget(self.build_hero())
        self.build_settings(layout)
        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)
        self.tray = BatteryTray('Attack Shark R1', self.show_window, self.quit_app, self)
        self.apply_theme(self.theme, persist=False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(250)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.scan)
        self.scan_timer.start(3000)
        self.scan()

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(208)
        column = QVBoxLayout(sidebar)
        column.setContentsMargins(18, 28, 18, 22)
        column.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(QIcon(str(Path(__file__).with_name('assets') / 'icon.svg')).pixmap(52, 52))
        column.addWidget(logo)
        title = QLabel('Attack Shark')
        title.setObjectName('brand')
        column.addWidget(title)
        subtitle = QLabel('R1 CONTROL\nPRECISÃO NO LINUX')
        subtitle.setObjectName('section')
        column.addWidget(subtitle)
        column.addSpacing(26)
        self.navigation = QListWidget()
        self.navigation.setObjectName('navigation')
        self.navigation.addItems(['DPI e sensor', 'Polling rate', 'Energia e cliques', 'Ajustes salvos'])
        self.navigation.setSpacing(5)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        column.addWidget(self.navigation, 1)
        foot = QLabel('ATTACK SHARK R1\nUSB · 2,4 GHz')
        foot.setObjectName('muted')
        column.addWidget(foot)
        return sidebar

    def navigate(self, index):
        if index < 0:
            return
        self.tabs.setCurrentIndex(index)
        self.page_title.setText(['Precisão do seu jeito', 'Cada movimento conta',
                                 'Seu ritmo de jogo', 'Seus ajustes, sempre à mão'][index])
        self.page_subtitle.setText(['Personalize os estágios de DPI e o comportamento do sensor.',
            'Escolha o equilíbrio entre taxa de atualização e bateria.',
            'Configure a suspensão e o tempo de resposta dos botões.',
            'Salve e recupere suas preferências neste computador.'][index])

    def apply_theme(self, name, persist=True):
        self.theme = name
        QApplication.instance().setStyleSheet(stylesheet(name))
        self.theme_button.setText('☀  Tema claro' if name == 'dark' else '☾  Tema escuro')
        self.ring.set_theme(name)
        self.mouse_preview.set_theme(name)
        if persist:
            save_theme(name)

    def build_hero(self):
        frame, outer = card()
        row = QHBoxLayout()
        row.setSpacing(18)
        self.ring = BatteryRing(self.theme)
        self.ring.setFixedSize(104, 104)
        row.addWidget(self.ring)
        info = QVBoxLayout()
        info.setSpacing(6)
        self.charge = QLabel('—')
        self.charge.hide()
        self.status = QLabel('Buscando receptor…')
        self.status.setObjectName('status')
        self.status.setWordWrap(True)
        info.addWidget(self.status)
        self.detail = QLabel('Bateria em passos de 10%. Ajustes enviados somente ao aplicar.')
        self.detail.setObjectName('muted')
        self.detail.setWordWrap(True)
        info.addWidget(self.detail)
        row.addLayout(info, 1)
        actions = QVBoxLayout()
        retry = QPushButton('Buscar mouse')
        retry.clicked.connect(self.retry)
        self.grant = QPushButton('Liberar leitura…')
        self.grant.clicked.connect(self.grant_access)
        self.grant.hide()
        actions.addWidget(retry)
        actions.addWidget(self.grant)
        row.addLayout(actions)
        outer.addLayout(row)
        return frame

    def build_settings(self, layout):
        row = QHBoxLayout()
        row.setSpacing(16)
        preview, pl = card('Seu mouse')
        preview.setMinimumWidth(290)
        self.mouse_preview = MouseView(self.theme)
        pl.addWidget(self.mouse_preview, 1)
        model = QLabel('ATTACK SHARK R1')
        model.setObjectName('model')
        model.setAlignment(Qt.AlignCenter)
        pl.addWidget(model)
        spec = QLabel('6 estágios de DPI  ·  até 1000 Hz')
        spec.setObjectName('muted')
        spec.setAlignment(Qt.AlignCenter)
        pl.addWidget(spec)
        note = QLabel('Os campos à direita são ajustes desejados.\nA leitura atual depende do firmware.')
        note.setObjectName('muted')
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        pl.addWidget(note)
        row.addWidget(preview, 4)
        frame, box = card('Personalizar')
        frame.setMinimumWidth(480)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        box.addWidget(self.tabs, 1)
        row.addWidget(frame, 6)
        layout.addLayout(row, 1)
        self.fields = {}
        self.apply_buttons = []
        hints = {'dpi': 'Seis estágios para alternar no botão do mouse. De 100 a 18000 DPI, em passos de 100.',
                 'polling': 'Mais atualizações por segundo reduzem o intervalo entre os movimentos enviados ao computador.',
                 'power': 'Defina quando o mouse deve dormir e o intervalo usado para filtrar cliques repetidos.'}
        for section, title in [('dpi', 'DPI e sensor'), ('polling', 'Polling rate'), ('power', 'Energia e cliques')]:
            page = QWidget()
            page.setObjectName('plain')
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 4, 0, 0)
            page_layout.setSpacing(14)
            hint = QLabel(hints[section])
            hint.setObjectName('muted')
            hint.setWordWrap(True)
            page_layout.addWidget(hint)
            form = QFormLayout()
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(12)
            if section == 'dpi':
                self.fields['dpis'] = []
                columns = QHBoxLayout()
                columns.setSpacing(20)
                halves = [QFormLayout(), QFormLayout()]
                for half in halves:
                    half.setVerticalSpacing(12)
                    columns.addLayout(half, 1)
                page_layout.addLayout(columns)
                for i in range(6):
                    spin = QSpinBox()
                    spin.setRange(0, 18000)
                    spin.setSingleStep(100)
                    spin.setSpecialValueText('Não lido')
                    spin.setSuffix(' DPI')
                    halves[i // 3].addRow(f'{i+1:02}', spin)
                    self.fields['dpis'].append(spin)
                active = QComboBox()
                active.addItem('Não lido', None)
                for i in range(1, 7):
                    active.addItem(f'Estágio {i}', i)
                self.fields['active'] = active
                form.addRow('Estágio ativo', active)
                for key, label in [('angle', 'Correção de ângulo'), ('ripple', 'Suavização do sensor')]:
                    combo = QComboBox()
                    for text, value in [('Não lido', None), ('Desligado', False), ('Ligado', True)]:
                        combo.addItem(text, value)
                    self.fields[key] = combo
                    form.addRow(label, combo)
            elif section == 'polling':
                self.fields['polling'] = QComboBox()
                self.fields['polling'].addItem('Não lido', None)
                for value in (125, 250, 500, 1000):
                    self.fields['polling'].addItem(f'{value} Hz', value)
                form.addRow('Taxa de atualização', self.fields['polling'])
                page_layout.addWidget(self.polling_description())
            else:
                for key, label, maximum, step in [('sleep', 'Suspensão', 30, 0.5),
                        ('deep_sleep', 'Suspensão profunda', 60, 1), ('debounce', 'Resposta dos botões', 50, 2)]:
                    spin = QDoubleSpinBox() if key == 'sleep' else QSpinBox()
                    spin.setRange(0, maximum)
                    spin.setSingleStep(step)
                    spin.setSpecialValueText('Não lido')
                    spin.setSuffix(' ms' if key == 'debounce' else ' min')
                    self.fields[key] = spin
                    form.addRow(label, spin)
            page_layout.addLayout(form)
            page_layout.addStretch()
            button = QPushButton('Aplicar ' + {'dpi': 'DPI e sensor', 'polling': 'polling rate', 'power': 'energia e cliques'}[section])
            button.setObjectName('primary')
            button.setMinimumHeight(42)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, name=section: self.apply_section(name))
            self.apply_buttons.append(button)
            page_layout.addWidget(button)
            self.tabs.addTab(page, title)
        page = QWidget()
        page.setObjectName('plain')
        saved = QVBoxLayout(page)
        saved.setContentsMargins(0, 4, 0, 0)
        explanation = QLabel('Salve uma combinação de DPI, sensor, polling e energia para reutilizar depois. Carregar um arquivo não altera o mouse automaticamente.')
        explanation.setObjectName('muted')
        explanation.setWordWrap(True)
        saved.addWidget(explanation)
        for text, callback in [('Preencher sugestão de ajustes', lambda: self.set_values(DEFAULTS, 'Sugestão carregada • ainda não aplicada no mouse.')),
                               ('Carregar ajustes salvos', self.load_local), ('Salvar ajustes neste computador', self.save_local)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            saved.addWidget(button)
        saved.addStretch()
        self.tabs.addTab(page, 'Ajustes salvos')
        connection, cl = card()
        bottom = QHBoxLayout()
        self.read_status = QLabel('Configuração atual: ainda não consultada.')
        self.read_status.setObjectName('muted')
        self.read_status.setWordWrap(True)
        bottom.addWidget(self.read_status, 1)
        read = QPushButton('Ler ajustes')
        read.clicked.connect(self.read_device)
        bottom.addWidget(read)
        self.write_grant = QPushButton('Liberar alterações…')
        self.write_grant.clicked.connect(lambda: self.grant_access(True))
        self.write_grant.hide()
        bottom.addWidget(self.write_grant)
        cl.addLayout(bottom)
        layout.addWidget(connection)
        self.config_status = QLabel('Aplique somente a seção que deseja alterar. Valores não lidos permanecem desconhecidos.')
        self.config_status.setObjectName('muted')
        self.config_status.setWordWrap(True)
        layout.addWidget(self.config_status)

    def polling_description(self):
        label = QLabel('125 Hz    8 ms entre envios\n250 Hz    4 ms entre envios\n500 Hz    2 ms entre envios\n1000 Hz  1 ms entre envios\n\nUma taxa menor pode ajudar a economizar bateria.')
        label.setObjectName('pollingHelp')
        return label

    def values(self):
        return {key: [item.value() for item in field] if isinstance(field, list) else
                field.currentData() if isinstance(field, QComboBox) else field.value()
                for key, field in self.fields.items()}

    def set_values(self, values, message):
        for key, value in values.items():
            if key not in self.fields:
                continue
            field = self.fields[key]
            if isinstance(field, list):
                for spin, number in zip(field, value):
                    spin.setValue(number)
            elif isinstance(field, QComboBox):
                field.setCurrentIndex(max(0, field.findData(value)))
            else:
                field.setValue(value)
        self.config_status.setText(message)

    def save_local(self):
        try:
            values = self.values()
            for section in ('dpi', 'polling', 'power'):
                build_report(section, values)
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            temporary = CONFIG.with_suffix('.tmp')
            temporary.write_text(json.dumps(values, indent=2))
            temporary.replace(CONFIG)
            self.config_status.setText('Ajustes salvos no app. Isso não escreve no mouse.')
        except (OSError, ValueError) as exc:
            self.config_status.setText(str(exc))

    def load_local(self):
        try:
            values = json.loads(CONFIG.read_text())
            for section in ('dpi', 'polling', 'power'):
                build_report(section, values)
            self.set_values(values, 'Ajustes locais carregados • ainda não enviados ao mouse.')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            self.config_status.setText(f'Não foi possível carregar: {exc}')

    def read_device(self):
        self.start_worker({'action': 'read'})

    def apply_section(self, section):
        try:
            values = self.values()
            build_report(section, values)
            self.start_worker(dict(action='apply', section=section, values=values))
        except ValueError as exc:
            self.config_status.setText(str(exc))

    def start_worker(self, request):
        if self.worker is not None:
            self.config_status.setText('Aguarde a operação em andamento.')
            return
        if self.demo or self.receiver is None:
            self.config_status.setText('Conecte o receptor para ler ou aplicar ajustes.')
            return
        self.worker_request = request
        self.worker_node = self.receiver
        request['node'] = str(self.receiver.node)
        worker = QProcess(self)
        self.worker = worker
        self.worker_timeout = QTimer(self)
        self.worker_timeout.setSingleShot(True)
        self.worker_timeout.timeout.connect(worker.kill)
        worker.finished.connect(self.worker_finished)
        worker.errorOccurred.connect(lambda error: self.worker_failed() if error == QProcess.FailedToStart else None)
        worker.setProgram(sys.executable)
        worker.setArguments([str(Path(__file__).with_name('device_worker.py'))])
        worker.start()
        worker.write(json.dumps(request).encode())
        worker.closeWriteChannel()
        self.worker_timeout.start(8000)
        self.config_status.setText('Consultando o mouse…' if request['action'] == 'read' else 'Enviando ajuste; aguardando confirmação…')
        for button in self.apply_buttons:
            button.setEnabled(False)

    def worker_failed(self):
        if self.worker:
            self.worker_timeout.stop()
            self.worker.deleteLater()
            self.worker = None
            self.config_status.setText('Não foi possível iniciar a comunicação com o mouse.')
            for button in self.apply_buttons:
                button.setEnabled(True)

    def worker_finished(self, code, exit_status):
        worker = self.worker
        if worker is None:
            return
        self.worker_timeout.stop()
        self.worker_timeout.deleteLater()
        self.worker = None
        for button in self.apply_buttons:
            button.setEnabled(True)
        try:
            if self.worker_node != self.receiver:
                raise ValueError('O receptor mudou durante a operação. Consulte novamente.')
            raw = bytes(worker.readAllStandardOutput()).decode()
            result = json.loads(raw)
            if code != 0 or 'error' in result:
                raise ValueError(result.get('error', 'Falha na comunicação.'))
            if self.worker_request['action'] == 'read':
                values = result['values']
                missing = ', '.join({'dpi': 'DPI/sensor', 'power': 'suspensão/resposta', 'polling': 'polling rate'}[name] for name in result['unavailable'])
                self.read_status.setText('Leitura atual: ' + ('valores recebidos do dispositivo.' if values else 'o firmware não retornou ajustes válidos.') +
                    (f' Não disponível: {missing}.' if missing else ''))
                self.set_values(values, 'Consulta concluída. Campos sem leitura não são substituídos por padrões.')
            else:
                self.config_status.setText(result['message'])
                self.read_status.setText('Um ajuste foi enviado. Consulte novamente para verificar os valores que o firmware permite ler.')
        except (ValueError, KeyError, TypeError) as exc:
            self.config_status.setText(f'Operação não confirmada: {exc}. Se estiver sem escrita, use Liberar alteração das configurações.')
        finally:
            worker.deleteLater()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def reset(self):
        if self.monitor:
            self.monitor.close()
        self.monitor = self.percent = self.last_read = None

    def retry(self):
        self.reset()
        self.receiver = None
        self.scan()

    def scan(self):
        devices = [] if self.demo else discover()
        receiver = devices[0] if devices else None
        if receiver != self.receiver:
            self.reset()
            self.receiver = receiver
        self.grant.setVisible(bool(receiver) and not receiver.wired and self.monitor is None)
        if receiver is None:
            self.status.setText('Modo demonstração • sem leitura real' if self.demo else 'Receptor R1 não encontrado. Conecte o dongle USB.')
        elif receiver.wired:
            self.status.setText('Conexão por cabo: bateria não validada neste modo.')
        elif not self.monitor:
            try:
                self.monitor = Monitor(receiver)
                self.status.setText('Receptor conectado. Aguardando bateria; mova ou ligue o mouse.')
                self.grant.hide()
            except PermissionError:
                self.status.setText('Sem permissão. Use Liberar leitura do receptor e autorize no Linux.')
            except OSError as exc:
                self.status.setText(f'Falha ao abrir receptor: {exc}')
        self.write_grant.setVisible(bool(receiver) and not os.access(receiver.node, os.W_OK))
        if receiver != self.read_attempted:
            self.read_attempted = receiver
            self.read_status.setText('Novo receptor. Consultando os ajustes atuais…' if receiver else 'Controle de configurações: receptor desconectado.')
            self.set_values(dict(dpis=[0]*6, active=None, angle=None, ripple=None, polling=None, sleep=0, deep_sleep=0, debounce=0), 'Aguardando consulta dos ajustes.')
            if receiver:
                QTimer.singleShot(0, self.read_device)
        self.update_display()

    def grant_access(self, write=False):
        if not self.receiver or self.auth:
            return
        pkexec, setfacl = shutil.which('pkexec'), shutil.which('setfacl')
        if not pkexec or not setfacl:
            self.status.setText('Instale acl e PolicyKit (pkexec) para liberar a leitura.')
            return
        if self.receiver not in discover():
            self.status.setText('Receptor desconectado. Busque novamente.')
            return
        try:
            self.auth = subprocess.Popen([pkexec, setfacl, '-m', f'u:{os.getuid()}:{"rw" if write else "r"}', '--', str(self.receiver.node)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.grant.setEnabled(False)
            self.status.setText('Autorize no Linux o acesso de leitura e escrita deste receptor.' if write else 'Autorize no Linux a leitura deste receptor.')
        except OSError as exc:
            self.status.setText(str(exc))

    def poll(self):
        if self.auth and self.auth.poll() is not None:
            code = self.auth.returncode
            self.auth = None
            self.grant.setEnabled(True)
            if code == 0:
                self.scan()
                QTimer.singleShot(0, self.read_device)
            else:
                self.status.setText('Autorização não concedida. Clique para tentar novamente.')
        if self.monitor:
            try:
                value = self.monitor.read()
                if value is not None:
                    self.percent, self.last_read = value, time.monotonic()
                    self.status.setText('Bateria recebida do mouse • dongle 2,4 GHz')
                self.update_display()
            except OSError:
                self.reset()
                self.status.setText('Receptor desconectado. Reconexão automática em até 3 segundos.')
                self.update_display()

    def update_display(self):
        stale = self.last_read is not None and time.monotonic() - self.last_read > 120
        value = None if stale else self.percent
        state = 'Leitura antiga • mova o mouse para atualizar' if stale else self.status.text()
        self.charge.setText('—' if value is None else f'{value}%')
        self.ring.set_value(value, stale)
        self.tray.update_battery(value, state)
        self.detail.setText('Sem relatório recente. O mouse pode estar dormindo.' if stale else
            'Bateria em passos de 10%. Os ajustes só são enviados ao clicar em Aplicar.')

    def quit_app(self):
        self.quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.tray.isVisible() and not self.quitting:
            self.hide()
            event.ignore()
            return
        if self.worker:
            self.worker.kill()
            self.worker.waitForFinished(1000)
        self.reset()
        self.timer.stop()
        self.scan_timer.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('attack-shark-r1-control')
    app.setDesktopFileName('attack-shark-r1-control')
    app.setWindowIcon(QIcon(str(Path(__file__).with_name('assets') / 'icon.svg')))
    app.setStyle('Fusion')
    app.setStyleSheet(stylesheet(load_theme()))
    window = Window('--demo' in sys.argv)
    window.show()
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(300, app.quit)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

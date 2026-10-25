"""Medidor circular de bateria."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPainterPath, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QWidget, QSizePolicy

from theme import PALETTES


class BatteryRing(QWidget):
    def __init__(self, theme='dark', parent=None):
        super().__init__(parent)
        self.palette_name = theme
        self.percent = None
        self.stale = False
        self.setFixedSize(150, 150)

    def set_theme(self, name):
        self.palette_name = name
        self.update()

    def set_value(self, percent, stale=False):
        if (percent, stale) != (self.percent, self.stale):
            self.percent, self.stale = percent, stale
            self.update()

    def paintEvent(self, _):
        p = PALETTES[self.palette_name]
        painter = QPainter(self)
        painter.scale(self.width()/150, self.height()/150)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(12, 12, 126, 126)
        pen = QPen(QColor(p['track']), 12)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        if self.percent is not None:
            color = p['danger'] if self.percent <= 20 else p['warn'] if self.percent <= 40 else p['ok']
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -round(360 * 16 * max(self.percent, 2) / 100))
        painter.setPen(QColor(p['text']))
        painter.setFont(QFont('Sans', 26, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, '—' if self.percent is None else f'{self.percent}%')
        painter.end()


class MouseView(QWidget):
    """Vista vetorial do mouse, independente da leitura de ajustes do firmware."""
    def __init__(self, theme='dark', parent=None):
        super().__init__(parent)
        self.palette_name = theme
        self.setMinimumSize(240, 290)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_theme(self, theme):
        self.palette_name = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width()/300, self.height()/400)
        p.translate((self.width()-300*scale)/2, (self.height()-400*scale)/2)
        p.scale(scale, scale)

        def gradient(left, right, x1=50, x2=245):
            g = QLinearGradient(x1, 0, x2, 0)
            g.setColorAt(0, QColor(left))
            g.setColorAt(1, QColor(right))
            return g

        # Vista superior baseada no R1 real: curva ergonômica e traseira arredondada.
        body = QPainterPath()
        body.moveTo(132, 26)
        body.cubicTo(144, 23, 160, 23, 174, 26)
        body.cubicTo(193, 28, 224, 42, 236, 54)
        body.cubicTo(244, 89, 235, 148, 239, 190)
        body.cubicTo(243, 231, 255, 271, 243, 312)
        body.cubicTo(229, 361, 196, 381, 151, 382)
        body.cubicTo(102, 383, 61, 360, 46, 323)
        body.cubicTo(33, 290, 47, 248, 52, 209)
        body.cubicTo(59, 163, 52, 112, 55, 62)
        body.cubicTo(64, 47, 105, 32, 132, 26)
        body.closeSubpath()
        p.save();p.translate(0, 6)
        p.setPen(Qt.NoPen);p.setBrush(QColor(0, 0, 0, 55));p.drawPath(body);p.restore()
        g = gradient('#404245', '#1d1f21')
        g.setColorAt(.22, QColor('#242628'))
        g.setColorAt(.54, QColor('#161819'))
        g.setColorAt(.85, QColor('#313335'))
        p.setPen(QPen(QColor('#55595b'), .9));p.setBrush(g);p.drawPath(body)
        p.save();p.setClipPath(body)
        highlight = QRadialGradient(QPointF(122, 334), 129)
        highlight.setColorAt(0, QColor(255,255,255,13))
        highlight.setColorAt(1, QColor(255,255,255,0))
        p.setPen(Qt.NoPen);p.setBrush(highlight);p.drawEllipse(QRectF(22,214,250,180))
        p.restore()

        # Botões separados, com a abertura central característica em volta da roda.
        left = QPainterPath()
        left.moveTo(132, 16)
        left.cubicTo(104, 24, 67, 34, 57, 48)
        left.cubicTo(58, 92, 61, 132, 65, 166)
        left.cubicTo(67, 178, 95, 186, 149, 187)
        left.lineTo(149, 111)
        left.cubicTo(136, 110, 132, 105, 132, 94)
        left.closeSubpath()
        right = QPainterPath()
        right.moveTo(166, 16)
        right.cubicTo(196, 24, 226, 36, 237, 48)
        right.cubicTo(236, 91, 231, 133, 230, 163)
        right.cubicTo(230, 180, 198, 186, 151, 187)
        right.lineTo(151, 111)
        right.cubicTo(164, 110, 166, 105, 166, 94)
        right.closeSubpath()
        p.setPen(QPen(QColor('#080a0b'), 1.3))
        g = gradient('#2b2d2f','#17191a',55,149)
        g.setColorAt(.32,QColor('#393b3d'))
        p.setBrush(g);p.drawPath(left)
        g = gradient('#353739','#121415',166,238)
        g.setColorAt(.38,QColor('#2b2d2f'))
        p.setBrush(g);p.drawPath(right)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor('#626568'), .65))
        p.drawLine(QPointF(133,17), QPointF(134,72))
        p.drawLine(QPointF(165,17), QPointF(165,72))

        # Roda preta estriada e bordas metálicas, sem iluminação inventada.
        p.setPen(QPen(QColor('#050708'),1.5));p.setBrush(QColor('#080a0b'))
        p.drawRoundedRect(QRectF(134,56,30,54),8,8)
        p.setPen(Qt.NoPen)
        g=gradient('#686b6c','#c4c6c6',136,140)
        p.setBrush(g);p.drawRoundedRect(QRectF(136,59,4,48),2,2)
        p.setBrush(gradient('#c4c6c6','#5a5d5e',159,163));p.drawRoundedRect(QRectF(159,59,4,48),2,2)
        p.setBrush(gradient('#202325','#101314',140,159));p.drawRoundedRect(QRectF(140,57,19,52),5,5)
        for y in range(61,106,3):
            p.setPen(QPen(QColor('#373a3b'), .8));p.drawLine(QPointF(141,y),QPointF(158,y))
            p.setPen(QPen(QColor('#07090a'), .8));p.drawLine(QPointF(141,y+1),QPointF(158,y+1))

        # Botão DPI e os dois botões laterais.
        p.setPen(QPen(QColor('#07090a'),1.6))
        p.setBrush(gradient('#303335','#16191a',143,157))
        p.drawRoundedRect(QRectF(142,128,15,33),7,7)
        p.setPen(QPen(QColor('#545859'),.65))
        p.drawRoundedRect(QRectF(143,129,13,30),6,6)
        for rect in (QRectF(53,126,7,52),QRectF(51,183,7,53)):
            p.setPen(QPen(QColor('#090b0d'),1.2))
            p.setBrush(gradient('#646768','#252829',51,61))
            p.drawRoundedRect(rect,3,3)

        # Receptor USB ao lado do mouse, como na referência.
        p.setPen(QPen(QColor('#5c6062'),.8));p.setBrush(gradient('#d7dadd','#909697',256,281))
        p.drawRect(QRectF(258,330,23,32))
        p.setBrush(QColor('#202426'));p.drawRect(QRectF(263,343,4,5));p.drawRect(QRectF(273,343,4,5))
        p.setBrush(gradient('#303638','#111619',254,285));p.setPen(QPen(QColor('#0b0e10'),1))
        p.drawRoundedRect(QRectF(254,360,31,19),2,2)
        p.setPen(QPen(QColor('#4c5356'),.7))
        for y in (365,370,375):p.drawLine(QPointF(254,y),QPointF(285,y))
        p.end()

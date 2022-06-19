from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QMessageBox, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal

import sys
from common import Application, WarningLevel


class AlarmMessageBox(QLabel):
    """Класс окна всплывающего уведомления которое умеет мигать"""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        font = self.font()
        font.setPointSize(20)
        self.setFont(font)

        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.resize(400, 200)

        self.blink = False
        self.startTimer(1000)
        self.timerEvent()

    def timerEvent(self, *args, **kwargs):
        self.setStyleSheet("background-color: yellow;" if not self.blink else "background-color: red;")
        self.blink = not self.blink

    def mousePressEvent(self, mouseEvent):
        self.close()
        self.closed.emit()


class AlarmWindow(QWidget):
    """Окно и логика оповещений о пропущенных просроченных каналах связи"""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Таймаут канала связи")
        self.layer = QVBoxLayout()

        self.log = QPlainTextEdit(self)
        self.layer.addWidget(self.log)

        self.setLayout(self.layer)

        # self.alarmBox = QMessageBox(QMessageBox.Warning, "Новых алармов", "Нет")
        # self.alarmBox.accepted.connect(self.alarmReading)
        self.alarmBox = AlarmMessageBox()
        self.alarmBox.closed.connect(self.alarmReading)

        self.warningLevel = WarningLevel.Warning
        self.newAlarmCount = 0

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        a0.accept()

    def logEvent(self, warningLevel, text, shortText = ''):
        """Записать событие в окно и вывести всплывающее уведомление"""
        if warningLevel.value <= self.warningLevel.value:
            return

        self.log.appendHtml(
            # f'<font color="{warningLevel.colorName}">'
            # f'{warningLevel.name}'
            # f'</font>::'
            f'{text}')

        if not self.isVisible():
            if not self.alarmBox.isVisible():
                self.alarmBox.show()
            self.newAlarmCount += 1
            self.alarmBox.setText(f'новые оценки\n'
                                  f'хуже: {self.warningLevel.name} {self.newAlarmCount}\n'
                                  f'последний: {shortText}')

    def alarmReading(self):
        self.newAlarmCount = 0

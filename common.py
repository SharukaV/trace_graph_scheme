import enum, datetime
# from dateutil import parser as dtparser


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTime


class WarningLevel(enum.IntEnum):
    """Перечисление уровней оценки и их цветов"""
    Default = 0, 'black', QtCore.Qt.black
    Passed = 1, 'green', QtCore.Qt.green
    Warning = 2, 'yellow', QtCore.Qt.yellow
    Error = 3, 'magenta', QtCore.Qt.magenta
    Fatal = 4, 'red', QtCore.Qt.red

    # Цвет вручную RGB
    # self.myColor = QtCore.Qt.magenta
    # self.myColor = QtGui.QColor(0x800080)
    # self.myColor = QtGui.QColor(0x80,0x00,0x80)

    def __new__(cls, keycode, colorName, color):
        obj = int.__new__(cls)
        obj._value_ = keycode
        obj.color = color
        obj.colorName = colorName
        return obj

velocityCaption = ('STM-1', 'STM-4', 'STM-16', 'STM-64','E1','E2','E3','E4','Оцк','Ethernet')

class Headers:
    horizontalHeaderModel = QtGui.QStandardItemModel()
    """Заголовок таблицы"""
    # можно переделать на парсер вложенного списка
    horizontalHeaderModel.setItem(0, 0, QtGui.QStandardItem("Номер\nЦТ"))
    horizontalHeaderModel.setItem(0, 1, QtGui.QStandardItem("Направление"))
    horizontalHeaderModel.setItem(0, 2, QtGui.QStandardItem("Номер\nсвязи"))
    horizontalHeaderModel.setItem(0, 3, QtGui.QStandardItem("ШТ\n(ООД)"))
    horizontalHeaderModel.setItem(0, 4, QtGui.QStandardItem("Трассы каналов"))
    horizontalHeaderModel.setItem(0, 5, QtGui.QStandardItem("Скорость ЦТ"))

    c6 = QtGui.QStandardItem("Время готовности")
    c61 = QtGui.QStandardItem("План.")
    c611 = QtGui.QStandardItem("отл.")
    c612 = QtGui.QStandardItem("хор.")
    c613 = QtGui.QStandardItem("уд.")
    c62 = QtGui.QStandardItem("Вр.н")
    c63 = QtGui.QStandardItem("∀")

    c6.appendColumn([c61])
    c6.appendColumn([c62])
    c6.appendColumn([c63])
    c61.appendColumn([c611])
    c61.appendColumn([c612])
    c61.appendColumn([c613])

    horizontalHeaderModel.setItem(0, 6, c6)

    c7 = QtGui.QStandardItem("Рассчет КИД")
    c71 = QtGui.QStandardItem("Данные")
    c711 = QtGui.QStandardItem("Реал")
    c712 = QtGui.QStandardItem("Отбой\nпо связи")
    c713 = QtGui.QStandardItem("Время выхода\nиз строя")
    c714 = QtGui.QStandardItem("Время\nвосстановления")
    c72 = QtGui.QStandardItem("КИД")
    c7.appendColumn([c71])
    c7.appendColumn([c72])
    c71.appendColumn([c711])
    c71.appendColumn([c712])
    c71.appendColumn([c713])
    c71.appendColumn([c714])

    horizontalHeaderModel.setItem(0, 7, c7)

    @staticmethod
    def columnCount():
        return Headers.horizontalHeaderModel.columnCount() + 4 + 4


class Application(QtWidgets.QApplication):
    """
    Расширение класса приложения Qt
    Поскольку существует по одному экземпляру на программу, здесь хранятся некоторые общие данные
    """

    applicationClockChanged = pyqtSignal(QtCore.QTime)

    # Настройки сораняемые между запусками
    settings = QtCore.QSettings('config.ini', QtCore.QSettings.IniFormat)
    # Внутренние часы программы
    app_datetime = QtCore.QDateTime.fromMSecsSinceEpoch(0, QtCore.Qt.UTC)
    # Монотонный таймер для обновления внутренних часов, для устранения погрешности
    uptime = QtCore.QElapsedTimer()
    uptime.start()

    def __init__(self, argv):
        super(Application, self).__init__(argv)

    def setClock(self, time):
        Application.app_datetime.setTime(time)
        Application.uptime.restart()
        self.applicationClockChanged.emit(time)


class ApplicationClock(QtWidgets.QLCDNumber):
    """Виджет внутренних часов программы"""

    timeUpdated = pyqtSignal(QtCore.QDateTime)

    def __init__(self, parent=None):
        super(ApplicationClock, self).__init__(parent)

        self.setSegmentStyle(QtWidgets.QLCDNumber.Filled)

        updateTimer = QtCore.QTimer(self)
        updateTimer.setTimerType(QtCore.Qt.PreciseTimer)
        updateTimer.timeout.connect(self.showTime)
        updateTimer.start(1000)
        self.showTime()

    def showTime(self):
        """Актуализировать время и обновить на отображении"""
        Application.app_datetime = Application.app_datetime.addMSecs(Application.uptime.restart())
        self.display(Application.app_datetime.toUTC().time().toString("hh:mm"))

        # datetime = Application.app_datetime.addMSecs(Application.uptime.elapsed())
        # self.display(datetime.time().toString("hh:mm"))

        self.timeUpdated.emit(Application.app_datetime)

    def mousePressEvent(self, mouseEvent):
        dialog = QtWidgets.QDialog(None)
        timeInput = QtWidgets.QTimeEdit(Application.app_datetime.time(), dialog)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(timeInput)
        dialog.setLayout(layout)
        dialog.exec()

        Application.instance().setClock(timeInput.time())


def fromVariantTime(data):
    time = data
    if not isinstance(time, QTime):
        # dt = dtparser.parse(data)
        # time = QTime(dt.time())
        time = QTime.fromString(data, 'hh:mm')
        if not time.isValid() or time.isNull():
            time = QTime.fromString(data, 'hh,mm')
        if not time.isValid() or time.isNull():
            time = QTime(0,0)
    return time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QVariant, QStringListModel, QDateTime, QTime, QSortFilterProxyModel
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QAbstractScrollArea, QPushButton
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QSizePolicy
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate

# from PyQtProxyModelWithHeaderModels import PyQtProxyModelWithHeaderModels
# from PyQtHierarchicalHeaderView import PyQtHierarchicalHeaderView
from graph import Link


class TimeDelegate(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        if isinstance(value, QTime):
            return locale.toString(value, "hh:mm")
        return super().displayText(value, locale)


class TracesDialog(QDialog):
    """Диалог таблицы трасс для объекта, реализация с моделью по умолчанию"""
    def __init__(self, item, items, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f'Трассы каналов связи {item.textItem.toPlainText()}')

        self.layer = QVBoxLayout()

        #Создание таблицы
        self.table = QTableWidget(self)
        self.blayer = QHBoxLayout()
        self.confirmButton = QPushButton("Сохранить", self)
        self.blayer.addSpacing(800)
        self.blayer.addWidget(self.confirmButton)

        self.layer.addWidget(self.table)
        self.layer.addLayout(self.blayer)

        self.setLayout(self.layer)

        #Заголовок таблицы
        self.table.setColumnCount(9)

        self.table.setHorizontalHeaderLabels(('№\nп/п','Номер\nТЦ',
                                              'Направление\nтрактов',
                                              'Трассы каналов',
                                              'Скорость ЦТ',
                                              'отл.', 'хор.', 'уд.', 'Реал'))

        self.velocityData = QStringListModel(self)
        self.velocityData.setStringList(('STM-1', 'STM-4', 'STM-16', 'STM-64',
                                          'E1','E2','E3','E4','Оцк','Ethernet'))

        date_delegate = TimeDelegate(self.table)
        self.table.setItemDelegateForColumn(5, date_delegate)
        self.table.setItemDelegateForColumn(6, date_delegate)
        self.table.setItemDelegateForColumn(7, date_delegate)
        self.table.setItemDelegateForColumn(8, date_delegate)

        self.table.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred))
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContentsOnFirstShow)

        self.confirmButton.released.connect(self.onConfirm)

        self.currentItem = item
        self.items = items
        self.traces = list()
        self.changedTraces = set()
        for item in self.items:
            if isinstance(item, Link):
                self.traces.append(item)

    def onConfirm(self):
        self.dataToScene()
        self.accept()

    def dataFromScene(self):
        """Простое заполнение параметрами трасс напрямую из графических объектов"""
        for trace in self.currentItem.traces:
            row = self.table.rowCount()
            self.table.insertRow(row)

            id_item = QTableWidgetItem()
            index = self.traces.index(trace)
            id_item.setData(Qt.DisplayRole, str(len(self.traces) - index))
            id_item.setData(Qt.UserRole, QVariant(index))

            #Заполнить встроенное хранилище таблицы построчно из GraphItem.traces[]
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1, QTableWidgetItem(str(trace.ID)))
            self.table.setItem(row, 2, QTableWidgetItem(trace.endItem().textItem.toPlainText()))

            velocityCB = QComboBox(self.table)
            velocityCB.setModel(self.velocityData)
            velocityCB.setCurrentIndex(trace.velocity)
            # заглушка для работы со стандартной моделью, если меняется комбобокс то вся таблица идет на обновление
            velocityCB.currentIndexChanged.connect(self.comboBoxDummy)
            self.table.setCellWidget(row, 4, velocityCB)

            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, trace.grades[0])
            self.table.setItem(row, 5, item)

            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, trace.grades[1])
            self.table.setItem(row, 6, item)

            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, trace.grades[2])
            self.table.setItem(row, 7, item)

            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, trace.rate)
            self.table.setItem(row, 8, item)

        self.table.cellChanged.connect(self.tableChanged)
        self.table.model().dataChanged.connect(self.modelChanged)
        self.table.cellPressed.connect(self.tableChanged)

    def comboBoxDummy(self):
        for row in range(self.table.rowCount()):
            self.changedTraces.add(row)

    def modelChanged(self, topLeft, bottomRight):
        rows = [row for row in range(topLeft.row(), bottomRight.row())]
        for row in rows:
            self.changedTraces.add(row)

    def tableChanged(self, row, column):
        self.changedTraces.add(row)


    def dataToScene(self):
        """Обратная функция, обновление данных схемы из таблицы"""
        for row in range(self.table.rowCount()):
            if row not in self.changedTraces:
                continue

            trace = self.currentItem.traces[row]
            trace.ID = int(self.table.item(row,1).data(Qt.DisplayRole))
            trace.endItem().setText(self.table.item(row,2).data(Qt.DisplayRole))
            trace.velocity = self.table.cellWidget(row,4).currentIndex()
            trace.grades[0] = self.table.item(row,5).data(Qt.DisplayRole)
            trace.grades[1] = self.table.item(row,6).data(Qt.DisplayRole)
            trace.grades[2] = self.table.item(row,7).data(Qt.DisplayRole)
            trace.rate = self.table.item(row,8).data(Qt.DisplayRole)

            trace.isConfigured = True

    def closeEvent(self, event):
        pass

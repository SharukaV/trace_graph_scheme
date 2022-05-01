from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QVariant, QByteArray, QModelIndex, QStringListModel, QSortFilterProxyModel, QSettings
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QMainWindow, QWidget, QTableView
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate, QItemDelegate, QStyleOptionComboBox, QStyle

# Дизайн окна создается в QDesigner и конвертируется из .ui в _ui.py утилитой pyuic5
from tracesWindow_ui import Ui_TracesWindow

from common import Application, velocityCaption
import HierarchicalHeaderView
import tracesModel


class ComboBoxDelegate(QtWidgets.QItemDelegate):
    """Ячейка таблицы выбора скорости из списка, замена стандартной"""
    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.velocityData = QStringListModel(self)
        self.velocityData.setStringList(velocityCaption)

    def setEditorData(self, editor, index):
        editor.blockSignals(True)
        editor.setCurrentIndex(int(index.model().data(index)))
        editor.blockSignals(False)

    def createEditor(self, parent, option, index) -> QWidget:
        combo = QComboBox(parent)
        combo.setModel(self.velocityData)
        combo.currentIndexChanged.connect(self.currentIndexChanged)
        return combo

    def currentIndexChanged(self):
        self.commitData.emit(self.sender())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex())

    def paint(self, painter, option, index) -> None:
        style = Application.style()
        opt = QStyleOptionComboBox()
        opt.rect = option.rect
        comboIndex = self.velocityData.index(index.data())
        opt.currentText = self.velocityData.data(comboIndex, Qt.DisplayRole)
        opt.palette = option.palette
        opt.state = option.state
        opt.subControls = QStyle.SC_All
        opt.activeSubControls = QStyle.SC_All
        opt.editable = False
        opt.frame = True
        style.drawComplexControl(QStyle.CC_ComboBox, opt, painter)
        style.drawControl(QStyle.CE_ComboBoxLabel, opt, painter)


class TracesWindow(QMainWindow, Ui_TracesWindow):
    """Диалог таблицы трасс"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Дизайн окна создается в QDesigner и конвертируется из .ui в _ui.py утилитой pyuic5
        self.setupUi(self)
        # self.setAttribute(Qt.WA_DeleteOnClose)

        hv = HierarchicalHeaderView.HierarchicalHeaderView(Qt.Horizontal, self.view)
        hv_state = Application.settings.value("TraceHeaderSize", type=QByteArray)
        hv.restoreState(hv_state)

        if isinstance(self.view, QtWidgets.QTableView):
            self.view.setHorizontalHeader(hv)
        elif isinstance(self.view, QtWidgets.QTreeView):
            self.view.setHeader(hv)

        self.view.setItemDelegateForColumn(5, ComboBoxDelegate(self))

        self.model = tracesModel.TraceModel()
        self.view.setModel(self.model)

        self.view.selectionModel().selectionChanged.connect(self.updateActions)
        self.createChannelAction.triggered.connect(self.updateActions)
        self.deleteChannelAction.triggered.connect(self.updateActions)

        self.updateActions()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        headerState = None
        if isinstance(self.view, QtWidgets.QTableView):
            headerState = self.view.horizontalHeader().saveState()
        elif isinstance(self.view, QtWidgets.QTreeView):
            headerState = self.view.header().saveState()

        Application.settings.setValue("TraceHeaderSize", headerState)
        a0.accept()

    def setData(self, traces):
        self.model.beginResetModel()
        self.model.rootItem.channels.clear()
        for trace in traces:
            trace.rootChannel.parentItem = self.model.rootItem
            self.model.rootItem.channels.append(trace.rootChannel)
        self.model.endResetModel()

    def setDataChannels(self, traces):
        self.model.beginResetModel()
        self.model.rootItem.channels.clear()
        for trace in traces:
            # self.model.rootItem.channels.extend(trace.rootChannel.channels)
            for channel in trace.rootChannel.channels:
                self.model.rootItem.channels.append(channel)
                #FIXME
                channel.parentItem = self.model.rootItem
        self.model.endResetModel()

    def createChannel(self):
        """Обработчик кнопки - Создать канал"""
        index = self.view.selectionModel().currentIndex()

        # if self.model.getItem(index).parent() == self.model.rootItem:
        #     # Вставить канал в трассу
        #     if not self.model.insertRow(0, index):
        #         return
        # else:
        #Вставить канал в текущую трассу
        if not self.model.insertRow(index.row()+1, index.parent()):
            return

        self.updateActions()

    def destroyChannel(self):
        """Обработчик кнопки - Удалить канал"""
        index = self.view.selectionModel().currentIndex()
        model = self.view.model()

        if (model.removeRow(index.row(), index.parent())):
            self.updateActions()

    def updateActions(self):
        """Изменение активных действий, в зависимости от позиции выделения таблицы"""
        selectedItem = self.model.getItem(self.view.selectionModel().currentIndex())

        hasParent = (selectedItem.parent() != self.model.rootItem)
        hasCurrent = self.view.selectionModel().currentIndex().isValid()
        hasSelection = not self.view.selectionModel().selection().isEmpty()

        self.deleteChannelAction.setEnabled(hasSelection)
        # self.createChannelAction.setEnabled(hasCurrent)

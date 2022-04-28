from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex
from PyQt5.QtCore import QVariant

import HierarchicalHeaderView
from common import Headers, Application
from graph_item import Channel


class TraceModel(QAbstractItemModel):
    """Модель дерева каналов, для отображения таблиц, Qt"""
    def __init__(self, parent=None):
        super(TraceModel, self).__init__(parent)

        self.horizontalHeaderModel = Headers.horizontalHeaderModel
        self.traces = []

        self.rootItem = Channel()
        self.parents = [self.rootItem]
        self.indentations = [0]

    def resetColumn(self, column=None):
        #FIXME перерисовывает всю таблицу скидывая редактируемые значения, необходимо сопоставить конкретный Channel модели
        startIndex = self.index(0, column)
        endIndex = self.index(self.rowCount(), column)

        if column is None or column <0 or column>self.columnCount():
            startIndex = self.index(0, 0)
            endIndex = self.index(self.rowCount(), self.columnCount())

        self.dataChanged.emit(startIndex, endIndex)

    def index(self, row, column, index=QModelIndex()):
        if index.isValid() and index.column() != 0:
            return QModelIndex()

        parentItem = self.getItem(index)
        childItem = parentItem.child(row)

        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = self.getItem(index)
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        #FIXME get None on all channels list
        childNumber = parentItem.childNumber()

        return self.createIndex(childNumber, 0, parentItem)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)

    def rowCount(self, index=QModelIndex()):
        if index.isValid():
            parent = index.internalPointer()
        else:
            parent = self.rootItem
        return parent.childCount()

    def columnCount(self, index=QModelIndex()):
        return self.rootItem.columnCount()

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.rootItem

    def insertRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)

        self.beginInsertRows(parent, position, position + rows - 1)
        success = parentItem.insertChildren(position, rows)
        self.endInsertRows()

        return success

    def removeRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)

        self.beginRemoveRows(parent, position, position + rows - 1)
        success = parentItem.removeChildren(position, rows)
        self.endRemoveRows()

        return success

    def data(self, index, role=Qt.DisplayRole):
        """ Returns the data stored under the given role for the item referred to by the index """
        if index.column() == 10:
                if role == Qt.BackgroundColorRole:
                    return QtGui.QColor(self.getItem(index).data(index.column()))
        elif role == Qt.DisplayRole:
            return self.getItem(index).data(index.column())
        elif role == Qt.EditRole:
            return self.getItem(index).data(index.column())
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignHCenter
        elif role == HierarchicalHeaderView.HorizontalHeaderDataRole:
            return self.horizontalHeaderModel

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        item = self.getItem(index)
        success = item.setData(index.column(), value)
        if success:
            item.updateWarning(Application.app_datetime.time())
            self.dataChanged.emit(index, index)
        return success

    def flags(self, index):
        if not index.isValid():
            super(TraceModel, self).flags(index)
        return Qt.ItemIsEditable | super(TraceModel, self).flags(index)

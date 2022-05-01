import csv, io
import bs4

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QVariant, QModelIndex, QAbstractItemModel
from PyQt5.QtWidgets import QTableView, QStyle, QMenu, QAction, QShortcut
from PyQt5.QtGui import QGuiApplication, QClipboard


def detect_engine():
    try:
        import lxml
    except ImportError:
        engine = 'html.parser'
    else:
        engine = 'lxml'
    return engine


class TableView(QTableView):
    """Таблица с вставкой из буфер обмена Word, Excel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = detect_engine()

        self.pasteAction = QtWidgets.QAction(self.style().standardIcon(QStyle.SP_MediaPlay),
                "Вставить", self,
                shortcut="Ctrl+V", statusTip="Вставить",
                triggered=self.paste)

        self.contextMenuIndex = None
        self.contextMenu = QMenu("Edit")
        self.contextMenu.addAction(self.pasteAction)

        self.addAction(self.pasteAction)

    def contextMenuEvent(self, event):
        self.contextMenuIndex = self.indexAt(event.pos())
        self.contextMenu.popup(QtGui.QCursor.pos())

    def clipboardParser(self, html):
        # парсинг mime:text/html буфера обмена на таблицу данных
        soup = bs4.BeautifulSoup(html, self.engine)
        csv_tables = []
        dict_tables = []
        for table_num, table in enumerate(soup.find_all('table')):
            csv_string = io.StringIO()
            csv_writer = csv.writer(csv_string)
            dict_table = []

            for tr in table.find_all('tr'):
                table_row = []
                csv_row = [''.join(cell.stripped_strings) for cell in tr.find_all(['td', 'th'])]
                for cell in tr.find_all(['td', 'th']):
                    table_row.append(cell.get_text().strip())

                csv_writer.writerow(csv_row)
                dict_table.append(table_row)

            table_attrs = dict(num=table_num)
            dict_tables.append(dict_table)
            csv_tables.append((csv_string.getvalue(), table_attrs))

        # print(dict_tables)
        # print(csv_tables)

        if len(dict_tables) > 0:
            return dict_tables[0]

        return None

    def paste(self):
        clipboard = QGuiApplication.clipboard()
        mimeData = clipboard.mimeData()
        html = mimeData.html()

        pasted_table = self.clipboardParser(html)

        selectedIndexes = self.selectionModel().selectedIndexes()

        if pasted_table is None:
            for index in selectedIndexes:
                self.model().setData(index, clipboard.text())
            return

        selectedIndexTable = []

        # индексы для вставки в виде таблицы
        if len(selectedIndexes) == 1:
            # #если в буфере таблица а выделена одна ячейка генерируем индексы для вставки
            rowShift = selectedIndexes[0].row()
            columnShift = selectedIndexes[0].column()

            # for rowIndex, row in enumerate(pasted_table):
            #     for columnIndex, data in enumerate(row):
            #         index = self.model().index(rowIndex+rowShift, columnIndex+columnShift)
            #         self.model().setData(index, data)

            for rowIndex, row in enumerate(pasted_table):
                rowModelIndex = []
                for columnIndex, column in enumerate(row):

                    #пропуск визуально скрытых столбцов
                    hiddenColumns = 0
                    while columnIndex+hiddenColumns < self.model().columnCount():
                        if self.isColumnHidden(columnShift+columnIndex+hiddenColumns):
                            hiddenColumns += 1
                        else:
                            break

                    rowModelIndex.append(self.model().index(rowIndex+rowShift, columnIndex+columnShift+hiddenColumns))

                selectedIndexTable.append(rowModelIndex)

            for rowIndex, row in enumerate(selectedIndexTable):
                for columnIndex, index in enumerate(row):
                    self.model().setData(index, pasted_table[rowIndex][columnIndex])
        else:
            currentRow  = selectedIndexes[0].row()
            rowModelIndex = []
            for index in selectedIndexes:
                if index.row() > currentRow:
                    selectedIndexTable.append(rowModelIndex)
                    rowModelIndex = [index]
                    currentRow += 1
                else:
                    rowModelIndex.append(index)
            selectedIndexTable.append(rowModelIndex)

            for rowIndex, row in enumerate(selectedIndexTable):
                if rowIndex >= len(pasted_table):
                    continue
                for columnIndex, index in enumerate(row):
                    if columnIndex >= len(pasted_table[rowIndex]):
                        continue
                    self.model().setData(index, pasted_table[rowIndex][columnIndex])

        # print([(index.row(),index.column()) for index in selectedIndexes])
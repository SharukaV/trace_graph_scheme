import sys, os
import pickle, json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QSizePolicy, QToolButton, QGridLayout, QLabel, QMessageBox
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTime, Qt

from common import Application, ApplicationClock, WarningLevel

#файл ресурсов конвертируется из Qtшного - иконки утилитой pyrcc5
import graph_rc

from graph import GraphScene, GraphItem, Link
from tracesWindow import TracesWindow
from alarmWindow import AlarmWindow


class MainWindow(QtWidgets.QMainWindow):
    """Основное окно Qt для поддержки тулбаров и главного меню"""
    InsertTextButton = 10

    def __init__(self):
        super(MainWindow, self).__init__()

        self.createActions()
        self.createMenus()
        self.statusBar()

        #Часы приложения, размещены в виджете
        self.applicationClock = ApplicationClock(self)
        self.applicationClock.setToolTip("Установить часы программы - клик мышью")
        self.applicationClock.setStatusTip("Установить часы программы - клик мышью")

        #Окно отображения трасс
        self.tracesWindow = TracesWindow()
        self.tracesWindow.toolBar.hide()
        self.tracesWindow.view.setColumnHidden(0, False)
        self.tracesWindow.view.setColumnHidden(2, True)
        self.tracesWindow.view.setColumnHidden(3, True)
        self.tracesWindow.view.setColumnHidden(5, False)
        self.tracesWindow.resize(1000, 500)

        # Окно отображения каналов
        self.channelWindowA = TracesWindow()
        self.channelWindowA.setWindowTitle("Каналы схемы")
        self.channelWindowA.toolBar.hide()
        self.channelWindowA.view.setColumnHidden(0, True)
        self.channelWindowA.view.setColumnHidden(2, False)
        self.channelWindowA.view.setColumnHidden(3, False)
        self.channelWindowA.view.setColumnHidden(5, True)
        self.channelWindowA.resize(1000, 500)

        # Окно отображения каналов
        self.channelWindow = TracesWindow()
        self.channelWindow.setWindowTitle("Каналы трассы")
        self.channelWindow.view.setColumnHidden(0, True)
        self.channelWindow.view.setColumnHidden(2, False)
        self.channelWindow.view.setColumnHidden(3, False)
        self.channelWindow.view.setColumnHidden(5, True)
        self.channelWindow.resize(1000, 500)

        #Окно отображения событий изменения оценки
        #В нем же хранится всплывающее сообщений
        self.alarmWindow = AlarmWindow()
        self.alarmWindow.resize(500, 1000)

        # Создание главного виджета отрисовки, размер viewport, масштабирование отключено
        self.scene_dump = None
        self.scene = GraphScene(self.itemMenu, self.channelMenu)
        self.scene.setSceneRect(QtCore.QRectF(0, 0, 5000, 5000))

        self.scene.itemInserted.connect(self.itemInserted)
        self.scene.itemSelected.connect(self.itemSelected)
        self.applicationClock.timeUpdated.connect(self.clockTick)
        Application.instance().applicationClockChanged.connect(self.clockSetted)

        self.createToolBars()
        self.createToolBox()

        layout = QtWidgets.QHBoxLayout()
        self.view = QtWidgets.QGraphicsView(self.scene)
        layout.addWidget(self.view)

        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(layout)

        self.setCentralWidget(self.widget)
        self.setWindowTitle("Graph")

        # активация стартового режима
        self.pointerTypeGroup.button(3).setChecked(True)

        #таймер автосохранения
        self.autoSaveTimer = QtCore.QTimer(self)
        self.autoSaveTimer.timeout.connect(lambda: self.saveSchema(False, 'autosave.json'))
        self.autoSaveTimer.start(60000)

        # #загрузка схемы по умолчанию
        # try:
        #     # fileName = f'{os.getcwd()}\schema.json'
        #     fileName = 'schema.json'
        #     file = open(fileName, 'rt')
        #     self.scene.clear()
        #     self.scene.json_deserialize(file)
        #     self.scene.update()
        #     file.close()
        # except:
        #     pass

    def clockSetted(self, time):
        for trace in self.scene.traces:
            trace.rootChannel.isAlarmRead = False
            for channel in trace.rootChannel.channels:
                channel.rate = time
            trace.rootChannel.rate = time

        self.tracesWindow.model.resetColumn(9)
        self.channelWindow.model.resetColumn(9)
        self.channelWindowA.model.resetColumn(9)
        self.scene.update()

    def clockTick(self):
        """Актуализация временных параметров трасс и уровней оповещения"""
        needUpdate = False

        for trace in self.scene.traces:
            commonWarning = WarningLevel.Passed

            # Апдейтить и обработать алармы каналов трассы
            for subchannel in trace.rootChannel.channels:
                updated = subchannel.updateWarning(Application.app_datetime.time())
                if updated:
                    level = subchannel.warningLevel
                    if level > commonWarning:
                        commonWarning = level
                    if level > WarningLevel.Passed:
                        self.alarmWindow.logEvent(level,
                                                  str(subchannel),
                                                  f'{subchannel.direction} {subchannel.traceDescription}')
                        needUpdate = True

            #Апдейтить и обработать алармы трассы
            updated = trace.rootChannel.updateWarning(Application.app_datetime.time())
            if updated or commonWarning.value > trace.rootChannel.warningLevel.value:
                if commonWarning.value > trace.rootChannel.warningLevel.value:
                    trace.rootChannel.warningLevel = commonWarning
                for link in trace.links:
                    link.myColor = trace.rootChannel.warningLevel.color

                if trace.rootChannel.warningLevel.value > WarningLevel.Passed.value:
                    self.alarmWindow.logEvent(trace.rootChannel.warningLevel,
                                              str(trace.rootChannel),
                                              f'{trace.rootChannel.direction} {trace.rootChannel.traceDescription}')
                    needUpdate = True

            for link in trace.links:
                if not trace.rootChannel.isAlarmRead \
                    and trace.rootChannel.warningLevel.value >= self.alarmWindow.warningLevel.value \
                    and QTime.currentTime().second() % 2 == 0:
                    link.myColor = WarningLevel.Default.color
                else:
                    link.myColor = trace.rootChannel.warningLevel.color

        if needUpdate:
            self.tracesWindow.model.resetColumn(10)
            self.channelWindow.model.resetColumn(10)
            self.channelWindowA.model.resetColumn(10)

        self.scene.update()

    ##Все операции с объектами работают сразу с мультивыделением (Ctrl+click)
    ##Прервать если нужно ничего не делать при выборе нескольких объектов одновременно
    #if self.scene.selectedItems().count() > 1:
    #    return
    ##либо включить обработку в циклах #break

    def alarmWindowShow(self):
        """Обработчик действия - показать главное окно"""
        self.alarmWindow.show()

    def zoomIn(self):
        # transform = self.view.transform()
        # self.view.resetTransform()
        # self.view.translate(transform.dx(), transform.dy())
        self.view.scale(1.5, 1.5)

    def zoomOut(self):
        # transform = self.view.transform()
        # self.view.resetTransform()
        # self.view.translate(transform.dx(), transform.dy())
        self.view.scale(0.75, 0.75)

    def setItemType(self, action):
        index = self.itemTypeActionGroup.actions().index(action)
        type = list(GraphItem.ItemType)[index]
        self.scene.setItemType(type)

    def tracesItem(self):
        """Окно трасс объекта"""
        graphItem = None

        for item in self.scene.selectedItems():
            if isinstance(item, GraphItem):
                graphItem = item
                break

        traces = graphItem.traces if graphItem else self.scene.traces

        for trace in traces:
            trace.rootChannel.isAlarmRead = True

        self.tracesWindow.setData(traces)
        self.tracesWindow.show()
        # self.tracesWindow.view.expandAll()
        self.tracesWindow.view.resizeColumnToContents(0)

    def channelsItem(self):
        """Окно каналов объекта"""
        linkItem = None
        for item in self.scene.selectedItems():
            if isinstance(item, Link):
                linkItem = item
                break

        for trace in self.scene.traces:
            if linkItem in trace.links:
                self.channelWindow.model.beginResetModel()

                trace.rootChannel.isAlarmRead = True

                # FIXME break index
                for channel in trace.rootChannel.channels:
                    channel.parentItem = trace.rootChannel

                self.channelWindow.model.rootItem = trace.rootChannel
                self.channelWindow.model.endResetModel()
                self.channelWindow.show()

    def channelsAll(self):
        """Окно каналов объекта"""
        self.channelWindowA.setDataChannels(self.scene.traces)
        self.channelWindowA.show()
        # self.tracesWindow.view.expandAll()
        # self.channelWindowA.view.resizeColumnToContents(0)

    def renameItem(self):
        """Переименовывает выделенный обьект"""
        for item in self.scene.selectedItems():
            #Объект является узлом
            if isinstance(item, GraphItem):
                if item.textItem.textInteractionFlags() == QtCore.Qt.NoTextInteraction:
                    item.textItem.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
                document = item.textItem.document()
                cursor = QtGui.QTextCursor(document)
                cursor.select(3)
                item.textItem.setFocus()
                break
            #Объект является линией связи между двумя узлами
            if isinstance(item, Link):
                for trace in self.scene.traces:
                    if item in trace.links:
                        input_id, ok = QtWidgets.QInputDialog.getText(self, 'Номер ЦТ', 'Введите номер ЦТ', 0, trace.numberZT)
                        if ok:
                            trace.numberZT = input_id
                        break

    def deleteItem(self):
        """Удаляет объект"""
        for item in self.scene.selectedItems():
            #Удаляется вся трасса при удалении любого из ее элементов, без перестроения топологии
            if isinstance(item, Link):
                for trace in self.scene.traces:
                    if item in trace.links:
                        self.scene.removeTraces([trace])
            if isinstance(item, GraphItem):
                self.scene.removeTraces(item.traces)
            self.scene.removeItem(item)

    def pointerGroupClicked(self, i):
        """Обработчик клика группы инструментов - перемещение создание объектов и трасс"""
        self.statusBar().clearMessage()
        if i == 1:
            self.scene.setItemType(GraphItem.ItemType.Circle)
            self.statusBar().showMessage("Левая кнопка-следующий узел, правая-закончить редактирование")
        self.scene.setMode(self.pointerTypeGroup.checkedId())

    def backgroundButtonGroupClicked(self, button):
        buttons = self.backgroundButtonGroup.buttons()
        for myButton in buttons:
            if myButton != button:
                button.setChecked(False)

        text = button.text()
        if text == "Custom Image":
            fileName = QtWidgets.QFileDialog.getOpenFileName()
            if fileName[0]:
                pixmap = QtGui.QPixmap()
                if pixmap.load(fileName[0]):
                    self.scene.setBackgroundBrush(QtGui.QBrush(QtGui.QPixmap(fileName[0])))
                else:
                    QMessageBox.warning(self, 'Ошибка загрузки фона', f'Файл {fileName[0]} не удалось распознать как изображение')
        elif text == "Blue Grid":
            self.scene.setBackgroundBrush(QtGui.QBrush(QtGui.QPixmap(':/images/background1.png')))
        elif text == "White Grid":
            self.scene.setBackgroundBrush(QtGui.QBrush(QtGui.QPixmap(':/images/background2.png')))
        elif text == "Gray Grid":
            self.scene.setBackgroundBrush(QtGui.QBrush(QtGui.QPixmap(':/images/background3.png')))
        else:
            self.scene.setBackgroundBrush(QtGui.QBrush(QtGui.QPixmap(':/images/background4.png')))

        self.scene.update()
        self.view.update()


    def openSchema(self, state=False, name=None):
        """Загрузить схему из файла"""
        fileName = [name]
        if name is None:
            fileName = QtWidgets.QFileDialog.getOpenFileName()
        if fileName[0]:
            file = open(fileName[0], 'rt')
            self.scene.clear()
            self.scene.json_deserialize(file)
            self.scene.update()
            file.close()

    def saveSchema(self, state=False, name=None):
        """Сохранить схему в файл"""
        fileName = [name]
        if name is None:
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, '', 'schema.json')
        if fileName[0]:
            file = open(fileName[0], 'wt')
            # pickle не работает с QObject :(
            self.scene.json_serialize(file)
            file.close()

    def dumpSchema(self):
        """Сохранить объект схемы"""
        self.scene_dump = json.dumps(self.scene, indent=4, default=GraphScene.json_serialize_dump_obj)
        print(self.scene_dump)

    def restoreSchema(self):
        """Восстановить объект"""
        if not self.scene_dump is None:
            self.scene.fromJSON(json.loads(self.scene_dump))
            self.scene.update()

    def bringToFront(self):
        """Изменяет порядок видимости объектов"""
        if not self.scene.selectedItems():
            return

        selectedItem = self.scene.selectedItems()[0]
        overlapItems = selectedItem.collidingItems()

        zValue = 0
        for item in overlapItems:
            if (item.zValue() >= zValue and isinstance(item, GraphItem)):
                zValue = item.zValue() + 0.1
        selectedItem.setZValue(zValue)

    def sendToBack(self):
        """Изменяет порядок видимости объектов, скрытие"""
        if not self.scene.selectedItems():
            return

        selectedItem = self.scene.selectedItems()[0]
        overlapItems = selectedItem.collidingItems()

        zValue = 0
        for item in overlapItems:
            if (item.zValue() <= zValue and isinstance(item, GraphItem)):
                zValue = item.zValue() - 0.1
        selectedItem.setZValue(zValue)

    def itemInserted(self, item):
        pass

    def itemSelected(self, item):
        font = item.font()
        color = item.defaultTextColor()
        self.fontCombo.setCurrentFont(font)
        self.fontSizeCombo.setEditText(str(font.pointSize()))
        self.boldAction.setChecked(font.weight() == QtGui.QFont.Bold)
        self.italicAction.setChecked(font.italic())
        self.underlineAction.setChecked(font.underline())

    def createItemTypeAction(self, itemType):
        item = GraphItem(itemType, None)
        icon = QtGui.QIcon(item.image())

        action = QtWidgets.QAction(icon, itemType.readableName, self)
        action.setCheckable(True)

        return action

    def createBackgroundCellWidget(self, text, image):
        button = QToolButton()
        button.setText(text)
        button.setIcon(QtGui.QIcon(image))
        button.setIconSize(QtCore.QSize(50, 50))
        button.setCheckable(True)
        self.backgroundButtonGroup.addButton(button)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget


    def createActions(self):
        self.openAction = QtWidgets.QAction(
                QtGui.QIcon(':/images/file_open.png'), "Open",
                self, shortcut="Ctrl+O", statusTip="Открыть файл со схемой",
                triggered=self.openSchema)

        self.saveAction = QtWidgets.QAction(
                QtGui.QIcon(':/images/save.png'), "Save as...",
                self, shortcut="Ctrl+S", statusTip="Сохранить схему",
                triggered=self.saveSchema)

        self.dumpAction = QtWidgets.QAction(
                QtGui.QIcon(''), "Dump schema",
                self, statusTip="Записать объект сцены в файл",
                triggered=self.dumpSchema)

        self.restoreAction = QtWidgets.QAction(
                QtGui.QIcon(''), "Schema from dump",
                self, statusTip="Восстановить объект сцены",
                triggered=self.restoreSchema)

        self.zoomIn = QtWidgets.QAction(
                QtGui.QIcon(':/images/zoom_in.png'), "Увеличить",
                self, shortcut="Ctrl+PageUp", statusTip="Увеличить",
                triggered=self.zoomIn)

        self.zoomOut = QtWidgets.QAction(
                QtGui.QIcon(':/images/zoom_out.png'), "Уменьшить",
                self, shortcut="Ctrl+PageDown", statusTip="Уменьшить",
                triggered=self.zoomOut)

        self.toFrontAction = QtWidgets.QAction(
                QtGui.QIcon(':/images/bringtofront.png'), "Bring to &Front",
                self, shortcut="Ctrl+F", statusTip="Bring item to front",
                triggered=self.bringToFront)

        self.sendBackAction = QtWidgets.QAction(
                QtGui.QIcon(':/images/sendtoback.png'), "Send to &Back", self,
                shortcut="Ctrl+B", statusTip="Send item to back",
                triggered=self.sendToBack)

        self.deleteAction = QtWidgets.QAction(QtGui.QIcon(':/images/delete.png'),
                "&Delete", self, shortcut="Delete",
                statusTip="Delete item from diagram",
                triggered=self.deleteItem)

        self.tracesAction = QtWidgets.QAction(QtGui.QIcon(':/images/traces.png'),
                "&Трассы...", self, shortcut="Трассы каналов связи",
                statusTip="Трассы каналов связи",
                triggered=self.tracesItem)

        self.channelsAction = QtWidgets.QAction(QtGui.QIcon(':/images/traces.png'),
                "&Каналы трассы...", self, shortcut="Каналы трассы",
                statusTip="Каналы трассы",
                triggered=self.channelsItem)

        self.allChannelsAction = QtWidgets.QAction(QtGui.QIcon(':/images/traces.png'),
                "&Каналы схемы...", self, shortcut="Каналы схемы",
                statusTip="Каналы схемы",
                triggered=self.channelsAll)

        self.alarmAction = QtWidgets.QAction(QtGui.QIcon(':/images/bell-ring.png'),
                "&Алармы...", self, shortcut="Оповещения времени каналов связи",
                statusTip="Оповещения времени каналов связи",
                triggered=self.alarmWindowShow)

        self.renameAction = QtWidgets.QAction(QtGui.QIcon(':/images/italic.png'),
                "&Переименовать...", self, shortcut="Переименовать",
                statusTip="Переименовать",
                triggered=self.renameItem)

        #типы объектов, действия смены типа объекта, берутся автоматически из перечисления GraphItem.ItemType
        self.itemTypeActionGroup = QtWidgets.QActionGroup(self)
        for itemType in GraphItem.ItemType:
            self.itemTypeActionGroup.addAction(self.createItemTypeAction(itemType))
        self.itemTypeActionGroup.triggered.connect(self.setItemType)

        self.exitAction = QtWidgets.QAction("E&xit", self, shortcut="Ctrl+X",
                statusTip="Quit Scenediagram example", triggered=self.close)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.dumpAction)
        self.fileMenu.addAction(self.restoreAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAction)

        self.itemMenu = QtWidgets.QMenu("&Item", self)
        self.itemMenu.addAction(self.tracesAction)
        self.itemMenu.addAction(self.renameAction)
        self.itemMenu.addSeparator()
        self.itemMenu.addAction(self.toFrontAction)
        self.itemMenu.addAction(self.sendBackAction)
        self.itemMenu.addSeparator()
        self.itemMenu.addAction(self.deleteAction)

        self.channelMenu = QtWidgets.QMenu("&Link", self)
        self.channelMenu.addAction(self.channelsAction)
        self.channelMenu.addAction(self.deleteAction)

        self.itemTypeMenu = QtWidgets.QMenu("Item &Type", self)
        self.itemTypeMenu.addActions(self.itemTypeActionGroup.actions())

    def createToolBars(self):
        self.infoToolbar = self.addToolBar("Information")
        self.infoToolbar.addWidget(self.applicationClock)
        self.infoToolbar.addAction(self.alarmAction)
        self.infoToolbar.addSeparator()
        self.infoToolbar.addAction(self.zoomIn)
        self.infoToolbar.addAction(self.zoomOut)

        self.pointerToolbar = self.addToolBar("Pointer type")

        pointerButton = QtWidgets.QToolButton(self.pointerToolbar)
        pointerButton.setCheckable(True)
        pointerButton.setIcon(QtGui.QIcon(':/images/pointer.png'))
        pointerButton.setToolTip("Выделение и перемещение объектов")
        pointerButton.setStatusTip("Выделение и перемещение объектов")

        figureButton = QtWidgets.QToolButton(self.pointerToolbar)
        figureButton.setCheckable(True)
        figureButton.setToolTip("Создание узлов связи")
        figureButton.setStatusTip("Создание узлов связи")
        figureButton.setIcon(QtGui.QIcon(':/images/figure.png'))

        figureButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        figureButton.setMenu(self.itemTypeMenu)

        linePointerButton = QtWidgets.QToolButton(self.pointerToolbar)
        linePointerButton.setCheckable(True)
        linePointerButton.setIcon(QtGui.QIcon(':/images/linepointer.png'))
        linePointerButton.setToolTip("Создание трасс")
        linePointerButton.setStatusTip("Создание трасс")

        self.pointerTypeGroup = QtWidgets.QButtonGroup()
        self.pointerTypeGroup.addButton(pointerButton, GraphScene.MoveItem)
        self.pointerTypeGroup.addButton(figureButton, GraphScene.InsertItem)
        self.pointerTypeGroup.addButton(linePointerButton, GraphScene.InsertTrace)
        self.pointerTypeGroup.buttonClicked[int].connect(self.pointerGroupClicked)

        self.pointerToolbar.addWidget(pointerButton)
        self.pointerToolbar.addWidget(figureButton)
        self.pointerToolbar.addWidget(linePointerButton)

        self.editToolBar = self.addToolBar("Edit")
        self.editToolBar.addAction(self.allChannelsAction)
        self.editToolBar.addAction(self.renameAction)
        self.editToolBar.addSeparator()
        self.editToolBar.addAction(self.toFrontAction)
        self.editToolBar.addAction(self.sendBackAction)
        self.editToolBar.addSeparator()
        self.editToolBar.addAction(self.deleteAction)

    def createToolBox(self):
        self.backgroundButtonGroup = QtWidgets.QButtonGroup()
        self.backgroundButtonGroup.buttonClicked.connect(self.backgroundButtonGroupClicked)

        backgroundLayout = QtWidgets.QGridLayout()
        backgroundLayout.addWidget(self.createBackgroundCellWidget("Custom Image",
                ':/images/image.png'), 0, 0)
        backgroundLayout.addWidget(self.createBackgroundCellWidget("Blue Grid",
                ':/images/background1.png'), 1, 0)
        backgroundLayout.addWidget(self.createBackgroundCellWidget("White Grid",
                ':/images/background2.png'), 2, 0)
        backgroundLayout.addWidget(self.createBackgroundCellWidget("Gray Grid",
                ':/images/background3.png'), 3, 0)
        backgroundLayout.addWidget(self.createBackgroundCellWidget("No Grid",
                ':/images/background4.png'), 4, 0)

        # backgroundLayout.setRowStretch(2, 10)
        # backgroundLayout.setColumnStretch(2, 10)

        backgroundWidget = QWidget()
        backgroundWidget.setLayout(backgroundLayout)

        self.toolBox = QtWidgets.QToolBox()
        self.toolBox.setSizePolicy(QtWidgets.QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))
        self.toolBox.setMinimumWidth(backgroundWidget.sizeHint().width())
        self.toolBox.addItem(backgroundWidget, "Backgrounds")

        self.dockToolBox = QtWidgets.QDockWidget(self)
        self.dockToolBox.setWidget(self.toolBox)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dockToolBox)


if __name__ == '__main__':
    app = Application(sys.argv)

    mainWindow = MainWindow()
    mainWindow.setGeometry(100, 100, 1000, 700)
    mainWindow.show()

    sys.exit(app.exec_())

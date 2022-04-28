import json
from graph_item import *


class GraphScene(QtWidgets.QGraphicsScene):
    """Хранилище объектов отображаемых, часть Qt фреймворка для отрисовки множества"""
    InsertItem, InsertTrace, InsertText, MoveItem  = range(4)

    itemInserted = QtCore.pyqtSignal(GraphItem)
    textInserted = QtCore.pyqtSignal(QtWidgets.QGraphicsTextItem)
    itemSelected = QtCore.pyqtSignal(QtWidgets.QGraphicsItem)

    def __init__(self, itemMenu, linkMenu, parent=None):
        super(GraphScene, self).__init__(parent)

        self.line = None
        self.trace = None
        self.textItem = None
        self.traces = []

        self.myItemMenu = itemMenu
        self.linkMenu = linkMenu
        self.myMode = self.MoveItem
        self.myItemType = GraphItem.ItemType.Circle

        self.myItemColor = QtCore.Qt.white
        self.myTextColor = QtCore.Qt.black
        self.myLineColor = QtCore.Qt.black
        self.myFont = QtGui.QFont()

    def setLineColor(self, color):
        self.myLineColor = color
        if self.isItemChange(Link):
            item = self.selectedItems()[0]
            item.setColor(self.myLineColor)
            self.update()

    def setTextColor(self, color):
        self.myTextColor = color
        item = self.selectedItems()[0]
        item.setDefaultTextColor(self.myTextColor)

    def setItemColor(self, color):
        self.myIttemColor = color
        if self.isItemChange(GraphItem):
            item = self.selectedItems()[0]
            item.setBrush(self.myItemColor)

    def setFont(self, font):
        self.myFont = font
        item = self.selectedItems()[0]
        item.setFont(self.myFont)

    def setMode(self, mode):
        """Режим графического редактора: выделение, перемещение, создание обьектов и трасс"""
        if self.trace:
            for link in self.trace.links:
                self.removeItem(link)
        self.trace = None
        self.removeItem(self.line)
        self.line = None

        self.myMode = mode

    def setItemType(self, type):
        self.myItemType = type

    def editorLostFocus(self, item):
        cursor = item.textCursor()
        cursor.clearSelection()
        item.setTextCursor(cursor)

        if not item.toPlainText():
            self.removeItem(item)
            item.deleteLater()

    def removeTraces(self, traces):
        for trace in list(set(traces) & set(self.traces)):
            try:
                for link in trace.links:
                    if link in self.items():
                        self.removeItem(link)
                self.traces.remove(trace)
            except ValueError:
                pass

    def mousePressEvent(self, mouseEvent):
        def topLevelItem(items):
            """
            Определить основной обьект схемы для вложенных
            (для GraphItemText будет содержащий его GraphItem например)
            """
            #TODO Список включает вложенные, необходимо корректно определять итем верхнего уровня
            for item in items:
                if item.parentItem() is None:
                    if isinstance(item, GraphItem):
                        return item
                        break
            return None

        # Вставка объекта
        if self.myMode == self.InsertItem:
            item = GraphItem(self.myItemType, self.myItemMenu)
            item.setBrush(self.myItemColor)
            self.addItem(item)
            item.setPos(mouseEvent.scenePos())
            self.itemInserted.emit(item)

        # Вставка трассы
        elif self.myMode == self.InsertTrace:
            if mouseEvent.button() == QtCore.Qt.LeftButton:
                #Создание новой трассы
                if self.trace is None:
                    self.trace = Trace()

                #Определение кликнутого узла
                clickItem = topLevelItem(self.items(mouseEvent.scenePos()))
                if not clickItem:
                    return super(GraphScene, self).mousePressEvent(mouseEvent)

                #Создать связь узлов, если есть линия отрисовки
                if self.line:
                    endItem = clickItem
                    #TODO startItem запомнить глобально, а не вычислять теперь из линии
                    startItems = self.items(self.line.line().p1())
                    if len(startItems) and startItems[0] == self.line:
                        startItems.pop(0)
                    startItem = topLevelItem(startItems)

                    if (startItem and endItem) and startItem != endItem:
                        link = Link(startItem, endItem)
                        link.setColor(self.myLineColor)
                        startItem.addTrace(self.trace)
                        endItem.addTrace(self.trace)
                        link.trace = self.trace
                        self.trace.links.append(link)

                        link.setZValue(-1000.0)
                        link.myContextMenu = self.linkMenu
                        # link.setParentItem(startItem)
                        self.addItem(link)
                        link.updatePosition()

                    if self.trace and len(self.trace.links) > 0:
                        nodeNames = []
                        for link in self.trace.links:
                            nodeNames.append(link.startItem().textItem.toPlainText())
                        last_link = self.trace.links[-1]
                        nodeNames.append(last_link.endItem().textItem.toPlainText())
                        self.traces.append(self.trace)

                    self.removeItem(self.line)
                    self.line = None
                    self.trace = None

                else:
                    #Создать связь для следующего узла
                    self.line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(mouseEvent.scenePos(), mouseEvent.scenePos()))
                    self.line.setPen(QtGui.QPen(self.myLineColor, 2))
                    self.addItem(self.line)

            #Завершение редактирования трассы по правой кнопке мышки
            elif mouseEvent.button() == QtCore.Qt.RightButton:
                if self.trace and len(self.trace.links) > 0:
                    nodeNames = []
                    for link in self.trace.links:
                        nodeNames.append(link.startItem().textItem.toPlainText())
                    last_link = self.trace.links[-1]
                    nodeNames.append(last_link.endItem().textItem.toPlainText())

                    # self.trace.rootChannel.direction = f'{nodeNames[0]}-{nodeNames[-1]}'
                    # self.trace.rootChannel.traceDescription = str.join('+', nodeNames)

                    self.traces.append(self.trace)
                self.removeItem(self.line)
                self.line = None
                self.trace = None

        super(GraphScene, self).mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        # Рисует линию будущей трассы при редактировании - когда еще не выбран второй объект для нее
        if self.myMode == self.InsertTrace and self.line:
            newLine = QtCore.QLineF(self.line.line().p1(), mouseEvent.scenePos())
            self.line.setLine(newLine)
        # перемещение объектов если выбраны объекты
        elif self.myMode == self.MoveItem:
            super(GraphScene, self).mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        pass
        super(GraphScene, self).mouseReleaseEvent(mouseEvent)

    def isItemChange(self, type):
        for item in self.selectedItems():
            if isinstance(item, type):
                return True
        return False

    """Блок сериализации в JSON"""
    # Serialize whole scene to JSON into stream
    def json_serialize(self, stream) -> None:
        json.dump(self, stream, indent=4, default=GraphScene.json_serialize_dump_obj)

    def json_deserialize(self, stream) -> None:
        self.fromJSON(json.load(stream))

    def fromJSON(self, json):
        """Парсинг схемы и создание объектов по информации из JSON"""

        self.removeTraces(self.traces)
        self.traces.clear()
        self.clear()
        graphItems = dict()

        # try:
        for itemJSON in json["items"]:
            # classItem = globals()[itemJSON["__classname__"]]
            # item = classItem()
            if itemJSON["__classname__"] != "GraphItem":
                continue

            item = GraphItem.fromJSON(itemJSON)
            item.setBrush(self.myItemColor)
            item.myContextMenu = self.myItemMenu
            self.addItem(item)

            old_id = int(itemJSON["id"], base=16)
            graphItems[old_id] = item

        for itemJSON in json["items"]:
            if itemJSON["__classname__"] != "Link":
                continue

            start_id = int(itemJSON["startItemID"], base=16)
            end_id = int(itemJSON["endItemID"], base=16)
            StartItem = graphItems.get(start_id, None)
            EndItem = graphItems.get(end_id, None)

            link = Link.fromJSON(itemJSON, StartItem, EndItem)

            link.setColor(self.myLineColor)
            link.myContextMenu = self.linkMenu
            link.setZValue(-1000.0)
            self.addItem(link)
            link.updatePosition()

            graphItems[int(itemJSON["id"], base=16)] = link

        for traceJson in json["traces"]:
            if traceJson["__classname__"] != "Trace":
                continue

            trace = Trace.fromJSON(traceJson, graphItems)
            self.traces.append(trace)

        # except Exception as e:
        #     exc_type, exc_obj, exc_tb = sys.exc_info()
        #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        #     print(exc_type, fname, exc_tb.tb_lineno)

    # This method is called on every object to be dumped/serialized
    @staticmethod
    def json_serialize_dump_obj(obj):
        # if object has a `json_dump_obj()` method call that...
        if hasattr(obj, "json_dump_obj"):
            return obj.json_dump_obj()
        # ...else just allow the default JSON serialization
        # return obj
        return None

    def childItems(self):
        return [item for item in self.items() if item.parentItem() is None]

    # Return dict object suitable for serialization via JSON.dump()
    # This one is in `ModelScene(QGraphicsScene)` class
    def json_dump_obj(self) -> dict:
        return {
            "__classname__": self.__class__.__name__,
            "items": self.childItems(),
            "traces": self.traces
        }

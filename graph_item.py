import math

from PyQt5.QtCore import QVariant, pyqtSignal

import common
from common import *


class jsonSerializationMixin:
    def json_dump_obj(self) -> dict:
        json = {
            "__classname__": self.__class__.__name__,
            "id": hex(id(self))
        }
        if isinstance(self, QtWidgets.QGraphicsItem):
            json.update({
                "x": self.x(),
                "y": self.y(),
                # "width": self.boundingRect().width(),
                # "height": self.boundingRect().height()
            })

        if hasattr(self, "childItems"):
            json.update({
                "items": self.childItems()
            })
        return json


class Channel(jsonSerializationMixin):
    """Канал связи, хранит информацию о времени готовности и свойствах канала"""

    def __str__(self):
        return (
            f'{self.numberZT}; '
            f'{self.direction}; '
            f'{self.number}; '
            f'{self.SHT}; '
            f'{self.traceDescription}; '
            f'{[grade.toString() for grade in self.grades]}; '
            f'{self.rate.toString()}'
        )

    @staticmethod
    def fromJSON(json, parent=None):
        item = Channel(parent)
        # TODO на сериализацию полей при большом количестве параметров и типов необходимо прикрутить что-то автоматическое
        item.number = json["number"]
        item.direction = json["direction"]
        item.traceDescription = json["traceDescription"]
        item.numberZT = json["numberZT"]
        item.velocity = json["velocity"]
        item.SHT = json["SHT"]
        item.rate = QtCore.QTime.fromMSecsSinceStartOfDay(json["rate"])
        grades = json["grades"]
        for i in range(len(grades)):
            item.grades[i] = QtCore.QTime.fromMSecsSinceStartOfDay(grades[i])
        for channelJson in json["channels"]:
            channel = Channel.fromJSON(channelJson, item)
            item.channels.append(channel)
        item.isConfigured = True
        return item

    def __init__(self, parent=None):
        self.parentItem = parent
        self.channels = []

        self.warningLevel = WarningLevel.Default

        self.direction = ''
        self.traceDescription = ''

        # Номер ЦТ
        self.numberZT = ''
        self.number = ''
        # Скорость в комбо-боксе на таблице (индексом по порядку списка)
        self.velocity = -1
        # таблица: ШТ(ООД)
        self.SHT = ''
        #Три нормативных времени, хранятся в Qt формате для упрощения отображения в таблице
        #TODO стоит переделать на python datetime
        self.grades = [QtCore.QTime.fromMSecsSinceStartOfDay(0)]*3
        #Затраченное время
        self.rate = Application.app_datetime.time()

        self.isConfigured = False
        self.isAlarmRead = False

    #Дальше блок функций поддержки иерархии дерева каналов и модели Qt
    def child(self, row):
        if row < len(self.channels):
            return self.channels[row]
        return None

    def childCount(self):
        return len(self.channels)

    def childNumber(self):
        if self.parentItem is not None:
            return self.parentItem.channels.index(self)

        #FIXME
        return 0

    def columnCount(self):
        return Headers.columnCount()

    def data(self, column):
        if column == 0:
            return self.numberZT
        elif column == 1:
            return self.direction
        elif column == 2:
            return self.number
        elif column == 3:
            return self.SHT
        elif column == 4:
            return self.traceDescription
        elif column == 5:
            return self.velocity
        elif column == 6:
            return self.grades[0]
        elif column == 7:
            return self.grades[1]
        elif column == 8:
            return self.grades[2]
        elif column == 9:
            return self.rate
        elif column == 10:
            return self.warningLevel.color
        return QVariant()

    def insertChildren(self, position, count):
        if position < 0 or position > len(self.channels):
            return False
        for row in range(count):
            channel = Channel(self)
            # channel.direction = self.direction
            # channel.traceDescription = self.traceDescription
            self.channels.insert(position, channel)
        return True

    def removeChildren(self, position, count):
        if position < 0 or position + count > len(self.channels):
            return False
        for row in range(count):
            self.channels.pop(position)
        return True

    def parent(self):
        return self.parentItem

    def setData(self, column, value):
        if column == 0:
            self.numberZT = value
        elif column == 1:
            self.direction = value
        elif column == 2:
            self.number = value
        elif column == 3:
            self.SHT = value
        elif column == 4:
            self.traceDescription = value
        elif column == 5:
            if isinstance(value, str):
                try:
                    self.velocity = list(common.velocityCaption).index(value)
                except:
                     self.velocity = 0
            else:
            # if idx < 0 or idx >= len(common.velocityCaption):
            #     self.velocity = 0
                self.velocity = value
        elif column == 6:
            self.grades[0] = fromVariantTime(value)
            self.isConfigured = True
        elif column == 7:
            self.grades[1] = fromVariantTime(value)
            self.isConfigured = True
        elif column == 8:
            self.grades[2] = fromVariantTime(value)
            self.isConfigured = True
        elif column == 9:
            self.rate = fromVariantTime(value)
        return True

    def updateWarning(self, time):
        # Актуализация уровня оценки времени, self.rate+self.grades сравнивается с time
        oldLevel = self.warningLevel

        if not self.isConfigured:
            self.warningLevel = WarningLevel.Default
        elif time <= self.rate.addMSecs(self.grades[0].msecsSinceStartOfDay()):
            self.warningLevel = WarningLevel.Passed
        elif time <= self.rate.addMSecs(self.grades[1].msecsSinceStartOfDay()):
            self.warningLevel = WarningLevel.Warning
        elif time <= self.rate.addMSecs(self.grades[2].msecsSinceStartOfDay()):
            self.warningLevel = WarningLevel.Error
        else:
            self.warningLevel = WarningLevel.Fatal

        if self.warningLevel.value != oldLevel.value:
            return True
        return False

    def json_dump_obj(self) -> dict:
        json = super().json_dump_obj()
        json.update({
            "number": self.number,
            "direction": self.direction,
            "traceDescription": self.traceDescription,
            "numberZT": self.numberZT,
            "velocity": self.velocity,
            "SHT": self.SHT,
            "grades": [grade.msecsSinceStartOfDay() for grade in self.grades],
            "rate": self.rate.msecsSinceStartOfDay(),
            "channels": self.channels
        })
        return json


class Trace(jsonSerializationMixin):
    """Трасса связи, хранит информацию о связанных узлах и свойствах трассы"""

    @staticmethod
    def fromJSON(json, graphItems):
        item = Trace()

        for link in json["links"]:
            link_id = int(link["id"], base=16)
            link = graphItems.get(link_id, None)
            link.startItem().addTrace(item)
            link.endItem().addTrace(item)
            item.links.append(link)

        item.rootChannel = Channel.fromJSON(json["rootChannel"], None)

        nodeNames = []
        for link in item.links:
            nodeNames.append(link.startItem().textItem.toPlainText())
        last_link = item.links[-1]
        nodeNames.append(last_link.endItem().textItem.toPlainText())

        # item.rootChannel.direction = f'{nodeNames[0]}-{nodeNames[-1]}'
        # item.rootChannel.traceDescription = str.join('+', nodeNames)

        return item

    def __init__(self):
        self.rootChannel = Channel()
        self.links = []

    def json_dump_obj(self) -> dict:
        json = super().json_dump_obj()
        json.update({
            "rootChannel": self.rootChannel,
            "links": self.links,
        })
        return json


class Link(QtWidgets.QGraphicsLineItem, jsonSerializationMixin):
    """Графический объект отрисовки связей между узлами"""

    @staticmethod
    def fromJSON(json, startItem, endItem):
        item = Link(startItem, endItem)
        item.setPos(json["x"], json["y"])
        return item

    def json_dump_obj(self) -> dict:
        json = super().json_dump_obj()
        json.update({
            "startItemID": hex(id(self.startItem())),
            "endItemID": hex(id(self.endItem())),
            "traceID": hex(id(self.trace))
        })

        return json

    def __init__(self, startItem, endItem, parent=None, scene=None):
        super(Link, self).__init__(parent)

        #Ссылки на объекты которые связывает
        self.trace = None
        self.myStartItem = startItem
        self.myEndItem = endItem

        self.myContextMenu = QtWidgets.QMenu()

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.myColor = QtCore.Qt.black
        self.setPen(QtGui.QPen(self.myColor, 5, QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        self.arrowHead = QtGui.QPolygonF()

    def setColor(self, color):
        self.myColor = color

    def startItem(self):
        return self.myStartItem

    def endItem(self):
        return self.myEndItem

    def contextMenuEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.myContextMenu.exec_(event.screenPos())

    def boundingRect(self):
        extra = (self.pen().width() + 20) / 2.0
        p1 = self.line().p1()
        p2 = self.line().p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        path = super(Link, self).shape()
        path.addPolygon(self.arrowHead)
        return path

    def updatePosition(self):
        line = QtCore.QLineF(self.mapFromItem(self.myStartItem, 0, 0), self.mapFromItem(self.myEndItem, 0, 0))
        self.setLine(line)

    def paint(self, painter, option, widget=None):
        """Основной отрисовщик объекта из Qt"""
        if (self.myStartItem.collidesWithItem(self.myEndItem)):
            return

        myStartItem = self.myStartItem
        myEndItem = self.myEndItem
        myPen = self.pen()
        myPen.setColor(self.myColor)
        arrowSize = 20.0
        painter.setPen(myPen)
        painter.setBrush(self.myColor)

        centerLine = QtCore.QLineF(myStartItem.pos(), myEndItem.pos())
        endPolygon = myEndItem.polygon()
        p1 = endPolygon.at(0) + myEndItem.pos()

        intersectPoint = QtCore.QPointF()
        for i in endPolygon:
            p2 = i + myEndItem.pos()
            polyLine = QtCore.QLineF(p1, p2)
            intersectType = polyLine.intersect(centerLine, intersectPoint)
            if intersectType == QtCore.QLineF.BoundedIntersection:
                break
            p1 = p2

        self.setLine(QtCore.QLineF(intersectPoint, myStartItem.pos()))
        line = self.line()

        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = (math.pi * 2.0) - angle

        self.arrowHead.clear()

        painter.drawLine(line)
        painter.drawPolygon(self.arrowHead)
        if self.isSelected():
            painter.setPen(QtGui.QPen(QtCore.Qt.blue, 1, QtCore.Qt.DashLine))
            myLine = QtCore.QLineF(line)
            myLine.translate(0, 4.0)
            painter.drawLine(myLine)
            myLine.translate(0,-8.0)
            painter.drawLine(myLine)


class GraphTextItem(QtWidgets.QGraphicsTextItem, jsonSerializationMixin):
    """Надпись название объекта"""
    lostFocus = pyqtSignal(QtWidgets.QGraphicsTextItem)

    def __init__(self, parent=None):
        super(GraphTextItem, self).__init__(parent)
        self.parent = parent
        self.lostFocus.connect(self.editorLostFocus)

    def focusOutEvent(self, event):
        """Событие потери фокуса отлавливается"""
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        document = self.document()
        cursor = QtGui.QTextCursor(document)
        cursor.clearSelection()
        #... и проводится оповещение кто ловит
        self.lostFocus.emit(self)
        super(GraphTextItem, self).focusOutEvent(event)

    def editorLostFocus(self, item):
        # Обработка события окончания редактирования, для коррекции надписи
        rect = self.boundingRect()
        rect.moveCenter(self.parent.boundingRect().center())
        self.setPos(rect.topLeft())

    def json_dump_obj(self) -> dict:
        json = super().json_dump_obj()
        return json


class GraphItem(QtWidgets.QGraphicsPolygonItem, jsonSerializationMixin):
    """Объекты схемы, сейчас круги, но наследуются от полигона"""

    #Типы объектов если понадобятся разные
    class ItemType(enum.Enum):
        Circle = 0, 'Круг'
        Square = 1, 'Квадрат'
        Triangle = 2, 'Треугольник'

        def __new__(cls, keycode, name):
            obj = object.__new__(cls)
            obj._value_ = keycode
            obj.readableName = name
            return obj

    lostFocus = QtCore.pyqtSignal(QtWidgets.QGraphicsTextItem)
    selectedChange = QtCore.pyqtSignal(QtWidgets.QGraphicsItem)

    @staticmethod
    def fromJSON(json):
        item = GraphItem(GraphItem.ItemType[json["type"]], None)
        item.setText(json["text"])
        item.setPos(json["x"], json["y"])
        return item

    def __init__(self, diagramType, contextMenu, parent=None):
        super(GraphItem, self).__init__(parent)

        self.traces = set()
        self.textItem = GraphTextItem(self)

        self.diagramType = diagramType
        self.myContextMenu = contextMenu

        self.setPen(QtGui.QPen(QtCore.Qt.red, 3))

        path = QtGui.QPainterPath()

        #Текущий тип - круг, цвет и линии заданы жестко сейчас
        if self.diagramType == GraphItem.ItemType.Circle:
            path.addEllipse(-50,-50,100,100)
            self.myPolygon = path.toFillPolygon()
        elif self.diagramType == GraphItem.ItemType.Square:
            self.myPolygon = QtGui.QPolygonF([
                    QtCore.QPointF(-50, -50), QtCore.QPointF(50, -50),
                    QtCore.QPointF(50, 50), QtCore.QPointF(-50, 50),
                    QtCore.QPointF(-50, -50)])
        elif self.diagramType == GraphItem.ItemType.Triangle:
            self.myPolygon = QtGui.QPolygonF([
                    QtCore.QPointF(0, -50), QtCore.QPointF(50, 50),
                    QtCore.QPointF(-50, 50), QtCore.QPointF(0, -50)])
        else:
            self.myPolygon = QtGui.QPolygonF([
                    QtCore.QPointF(-120, -80), QtCore.QPointF(-70, 80),
                    QtCore.QPointF(120, 80), QtCore.QPointF(70, -80),
                    QtCore.QPointF(-120, -80)])

        self.setPolygon(self.myPolygon)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)

    def setText(self, text):
        self.textItem.setHtml(f'<center>{text}</center>')
        # self.textItem.setTextWidth(self.boundingRect().width())
        rect = self.textItem.boundingRect()
        rect.moveCenter(self.boundingRect().center())
        self.textItem.setPos(rect.topLeft())

    def mouseDoubleClickEvent(self, event):
        #Редактирование надписи по даблклику
        if self.textItem.textInteractionFlags() == QtCore.Qt.NoTextInteraction:
            self.textItem.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        document = self.textItem.document()
        cursor = QtGui.QTextCursor(document)
        cursor.select(3)
        self.textItem.setFocus()
        super(QtWidgets.QGraphicsPolygonItem, self).mouseDoubleClickEvent(event)

    def addTrace(self, trace):
        self.traces.add(trace)

    def image(self):
        pixmap = QtGui.QPixmap(250, 250)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 8))
        painter.translate(125, 125)
        painter.drawPolyline(self.myPolygon)
        return pixmap

    def contextMenuEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.myContextMenu.exec_(event.screenPos())

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            for arrow in self.traces:
                arrow.updatePosition()

        return value

    def json_dump_obj(self) -> dict:
        json = super().json_dump_obj()

        json.update({
            "type": self.diagramType.name,
            "text": self.textItem.toPlainText(),
            # убрал по причине дублирования в JSON
            # "traces": self.traces
        })

        return json

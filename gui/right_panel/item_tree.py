'''
Created on Jun 1, 2022

@author: Vlad
'''

import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from gui.dialogs import op_dialog

class ItemTree(QtWidgets.QTreeView):
    
    def __init__(self, displayModel):
        super(ItemTree, self).__init__()
        
        self.displayModel = displayModel
        self.columnFuncs = []
        self.items = {}
        self.hoverId = None
        self.selectedIds = set()
        self.adding = None
        
        model = QtGui.QStandardItemModel()
        self.setModel(model)       
        model.setRowCount(0)
            
        self.setSortingEnabled(True)
        #self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.header().setMinimumSectionSize(0)
        self.header().setStretchLastSection(False)
        #self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)        
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        #self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.setMouseTracking(True)
        
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rcMenu)
        
    def setColumns(self, columnFuncs):
        self.columnFuncs = columnFuncs
        headers = [pair[0] for pair in columnFuncs]
        self.model().setHorizontalHeaderLabels(headers)
        for i in range(len(headers)):
            item = self.model().horizontalHeaderItem(i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)            
            if headers[i].lower() == "status":
                self.setItemDelegateForColumn(i, StatusDelegate(self))
        
    def updateItems(self, itemIds):
        self.items = {}
        self.model().removeRows(0, self.model().rowCount())
        #self.model().clear()
        
        childs = {}
        parents = {}
        for mid in itemIds:
            if self.displayModel.items[mid].itemType not in ("cluster", "clustering", "root", "matrix", "busco", "maf", "local alignments"):
                continue
            
            parent = self.displayModel.items[mid].parent
            
            while True:
                if mid in parents:
                    break
                elif parent is None:
                    childs[parent] = childs.get(parent, [])
                    childs[parent].append(mid)
                    parents[mid] = parent
                    break
                elif self.displayModel.items[parent].itemType in ("cluster", "clustering", "root", "matrix", "busco", "maf", "local alignments"):
                    childs[parent] = childs.get(parent, [])
                    childs[parent].append(mid)
                    parents[mid] = parent
                    mid = parent
                    parent = self.displayModel.items[mid].parent
                else:
                    parent = self.displayModel.items[parent].parent
        
        #stack = [self.displayModel.itemInfos[mid]]
        root = self.model().invisibleRootItem()
        #root.clusterId = None
        stack = [(mid, root) for mid in childs.get(None, [])]
        while len(stack) > 0:
            mid, parent = stack.pop()
            newItems = [StandardItem(str(pair[1](mid))) for pair in self.columnFuncs]
            
            for i, item in enumerate(newItems):
                item.id = mid   
                if self.columnFuncs[i][0].lower() != "id":         
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                if self.columnFuncs[i][0].lower() == "status":
                    status = self.displayModel.operationStatus.get(mid, {})
                    item.setData(status.get("status"), QtCore.Qt.ItemDataRole.UserRole + 1000)
                    item.setData(status.get("progress"), QtCore.Qt.ItemDataRole.UserRole + 1001)
            
            parent.appendRow(newItems)
            child = newItems[0] #parent.child(parent.rowCount() - 1)
            self.items[mid] = newItems
            for c in childs.get(mid, []):
                stack.append((c, child))
        #self.layoutChanged.emit()
        #self.dataChanged.emit(self.index(0,0), self.index(0,0))
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    
    def hoverOverItem(self, mid):
        prevId, self.hoverId = self.hoverId, mid
        prevRow, newRow = self.items.get(prevId), self.items.get(self.hoverId)
        if prevRow == newRow:
            return        
        if prevRow is not None:
            for item in prevRow:
                if prevId in self.selectedIds:
                    item.setData(QtGui.QColor(255*0, 255*0.6, 255*0.3), QtCore.Qt.ItemDataRole.BackgroundRole)
                else:
                    item.setData(None, QtCore.Qt.ItemDataRole.BackgroundRole)
        if newRow is not None:
            for item in newRow:
                item.setData(QtGui.QColor(255*0.5, 255*0.9, 255*0.7), QtCore.Qt.ItemDataRole.BackgroundRole)
            
    def updateSelectedItems(self, itemIds):        
        for mid in list(self.selectedIds):
            if mid not in itemIds:
                self.selectedIds.remove(mid)
                if mid in self.items:
                    for item in self.items[mid]:
                        item.setData(None, QtCore.Qt.ItemDataRole.BackgroundRole)

        for mid in itemIds:
            if mid in self.items: 
                if mid not in self.selectedIds:
                    self.selectedIds.add(mid)
                    for item in self.items[mid]:
                        item.setData(QtGui.QColor(255*0, 255*0.6, 255*0.3), QtCore.Qt.ItemDataRole.BackgroundRole)
                        
    def rcMenu(self, point):
        item = self.model().itemFromIndex(self.indexAt(point))       
        if item is None:
            return
        
        itemInfo = self.displayModel.itemInfos[item.id]
        menu = QtWidgets.QMenu()
        
        sa1 = menu.addAction("Select")
        sa2 = menu.addAction("Select all children")
        sa3 = menu.addAction("Select all descendants")
        menu.addSeparator()
        
        #if itemInfo.itemType in ("root", "cluster", "matrix"):
        
        ca1 = menu.addAction("Build matrix..")    
        ca1.triggered.connect(lambda : op_dialog.OperationDialog(self.displayModel, "matrix", self.parent().parent(), item.id))
        ca2 = menu.addAction("Build clustering..")
        ca2.triggered.connect(lambda : op_dialog.OperationDialog(self.displayModel, "clustering", self.parent().parent(), item.id))
        ca3 = menu.addAction("Build local alignments..")
        ca3.triggered.connect(lambda : op_dialog.OperationDialog(self.displayModel, "align", self.parent().parent(), item.id))
        ca4 = menu.addAction("Build MAF file..")
        ca4.triggered.connect(lambda : op_dialog.OperationDialog(self.displayModel, "maf", self.parent().parent(), item.id))
        
        #action.triggered.connect(lambda : self.check(itemInfo))

        menu.exec(self.mapToGlobal(point))      
    
    def mouseMoveEvent(self, event):
        item = self.model().itemFromIndex(self.indexAt(event.pos())) 
        if item is not None:
            if event.buttons() == Qt.MouseButton.LeftButton:
                if self.adding:
                    self.displayModel.selectItems([item.id], [])
                    self.displayModel.hoverOverItem(None)
                else:
                    self.displayModel.selectItems([], [item.id])
                    self.displayModel.hoverOverItem(None)
            else:
                self.displayModel.hoverOverItem(item.id)
        else:
            self.displayModel.hoverOverItem(None)
        #return QtWidgets.QTreeView.mouseMoveEvent(self, event)
    
    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            idx = self.indexAt(event.pos())
            item = self.model().itemFromIndex(idx) 
            #if idx.isValid():
            
            if item is not None: # and not self.items[item.id][0].hasChildren():           
                vrect = self.visualRect(idx)
                itemIdentation = vrect.x() - self.visualRect(self.rootIndex()).x()
                if event.pos().x() >= itemIdentation:
                    if item.id not in self.displayModel.selectedItems:
                        self.displayModel.selectItems([item.id], [])
                        self.adding = True
                    else:
                        self.displayModel.selectItems([], [item.id])
                        self.adding = False
                    self.displayModel.hoverOverItem(None)
        return QtWidgets.QTreeView.mousePressEvent(self, event)
    
    def mouseDoubleClickEvent(self, event):
        item = self.model().itemFromIndex(self.indexAt(event.pos())) 
        if item is not None:
            ids = []
            itemInfo = self.displayModel.items[item.id]
            if itemInfo.itemType == "cluster":
                ids.append(item.id)
            else:
                for p, pinfo in self.displayModel.items.items():
                    if pinfo.parent == item.id and pinfo.itemType == "cluster":
                        ids.append(p)
            pinned = [i for i in ids if i in self.displayModel.selectedItems]  
            unpinned = [i for i in ids if i not in self.displayModel.selectedItems]  
               
            if len(unpinned) > 0:
                self.displayModel.selectItems(unpinned, [])
                self.displayModel.hoverOverItem(None)
            elif len(pinned) > 0:
                self.displayModel.selectItems([], pinned)
                self.displayModel.hoverOverItem(None)
        return QtWidgets.QTreeView.mouseDoubleClickEvent(self, event)
        
    def mouseReleaseEvent(self, event):
        self.adding = None
        #return QtWidgets.QTreeView.mouseReleaseEvent(self, event)
    
    def leaveEvent(self, event):
        self.displayModel.hoverOverItem(None)
        #return QtWidgets.QTreeView.leaveEvent(self, event)  


class OperationTree(QtWidgets.QTreeView):
    
    def __init__(self, displayModel):
        super(OperationTree, self).__init__()
        
        self.displayModel = displayModel
        self.columnFuncs = []
        self.items = {}
        
        model = QtGui.QStandardItemModel()
        self.setModel(model)       
        model.setRowCount(0)
            
        self.setSortingEnabled(True)
        #self.setItemsExpandable(False)
        #self.setExpandsOnDoubleClick(True)
        #self.setAlternatingRowColors(True)
        #self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.SelectedClicked)
        
        self.header().setMinimumSectionSize(0)
        self.header().setStretchLastSection(False)  
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.setMouseTracking(True)
        
        #self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        #self.customContextMenuRequested.connect(self.rcMenu)
        
    def setColumns(self, columnFuncs):
        self.columnFuncs = columnFuncs
        headers = [pair[0] for pair in columnFuncs]
        self.model().setHorizontalHeaderLabels(headers)
        for i in range(len(headers)):
            item = self.model().horizontalHeaderItem(i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if headers[i].lower() == "status":
                self.setItemDelegateForColumn(i, StatusDelegate(self))
    
    def updateItemStatus(self, mid):
        row = self.items.get(mid)
        if row is None:
            root = self.model().invisibleRootItem()
            row = [StandardItem(str(pair[1](mid))) for pair in self.columnFuncs]                
            for i, item in enumerate(row):
                item.id = mid   
                if self.columnFuncs[i][0].lower() != "id":         
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if self.columnFuncs[i][0].lower() == "status":
                    op = self.displayModel.operations[mid]
                    item.setData(op.opStatus, QtCore.Qt.ItemDataRole.UserRole + 1000)
                    item.setData(op.opProgress, QtCore.Qt.ItemDataRole.UserRole + 1001)
            root.appendRow(row)
            self.items[mid] = row
            
        for i, item in enumerate(row):
            #print(self.columnFuncs[i][0].lower())
            if self.columnFuncs[i][0].lower() == "status":
                #print("UPDATING..", status)
                #pair = (status.get("status"), status.get("progress"))
                op = self.displayModel.operations[mid]
                item.setData(op.opStatus, QtCore.Qt.ItemDataRole.UserRole + 1000)
                item.setData(op.opProgress, QtCore.Qt.ItemDataRole.UserRole + 1001)
     

class StatusDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        #data = index.data(QtCore.Qt.ItemDataRole.UserRole+1000)
        status = index.data(QtCore.Qt.ItemDataRole.UserRole + 1000)
        progress = index.data(QtCore.Qt.ItemDataRole.UserRole + 1001)
        #print("THE DATA IS", status, progress)
        status = status if status is not None else "No Status"
        progress = progress if progress is not None else 0
        #print(status)
        #print(progress)
        #status, progress = index.data(QtCore.Qt.UserRole)
        opt = QtWidgets.QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = progress
        #opt.text = "{}%".format(progress)
        opt.text = "{}".format(status)
        opt.textVisible = True
        opt.textAlignment = Qt.AlignmentFlag.AlignCenter
        opt.state |= QtWidgets.QStyle.StateFlag.State_Horizontal
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.ControlElement.CE_ProgressBar, opt, painter)
    
class StandardItem(QtGui.QStandardItem):
    '''
    def __init__(self, txt='', font_size=12, set_bold=False, color=QtGui.QColor(0, 0, 0)):
        super().__init__()

        fnt = QtGui.QFont('Open Sans', font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)
    '''
    
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except:
            return self.text() < other.text()
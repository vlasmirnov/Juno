'''
Created on Sep 6, 2022

@author: Vlad
'''

import math
from PyQt6 import QtCore, QtWidgets, QtGui
from gui.view import drawer
from helpers import matrixutils


class ViewerScene(QtWidgets.QGraphicsScene):
    
    def __init__(self, model):
        #screen = QtWidgets.QApplication.primaryScreen()
        rect = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        print('Available: %d x %d' % (rect.width(), rect.height()))

        self.drawer = drawer.Drawer(self)
        self.maxX = rect.width() 
        self.maxY = rect.height() 
        self.model = model
        self.itemObjects = {}
        self.maxLength = None
        
        self.selectedSeqs = set()
        self.seqGrid = {}
        self.seqGridPos = {}
        
        self.pressed = False
        self.rubbering = False
        self.dragging = False
        self.clickX = 0
        self.clickY = 0
        self.controlPressed = False
        self.rubberBand = None
        
        self.hoverId = None
        self.selectedIds = set()
        
        
        self.intervalClusterMap = {}
        self.interval = 16384
        #self.cols = 4
        
        super().__init__(0, 0, self.maxX, self.maxY)
        self.initScene()
        
        
        model.signals.contextChangedSignal.connect(self.contextChanged)
        model.signals.hoverOverItemSignal.connect(self.hoverOverItem)
        model.signals.selectedItemsChangedSignal.connect(self.selectedItemsChanged)
        model.signals.selectedSeqsChangedSignal.connect(self.selectedSeqsChanged)
        model.signals.searchItemsChangedSignal.connect(self.searchItemsChanged)
        
        
    def initScene(self):
        self.itemObjects = {}
        self.clear()
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(0,0,0)))
        self.drawer.drawRubberBand()
    
    def seqMap(self):
        return self.model.context.sequenceInfo.seqMap
    
    def sceneToSeqPos(self, sx, sy):
        if len(self.seqGrid) == 0 or sx is None or sy is None:
            return None, None
        colWidth = self.maxX / len(self.seqGrid)
        sPerCol = max(max(col)+1 for col in self.seqGrid.values())
        rowWidth = self.maxY / (sPerCol + 1)
        
        sRow, sRowRem, sCol, sColRem = int(sy / rowWidth), int(sy % rowWidth), int(sx / colWidth), int(sx % colWidth)
        r, c = None, sCol
        if sRowRem <= 10:
            r = sRow - 1
        elif sRowRem >= rowWidth - 10:
            r = sRow
        
        s, p = None, None
        if r is not None and c is not None and c in self.seqGrid and r in self.seqGrid[c]:
            s = self.seqGrid[c][r]
            p = (sColRem / colWidth - 0.02) * self.maxLength / 0.96
            if p < - len(self.seqMap()[s]) * 0.00 or p > len(self.seqMap()[s]) * 1.00:
                s, p = None, None
            else:
                p = min(max(0, p), len(self.seqMap()[s]))
            
        return s, p
    
    def sceneToRowColInsert(self, sx, sy):
        if len(self.seqGrid) == 0 or sx is None or sy is None:
            return None, None
        colWidth = self.maxX / len(self.seqGrid)
        sPerCol = max(max(col)+1 for col in self.seqGrid.values())
        rowWidth = self.maxY / (sPerCol + 1)
        
        sRow, sRowRem, sCol, sColRem = int(sy / rowWidth), int(sy % rowWidth), int(sx / colWidth), int(sx % colWidth)
        r, c = None, None
        
        if sColRem < colWidth * 0.2:
            c = sCol - 0.5
        elif sColRem > colWidth * 0.8:
            c = sCol + 0.5
        else:
            c = sCol
            
        #if (sRowRem > rowWidth * 0.25 or sRow == 0) and (sRowRem < rowWidth * 0.75 or sRow == sPerCol):
        #    r = sRow - 0.5
        #else:
        #    r = sRow
        r = sRow - 0.5
            
        return r, c
    
    def seqToScenePos(self, s, x):
        c, r = self.seqGridPos[s]
        colWidth = self.maxX / len(self.seqGrid)
        sPerCol = max(max(col)+1 for col in self.seqGrid.values())
        sx = colWidth * (0.02 + 0.96 * x/self.maxLength) + colWidth * c
        sy = self.maxY * (r + 1)/(sPerCol + 1)
        return sx, sy
    
    def getIntervalDisplayClusters(self, s, i):
        return {m : self.model.clusters[m] for m in self.intervalClusterMap.get((s, i), [])}
    
    def getSequenceDisplayClusters(self, s):
        return {m : self.model.clusters[m] for i in range(len(self.seqMap()[s]) // self.interval) for m in self.intervalClusterMap.get((s, i), [])}
    
    def removeItemObjects(self, itemIds):
        for mid in itemIds:
            if mid in self.itemObjects:
                #print("here", mid)
                for item in self.itemObjects[mid]:
                    self.removeItem(item)
                self.itemObjects.pop(mid)
                #print("and here", mid)
        self.update()
    
    def press(self, x, y):
        self.pressed = True
        self.clickX, self.clickY = x, y
        s, p = self.sceneToSeqPos(x, y)
        if s is not None:
            if s not in self.model.selectedSequences:
                if self.controlPressed:
                    self.model.selectSeqs([s], [])
                else:
                    self.model.setSelectedSeqs([s])
            else:
                if self.controlPressed:
                    self.model.selectSeqs([], [s])
        else:
            self.model.setSelectedSeqs(set())
            self.rubberBand.setRect(x, y, 0, 0)
            self.rubberBand.show()
            self.rubbering = True
    
    def release(self, x, y):
        if self.dragging:    
            if len(self.model.selectedSequences) > 0:
                r, c = self.sceneToRowColInsert(x, y)
                self.repositionSequences(self.model.selectedSequences, r, c)
                self.initScene()
                self.drawer.drawSequences([seq.num for seq in self.model.sequences])
                self.mapIntervalsClusters(self.interval, self.model.clusters)
        else:
            if not self.rubbering:
                s, p = self.sceneToSeqPos(x, y)
                if s is not None and s in self.model.selectedSequences and not self.controlPressed:
                    self.model.setSelectedSeqs([s])
        
        self.removeItemObjects(["dragging ghosts"])
        self.removeItemObjects(["dragging slot"])        
        self.pressed = False
        self.dragging = False
        self.rubbering = False
        self.rubberBand.setVisible(False)
        self.update()
    
    def hoverOverPos(self, x, y):
        s, p = self.sceneToSeqPos(x, y)
        if s is None:
            self.model.hoverOverItem(None)
        elif s not in self.selectedSeqs:
            i = p // self.interval
            displayClusters = self.getIntervalDisplayClusters(s, i)
            if len(displayClusters) > 0:
                self.model.setSelectedItems(displayClusters)
                #self.model.hoverOverItem(next(iter(displayClusters.keys())))
                #for k in displayClusters:
                #    self.model.hoverOverItem(k)
            else:
                self.model.hoverOverItem(None)
        else:
            displayClusters = self.getSequenceDisplayClusters(s)
            if len(displayClusters) > 0:
                self.model.setSelectedItems(displayClusters)
            else:
                self.model.hoverOverItem(None)
        
        if self.rubbering:
            #self.rubberBand.setGeometry(QtCore.QRect(self.clickX, self.clickY, x - self.clickX, y - self.clickY)) #.normalized())
            self.rubberBand.setRect(self.clickX, self.clickY, x - self.clickX, y - self.clickY)
            
            r1, c1 = self.sceneToRowColInsert(self.clickX, self.clickY)
            r2, c2 = self.sceneToRowColInsert(x, y)
            if not None in (r1, r2, c1, c2):
                r1, r2 = sorted((r1, r2))
                c1, c2 = sorted((c1, c2))
                grabbedSeqs = []
                for c in range(math.ceil(c1), int(c2) + 1):
                    for r in range(math.ceil(r1), int(r2) + 1):
                        if c in self.seqGrid and r in self.seqGrid[c]:
                            grabbedSeqs.append(self.seqGrid[c][r])
                self.model.setSelectedSeqs(grabbedSeqs)    
            self.update()
            
        elif self.pressed:
            self.dragging = True
            if len(self.model.selectedSequences) > 0:
                if "dragging ghosts" not in self.itemObjects:
                    self.drawer.drawDraggingGhosts(self.model.selectedSequences)
                for item in self.itemObjects["dragging ghosts"]:
                    item.setPos(item.orx + x, item.ory + y)                
                self.drawer.drawDraggingSlot(x, y)                
                self.update()
        
    def repositionSequences(self, seqs, ir, ic):
        for n, s in enumerate(seqs):
            c, r = self.seqGridPos[s]
            self.seqGrid[c].pop(r)            
            if len(self.seqGrid[c]) == 0:
                self.seqGrid.pop(c)
            
            self.seqGrid[ic] = self.seqGrid.get(ic, {})
            self.seqGrid[ic][ir + 0.5*(n+1)/(len(seqs)+1)] = s
            #self.seqGridPos[s] = (ic, ir + 0.5*n/len(seqs))
        
        cols = sorted(self.seqGrid)
        self.seqGrid = {n : self.seqGrid[col] for n, col in enumerate(cols)}
        for n in self.seqGrid:
            rows = sorted(self.seqGrid[n])
            self.seqGrid[n] = {m : self.seqGrid[n][row] for m, row in enumerate(rows)}
            for m in self.seqGrid[n]:
                self.seqGridPos[self.seqGrid[n][m]] = (n, m)
            
    
    def hoverOverItem(self, mid):
        prevId, self.hoverId = self.hoverId, mid
        if prevId == self.hoverId:
            return
        self.removeItemObjects([prevId])
        #if prevId in self.itemObjects:
        #    for item in self.itemObjects[prevId]:
        #        item.setVisible(False)
        
        if self.hoverId is None:
            return
        
        if self.hoverId in self.itemObjects:
            for item in self.itemObjects[self.hoverId]:
                item.setVisible(True)
            return 
        
        #itemInfo = self.model.itemInfos[self.hoverId]                    
        if self.hoverId in self.model.clusters:
            hoverColor = (0.5, 0.9, 0.7)    
            icolor = (0.9, 0.5, 0.7)
            if self.hoverId is not None:
                self.drawer.drawClusters({self.hoverId : self.model.clusters[self.hoverId]}, hoverColor, icolor)
        
    def contextChanged(self, context):
        self.initScene()
        posSeqs = [seq for seq in self.model.sequences]
        numCols = max(1, int((len(posSeqs) ** 0.5) * 0.5))
        sPerCol = math.ceil(len(posSeqs) / numCols)
        self.seqGrid = {n : {} for n in range(numCols)}
        for s, seq in enumerate(posSeqs):
            r = s % sPerCol
            c = s // sPerCol
            self.seqGrid[c][r] = seq.num
            self.seqGridPos[seq.num] = (c, r)
        
        self.drawer.drawSequences([seq.num for seq in self.model.sequences])
        self.mapIntervalsClusters(self.interval, self.model.clusters)
        #self.addSequenceIntervals(context.sequences, 4**9) 
    
    def searchItemsChanged(self, itemIds):
        self.mapIntervalsClusters(self.interval, self.model.clusters)
        
    def selectedItemsChanged(self, itemIds):
        color = (0, 0.6, 0.3)
        icolor = (0.6, 0, 0.3)
        unselect = [mid for mid in self.selectedIds if mid not in itemIds]
        select = [mid for mid in itemIds if mid not in self.selectedIds]
        self.selectedIds = set(itemIds)
        self.removeItemObjects(set((m, "selected") for m in unselect))
        clusters = {(m, "selected") : self.model.clusters[m] for m in select if self.model.items[m].itemType != "root" and m in self.model.clusters}
        self.drawer.drawClusters(clusters, color, icolor)
        
        for m in select:
            if self.model.items[m].itemType == "matrix":
                hoverColor = (0.9, 0.4, 0.5)
                self.drawer.drawMatrix(self.model.items[m], hoverColor)
    
    def selectedSeqsChanged(self, seqNums):
        unselect = [mid for mid in self.selectedSeqs if mid not in seqNums]
        select = [mid for mid in seqNums if mid not in self.selectedSeqs]
        self.selectedSeqs = set(seqNums)
        if len(select) == 0 and len(unselect) == 0:
            return
        
        sPerCol = max(max(col)+1 for col in self.seqGrid.values())
        rowWidth = self.maxY / (sPerCol + 1)
        lineWidth = 2
        textSize = int(min(18, 0.25*rowWidth))
        scolor = QtGui.QColor(255*0.25, 255*0.75, 255*1)
        pen = QtGui.QPen(scolor)
        pen.setWidth(lineWidth)
        font = QtGui.QFont()
        font.setPixelSize(textSize)
        for s in unselect:
            for line in self.itemObjects[s, "sequence line"]:
                line.setPen(pen)
            for text in self.itemObjects[s, "sequence text"]:
                text.setFont(font)
                text.setDefaultTextColor(scolor)
        
        scolor = QtGui.QColor(255*0.75, 255*0.9, 255*1)
        pen = QtGui.QPen(scolor)
        pen.setWidth(lineWidth * 1.5)
        font = QtGui.QFont()
        font.setPixelSize(textSize * 1.0)     
        font.setBold(True)  
        for s in select:
            for line in self.itemObjects[s, "sequence line"]:
                line.setPen(pen)
            for text in self.itemObjects[s, "sequence text"]:
                text.setFont(font)
                text.setDefaultTextColor(scolor)
        
        #for s in select:
        #    displayClusters = self.getSequenceDisplayClusters(s)
        #    if len(displayClusters) > 0:
        #        self.model.setSelectedItems(displayClusters)
    
    def mapIntervalsClusters(self, interval, clusters):
        self.intervalClusterMap = {}
        pairs = list(clusters.items())
        pairs.sort(key=lambda p : (min(v[1]-v[0]+1 for v in p[1]), sum(v[1]-v[0]+1 for v in p[1])), reverse=True)
        for m, cluster in pairs:
            if self.model.items[m].itemType == "root":
                continue
            for i1, i2, s, strand in cluster:
                for i in range(i1 // interval, 1 + i2 // interval):
                    self.intervalClusterMap[s, i] = self.intervalClusterMap.get((s, i), [])
                    self.intervalClusterMap[s, i].append(m)
        
        #for k, clusterNums in self.intervalClusterMap.items():
        #    clusterNums = [m for m in clusterNums if len(clusters[m]) < 100][:1]
        #    self.intervalClusterMap[k] = clusterNums
    
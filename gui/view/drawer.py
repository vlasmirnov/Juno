'''
Created on Sep 6, 2022

@author: Vlad
'''

import math
from PyQt6 import QtCore, QtWidgets, QtGui
from helpers import matrixutils


class Drawer():
    
    def __init__(self, scene):
        self.scene = scene

    def drawRubberBand(self):
        self.scene.rubberBand = QtWidgets.QGraphicsRectItem(0, 0, 0, 0)
        rubberBandColor = QtGui.QColor(255*0*1.5, 255*0.5*1.5, 255*0.6*1.5)
        self.scene.rubberBand.setBrush(QtGui.QBrush(rubberBandColor))
        self.scene.rubberBand.setOpacity(0.2)
        self.scene.rubberBand.setZValue(0)
        self.scene.rubberBand.setVisible(False)
        self.scene.addItem(self.scene.rubberBand)
    
    def drawSequences(self, sequences):        
        if len(sequences) == 0:
            return
        
        self.scene.maxLength = max(len(self.scene.seqMap()[s]) for s in sequences)
        sPerCol = max(max(col)+1 for col in self.scene.seqGrid.values())
        rowWidth = self.scene.maxY / (sPerCol + 1)
        
        for s in sequences:
            seq = self.scene.seqMap()[s]
            selected = s in self.scene.model.selectedSequences
            scolor = QtGui.QColor(255*0.75, 255*0.9, 255*1) if selected else QtGui.QColor(255*0.25, 255*0.75, 255*1)
            barWidth = min(5, 0.1 * rowWidth) #* factor
            textSize = int(min(18, 0.25*rowWidth)) #* factor
            textBold = s in self.scene.model.selectedSequences
            lineWidth = 3 if selected else 2
            
            newItems = []
            sx1, sy1 = self.scene.seqToScenePos(s, 0)
            sx2, sy2 = self.scene.seqToScenePos(s, len(seq))    
            
            pen = QtGui.QPen(scolor)
            pen.setWidth(lineWidth)
            line = QtWidgets.QGraphicsLineItem(sx1, sy1, sx2, sy2)
            line.setPen(pen)
            newItems.append(line)  
            
            line = QtWidgets.QGraphicsLineItem(sx1, sy1 - barWidth, sx1, sy1 + barWidth)
            line.setPen(pen)
            newItems.append(line)
            
            line = QtWidgets.QGraphicsLineItem(sx2, sy2 - barWidth, sx2, sy2 + barWidth)
            line.setPen(pen)
            newItems.append(line)
            
            text = QtWidgets.QGraphicsTextItem()
            text.setDefaultTextColor(scolor)
            text.setPos(sx1, sy1 + 0.15 * barWidth)
            font = QtGui.QFont()
            font.setPixelSize(textSize)
            font.setBold(textBold)
            text.setFont(font)
            text.setPlainText(seq.name)
            text.setZValue(-1)
            #self.addItem(text)
            self.scene.itemObjects[seq.num, "sequence line"] = newItems
            self.scene.itemObjects[seq.num, "sequence text"] = [text]
            for item in newItems:
                self.scene.addItem(item)
            self.scene.addItem(text)
            
    def drawClusters(self, clusters, color, icolor = None):
        newItems = []        
        icolor = icolor or color
        
        edgeColor = QtGui.QColor(255*color[0], 255*color[1], 255*color[2])
        fillColor = QtGui.QColor(255*color[0]*0.4, 255*color[1]*0.4, 255*color[2]*0.4)
        iedgeColor = QtGui.QColor(255*icolor[0], 255*icolor[1], 255*icolor[2])
        ifillColor = QtGui.QColor(255*icolor[0]*0.4, 255*icolor[1]*0.4, 255*icolor[2]*0.4)
        
        for m, cluster in clusters.items():
            if m in self.scene.itemObjects:
                continue
            clusterItems = []
            seqClusters, joinPairs = self.findClusterCorners(cluster)
            for s1, items in seqClusters.items():
                for interval in items:
                    i1, i2, s, strand = interval                        
                    sx1, sy1 = self.scene.seqToScenePos(s, i1)
                    sx2, sy2 = self.scene.seqToScenePos(s, i2+1)
                    #print(interval, strand)
                    pen = QtGui.QPen(edgeColor if strand == 1 else iedgeColor)
                    pen.setWidth(2)
                    line = QtWidgets.QGraphicsLineItem(sx1, sy1, sx2, sy2)
                    line.setPen(pen)
                    self.scene.addItem(line)
                    clusterItems.append(line)
            
            for s1, s2 in joinPairs:
                items1, items2 = seqClusters[s1], seqClusters[s2]
                c1, c2, ptr = 0, 0, 0
                while True:
                    cords1 = items1[c1]
                    cords2 = items2[c2]
                    if cords1[3] != 1:
                        cords1 = (cords1[1], cords1[0], cords1[2], cords1[3])
                    if cords2[3] != 1:
                        cords2 = (cords2[1], cords2[0], cords2[2], cords2[3])
                    sx11, sy11 = self.scene.seqToScenePos(s1, cords1[0])
                    sx12, sy12 = self.scene.seqToScenePos(s1, cords1[1]+1)
                    sx21, sy21 = self.scene.seqToScenePos(s2, cords2[0])
                    sx22, sy22 = self.scene.seqToScenePos(s2, cords2[1]+1)
                    
                    polypoints = QtGui.QPolygonF([QtCore.QPointF(sx11, sy11), 
                                  QtCore.QPointF(sx21, sy21), 
                                  QtCore.QPointF(sx22, sy22), 
                                  QtCore.QPointF(sx12, sy12)])
                    pen = QtGui.QPen(edgeColor if cords1[3] == cords2[3] else iedgeColor)
                    pen.setWidth(0.1)
                    polygon = QtWidgets.QGraphicsPolygonItem(polypoints)
                    polygon.setPen(pen)
                    polygon.setZValue(-50)
                    #polygon.setOpacity(0.5)
                    #polygon.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)
                    #self.scene.addItem(polygon)
                    #clusterItems.append(polygon)
                    
                    polygon = QtWidgets.QGraphicsPolygonItem(polypoints)
                    polygon.setBrush(QtGui.QBrush(fillColor if cords1[3] == cords2[3] else ifillColor))
                    polygon.setZValue(-100)
                    
                    #pen = QtGui.QPen(fillColor if cords1[3] == cords2[3] else ifillColor)
                    pen = QtGui.QPen(edgeColor if cords1[3] == cords2[3] else iedgeColor)
                    pen.setWidth(0.1)
                    polygon.setPen(pen)
                    #polygon.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)
                    self.scene.addItem(polygon)
                    clusterItems.append(polygon)
                    
                    if c1 == len(items1) - 1 and c2 == len(items2) - 1:
                        break
                    if len(items1) > len(items2):
                        c1 = c1 + 1 
                        c2 = round(c1 * (len(items2)-1) / (len(items1)-1))
                    else:
                        c2 = c2 + 1 
                        c1 = round(c2 * (len(items1)-1) / (len(items2)-1))
            self.scene.itemObjects[m] = clusterItems
            newItems.extend(clusterItems)
        #self.update()
        return newItems
    
    def findClusterCorners(self, cluster):
        seqClusters = {}
        for cords in cluster:
            s, seq = cords[2], self.scene.seqMap()[cords[2]]
            #if cords[3] != 1:
            seqClusters[s] = seqClusters.get(s, [])
            seqClusters[s].append(cords)
        for s in seqClusters:
            seqClusters[s].sort()
            
        joinPairs = []
        sList = sorted(list(seqClusters.keys()), key = lambda x : self.scene.seqGridPos[x])
        #sPerCol = math.ceil(len(self.sequences) / self.cols)
        joined = [False for s in sList]
        #gridSeq = {(s // sPerCol, s % sPerCol) : s for s in sList}
        for i in range(len(sList)-1):
            if self.scene.seqGridPos[sList[i]][0] == self.scene.seqGridPos[sList[i+1]][0]:
                joinPairs.append((sList[i], sList[i+1]))
                joined[i], joined[i+1] = True, True
                
        for i in range(len(sList)):
            if not joined[i]:
                for j in range(i+1, len(sList)):
                    if self.scene.seqGridPos[sList[i]][1] != self.scene.seqGridPos[sList[j]][1]:
                        joinPairs.append((sList[i], sList[j]))
                        joined[i], joined[j] = True, True
                        break
            if not joined[i]:
                for j in range(i-1, -1, -1):
                    if self.scene.seqGridPos[sList[i]][1] != self.scene.seqGridPos[sList[j]][1]:
                        joinPairs.append((sList[j], sList[i]))
                        joined[i], joined[j] = True, True
                        break
            #elif i > 0 and sList[i] // sPerCol != sList[i-1] // sPerCol and sList[i] % sPerCol != sList[i-1] % sPerCol:
            #    joinPairs.append((sList[i-1], sList[i]))
    
        return seqClusters, joinPairs
    
    def drawDraggingGhosts(self, seqNums):
        sPerCol = max(max(col)+1 for col in self.scene.seqGrid.values())
        rowWidth = self.scene.maxY / (sPerCol + 1)
        colWidth = self.scene.maxX / len(self.scene.seqGrid)
        newItems = []
        
        for s, seqNum in enumerate(seqNums):
            seq = self.scene.seqMap()[seqNum]            
            selected = seq.num in self.scene.model.selectedSequences
            scolor = QtGui.QColor(255*0.75, 255*0.9, 255*1) if selected else QtGui.QColor(255*0.25, 255*0.75, 255*1)
            barWidth = min(5, 0.1 * rowWidth) #* factor
            textSize = int(min(18, 0.25*rowWidth)) #* factor
            textBold = seq.num in self.scene.model.selectedSequences
            lineWidth = 3 if selected else 2
            
            
            #sx = colWidth * (0.02 + 0.96 * len(seq)/self.maxLength)
            #sy = self.maxY * (r + 1)/(sPerCol + 1)
            sx1, sy1 = 0, self.scene.maxY * s / (sPerCol + 1)
            sx2, sy2 = colWidth * (0.02 + 0.96 * len(seq)/self.scene.maxLength), self.scene.maxY * s / (sPerCol + 1)
            
            pen = QtGui.QPen(scolor)
            pen.setWidth(lineWidth)
            line = QtWidgets.QGraphicsLineItem(sx1, sy1, sx2, sy2)
            line.setPen(pen)
            newItems.append(line)  
            
            line = QtWidgets.QGraphicsLineItem(sx1, sy1 - barWidth, sx1, sy1 + barWidth)
            line.setPen(pen)
            newItems.append(line)
            
            line = QtWidgets.QGraphicsLineItem(sx2, sy2 - barWidth, sx2, sy2 + barWidth)
            line.setPen(pen)
            newItems.append(line)
            
            text = QtWidgets.QGraphicsTextItem()
            text.setDefaultTextColor(scolor)
            text.setPos(sx1, sy1 + 0.15 * barWidth)
            font = QtGui.QFont()
            font.setPixelSize(textSize)
            font.setBold(textBold)
            text.setFont(font)
            text.setPlainText(seq.name)
            newItems.append(text)
            #self.addItem(text)
        
        self.scene.itemObjects["dragging ghosts"] = newItems    
        #self.itemObjects[seq.num, "sequence text"] = [text]
        for item in newItems:
            item.setOpacity(0.2)
            item.setZValue(0)
            item.orx, item.ory = item.pos().x(), item.pos().y()
            self.scene.addItem(item)
            
    
    def drawDraggingSlot(self, x, y):
        self.scene.removeItemObjects(["dragging slot"])
        r, c = self.scene.sceneToRowColInsert(x, y)
        if r is None or c is None:
            return
        
        sPerCol = max(max(col)+1 for col in self.scene.seqGrid.values())
        rowWidth = self.scene.maxY / (sPerCol + 1)
        colWidth = self.scene.maxX / len(self.scene.seqGrid)
        newItems = []
        
        scolor = QtGui.QColor(255*0.6, 255*0.6, 255*0.6)
        lineWidth = 2
        
        #sx = colWidth * (0.02 + 0.96 * x/self.maxLength) + colWidth * c
        #sy = self.maxY * (r + 1)/(sPerCol + 1)
        sx1, sy1 = colWidth * (c + 0.02), self.scene.maxY * (r + 1)/(sPerCol + 1)
        sx2, sy2 = colWidth * (c + 0.5), self.scene.maxY * (r + 1)/(sPerCol + 1)
        
        pen = QtGui.QPen(scolor)
        pen.setWidth(lineWidth)
        line = QtWidgets.QGraphicsLineItem(sx1, sy1, sx2, sy2)
        line.setPen(pen)
        newItems.append(line)  
        
        self.scene.itemObjects["dragging slot"] = newItems    
        for item in newItems:
            #item.setOpacity(0.5)
            #item.orx, item.ory = item.pos().x(), item.pos().y()
            self.scene.addItem(item)
    
    def drawMatrix(self, matrixItem, color):  
        #color = (0.9, 0.4, 0.5)
        newItems = []
        print("here..")
        #sCols = self.findSeqCols([s.num for s in self.sequences])      
        for scol in self.scene.seqGrid.values():
            for i in range(len(scol)-1):
                iseq = scol[i]
                for j in range(i+1, len(scol)):
                    jseq = scol[j]
                    
                    s1, s2 = sorted((iseq, jseq))
                    s1seq = self.scene.seqMap()[s1]
                    s2seq = self.scene.seqMap()[s2]
                    matrix = matrixutils.readPairMatrixFromFile(matrixItem.path, s1, s2, 0)
                    if matrix is None or len(matrix) == 0:
                        #continue
                        break
                    
                    allValues = sorted(matrix.values())
                    maxValue = allValues[int(0.75*len(allValues))]
                    
                    for a, b in matrix.keys():
                        value = matrix[a,b] 
    
                        factor = min(value,maxValue)/maxValue            
                        #factor = 1
                        sx1, sy1 = self.scene.seqToScenePos(s1, min(len(s1seq), (a + 0.5) * matrixItem.patchSize))
                        sx2, sy2 = self.scene.seqToScenePos(s2, min(len(s2seq), (b + 0.5) * matrixItem.patchSize))
                        
                        scolor = QtGui.QColor(255*color[0]*factor, 255*color[1]*factor, 255*color[2]*factor)
                        pen = QtGui.QPen(scolor)
                        pen.setWidth(0.25)
                        line = QtWidgets.QGraphicsLineItem(sx1, sy1, sx2, sy2)
                        line.setPen(pen)
                        line.setZValue(-100)
                        self.scene.addItem(line)  
                        newItems.append(line)
                    break
        self.scene.itemObjects[matrixItem.relativePath, "selected"] = newItems
        #self.update()
        return newItems
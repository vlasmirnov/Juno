'''
Created on May 11, 2022

@author: Vlad
'''

import math
from PyQt6 import QtCore, QtWidgets, QtGui
from gui.view import scene
from gui.dialogs.cluster_searcher import ClusterSearcher

class Viewer(QtWidgets.QGraphicsView):    
    
    def __init__(self, model):
        viewerScene = scene.ViewerScene(model)    
        super(Viewer, self).__init__(viewerScene)
        self.model = model
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)
        #self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        #self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.pressed = False
        self.clickX = 0
        self.clickY = 0
        self.origSceneRect = self.scene().sceneRect()
    
    def resizeEvent(self, *args, **kwargs):
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)        
        return QtWidgets.QGraphicsView.resizeEvent(self, *args, **kwargs)
    
    def mousePressEvent(self, event):
        position = QtCore.QPoint(event.pos())
        scenePos = self.mapToScene(position)   
             
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.scene().press(scenePos.x(), scenePos.y())
            #print(scenePos.x(), scenePos.y())
        if event.buttons() == QtCore.Qt.MouseButton.RightButton: 
            self.pressed = True   
            self.clickX, self.clickY = scenePos.x(), scenePos.y()
            '''
            s, p = self.scene().sceneToSeqPos(scenePos.x(), scenePos.y())
            if s is not None and p is not None:
                searcher = ClusterSearcher(self.scene().model)
                searcher.position = int(p)
                searcher.sequences = set([self.scene().model.context.sequenceInfo.seqMap[s].name])
                self.scene().model.clusterSearch(searcher)
            '''
        return QtWidgets.QGraphicsView.mousePressEvent(self, event)
    
    def mouseReleaseEvent(self, event):
        #if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
        position = QtCore.QPoint(event.pos())
        scenePos = self.mapToScene(position)
        self.pressed = False        
        self.scene().release(scenePos.x(), scenePos.y())
        return QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
    
    def mouseMoveEvent(self, event):
        position = QtCore.QPoint(event.pos())
        scenePos = self.mapToScene(position)
        if self.pressed:            
            sr = self.scene().sceneRect()
            sr2 = QtCore.QRectF(sr.x() - scenePos.x() + self.clickX,
                                sr.y() - scenePos.y() + self.clickY,
                                sr.width(), sr.height())
            
            self.scene().setSceneRect(sr2)
            scenePos = self.mapToScene(position)
            self.clickX, self.clickY = scenePos.x(), scenePos.y()
        self.scene().hoverOverPos(scenePos.x(), scenePos.y())
        return QtWidgets.QGraphicsView.mouseMoveEvent(self, event)
    
    def wheelEvent(self, event):
        factor = 0.9
        if event.angleDelta().y() < 0:
            factor = 1.1
        self.zoom(factor)
        return QtWidgets.QGraphicsView.wheelEvent(self, event)    
    
    def leaveEvent(self, event):
        self.scene().hoverOverPos(None, None)
        return QtWidgets.QGraphicsView.leaveEvent(self, event)
    
    def keyPressEvent(self, event):
        super(Viewer, self).keyPressEvent(event)
        if event.key() == QtCore.Qt.Key.Key_Control:
            self.scene().controlPressed = True
        elif event.key() == QtCore.Qt.Key.Key_Equal:
            self.zoom(0.9)
        elif event.key() == QtCore.Qt.Key.Key_Minus:
            self.zoom(1.1)
        elif event.key() == QtCore.Qt.Key.Key_Space:
            self.scene().setSceneRect(self.origSceneRect)  
            self.fitInView(self.scene().sceneRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio) 
    
    def keyReleaseEvent(self, event):
        super(Viewer, self).keyReleaseEvent(event)
        if event.key() == QtCore.Qt.Key.Key_Control:
            self.scene().controlPressed = False

    def zoom(self, factor):
        sr = self.scene().sceneRect()
        srcp = sr.center()
        sr2 = QtCore.QRectF((sr.x() - srcp.x())*factor + srcp.x(),
                            (sr.y() - srcp.y())*factor + srcp.y(),
                            sr.width()*factor, sr.height()*factor)
        self.scene().setSceneRect(sr2)  
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)   
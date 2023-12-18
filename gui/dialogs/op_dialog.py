'''
Created on Nov 10, 2022

@author: Vlad
'''

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from gui import aligner_interface
from gui.dialogs import widgets
from operations import aligner_operations
import os

class OperationDialog(QtWidgets.QDialog):
    
    runTypes = {"clustering"  : ("root", "cluster", "clustering", "matrix"),
                "align" : ("root", "cluster", "clustering", "maf"),
                "matrix" : ("root", "cluster", "matrix")}
    
    def __init__(self, model, operation, parent=None, itemId = None, **kwargs):  
        self.model = model
        self.itemId = itemId
        self.operation = operation
        
        self.runSet = set(i for i in self.model.selectedItems if self.model.itemInfos[i].itemType in OperationDialog.runTypes[self.operation])
        if self.itemId is not None and self.model.itemInfos[self.itemId].itemType in OperationDialog.runTypes[self.operation]:
            self.runSet.add(self.itemId)
        if len(self.runSet) > 0:
            super(OperationDialog, self).__init__(parent)
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.widget = None
            self.buildDialog(self.operation, **kwargs)
    
    def buildDialog(self, operation, **kwargs):
        if operation == "clustering":
            self.widget = widgets.ClusteringWidget(self.model, self, self.itemId, **kwargs)
            self.setWindowTitle("Build Clustering..")
            runButton = QtWidgets.QPushButton("Build Clustering")
        elif operation == "align":
            self.widget = widgets.LocalAlignWidget(self.model, self, self.itemId, **kwargs)
            self.setWindowTitle("Build Alignments..")
            runButton = QtWidgets.QPushButton("Build Alignments")
        elif operation == "matrix":
            self.widget = widgets.MatrixWidget(self.model, self, self.itemId, **kwargs)
            self.setWindowTitle("Build Matrices..")
            runButton = QtWidgets.QPushButton("Build Matrix")
        elif operation == "maf":
            self.widget = widgets.MafWidget(self.model, self, self.itemId, **kwargs)
            self.setWindowTitle("Build MAF File..")
            runButton = QtWidgets.QPushButton("Build MAF File")
            
        runButton.clicked.connect(self.launchOperation)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)    
        
        hLayout = QtWidgets.QHBoxLayout()
        hLayout.addWidget(runButton)
        hLayout.addWidget(cancelButton)
        
        vLayout = QtWidgets.QVBoxLayout()  
        vLayout.addWidget(self.widget)
        vLayout.addLayout(hLayout) 
        
        #vLayout.set
        #vLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize) 
        self.setLayout(vLayout)
        
        self.exec()
    
    def launchOperation(self):
        self.close()
        context = self.widget.buildContext()        
        
        for itemId in self.runSet:
            itemInfo = self.model.itemInfos[itemId]
            if itemInfo.itemType == "clustering" or itemInfo.itemType == "maf":
                context.inClusterDir = itemInfo.path
            elif itemInfo.itemType == "matrix":
                context.inMatrixDir = itemInfo.path
                context.inPatchSize = itemInfo.patchSize 
                context.inKmerSize  = itemInfo.kmerSize
            elif itemInfo.itemType == "local alignments":
                context.localAlignDir = itemInfo.path
                #context.inClusterDir = item_info.getAbsolutePath(itemInfo.inClusterDir, GlobalContext.context.dir)
                 
            cItem = itemInfo
            while cItem.itemType not in ("root", "cluster") and cItem.parent is not None:
                cItem = self.model.itemInfos[cItem.parent]
            if cItem.itemType in ("root", "cluster"):
                context.cluster = [interval for interval in self.model.clusters[cItem.relativePath] if interval[2] in context.sequences]
                context.cluster.sort(key = lambda x : (x[2], x[0], x[1]))
                context.workingDir = cItem.path
            
            label = context.label or self.operation
            context.id, n = label, 1
            while context.id in self.model.operations:
                context.id, n = "{}_{}".format(label, n), n+1    
            print(context.id, context.label, self.operation)
            
            #print(args)
            self.model.operationLaunched(context)
            aligner_interface.launchOperation(aligner_operations.runOperation, self.model.operationFinished, 
                                              self.model.operationStatusChanged, context, self.operation)
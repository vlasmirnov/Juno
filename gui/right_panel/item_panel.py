'''
Created on May 9, 2022

@author: Vlad
'''

import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from gui.right_panel.item_tree import ItemTree, OperationTree
from gui.dialogs.cluster_searcher import ClusterSearcher


class ItemPanel(QtWidgets.QWidget):
    
    def __init__(self, model):
        super(ItemPanel, self).__init__()
        self.model = model
               
        self.searchTable = ItemTree(model)        
        self.operationTable = OperationTree(model)
        
        searchColumns = [('ID', lambda mid : model.items[mid].label),
                        ('Patch Size', lambda mid : getattr(model.items[mid], 'patchSize', "")),
                        ('Kmer Size', lambda mid : getattr(model.items[mid], 'kmerSize', "")),
                        ('Width', lambda mid : max(v[1]-v[0]+1 for v in model.clusters[mid]) if mid in model.clusters else ""),
                        #('Size', lambda mid : sum(v[1]-v[0]+1 for v in model.clusters[mid]))
                        ]
        self.searchTable.setColumns(searchColumns)
        #self.searchTable.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        #self.searchTable.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        operationColumns = [('ID', lambda mid : model.operations[mid].id),
                        ('Status', lambda mid : model.operations[mid].opStatus or "")]
        self.operationTable.setColumns(operationColumns)
        self.operationTable.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            
        model.signals.hoverOverItemSignal.connect(self.searchTable.hoverOverItem)
        model.signals.selectedItemsChangedSignal.connect(self.searchTable.updateSelectedItems)
        model.signals.searchItemsChangedSignal.connect(self.searchTable.updateItems)
        model.signals.operationChangedSignal.connect(self.operationTable.updateItemStatus)
        
        self.clusterSearcher = ClusterSearcher(model, parent = self.parent())
        self.searchButton = QtWidgets.QPushButton("Search")
        self.searchButton.clicked.connect(self.clusterSearcher.showClusterSearchDialog)    
        self.clearButton = QtWidgets.QPushButton("Clear Search")
        self.clearButton.clicked.connect(model.clearSearch)   
        #self.addButton = QtWidgets.QPushButton("Add to Selection")
        #self.addButton.clicked.connect(model.addClustersToSelection)    
        self.unpinButton = QtWidgets.QPushButton("Clear Selection")
        self.unpinButton.clicked.connect(lambda : model.setSelectedItems(set()))    
        #self.runButton = QtWidgets.QPushButton("Build Clusters")
        #self.runButton.clicked.connect(self.operationLauncher.showClusterLauncherDialog)
        #self.removeButton = QtWidgets.QPushButton("Remove from Selection")
        #self.removeButton.clicked.connect(self.model.removeClustersFromSelection)
        
        #layout = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.searchTable, 2) #, stretch = 4)
        buttonsLayout1 = QtWidgets.QGridLayout()
        buttonsLayout1.addWidget(self.searchButton, 0, 0)
        buttonsLayout1.addWidget(self.clearButton, 0, 1)
        #buttonsLayout1.addWidget(self.addButton, 1, 0)
        buttonsLayout1.addWidget(self.unpinButton, 1, 0)
        layout.addLayout(buttonsLayout1)
        #layout.addLayout(self.searchPanel, 0)
        layout.addWidget(self.operationTable, 0)
        #layout.addLayout(self.runPanel, 0)
        
        #buttonsLayout2 = QtWidgets.QGridLayout()
        #buttonsLayout2.addWidget(self.runButton, 0, 0)
        #buttonsLayout2.addWidget(self.removeButton, 0, 1)
        #layout.addLayout(buttonsLayout2)
        
        
        
        #layout.setSizes([800, 200])
        #layout.setStretchFactor(searchTable, 1)
        #layout.setStretchFactor(controlPanel, 0)
        #layout.setStretchFactor(selectionTable, 0)


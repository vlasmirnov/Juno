'''
Created on Jun 10, 2022

@author: Vlad
'''

import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from helpers.guiutils import CheckableComboBox


class ClusterSearcher():
    
    def __init__(self, model, parent=None):
        self.dialog = None
        self.model = model
        self.parent = parent
        
        self.minLength = None
        self.maxLength = None
        self.position = None
        self.sequences = set()
        self.sortBy = None
        self.sortAsc = None
        
    def populateSequenceDropdown(self, seqList):
        allSeqNames = set(s.name for s in self.model.sequences)
        self.sequences = self.sequences.intersection(allSeqNames)
        self.sequences = allSeqNames if len(self.sequences) == 0 else self.sequences
        
        seqList.clear()
        seqList.addItem("Sequences")
        seqList.setItemChecked(0, len(self.sequences) == len(self.model.sequences))
        for s, sequence in enumerate(self.model.sequences):
            seqList.addItem(sequence.name)
            seqList.setItemChecked(s+1, sequence.name in self.sequences)
    
    def formatPatchSize(self, p):
        if p < 1000:
            return str(p)
        elif p < 1000000:
            return "{}K".format(round(p/1000))
        else:
            return "{}M".format(round(p/1000000))   
        
        
    def searchMinLengthChanged(self, s):
        self.minLength = int(s) if len(s) > 0 else None
    
    def searchMaxLengthChanged(self, s):
        self.maxLength = int(s) if len(s) > 0 else None
        
    def searchPositionChanged(self, s):
        self.position = int(s) if len(s) > 0 else None
    
    def searchSequencesChanged(self, sList):
        self.sequences = set(sList)
    
    def searchSortByChanged(self, s):
        self.sortBy = s
        
    def searchSortAscChanged(self, s):
        self.sortAsc = s    
    
    def searchClustersPressed(self):
        self.model.clusterSearch(self)
        self.dialog.close()
    
    def showClusterSearchDialog(self):
        self.dialog = QtWidgets.QDialog(self.parent)
        self.dialog.setWindowTitle("Clustering Parameters")
        self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)                      
        
        regexp = QtCore.QRegularExpression('(^[0-9]+$|^$)')
        
        self.minBox = QtWidgets.QGroupBox("Minimum Length")
        minLength = QtWidgets.QLineEdit()
        minLength.setMaxLength(10)
        minLength.setText(str(self.minLength) if self.minLength is not None else "")
        minLength.setValidator(QtGui.QRegularExpressionValidator(regexp))
        minLength.textChanged.connect(self.searchMinLengthChanged)
        minBoxLayout = QtWidgets.QVBoxLayout()
        minBoxLayout.addWidget(minLength)
        self.minBox.setLayout(minBoxLayout)
        
        self.maxBox = QtWidgets.QGroupBox("Maximum Length")
        maxLength = QtWidgets.QLineEdit()
        maxLength.setMaxLength(10)
        maxLength.setText(str(self.maxLength) if self.maxLength is not None else "")
        maxLength.setValidator(QtGui.QRegularExpressionValidator(regexp))
        maxLength.textChanged.connect(self.searchMaxLengthChanged)
        maxBoxLayout = QtWidgets.QVBoxLayout()
        maxBoxLayout.addWidget(maxLength)
        self.maxBox.setLayout(maxBoxLayout)
        
        self.posBox = QtWidgets.QGroupBox("Position")
        pos = QtWidgets.QLineEdit()
        pos.setMaxLength(10)
        pos.setText(str(self.position) if self.position is not None else "")
        pos.setValidator(QtGui.QRegularExpressionValidator(regexp))
        pos.textChanged.connect(self.searchPositionChanged)
        posBoxLayout = QtWidgets.QVBoxLayout()
        posBoxLayout.addWidget(pos)
        self.posBox.setLayout(posBoxLayout)
        
        runSeqs = CheckableComboBox()      
        self.populateSequenceDropdown(runSeqs)      
        runSeqs.dataSignal.connect(self.searchSequencesChanged)   
        
        sortByList =  QtWidgets.QComboBox()
        sortByList.addItems(["Length", "Position"])
        sortByList.currentTextChanged.connect(self.searchSortByChanged)
        sortAscList = QtWidgets.QComboBox()
        sortAscList.addItems(["Ascending", "Descending"])
        sortAscList.currentTextChanged.connect(self.searchSortAscChanged) 
        
        searchButton = QtWidgets.QPushButton("Search Clusters")
        searchButton.clicked.connect(self.searchClustersPressed)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.clicked.connect(self.dialog.close)   
            
        runPanel = QtWidgets.QGridLayout()
        runPanel.addWidget(self.minBox, 0, 0)
        runPanel.addWidget(self.maxBox, 0, 1)
        runPanel.addWidget(self.posBox, 1, 0)
        runPanel.addWidget(runSeqs, 1, 1)
        runPanel.addWidget(sortByList, 2, 0)
        runPanel.addWidget(sortAscList, 2, 1)
        runPanel.addWidget(searchButton, 3, 0)
        runPanel.addWidget(cancelButton, 3, 1)
        self.dialog.setLayout(runPanel)
        
        self.dialog.exec()
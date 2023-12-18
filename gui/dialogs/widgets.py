'''
Created on Sep 7, 2022

@author: Vlad
'''


from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from helpers.guiutils import CheckableComboBox, formatShortNum
from data.context import Context
import os
import math


class MatrixWidget(QtWidgets.QWidget):
    
    def __init__(self, model, parent=None, itemId = None, **kwargs):        
        super(MatrixWidget, self).__init__(parent)
        
        self.model = model
        self.itemId = itemId
        
        self.patchBase = 2
        self.patchSize = self.patchBase ** 15
        self.kmerSize = 15
        self.matrixTrimDegree = 1
        self.label = None
        self.sequences = set()
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)    
        #self.attributes =  list(vars(self).keys())
        self.buildWidget()
    
    def buildContext(self):
        context = Context()
        context.sequences = set(seq.num for seq in self.model.sequences if len(self.sequences) == 0 or seq.name in self.sequences)    
        context.patchSize = self.patchSize
        context.kmerSize = self.kmerSize
        context.matrixTrimDegree = self.matrixTrimDegree
        
        '''
        context.matrixPatches = [self.patchSize]
        context.matrixKmers = [self.kmerSize]
        context.matrixTrimFractions = [None]
        context.matrixTrimDegrees = [self.matrixTrimDegree]
        context.matrixTrimMinWidths = [2]
        '''
        
        context.label = self.label if self.label not in (None, "", "Default") else None
        context.matrixId = context.label
        return context
    
    def buildWidget(self):
        regexp = QtCore.QRegularExpression('(^[0-9]+$|^$)')
        
        self.patchBox = QtWidgets.QGroupBox("Patch Size: {}".format(formatShortNum(self.patchSize)))
        patch = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        patch.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
        patch.setMinimum(1)
        patch.setMaximum(math.ceil(math.log(1e9, self.patchBase)))
        patch.setValue(int(math.log(self.patchSize, self.patchBase)))
        patch.setTickInterval(1)
        patch.valueChanged.connect(self.buildPatchLengthChanged)
        patchBoxLayout = QtWidgets.QVBoxLayout()
        patchBoxLayout.addWidget(patch)
        self.patchBox.setLayout(patchBoxLayout)
        
        self.kmerBox = QtWidgets.QGroupBox("Kmer Size: {}".format(self.kmerSize))
        kmer = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        kmer.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
        kmer.setMinimum(4)
        kmer.setMaximum(30)
        kmer.setValue(self.kmerSize)
        kmer.setTickInterval(1)
        kmer.valueChanged.connect(self.buildKmerSizeChanged)
        kmerBoxLayout = QtWidgets.QVBoxLayout()
        kmerBoxLayout.addWidget(kmer)
        self.kmerBox.setLayout(kmerBoxLayout)
        
        maxDegreeBox = QtWidgets.QGroupBox("Matrix Degree")
        maxDegree = QtWidgets.QLineEdit()
        maxDegree.setMaxLength(10)
        maxDegree.setValidator(QtGui.QIntValidator(self))
        maxDegree.setText(str(self.matrixTrimDegree))
        maxDegree.textChanged.connect(self.buildMatrixTrimDegreeChanged)
        maxDegreeBoxLayout = QtWidgets.QVBoxLayout()
        maxDegreeBoxLayout.addWidget(maxDegree)
        maxDegreeBox.setLayout(maxDegreeBoxLayout)
        
        seqBox = QtWidgets.QGroupBox("Sequences to Include")
        runSeqs = CheckableComboBox()      
        self.populateSequenceDropdown(runSeqs)      
        runSeqs.dataSignal.connect(self.buildSequencesChanged)   
        runSeqsLayout = QtWidgets.QVBoxLayout()
        runSeqsLayout.addWidget(runSeqs)
        seqBox.setLayout(runSeqsLayout)
        
        labelBox = QtWidgets.QGroupBox("Matrix Label")
        label = QtWidgets.QLineEdit()
        #label.setMaxLength(20)
        label.setPlaceholderText("Default")
        label.textChanged.connect(self.buildLabelChanged)
        labelBoxLayout = QtWidgets.QVBoxLayout()
        labelBoxLayout.addWidget(label)
        labelBox.setLayout(labelBoxLayout)
            
        runPanel = QtWidgets.QGridLayout()
        runPanel.addWidget(self.patchBox, 0, 0)
        runPanel.addWidget(self.kmerBox, 0, 1)
        runPanel.addWidget(maxDegreeBox, 1, 0)
        runPanel.addWidget(seqBox, 1, 1)
        runPanel.addWidget(labelBox, 2, 0)
        self.setLayout(runPanel)
        
    def populateSequenceDropdown(self, seqList):
        self.sequences = set(s.name for s in self.model.sequences if s.num in self.model.selectedSequences or len(self.model.selectedSequences) == 0)
        
        seqList.clear()
        seqList.addItem("Sequences")
        seqList.setItemChecked(0, len(self.sequences) == len(self.model.sequences))
        for s, sequence in enumerate(self.model.sequences):
            seqList.addItem(sequence.name)
            seqList.setItemChecked(s+1, sequence.name in self.sequences) 
    
    def buildPatchLengthChanged(self, s):
        self.patchSize = self.patchBase**s
        self.patchBox.setTitle("Patch Size: {}".format(formatShortNum(self.patchSize)))
    
    def buildKmerSizeChanged(self, s):
        self.kmerSize = s
        self.kmerBox.setTitle("Kmer Size: {}".format(self.kmerSize))
    
    def buildMatrixTrimDegreeChanged(self, s):
        self.matrixTrimDegree = int(s) if len(s) > 0 else None #self.buildMaxDegree
    
    def buildSequencesChanged(self, sList):
        self.sequences = set(sList)
        
    def buildLabelChanged(self, s):
        self.label = s
        
class ClusteringWidget(QtWidgets.QWidget):
    
    def __init__(self, model, parent=None, itemId = None, **kwargs):        
        super(ClusteringWidget, self).__init__(parent)
        self.model = model
        self.itemId = itemId
        
        self.minMatchWidth = 2
        
        self.clusterStrategy = "FM"
        self.clusterCriterion = "Number of Balanced Clusters"
        self.clusterParameter = 16
        
        self.matrix = None
        self.sequences = set()
        self.matrices = {}
        self.label = None
        
        self.matrixWidget = MatrixWidget(model, parent, itemId, **kwargs)
        self.matrixWidget.hide()
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)    
        #self.attributes =  list(vars(self).keys())
        self.buildWidget()
    
    def buildContext(self):
        context = Context()
        if self.matrix is not None:
            mItem = self.matrices[self.matrix]
            context.inMatrixDir = mItem.path
            context.inPatchSize = mItem.patchSize
            context.inKmerSize = mItem.kmerSize
            context.matrixPatches = None
        else:
            context = self.matrixWidget.buildContext()
        
        context.sequences = set(seq.num for seq in self.model.sequences if len(self.sequences) == 0 or seq.name in self.sequences)    
        context.minMatchWidth = self.minMatchWidth
        context.clusterStrategy = self.clusterStrategy
        context.clusterCriterion = self.clusterCriterion
        context.clusterParameter = self.clusterParameter
        context.label = self.label if self.label not in (None, "", "Default") else None
        context.clusteringId = context.label
        return context
    
    def buildWidget(self):
        regexp = QtCore.QRegularExpression('(^[0-9]+$|^$)')
        
        minLengthBox = QtWidgets.QGroupBox("Min Patches per Cluster")
        minLength = QtWidgets.QLineEdit()
        minLength.setMaxLength(10)
        #minLength.setValidator(QtGui.QRegularExpressionValidator(regexp))
        minLength.setValidator(QtGui.QIntValidator(self))
        minLength.setText(str(self.minMatchWidth))
        minLength.textChanged.connect(self.minMatchWidthChanged)
        minLengthBoxLayout = QtWidgets.QVBoxLayout()
        minLengthBoxLayout.addWidget(minLength)
        minLengthBox.setLayout(minLengthBoxLayout)
        
        clusterStrategyBox = QtWidgets.QGroupBox("Clustering Strategy")
        clusterStrategy = QtWidgets.QComboBox()
        clusterStrategy.addItem("FM")
        clusterStrategy.addItem("Region Growing")
        clusterStrategy.addItem("Largest First")
        clusterStrategy.currentTextChanged.connect(self.clusterStrategyChanged)
        clusterStrategyLayout = QtWidgets.QVBoxLayout()
        clusterStrategyLayout.addWidget(clusterStrategy)
        clusterStrategyBox.setLayout(clusterStrategyLayout)
        
        clusterCriterionBox = QtWidgets.QGroupBox("Clustering Criterion")
        clusterCriterion = QtWidgets.QComboBox()
        clusterCriterion.addItem("Number of Balanced Clusters")
        clusterCriterion.addItem("Number of Clusters")
        clusterCriterion.addItem("Maximum Size")
        clusterCriterion.currentTextChanged.connect(self.clusterCriterionChanged)
        clusterCriterionLayout = QtWidgets.QVBoxLayout()
        clusterCriterionLayout.addWidget(clusterCriterion)
        clusterCriterionBox.setLayout(clusterCriterionLayout)
        
        clusterParameterBox = QtWidgets.QGroupBox("Clustering Parameter")
        self.clusterParameterLine = QtWidgets.QLineEdit()
        self.clusterParameterLine.setMaxLength(10)
        self.clusterParameterLine.setValidator(QtGui.QIntValidator(self))
        self.clusterParameterLine.setText(str(self.clusterParameter))
        self.clusterParameterLine.textChanged.connect(self.clusterParameterChanged)
        clusterParameterLayout = QtWidgets.QVBoxLayout()
        clusterParameterLayout.addWidget(self.clusterParameterLine)
        clusterParameterBox.setLayout(clusterParameterLayout)
        
        seqBox = QtWidgets.QGroupBox("Sequences to Include")
        runSeqs = CheckableComboBox()      
        self.populateSequenceDropdown(runSeqs)      
        runSeqs.dataSignal.connect(self.buildSequencesChanged)   
        runSeqsLayout = QtWidgets.QVBoxLayout()
        runSeqsLayout.addWidget(runSeqs)
        seqBox.setLayout(runSeqsLayout)
        
        matBox = QtWidgets.QGroupBox("Matrix")
        matList = QtWidgets.QComboBox()
        self.populateMatrixDropdown(matList)
        matList.currentTextChanged.connect(self.buildMatrixChanged)
        matBoxLayout = QtWidgets.QVBoxLayout()
        matBoxLayout.addWidget(matList)
        matBox.setLayout(matBoxLayout)
        
        labelBox = QtWidgets.QGroupBox("Clustering Label")
        label = QtWidgets.QLineEdit()
        #label.setMaxLength(10)
        label.setPlaceholderText("Default")
        label.textChanged.connect(self.buildLabelChanged)
        labelBoxLayout = QtWidgets.QVBoxLayout()
        labelBoxLayout.addWidget(label)
        labelBox.setLayout(labelBoxLayout)
        
        runPanel = QtWidgets.QGridLayout()
        runPanel.addWidget(minLengthBox, 0, 0)
        runPanel.addWidget(clusterStrategyBox, 0, 1)
        runPanel.addWidget(clusterCriterionBox, 1, 0)
        runPanel.addWidget(clusterParameterBox, 1, 1)
        runPanel.addWidget(matBox, 2, 0)
        runPanel.addWidget(seqBox, 2, 1)
        runPanel.addWidget(labelBox, 3, 0)
        
        fullLayout = QtWidgets.QVBoxLayout()
        fullLayout.addLayout(runPanel)
        fullLayout.addWidget(self.matrixWidget)
        #fullLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(fullLayout)
        
        #self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        
        self.minSize = self.size()
        if self.matrix is None:
            self.matrixWidget.show()
        
    def populateSequenceDropdown(self, seqList):
        self.sequences = set(s.name for s in self.model.sequences if s.num in self.model.selectedSequences or len(self.model.selectedSequences) == 0)
        
        seqList.clear()
        seqList.addItem("Sequences")
        seqList.setItemChecked(0, len(self.sequences) == len(self.model.sequences))
        for s, sequence in enumerate(self.model.sequences):
            seqList.addItem(sequence.name)
            seqList.setItemChecked(s+1, sequence.name in self.sequences) 
    
    def populateMatrixDropdown(self, matList):
        for itemId, item in self.model.itemInfos.items():
            if item.itemType == "matrix":
                self.matrices[itemId] = item
        
        matList.clear()
        for m in self.matrices.keys():
            self.matrix = self.matrix or m
            matList.addItem(m)
        matList.addItem("New matrix..")
    
    def minMatchWidthChanged(self, s):
        self.minMatchWidth = int(s) if len(s) > 0 else None
    
    def clusterStrategyChanged(self, s):
        self.clusterStrategy = s
    
    def clusterCriterionChanged(self, s):
        self.clusterCriterion = s
        if s == "Number of Clusters":
            self.clusterParameter = 16
        elif s == "Maximum Size":
            self.clusterParameter = 200000
        elif s == "Number of Balanced Clusters":
            self.clusterParameter = 16
        self.clusterParameterLine.setText(str(self.clusterParameter))
    
    def clusterParameterChanged(self, s):
        self.clusterParameter = int(s) if len(s) > 0 else None
    
    def refineLimitChanged(self, s):
        self.refineLimit = int(s) if len(s) > 0 else None
    
    def buildSequencesChanged(self, sList):
        self.sequences = set(sList)
        
    def buildMatrixChanged(self, matrix):
        if matrix == "New matrix..":
            self.matrix = None
            self.matrixWidget.show()
            #self.fullLayout.addWidget(self.matrixWidget)
        else:
            #if self.matrix is None:
            self.matrixWidget.hide()
            
            if self.parent() is not None:
                self.parent().resize(self.parent().minimumSizeHint())
                self.parent().adjustSize()
                #
            #QtCore.QTimer.singleShot(0, lambda : self.resize(self.minimumSizeHint()))
            #self.resize(self.minSize)
            self.matrix = matrix
    
    def buildLabelChanged(self, s):
        self.label = s


class LocalAlignWidget(QtWidgets.QWidget):
    
    def __init__(self, model, parent=None, itemId = None, **kwargs):        
        super(LocalAlignWidget, self).__init__(parent)
        
        self.model = model
        self.itemId = itemId
        
        self.label = None
        self.sequences = set()
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)    
        #self.attributes =  list(vars(self).keys())
        self.buildWidget()
    
    def buildContext(self):
        context = Context()
        #context.sequences = set(seq.num for seq in self.model.sequences if len(self.sequences) == 0 or seq.name in self.sequences)    
        sequences = [seq.num for seq in self.model.sequences if len(self.sequences) == 0 or seq.name in self.sequences]
        context.refSequence = sequences[0]
        context.label = self.label if self.label not in (None, "") else None
        context.alignId = context.label
        return context
    
    def buildWidget(self):
        regexp = QtCore.QRegularExpression('(^[0-9]+$|^$)')
        
        seqBox = QtWidgets.QGroupBox("Sequences to Include")
        runSeqs = CheckableComboBox()      
        self.populateSequenceDropdown(runSeqs)      
        runSeqs.dataSignal.connect(self.buildSequencesChanged)   
        runSeqsLayout = QtWidgets.QVBoxLayout()
        runSeqsLayout.addWidget(runSeqs)
        seqBox.setLayout(runSeqsLayout)
        
        labelBox = QtWidgets.QGroupBox("Alignment Label")
        label = QtWidgets.QLineEdit()
        #label.setMaxLength(20)
        label.setPlaceholderText("Default")
        label.textChanged.connect(self.buildLabelChanged)
        labelBoxLayout = QtWidgets.QVBoxLayout()
        labelBoxLayout.addWidget(label)
        labelBox.setLayout(labelBoxLayout)
            
        runPanel = QtWidgets.QGridLayout()
        runPanel.addWidget(seqBox, 0, 0)
        runPanel.addWidget(labelBox, 0, 1)
        self.setLayout(runPanel)
        
    def populateSequenceDropdown(self, seqList):
        self.sequences = set(s.name for s in self.model.sequences if s.num in self.model.selectedSequences or len(self.model.selectedSequences) == 0)
        
        seqList.clear()
        seqList.addItem("Sequences")
        seqList.setItemChecked(0, len(self.sequences) == len(self.model.sequences))
        for s, sequence in enumerate(self.model.sequences):
            seqList.addItem(sequence.name)
            seqList.setItemChecked(s+1, sequence.name in self.sequences) 
    
    def buildSequencesChanged(self, sList):
        self.sequences = set(sList)
        
    def buildLabelChanged(self, s):
        self.label = s

class MafWidget(QtWidgets.QWidget):
    
    def __init__(self, model, parent=None, itemId = None, **kwargs):        
        super(MafWidget, self).__init__(parent)
        
        self.model = model
        self.itemId = itemId
        
        self.label = None
        self.sequences = set()
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)    
        #self.attributes =  list(vars(self).keys())
        self.buildWidget()
    
    def buildContext(self):
        context = Context()
        sequences = [seq.num for seq in self.model.sequences if len(self.sequences) == 0 or seq.name in self.sequences]
        context.refSequence = sequences[0]
        context.label = self.label if self.label not in (None, "") else None
        context.mafId = context.label
        return context
    
    def buildWidget(self):
        regexp = QtCore.QRegularExpression('(^[0-9]+$|^$)')
        
        seqBox = QtWidgets.QGroupBox("Sequences to Include")
        runSeqs = CheckableComboBox()      
        self.populateSequenceDropdown(runSeqs)      
        runSeqs.dataSignal.connect(self.buildSequencesChanged)   
        runSeqsLayout = QtWidgets.QVBoxLayout()
        runSeqsLayout.addWidget(runSeqs)
        seqBox.setLayout(runSeqsLayout)
        
        labelBox = QtWidgets.QGroupBox("MAF Label")
        label = QtWidgets.QLineEdit()
        #label.setMaxLength(20)
        label.setPlaceholderText("Default")
        label.textChanged.connect(self.buildLabelChanged)
        labelBoxLayout = QtWidgets.QVBoxLayout()
        labelBoxLayout.addWidget(label)
        labelBox.setLayout(labelBoxLayout)
            
        runPanel = QtWidgets.QGridLayout()
        runPanel.addWidget(seqBox, 0, 0)
        runPanel.addWidget(labelBox, 0, 1)
        self.setLayout(runPanel)
        
    def populateSequenceDropdown(self, seqList):
        self.sequences = set(s.name for s in self.model.sequences if s.num in self.model.selectedSequences or len(self.model.selectedSequences) == 0)
        
        seqList.clear()
        seqList.addItem("Sequences")
        seqList.setItemChecked(0, len(self.sequences) == len(self.model.sequences))
        for s, sequence in enumerate(self.model.sequences):
            seqList.addItem(sequence.name)
            seqList.setItemChecked(s+1, sequence.name in self.sequences) 
    
    def buildSequencesChanged(self, sList):
        self.sequences = set(sList)
        
    def buildLabelChanged(self, s):
        self.label = s
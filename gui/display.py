'''
Created on May 5, 2022

@author: Vlad
'''

import sys
import os
from PyQt6 import QtCore, QtWidgets, QtGui
from gui import display_model
from gui.view import viewer
from gui.right_panel import item_panel
from data.config import configs
from data.context import Context
from data import sequence

def launchDisplay():    
    app = QtWidgets.QApplication(sys.argv)
    model = display_model.DisplayModel()
    window = MainDisplay(model)    
    window.showMaximized()
    
    context = Context(configs().dir)
    context.initFromArgs()
    context.sequenceInfo.sequencePaths = None
    context.initContext()
    model.loadContext(context)
    
    app.exec()


class MainDisplay(QtWidgets.QMainWindow):
    
    def __init__(self, model):
        super().__init__()
        
        self.model = model
        self.setWindowTitle("Genome Aligner")    
        
        self.viewer = viewer.Viewer(model)
        #self.oldviewer.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        self.itemPanel = item_panel.ItemPanel(model)        
        
        layout = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        #layout = QHBoxLayout()
        layout.addWidget(self.viewer) #, stretch = 4)
        layout.addWidget(self.itemPanel) #, stretch = 1)
        layout.setSizes([800, 200])
        #layout.setStretchFactor(0, 4)
        #layout.setStretchFactor(1, 1)

        #widget = QWidget()
        #widget.setLayout(layout)
        #self.setCentralWidget(widget)
        self.setCentralWidget(layout)
        self.buildMenuBar()

    def buildMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        settingsMenu = menuBar.addMenu('&Settings')
        helpMenu = menuBar.addMenu('&Help')
        
        newAction = fileMenu.addAction("New Working Directory...")
        openAction = fileMenu.addAction("Open Working Directory...")
        fileMenu.addSeparator()
        seqFilesAction = fileMenu.addAction("Open Sequence Files...")
        seqDirAction = fileMenu.addAction("Open Sequence Directory...")
        fileMenu.addSeparator()
        buscoDirAction = fileMenu.addAction("Open Busco Directory...")
        mafFileAction = fileMenu.addAction("Open MAF File...")
        
        newAction.triggered.connect(self.fileNew)
        openAction.triggered.connect(self.fileOpen)
        seqFilesAction.triggered.connect(self.seqFilesOpen)
        seqDirAction.triggered.connect(self.seqDirOpen)
        buscoDirAction.triggered.connect(self.buscoDirOpen)
        mafFileAction.triggered.connect(self.mafOpen)
    
    
    def fileNew(self):
        dialog = QtWidgets.QFileDialog(self, caption='New Working Directory')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        #dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        
        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles()        
            if len(dirName) > 0:
                configs().setWorkspace(dirName[0])
                context = Context(dirName[0])
                context.initFromArgs()
                context.sequenceInfo.sequencePaths = None
                #context.initContext()
                self.model.loadContext(context)
        print(dirName)
        
    def fileOpen(self):
        #dirName = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Working Directory",
        #                                                      '', QtWidgets.QFileDialog.Option.ShowDirsOnly)
        dialog = QtWidgets.QFileDialog(self, caption='Open Working Directory')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        #dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        #dialog.setDirectory(log_dir)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)
        
        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles() 
            if len(dirName) > 0:
                configs().setWorkspace(dirName[0])
                context = Context(dirName[0])
                context.initFromArgs()
                context.sequenceInfo.sequencePaths = None
                context.initContext()
                self.model.loadContext(context)    
        print(dirName)
        
        
    def seqFilesOpen(self):
        dialog = QtWidgets.QFileDialog(self, caption='Select Sequence Files')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        #dialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        #dialog.setDirectory(log_dir)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        #dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)
        
        #l = dialog.findChild(QtWidgets.QListView, "listView")
        #if l is not None:
        #    l.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        #t = dialog.findChild(QtWidgets.QTreeView)
        #if t is not None:
        #    t.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        
        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles()    
            if len(dirName) > 0:
                sequencePaths = []
                for p in dirName:
                    path = os.path.abspath(p)
                    if os.path.isdir(path):
                        for filename in os.listdir(path):
                            sequencePaths.append(os.path.join(path, filename))
                    else:
                        sequencePaths.append(path)
                print(sequencePaths)
                #self.model.context.initContext() 
                sequence.loadSequences(self.model.context, sequencePaths) 
                self.model.loadContext(self.model.context)
        print(dirName)
        
    def seqDirOpen(self):
        dialog = QtWidgets.QFileDialog(self, caption='Select Sequence Directory')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        #dialog.setDirectory(log_dir)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        #dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)

        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles() 
            if len(dirName) > 0:
                sequencePaths = []
                for p in dirName:
                    path = os.path.abspath(p)
                    if os.path.isdir(path):
                        for filename in os.listdir(path):
                            sequencePaths.append(os.path.join(path, filename))
                    else:
                        sequencePaths.append(path)
                print(sequencePaths)
                #self.model.context.initContext()  
                sequence.loadSequences(self.model.context, sequencePaths)  
                self.model.loadContext(self.model.context)
        print(dirName)
    
    def buscoDirOpen(self):
        dialog = QtWidgets.QFileDialog(self, caption='Open Busco Directory')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)
        
        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles() 
            if len(dirName) > 0:
                for p in dirName:
                    self.model.loadNewBuscoDir(p)
        print(dirName)
    
    def mafOpen(self):
        dialog = QtWidgets.QFileDialog(self, caption='Select MAF Files')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        
        dirName = None
        if dialog.exec() == QtWidgets.QFileDialog.DialogCode.Accepted:
            dirName = dialog.selectedFiles() 
            if len(dirName) > 0:
                for p in dirName:
                    self.model.loadNewMafFile(p)
        print(dirName)    
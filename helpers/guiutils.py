'''
Created on Aug 24, 2022

@author: Vlad
'''

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt


def formatShortNum(p):
    if p < 1000:
        return str(p)
    elif p < 1000000:
        return "{}K".format(round(p/1000))
    else:
        return "{}M".format(round(p/1000000))  

class CheckableComboBox(QtWidgets.QComboBox):
    
    dataSignal = QtCore.pyqtSignal(list)
    
    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QtGui.QStandardItemModel(self))
        self.changed = False

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if index.row() == 0:
            state = item.checkState()
            for idx in range(self.model().rowCount()):
                otherItem = self.model().item(idx)
                otherItem.setCheckState(QtCore.Qt.CheckState.Unchecked if state == QtCore.Qt.CheckState.Checked else QtCore.Qt.CheckState.Checked)
        else:
            item.setCheckState(QtCore.Qt.CheckState.Unchecked if item.checkState() == QtCore.Qt.CheckState.Checked else QtCore.Qt.CheckState.Checked)
        self.changed = True
        checkedItems = [self.model().item(idx) for idx in range(1, self.model().rowCount())]
        checkedItems = [item.text() for item in checkedItems if item.checkState() == QtCore.Qt.CheckState.Checked]
        self.dataSignal.emit(checkedItems)
    
    def hidePopup(self):
        if not self.changed:
            super(CheckableComboBox, self).hidePopup()
        self.changed = False

    def itemChecked(self, index):
        item = self.model().item(index, self.modelColumn())
        return item.checkState() == QtCore.Qt.CheckState.Checked

    def setItemChecked(self, index, checked=True):
        item = self.model().item(index, self.modelColumn())
        if checked:
            item.setCheckState(QtCore.Qt.CheckState.Checked)
        else:
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
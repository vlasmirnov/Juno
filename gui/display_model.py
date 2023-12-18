'''
Created on May 11, 2022

@author: Vlad
'''

from PyQt6 import QtCore
from gui import aligner_interface
from gui.aligner_interface import ItemInfo
from data.config import configs
import os

class ModelSignals(QtCore.QObject):    
    contextChangedSignal = QtCore.pyqtSignal(object)
    hoverOverItemSignal = QtCore.pyqtSignal(object)
    searchItemsChangedSignal = QtCore.pyqtSignal(set)
    selectedItemsChangedSignal = QtCore.pyqtSignal(set)
    selectedSeqsChangedSignal = QtCore.pyqtSignal(set)
    operationChangedSignal = QtCore.pyqtSignal(object)

class DisplayModel:  
    
    def __init__(self):
        self.signals = ModelSignals()                
        
        self.context = None
        self.sequences = None
        self.items = None
        self.clusters = {}
        self.operations = {}
    
        self.hoverItem = None
        self.searchItems = set()
        self.selectedItems = set()
        self.selectedSequences = set()
        
        configs().connectSignal("status", self.operationStatusChanged)
        #self.signals.statusChangedSignal.connect(self.alignOperationStatusChanged)
        
    def loadContext(self, context):
        self.context = context
        self.sequences = context.sequenceInfo.sequences
        self.items = aligner_interface.loadItemInfos()
        
        self.hoverItem = None
        self.searchItems = set(self.items)
        self.selectedItems = set()
        
        self.signals.contextChangedSignal.emit(context)
        self.signals.hoverOverItemSignal.emit(self.hoverItem)
        self.signals.searchItemsChangedSignal.emit(self.searchItems)
        self.signals.selectedItemsChangedSignal.emit(self.selectedItems)
    
    def loadClusters(self, item):
        items, clusters = aligner_interface.loadClusters(self.context, item)
        self.items.update(items)
        self.clusters.update(clusters)
        self.searchItems.update(items)
        self.signals.searchItemsChangedSignal.emit(self.searchItems)
            
    def loadNewBuscoDir(self, buscoDir):
        item = ItemInfo(itemType = "busco", label = os.path.basename(buscoDir), path = buscoDir)
        self.items[item.path] = item
        self.searchItems.add(item.path)
        self.signals.searchItemsChangedSignal.emit(self.searchItems)
    
    def loadNewMafFile(self, mafFile):
        item = ItemInfo(itemType = "maf", label = os.path.basename(mafFile), path = mafFile)
        self.items[item.path] = item
        self.searchItems.add(item.path)
        self.signals.searchItemsChangedSignal.emit(self.searchItems)
        self.loadClusters(item)
    
    def operationLaunched(self, operation):
        self.operations[operation.id] = operation
        self.signals.operationChangedSignal.emit(operation.id)
    
    def operationFinished(self, result):
        print("HIT THE CALLBACK..")
        self.items = aligner_interface.loadItemInfos()
        aligner_interface.assignItemParents(self.items)
        self.searchItems = set(self.items)
        self.signals.searchItemsChangedSignal.emit(self.searchItems)
    
    def operationStatusChanged(self, status):
        operationId = status["id"]
        #self.operations[operationId] = operation
        if operationId in self.operations:
            self.signals.operationChangedSignal.emit(operationId)
    
    def checkSearchCluster(self, cluster, searcher):
        length =  max(v[1]-v[0]+1 for v in cluster)
        if searcher.minLength is not None and searcher.minLength > length:
            return False
        if searcher.maxLength is not None and searcher.maxLength < length:
            return False
        if searcher.sequences is not None and len(searcher.sequences) > 0:
            if not any(self.context.sequenceInfo.seqMap[v[2]].name in searcher.sequences for v in cluster):
                return False
            if len(searcher.sequences) == 1 and searcher.position is not None:
                if not any(self.context.sequenceInfo.seqMap[v[2]].name in searcher.sequences and 
                           v[0] <= searcher.position and v[1] >= searcher.position for v in cluster):
                    return False
        return True
    
    def clusterSearch(self, searcher):
        idxs = [m for m, cluster in self.clusters.items() if self.checkSearchCluster(cluster, searcher)]        
        if searcher.sortBy == "Position":
            sortKey = lambda x : self.clusters[x]
            idxs.sort(key=sortKey, reverse=searcher.sortAsc == "Descending")
        #else:
        #    sortKey = lambda x : (max(v[1]-v[0]+1 for v in self.clusters[x]), sum(v[1]-v[0]+1 for v in self.clusters[x]))
        #idxs.sort(key=sortKey, reverse=self.searchSortAsc == "Descending")
    
        self.searchItems = set(idxs)        
        self.signals.searchItemsChangedSignal.emit(self.searchItems)        
        self.setSelectedItems(self.selectedItems.intersection(self.searchItems))
    
    def clearSearch(self):
        self.searchItems = set(self.items)        
        self.signals.searchItemsChangedSignal.emit(self.searchitems) 
            
    def hoverOverItem(self, mid):
        self.hoverItem, prev = mid, self.hoverItem
        if self.hoverItem != prev:
            self.signals.hoverOverItemSignal.emit(mid)
    
    def selectItems(self, selectIds, unselectIds):
        self.selectedItems.update(selectIds)
        self.selectedItems.difference_update(unselectIds)
        self.signals.selectedItemsChangedSignal.emit(self.selectedItems)
           
    def setSelectedItems(self, ids):
        self.selectedItems = set(ids)
        self.signals.selectedItemsChangedSignal.emit(self.selectedItems)
    
    def selectSeqs(self, selectNums, unselectNums):
        self.selectedSequences.update(selectNums)
        self.selectedSequences.difference_update(unselectNums)
        self.signals.selectedSeqsChangedSignal.emit(self.selectedSequences)
    
    def setSelectedSeqs(self, nums):
        self.selectedSequences = set(nums)
        self.signals.selectedSeqsChangedSignal.emit(self.selectedSequences)
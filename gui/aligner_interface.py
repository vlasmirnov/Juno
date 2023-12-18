'''
Created on May 17, 2022

@author: Vlad
'''

import random
import json
from PyQt6 import QtCore
from PyQt6.QtCore import pyqtSlot
from operations import aligner_operations
from helpers import clusterutils, buscoutils, mafutils, fileutils
import traceback, sys, os, pathlib


def loadItemInfos():
    #return item_info.readItemInfos(GlobalContext.context)
    return {}

def assignItemParents(itemInfos):
    for item in itemInfos.values():
        if item.itemType == "root":
            print(item.relativePath)
        parts = pathlib.Path(item.relativePath).parts
        for i in range(1, len(parts)):
            pk = str(pathlib.PurePosixPath(*parts[:-i]))
            if item.itemType == "matrix":
                print(pk)
            if pk in itemInfos:
                item.parent = pk
                break    

def loadClusters(context, clusterItem):
    items = {}
    clusters = {}    
    
    if clusterItem.itemType == "root" and len(context.sequences) > 0:
        clusters[clusterItem.relativePath] = [(0, len(seq)-1, seq.num, strand) for seq in context.sequences for strand in (1,0)]
        #clusters[clusterItem.relativePath] = [(0, len(seq)-1, seq.num, 1) for seq in globalContext.sequences]
    
    if clusterItem.itemType == "clustering":
        dirclusters = clusterutils.readClustersFromDb(clusterItem.path, context.sequences)
        for label, cluster in dirclusters.items():
            item = ItemInfo(itemType = "cluster", label = label, 
                                      relativePath = str(pathlib.PurePosixPath(clusterItem.relativePath, label)), 
                                      path = os.path.join(clusterItem.path, label))
            item.parent = clusterItem.relativePath
            items[item.relativePath] = item            
            clusters[item.relativePath] = cluster
    
    if clusterItem.itemType == "busco":
        dirclusters = buscoutils.readBuscoFiles(clusterItem.path)
        for label, cluster in dirclusters.items():
            item = ItemInfo(itemType = "cluster", label = label, 
                                      relativePath = str(pathlib.PurePosixPath(clusterItem.relativePath, label)), 
                                      path = os.path.join(clusterItem.path, label))
            item.parent = clusterItem.relativePath
            items[item.relativePath] = item            
            clusters[item.relativePath] = cluster
    
    if clusterItem.itemType == "maf":
        dirclusters = mafutils.getMafClusters(clusterItem.path)
        dirclusters = mafutils.getMafMatches(clusterItem.path, context.sequenceInfo.seqMap)
        dirclusters = list(dirclusters.items())
        print("{} clusters left..".format(len(dirclusters)))
        #dirclusters.sort(key=lambda x : max(v[1]-v[0]+1 for v in x[1]), reverse=True)
        #random.shuffle(dirclusters)
        #dirclusters = dirclusters[:10000]
        for label, cluster in dirclusters:
            item = ItemInfo(itemType = "cluster", label = label, path = os.path.join(clusterItem.path, label))
            item.parent = clusterItem.path
            items[item.path] = item            
            clusters[item.path] = cluster    
    return items, clusters

class ItemInfo:
    
    def __init__(self,  **kwargs):
        self.label = None
        self.itemType = None
        self.relativePath = None
          
        self.attributes =  list(vars(self).keys())
        ##################
        
        self.path = None
        self.parent = None
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr) 
            self.attributes.append(attr)
        
        
    def resolveRelativePath(self, basePath):
        if self.path is not None and self.relativePath is None:
            self.relativePath = fileutils.getRelativePath(self.path, basePath)
            self.label = self.label or os.path.basename(self.path)
    
    def resolveAbsolutePath(self, basePath):
        if self.relativePath is not None and self.path is None:
            self.path = fileutils.getAbsolutePath(self.relativePath, basePath)
    
    def toJson(self):
        return json.dumps({attr : getattr(self, attr) for attr in self.attributes})

def launchOperation(operation, resultCallback, statusCallback, *args, **kwargs):
    worker = Worker(operation, *args, **kwargs)
    worker.signals.result.connect(resultCallback)    
    #worker.signals.finished.connect(lolDone)
    #worker.progress.connect(self.progress_fn)
    worker.signals.status.connect(statusCallback)
    Worker.threadPool.start(worker)
    

class WorkerSignals(QtCore.QObject):    
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(dict)

class Worker(QtCore.QRunnable):
    
    threadPool = QtCore.QThreadPool()
    threadPool.setMaxThreadCount(1)

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        #self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        try:
            print(self.args)
            print(self.kwargs)
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result) 
        finally:
            self.signals.finished.emit() 
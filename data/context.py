'''
Created on Nov 3, 2021

@author: Vlad
'''

import re
import os
import json
from data import sequence
from data.config import configs


class Context:
    
    def __init__(self, cdir, **kwargs):
        
        self.dir = cdir
        self.workingDir = os.path.join(self.dir, "working_data")
        
        self.sequenceInfo = None
        self.matrixInfo = None
        self.matchInfo = None
        self.clusterInfo = None
        self.localAlignInfo = None
        self.mafInfo = None
        
        self.cluster = None
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs[attr] 
        
    def initFromArgs(self):
        self.sequenceInfo = configs().initObjectFromArgs(SequenceInfo(), "SEQUENCES") 
        self.matrixInfo = configs().initObjectFromArgs(MatrixInfo(), "MATRIX")  
        self.matchInfo = configs().initObjectFromArgs(MatchInfo(), "MATCH")
        self.clusterInfo = configs().initObjectFromArgs(ClusterInfo(), "CLUSTER")
        self.localAlignInfo = configs().initObjectFromArgs(LocalAlignInfo(), "ALIGN")  
        self.mafInfo = configs().initObjectFromArgs(MafInfo(), "MAF")  
    
    def initContext(self):
        sequence.loadSequences(self) #, self.sequenceInfo.sequencePaths)
        #self.rootCluster()
        
    def rootCluster(self):
        self.cluster = [(0, len(seq)-1, seq.num, strand) for seq in self.sequenceInfo.sequences for strand in (1,0)]
    
    def seqGroup(self, seqNum):
        if self.mafInfo.seqFilter in ("species", "", None):
            return self.sequenceInfo.seqMap[seqNum].baseName 
        elif self.mafInfo.seqFilter in ("sequence", "chromosome", "chrom"):
            return seqNum
        return seqNum 
            
    def toJson(self):
        return json.dumps({attr : getattr(self, attr) for attr in self.attributes})
    
    def status(self, status, progress = None):
        id = ""
        if progress is None:
            configs().log("Status {}: {}".format(id, status))
        else:
            configs().log("Status {}: {}, {}%".format(id, status, int(progress)))
        configs().emitSignal("status", {"id" : id, "status" : status, "progress" : progress})
        

class SequenceInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.filePath = None
        self.dir = None
        
        self.sequencePaths = None
        self.sequences = []       
        self.seqMap = {}        
        
        self.ref = None
        self.query = None
        self.refMap = None
        self.refSequences = None

class MatrixInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
        
        self.curRef = None
        
        self.sketchDir = None
        self.sketchLimit = 10000
        self.sketchCache = {}
        
        self.edgeLimit = 20000
        self.update = False
        self.keepKmers = False
        self.chunkSize = 30000
        
        self.patches = None
        self.kmers = None
        self.trimFractions = None
        self.trimDegrees = None
        self.trimMinWidths = None     
        
        self.attributes =  list(vars(self).keys())
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  

class SketchInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  

class MatchInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
                
        self.minWidth = 128
        self.maxWidth = 10000
        self.maxGap = 1280
        self.minWidthRatio = 0.5
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  

class ClusterInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
        
        self.policy = None
        self.parameter = 1
        self.climit = 10000000
        self.update = False
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  

class LocalAlignInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
        
        self.limit = None
        self.factor = 1
        self.depth = None
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  
        

class MafInfo:
    
    def __init__(self, **kwargs):
        self.id = None
        self.label = None
        self.dir = None
        
        self.policy = None
        self.maxDistance = None
        self.patchSize = None
        self.seqFilter = None
        self.singleFile = False
        self.refGaps = False
        
        self.attributes =  list(vars(self).keys())
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  
        
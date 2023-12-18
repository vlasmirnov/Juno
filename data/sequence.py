'''
Created on Oct 28, 2021

@author: Vlad
'''

import re
import os
import json
from helpers import stringutils, sequenceutils, mputils
from data.config import configs

 
def loadSequences(context, sequencePaths = None):
    configs().log("Loading sequences..")
    context.sequenceInfo.filePath = os.path.join(context.dir, "sequences.txt") 
    context.sequenceInfo.dir =  os.path.join(context.workingDir, "sequences")
    if sequencePaths is None:
        mputils.awaitRun("Load sequences", addSequencesFromPaths, context.sequenceInfo, context.sequenceInfo.sequencePaths) 
    else:
        mputils.awaitRun("Load sequences {}".format(sequencePaths), addSequencesFromPaths, context.sequenceInfo, sequencePaths) 
    readSequenceInfos(context.sequenceInfo)
    initRefSequences(context.sequenceInfo)
    configs().log("Loaded sequences..")
    context.rootCluster()
           
def readSequenceInfos(sequenceInfo):     
    sequenceInfo.sequences = []       
    sequenceInfo.seqMap = {}                   
    if os.path.exists(sequenceInfo.filePath):
        with open(sequenceInfo.filePath) as file:
            for line in file.readlines():
                info = json.loads(line.strip())
                newSeq = Sequence(**info)
                addSequenceToContext(sequenceInfo, newSeq)

def addSequencesFromPaths(sequenceInfo, sequencePaths):
    if sequencePaths is None:
        return
    
    os.makedirs(sequenceInfo.dir, exist_ok = True)
    readSequenceInfos(sequenceInfo)    
    seqNames = set(seq.name for seq in sequenceInfo.sequences)
    seqSources = os.path.join(sequenceInfo.dir, "source_files.txt")
    usedPaths = set()
    if os.path.exists(seqSources):
        with open(seqSources, 'r') as usedFile:
            usedPaths = set(line.strip() for line in usedFile)
    
    with open(seqSources, 'a') as usedFile:
        with open(sequenceInfo.filePath, 'a') as infoFile:
            for filePath in sequencePaths:
                if filePath not in usedPaths:        
                    sequences = sequenceutils.readFromFastaOrderedFull(filePath, False)
                    for i, s in enumerate(sequences):
                        newSeq = Sequence().initFromSourceFile(filePath, s.tag)
                        if newSeq.name not in seqNames:
                            addSequenceToContext(sequenceInfo, newSeq, s.seq)
                            infoFile.write(newSeq.toJson() + '\n')
                    usedFile.write(filePath + '\n')      

def addSequenceToContext(sequenceInfo, newSeq, string = None):
    newSeq.num = newSeq.num or max(sequenceInfo.seqMap, default = -1) + 1
    newSeq.binFile = os.path.join(sequenceInfo.dir, newSeq.baseName, "{}.txt".format(newSeq.tagName))
    newSeq.initFromString(string)
        
    sequenceInfo.seqMap[newSeq.num] = newSeq
    sequenceInfo.sequences.append(newSeq)    
    configs().debug("Added sequence {} of length {}..".format(newSeq.name, len(newSeq)))
     
def initRefSequences(sequenceInfo):
    if sequenceInfo.ref is not None:
        sequenceInfo.refSequences = []
        sequenceInfo.refMap = {rname : [] for rname in sequenceInfo.ref}
        strNames, baseNames = buildNamingMap(sequenceInfo)
            
        for rname in sequenceInfo.ref:
            rseq = re.sub(r'[^A-Za-z0-9]+', '', rname).lower()
            if rseq in strNames:
                sequenceInfo.refSequences.append(strNames[rseq])
                sequenceInfo.refMap[rname].append(strNames[rseq])
            elif rseq in baseNames:
                sequenceInfo.refSequences.extend(baseNames[rseq])
                sequenceInfo.refMap[rname].extend(baseNames[rseq])
            else:
                raise Exception("Reference sequence or species {} not found in sequence set.".format(rname))
        
        configs().log("Reference sequences:")
        for rname in sequenceInfo.refMap:
            configs().log("{}:".format(rname))
            for r in sequenceInfo.refMap[rname]:
                configs().log("{}: {}".format(r, sequenceInfo.seqMap[r].name))
            configs().log("")

def buildNamingMap(sequenceInfo):
    strNames, baseNames = {}, {}
    for num, seq in sequenceInfo.seqMap.items():
        sname = re.sub(r'[^A-Za-z0-9]+', '', seq.name).lower()
        bname = re.sub(r'[^A-Za-z0-9]+', '', seq.baseName).lower()
        strNames[sname] = num
        strNames[num] = num
        baseNames[bname] = baseNames.get(bname, [])
        baseNames[bname].append(num)
    return strNames, baseNames


class Sequence:
    
    def __init__(self, **kwargs):
        self.name = None
        self.baseName = None
        self.tagName = None
        self.num = None
        self.length = None
          
        self.attributes =  list(vars(self).keys())
    
        self.binFile = None    
        
        for attr in kwargs:
            vars(self)[attr] = kwargs.get(attr)  
    
    def initFromSourceFile(self, sourceFile, tag):
        #tokens = os.path.basename(sourceFile).split('.')
        self.baseName = os.path.splitext(os.path.basename(sourceFile))[0] #'_'.join(tokens[:-1]) if len(tokens) > 1 else tokens[0]
        self.tagName = tag #re.sub('[^A-Za-z0-9_]+', '_', tag)
        self.name = "{}.{}".format(self.baseName, self.tagName)
        return self
    
    def toJson(self):
        return json.dumps({attr : getattr(self, attr) for attr in self.attributes})
        
    def initFromString(self, string):
        if string is None:
            return
        self.length = len(string)
        directory = os.path.dirname(self.binFile)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(self.binFile, 'wb') as fw:
            b = stringutils.sequenceToBytes(string.upper())
            fw.write(b)
            
    def __len__(self):
        return self.length
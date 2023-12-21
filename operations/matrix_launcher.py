'''
Created on Jul 19, 2022

@author: Vlad
'''


import time
import os
import shutil
from operations import matrix_builder, sketch, matching
from helpers import matrixutils, mputils, metricsutils, clusterutils
from data.config import configs


def buildMatrix(context, ref = None, clean = True):
    matrixInfo = context.matrixInfo
    context.status("Building matrix..")
    configs().log("Matrix parameters: ")
    configs().log("Patches: {}".format(matrixInfo.patches))
    configs().log("Kmers: {}".format(matrixInfo.kmers))
    configs().log("Trim degrees: {}".format(matrixInfo.trimDegrees))
    context.matrixInfo.dir = context.matrixInfo.dir or os.path.join(context.workingDir, "matrix")
    context.matchInfo.dir = context.matchInfo.dir or os.path.join(context.workingDir, "matches") 
    context.matrixInfo.sketchDir = context.matrixInfo.sketchDir or os.path.join(context.workingDir, "kmers")
    
    if ref is not None:
        buildMatrixForReference(context, ref)
    else:
        t1 = time.time() 
        for ref in context.sequenceInfo.refSequences: 
            buildMatrixForReference(context, ref)         
        t2 = time.time()      
        mputils.awaitRun("Matrix timing", configs().metrics, "All matrices finished, took {} min..".format((t2-t1)/60.0), pathSuffix = "timings")
    
    if clean:
        cleanup(matrixInfo)
        
    context.status("Matrix built..")

def buildMatrixForReference(context, ref):
    t1 = time.time()   
    matrixData = MatrixData(context, ref)
    mputils.runWorkers(workGenerator = matrixWorkGenerator(context, matrixData),
                       workTask = (matrixTask, context), 
                       resultProcessor = (matrixResultProcessor, context, matrixData),
                       managedTasks = True)
    matrixData.finalize(context)    
    t2 = time.time()
    mputils.awaitRun("Matrix {} timing".format(ref), configs().metrics, "Matrix {} finished, took {} min..".format(ref, (t2-t1)/60.0), pathSuffix = "timings")

def matrixWorkGenerator(context, matrixData):
    for pair in matrixStrategy(context, matrixData):
        if pair in ("wait", None):
            yield pair
        else:
            i, j, strand, istr, jstr = pair
            i, j = sorted((i,j))
            seq1, seq2 = context.sequenceInfo.seqMap[i], context.sequenceInfo.seqMap[j]
            matId = "Matrix {} {} {}".format(i, j, strand)        
            if (i, j, strand) in matrixData.finishedMatches:
                matrixResultProcessor(context, matrixData, seq1, seq2, strand, istr, jstr, None)
            else:
                yield (matId, seq1, seq2, strand, istr, jstr)   

def matrixTask(context, seq1, seq2, strand, istr, jstr):
    matrix = matrix_builder.buildMatrix(context.matrixInfo, seq1, seq2, strand, istr, jstr)
    matching.buildMatches(context.matchInfo, context.matrixInfo, matrix, seq1, seq2, strand)
    return float(matrix.sum())
    
def matrixResultProcessor(context, matrixData, seq1, seq2, strand, istr, jstr, result):
    i,j = sorted((seq1.num, seq2.num))
    matrixData.similarities[i, j, strand] = result
    matrixData.finishedMatches.add((i, j, strand))
    matrixData.pairsFinished.add((i, j, strand, result))
    
    if (100 * len(matrixData.pairsFinished) // matrixData.pairsLimit) > (100 * (len(matrixData.pairsFinished)-1) // matrixData.pairsLimit):
        context.status("Building matrix..", 100 * len(matrixData.pairsFinished) // matrixData.pairsLimit)  

def matrixStrategy(context, matrixData):  
    if matrixData.pairsLimit >= len(matrixData.seqs) * (len(matrixData.seqs)-1):
        pairsGenerator = pairsGeneratorAll(context, matrixData)  
    else: 
        pairsGenerator = pairsGeneratorNN(context, matrixData)    
    return pairsGenerator
    
def pairsGeneratorAll(context, matrixData):
    pairs = set()
    for n, j in enumerate(matrixData.seqs):
        for i in matrixData.seqs[:n]:
            for strand in (0,1):
                addPair(matrixData, pairs, i, j, strand)
    configs().log("Yielding all {} pairs..".format(len(pairs)))
    yield from batchifyPairs(context, matrixData, pairs)

def pairsGeneratorNN(context, matrixData):
    configs().log("Building NN graph for {}, yielding up to {} pairs..".format(matrixData.ref, matrixData.pairsLimit))  
    pairs = pairsInitial(matrixData)
    configs().log("Yielding initial {} pairs..".format(len(pairs)))
    yield from batchifyPairs(context, matrixData, pairs)  
    if matrixData.pairsLimit > len(pairs):  
        pairs = pairsAdditional(matrixData)
        configs().log("Yielding additional {} pairs..".format(len(pairs)))
        yield from batchifyPairs(context, matrixData, pairs)
    
def pairsInitial(matrixData):
    pairs = set()
    for i in matrixData.seqs:
        addPair(matrixData, pairs, i, matrixData.ref)
    return pairs

def pairsAdditional(matrixData):
    i = matrixData.ref
    nbrs = [(j, strand) for j in matrixData.seqs if j != i for strand in (1,0)]
    nbrs.sort(key= lambda x : matrixData.similarities[min(i,x[0]), max(i,x[0]), x[1]], reverse=True)
    pairs = set()
    for n, p1 in enumerate(nbrs):
        for p2 in nbrs[:n]:
            strand = 1 if p1[1] == p2[1] else 0
            addPair(matrixData, pairs, p1[0], p2[0], strand)
            if len(pairs) + len(matrixData.pairsSubmitted) >= matrixData.pairsLimit:
                return pairs
    return pairs

def addPair(matrixData, pairs, i, j, strand = None):
    if i != j:
        strands = (1, 0) if strand is None else (strand,)
        for strand in strands:
            pair = (min(i, j), max(i, j), strand)
            if pair not in matrixData.pairsSubmitted:
                pairs.add(pair)

def batchifyPairs(context, matrixData, pairs):    
    pairs = sortPairs(pairs)
    configs().log("Batchifying {} pairs..".format(len(pairs)))
    
    batch, nsCounts, newSketches, sk  = [], {}, set(), sketchesMap(pairs)
    for pn, p in enumerate(pairs):
        i, j, strand = p
        istr, jstr = (1,1) if strand == 1 else (1,0) if sk[i,0] <= sk[j,0] else (0,1)
        batch.append((i, j, strand, istr, jstr))
        if not p in matrixData.finishedMatches and not p in context.matrixInfo.existingPairs:
            for k in [(i, istr), (j, jstr)]:
                nsCounts[k] = nsCounts.get(k, 0) + 1
                if nsCounts[k] > 1 or k in matrixData.sketchCache:
                    newSketches.add(k)        
        if len(newSketches) >= context.matrixInfo.sketchLimit or pn == len(pairs) - 1:
            configs().log("Yielding batch {} pairs..".format(len(batch)))
            yield from releaseBatch(context, matrixData, batch, newSketches)
            batch, newSketches = [], set() 

def releaseBatch(context, matrixData, batch, newSketches):
    matrixData.pairsSubmitted.update((i, j, strand) for i, j, strand, istr, jstr in batch)
    time1 = time.time()
    batch = sortBatch(batch)
    cacheSketches(context, matrixData, newSketches)
    yield from batch
    while len(matrixData.pairsFinished) < len(matrixData.pairsSubmitted):
        yield "wait"  
    time2 = time.time()
    configs().debug("Batch {} took {} sec..".format(MatrixData.batchNum, time2 - time1))
    MatrixData.batchNum = MatrixData.batchNum + 1

def sketchesMap(pairs):
    sk = {}
    for i, j, strand in pairs:
        for k in ((i, strand), (j,strand)):
            sk[k] = sk.get(k, 0) + 1
    return sk

def sortPairs(pairs):
    sk = sketchesMap(pairs)
    ms = {(i,j,strand) : (sk[i, strand] + sk[j, strand], i, j) for i,j,strand in pairs}
    sp = sorted(pairs, key = lambda x : ms[x], reverse = True )
    return sp

def sortBatch(pairs):
    sk = {}
    for i, j, strand, istr, jstr in pairs:
        sk[i, istr] = sk.get((i, istr), 0) + 1
        sk[j, jstr] = sk.get((j, jstr), 0) + 1
    ms = {(i,j,strand,istr,jstr) : max((sk[i,istr], i, istr), (sk[j,jstr], j, jstr)) for i,j,strand,istr,jstr in pairs}
    sp = sorted(pairs, key = lambda x : ms[x], reverse = True )
    return sp

def cacheSketches(context, matrixData, newSketches):  
    extras = matrixData.sketchCache.difference(newSketches)
    while len(extras) + len(newSketches) > context.matrixInfo.sketchLimit and len(extras) > 0:
        uncacheSketch(context.matrixInfo, matrixData, extras.pop())
    
    sbatch = set(x for x in newSketches if x not in matrixData.sketchCache)
    matrixData.sketchNum = matrixData.sketchNum + len(sbatch)
    configs().debug("Caching {} sketches..".format(len(sbatch)))
    matrixData.sketchCache.update(sbatch)
    sketch.buildSketches(context.matrixInfo, context.sequenceInfo, sbatch, "Batch {}".format(MatrixData.batchNum))
    configs().debug("Cached {} sketches..".format(matrixData.sketchNum))

def uncacheSketch(matrixInfo, matrixData, sketch):
    matrixData.sketchCache.discard(sketch)
    dr = os.path.join(matrixInfo.sketchDir, "{}_{}".format(*sketch))
    shutil.rmtree(dr, ignore_errors = True)
    
def cleanup(matrixInfo):
    if not matrixInfo.keepKmers:
        shutil.rmtree(matrixInfo.sketchDir, ignore_errors = True)
    
        

class MatrixData:
    
    batchNum = 1
    
    def __init__(self, context, ref):
        matrixInfo = context.matrixInfo
        n = len(context.sequenceInfo.seqMap)
        self.ref = ref
        self.seqs = sorted(context.sequenceInfo.seqMap)
        self.pairsLimit = int( max(2*(n-1), min(n*(n-1), matrixInfo.edgeLimit)) if matrixInfo.edgeLimit != -1 else n*(n-1) )
        
        self.similarities = {}
        self.finishedMatches = set()
        
        self.pairsSubmitted = set()
        self.pairsFinished = set()
        self.sketchCache = set()
        self.sketchNum = 0       
        
        self.initialize(context)
    
    def initialize(self, context):
        context.matrixInfo.curRef = self.ref
        matchdb = clusterutils.getClusterDbPath(context.matchInfo.dir, self.ref)
        #matrixutils.cleanMatrixDb(context.matrixInfo.dir)
        mputils.awaitRun("Initializing matrices {}".format(self.ref), matrixutils.consolidateMatrixDb, context.matrixInfo.dir)
        mputils.awaitRun("Initializing matches {}".format(self.ref), clusterutils.consolidateClusterDb, matchdb)
        
        context.matrixInfo.existingPairs = matrixutils.getMatrixManifest(context.matrixInfo.dir)
        configs().log("Detected {} existing matrix pairs in database..".format(len(context.matrixInfo.existingPairs)))
        self.finishedMatches = clusterutils.getClusterKeys(matchdb)
        configs().log("Detected {} existing match pairs in database..".format(len(self.finishedMatches)))

    def finalize(self, context):
        matchdb = clusterutils.getClusterDbPath(context.matchInfo.dir, self.ref)
        mputils.awaitRun("Finalizing matrices {}".format(self.ref), matrixutils.consolidateMatrixDb, context.matrixInfo.dir)
        mputils.awaitRun("Finalizing matches {}".format(self.ref), clusterutils.consolidateClusterDb, matchdb)
        

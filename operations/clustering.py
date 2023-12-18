'''
Created on Apr 4, 2022

@author: Vlad
'''

import math
import time
import os
import heapq
from helpers.intervalutils import *
from helpers import clusterutils, mputils, matrixutils, metricsutils
from data.config import configs


def selectEdgeMatches(context, refSeqs):
    matches = {}
    similarities = matrixutils.readSequenceSimilaritiesFromFile(context.matrixInfo.dir)
    for refSeq in refSeqs:
        rp = refPairs(context, refSeq, similarities)
        fn = lambda c : (c[0][2], c[1][2], c[1][3]) in rp
        clusters = clusterutils.readFilterMatchesFromDb(context.matchInfo.dir, fn)
        matches.update(clusters)
    return matches

def refPairs(context, refSeq, similarities):
    i = refSeq
    nbrs = [(j, strand) for j in context.sequenceInfo.seqMap for strand in (1,0) if (min(i,j), max(i,j), strand) in similarities]
    nbrs.sort(key= lambda x : similarities[min(i,x[0]), max(i,x[0]), x[1]], reverse=True)
    pairs = set( (min(i,j), max(i,j), strand) for j, strand in nbrs) 
    
    if context.matrixInfo.edgeLimit > 0:
        for n, p1 in enumerate(nbrs):
            for p2 in nbrs[:n]:
                strand = 1 if p1[1] == p2[1] else 0
                pair = (min(p1[0], p2[0]), max(p1[0], p2[0]), strand)
                if pair in similarities:
                    pairs.add(pair)
                    if len(pairs) >= context.matrixInfo.edgeLimit:
                        return pairs
    return pairs

def generateClusters(context, clusterData, matches):
    yield from absorbMatches(context, clusterData, matches)
    yield from mergeClusters(context, clusterData)

def absorbMatches(context, clusterData, matches): 
    configs().log("Generating clusters from {} matches..".format(len(matches)))
    matches.sort(key = lambda x : sum(getIntervalLength(i) for i in x))
    matches = matches[-clusterData.maxClustersHeld:]
    configs().log("Keeping largest {} matches..".format(len(matches)))
    
    for c, cluster in enumerate(matches):
        addCluster(clusterData, c, cluster)
        checkCluster(context, clusterData, c, cluster)
        if c in clusterData.finishedClusters:
            yield clusterData.finishedClusters[c]
        else:
            clusterData.activationHeap.append(c)   
    configs().log("Added {} matches..".format(len(matches)))

def mergeClusters(context, clusterData):
    yield from eatHeap(context, clusterData)
        
    clusters = {c : mergeIntervals(sortIntervals(clusterData.clusters[c])) for c in clusterData.refClusters} 
    keys = sorted(clusters, key = lambda x : -max((getIntervalLength(i) for i in clusters[x] if i[2] in clusterData.refSeqs), default = 0))
    additional = [clusters[c] for c in keys if c not in clusterData.finishedClusters]
    configs().log("Yielded {} finished clusters, adding {} additional clusters.. ".format(len(clusterData.finishedClusters), len(additional)))
    yield from additional

def cleanHeap(clusterData):
    clusterData.heap = [(-clusterData.shares[h], h) for h in clusterData.shares]
    heapq.heapify(clusterData.heap)
    
def eatHeap(context, clusterData):
    while not clusterData.windDown and len(clusterData.heap) + len(clusterData.activationHeap) > 0: 
        promoteClusters(clusterData)
        if len(clusterData.heap) > 0:
            val, pair = heapq.heappop(clusterData.heap)
            a, b, strand = pair
            for c1, c2 in [(a, b), (b, a)]:
                if c1 in clusterData.refClusters and c2 in clusterData.clusters:
                    joinClusters(context, clusterData, c1, c2, strand)
                    if c1 in clusterData.finishedClusters:
                        yield clusterData.finishedClusters[c1]
                    if len(clusterData.heap) > 10 * len(clusterData.shares):
                        cleanHeap(clusterData)   
                    break
  
def promoteClusters(clusterData):
    while len(clusterData.activationHeap) > 0 and len(clusterData.shares) < 1000000:
        c = clusterData.activationHeap.pop()
        if c in clusterData.clusters:
            activateCluster(clusterData, c)

def addCluster(clusterData, c, cluster):
    if c not in clusterData.clusters:
        clusterData.clusters[c] = cluster
        clusterData.shareMap[c] = set()
        for i in cluster:
            if clusterData.policy in (None, "slow", "all") or i[2] in clusterData.refSeqs:
                clusterData.refClusters[c] = max(clusterData.refClusters.get(c, 0), getIntervalLength(i))
        
def removeCluster(clusterData, c):
    if c in clusterData.clusters:        
        if c in clusterData.activeClusters:
            if c in clusterData.refClusters:
                removeClusterFromMappings(clusterData, c, clusterData.refIntervalMap, clusterData.refPatchMap)
            else:
                removeClusterFromMappings(clusterData, c, clusterData.intervalMap, clusterData.patchMap)
    
        removeFromShares(clusterData, c)
        clusterData.activeClusters.discard(c)
        clusterData.clusters.pop(c)
        clusterData.refClusters.pop(c, None)

def checkCluster(context, clusterData, c, cluster):       
    mc = mergeIntervals(sortIntervals(cluster))
    if (mc[:,1] - mc[:,0] + 1).max() * len(mc) >= context.clusterInfo.parameter:    
        clusterData.finishedClusters[c] = mc
        removeCluster(clusterData, c)     
 
def activateCluster(clusterData, c):
    if c not in clusterData.activeClusters:
        clusterData.activeClusters.add(c)
        buildClusterShares(clusterData, c, clusterData.refIntervalMap, clusterData.refPatchMap)
        if c in clusterData.refClusters:
            buildClusterShares(clusterData, c, clusterData.intervalMap, clusterData.patchMap)
            addClusterToMappings(clusterData, c, clusterData.refIntervalMap, clusterData.refPatchMap)
        else:
            addClusterToMappings(clusterData, c, clusterData.intervalMap, clusterData.patchMap)

def joinClusters(context, clusterData, c1, c2, strand):
    if c2 not in clusterData.refClusters:
        buildClusterShares(clusterData, c2, clusterData.intervalMap, clusterData.patchMap)
        removeClusterFromMappings(clusterData, c2, clusterData.intervalMap, clusterData.patchMap)
        addClusterToMappings(clusterData, c2, clusterData.refIntervalMap, clusterData.refPatchMap)
    
    clusters = clusterData.clusters
    for i in clusters[c2]:
        clusterData.refIntervalMap[tuple(i[:3])].discard((c2, i[3]))
        clusterData.refIntervalMap[tuple(i[:3])].add((c1, i[3] if strand == 1 else 1-i[3]))
    if strand == 0:
        clusters[c2][:,3] = 1 - clusters[c2][:,3]
    clusters[c1] = np.vstack([clusters[c1], clusters[c2]])
    clusterData.refClusters[c1] = max(clusterData.refClusters[c1], clusterData.refClusters.get(c2, 0)) 
    checkCluster(context, clusterData, c1, clusters[c1])
    
    if c1 in clusters:
        for nbr, nstr in clusterData.shareMap[c2]:  
            if nbr != c1:
                newstr = nstr if strand == 1 else 1 - nstr
                addShare(clusterData, c1, nbr, newstr, clusterData.shares[(min(c2, nbr), max(c2, nbr), nstr)])    
    removeFromShares(clusterData, c2)
    clusters.pop(c2)
    clusterData.refClusters.pop(c2, None)
    clusterData.activeClusters.discard(c2)
    
    if len(clusterData.clusters) % 100000 == 0:
        logStatus(clusterData)

def buildClusterShares(clusterData, c, imap, patchMap):
    if len(imap) == 0:
        return 
    
    for i in clusterData.clusters[c]:
        p2 = findPowerofTwo(getIntervalLength(i))
        for level in range(p2-1, p2+2):
        #for level in patchMap:
            for p in subintervals((i[0]-1, i[1]+1, i[2]), 2 ** level):
                for i2 in patchMap.get(level,{}).get(p, []):
                    over = getIntervalOverlap(i, i2)
                    if over >= max(clusterData.minOverlap, 0.5 * getIntervalLength(i), 0.5 * getIntervalLength(i2)):
                        for c2, cs2 in imap[i2]:
                            if c2 != c and c2 in clusterData.clusters:
                                strand = 1 if i[3] == cs2 else 0
                                addShare(clusterData, c, c2, strand, over)            
                                
def addShare(clusterData, c1, c2, strand, value):
    c1, c2 = sorted((c1, c2))
    clusterData.shares[c1,c2,strand] = clusterData.shares.get((c1,c2,strand), 0) + value
    clusterData.shareMap[c1].add((c2, strand))
    clusterData.shareMap[c2].add((c1, strand))
    
    if c1 in clusterData.activeClusters and c2 in clusterData.activeClusters:
        heapq.heappush(clusterData.heap, (-clusterData.shares[c1,c2,strand], (c1, c2, strand)) )
        #heapq.heappush(clusterData.heap, ((-clusterData.shares[c1,c2,strand], -val), (c1, c2, strand)) )
        
def removeFromShares(clusterData, c):
    for nbr, nstr in clusterData.shareMap[c]:
        clusterData.shares.pop( (min(c, nbr), max(c, nbr), nstr) )        
        clusterData.shareMap[nbr].discard((c, 0))
        clusterData.shareMap[nbr].discard((c, 1))     
    clusterData.shareMap.pop(c) 

def addClusterToMappings(clusterData, c, imap, patchMap):
    for i in clusterData.clusters[c]:
        ci = tuple(i[:3])   
        p2 = findPowerofTwo(getIntervalLength(i))
        #cp = getIntervalCenter(i, clusterData.patchSize)
        cp = getIntervalCenter(i, 2 ** p2)
        
        patchMap[p2] = patchMap.get(p2, {})
        patchMap[p2][cp] = patchMap[p2].get(cp, set())
        patchMap[p2][cp].add(ci)       
        imap[ci] = imap.get(ci, set())
        imap[ci].add((c, i[3]))
    
def removeClusterFromMappings(clusterData, c, imap, patchMap):
    for i in clusterData.clusters[c]:
        ci = tuple(i[:3])
        if ci in imap:
            imap[ci].discard((c, i[3]))
            if len(imap[ci]) == 0:
                imap.pop(ci)        
                  
                p2 = findPowerofTwo(getIntervalLength(i))  
                #cp = getIntervalCenter(i, clusterData.patchSize)
                cp = getIntervalCenter(i, 2 ** p2)    
                patchMap[p2][cp].discard(ci)
                if len(patchMap[p2][cp]) == 0:
                    patchMap[p2].pop(cp)        
                
def getIntervalCenter(i, ps):
    lb = int(i[0] + getIntervalLength(i) * 0.5)
    return patch(lb, ps, i[2])

def patch(i, ps, s):
    a = (i//ps) * ps
    return (a,  a+ps-1, s)

def subintervals(interval, ps):
    return ( (p, p+ps-1, interval[2]) for p in range((interval[0] // ps) * ps, interval[1] + 1, ps) )

def findPowerofTwo(n): 
    return int(math.log(max(n,1), 2))

def findAllMatchesForSequencePair(matchInfo, s1, s2, strand):
    matches = []
    allmatches = clusterutils.readMatchesFromDb(matchInfo.dir, s1, s2, strand)
    configs().debug("Loaded {} matches for {}".format(len(allmatches), (s1, s2, strand)))
    for m11, m12, m21, m22 in allmatches:
        matches.append(np.array([(m11, m12, s1, 1), (m21, m22, s2, strand)]))
    return matches

def logStatus(clusterData):
    configs().log("Holding {} clusters, {} ref, {} on deck, {} heap, {} shares, {} finished..".format(
        len(clusterData.clusters), len(clusterData.refClusters), len(clusterData.activeClusters), 
        len(clusterData.heap), len(clusterData.shares), len(clusterData.finishedClusters)))
    

class ClusterData:
    
    def __init__(self, context):
        self.alignLimit = 1 * context.localAlignInfo.limit #1000000
        self.maxClustersHeld = context.clusterInfo.climit
        self.minOverlap = context.matrixInfo.patches[-1] * 3
        self.patchSize = context.matrixInfo.patches[-1]
        self.windDown = False
        self.policy = context.clusterInfo.policy
                
        self.refSeqs = set(context.sequenceInfo.refSequences) if context.sequenceInfo.refSequences is not None else context.sequenceInfo.seqMap
        #self.refSeqs = context.sequenceInfo.seqMap
        self.curId = 0  
        
        self.clusters = {}
        self.refClusters = {}
        self.finishedClusters = {}
        self.activeClusters = set()
        self.activationHeap = []
         
        self.patchMap = {}
        self.intervalMap = {}
        self.refPatchMap = {}
        self.refIntervalMap = {}
        
        self.heap = []
        self.shareMap = {}
        self.shares = {}
            
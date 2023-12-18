'''
Created on Mar 9, 2023

@author: Vlad
'''

import os
import math
import numpy as np
from helpers import matrixutils, intervalutils, buscoutils, clusterutils, mputils
from scipy.sparse import *
from data.config import configs

def buildClusterSizes(context):
    clusters = clusterutils.readClustersFromDb(context.clusterInfo.dir, context.sequenceInfo.sequences).values()
    csizes = [sum(intervalutils.getIntervalLength(i) for i in x) for x in clusters]
    csizes = sorted(csizes, reverse = True)
    return csizes

def buildMatrixPatchCoverages(context, matrixInfo, refSeqs = None):
    refSeqs = refSeqs or context.sequenceInfo.refSequences
    for rnum in refSeqs:
        refSeq = context.sequenceInfo.seqMap[rnum]
        
        coverages = []
        for s in context.sequenceInfo.seqMap:
            if s == refSeq.num:
                continue
            matrices = []
            i, j = sorted((s, refSeq.num))
            for strand in (0,1):
                matPath = os.path.join(matrixInfo.dir, "{}_{}_{}.npz".format(i, j, strand))
                matrices.append(load_npz(matPath).tocoo() if os.path.exists(matPath) else None)
            coverage = computeMatrixPatchCoverage(i, j, refSeq, matrices)
            coverages.append((coverage, s))
                
        coverages.sort(reverse=True)
        configs().metrics("Matrices against {}".format(refSeq.name), pathSuffix = "coverage")
        for coverage, s in coverages:
            configs().metrics("Matrix Coverage: {}    {}    {}".format(coverage, context.sequenceInfo.seqMap[s].name, refSeq.name), pathSuffix = "coverage")
        configs().metrics("", pathSuffix = "coverage")
        
def computeMatrixPatchCoverage(s1, s2, refSeq, matrices):
    patchSet = set()
    denom = 1
    for strand, matrix in enumerate(matrices):
        if matrix is None:
            continue
        denom = (matrix.shape[0] if s1 == refSeq.num else matrix.shape[1])
        matrix = matrixutils.enrichMatrix3(matrix, strand)
        patchSet.update(i if s1 == refSeq.num else j for i,j in matrix.keys())
    coverage = len(patchSet) / denom
    return coverage

def buildMatchesPatchCoverages(context, refSeqs = None):
    refSeqs = refSeqs or context.sequenceInfo.refSequences
    for rnum in refSeqs:
        refSeq = context.sequenceInfo.seqMap[rnum]   
        clusters = {}     
        for s in context.sequenceInfo.seqMap:
            if s == refSeq.num:
                continue
            for strand in (1,0):                
                i, j = sorted((s, refSeq.num))
                matches = clusterutils.readMatchesFromDb(context.matchInfo.dir, i, j, strand)
                if matches is not None:
                    for m11, m12, m21, m22 in matches:
                        clusters[len(clusters)] = [(m11, m12, i, 1), (m21, m22, j, strand)] 
    
        coverage = computeClusterPatchCoverage(clusters, refSeq, context.matrixInfo.patchSize)
        
        coverages = [(c, s) for s, c in coverage.items()]    
        coverages.sort(reverse=True)
        configs().metrics("Matches: {}".format(len(clusters)), pathSuffix = "coverage")
        for coverage, s in coverages:
            configs().metrics("Matches Coverage: {}    {}    {}".format(coverage, context.sequenceInfo.seqMap[s].name, refSeq.name), pathSuffix = "coverage")
        configs().metrics("", pathSuffix = "coverage")
            
def buildClustersPatchCoverages(context, clusters = None, refSeqs = None):
    clusters = clusters or clusterutils.readClustersFromDb(context.clusterInfo.dir, context.sequenceInfo.sequences)
    refSeqs = refSeqs or context.sequenceInfo.refSequences
    for rnum in refSeqs:
        refSeq = context.sequenceInfo.seqMap[rnum]
        coverage = computeClusterPatchCoverage(clusters, refSeq, context.matrixInfo.patchSize)
        
        coverages = [(c, s) for s, c in coverage.items()]    
        coverages.sort(reverse=True)
        configs().metrics("Clusters: {}".format(len(clusters)), pathSuffix = "coverage")
        for coverage, s in coverages:
            configs().metrics("Clusters Coverage: {}    {}    {}".format(coverage, context.sequenceInfo.seqMap[s].name, refSeq.name), pathSuffix = "coverage")
        configs().metrics("", pathSuffix = "coverage")

def computeClusterPatchCoverage(clusters, refSeq, patchSize):
    if clusters is None:
        return 0
    
    patchSets = {}
    for c, cluster in clusters.items():
        cseqs = set(s for i1, i2, s, strand in cluster if s != refSeq.num)
        for i1, i2, s, strand in cluster:
            if s == refSeq.num:
                for patch in range(i1 // patchSize, i2 // patchSize + 1):
                    for seq in cseqs:
                        patchSets[seq] = patchSets.get(seq, set())
                        patchSets[seq].add(patch)
    
    coverage = {s : len(cset) / math.ceil(len(refSeq) / patchSize) for s, cset in patchSets.items()}
    return coverage
    
    
def buildMatchingBuscoScores(context, matchDirs):
    clusters = []
    for mdir in matchDirs:
        seqs = sorted(context.sequenceInfo.sequences, key = lambda x : x.num)
        for i in range(len(seqs)-1):
            for j in range(i+1, len(seqs)):
                for strand in (1,0):
                    matches = clusterutils.readMatchesFromDb(mdir, seqs[i].num, seqs[j].num, strand)
                    if matches is not None:
                        for m11, m12, m21, m22 in matches:
                            clusters.append( [(m11, m12, seqs[i].name, 1), (m21, m22, seqs[j].name, strand)] )
    #clusters = ([(i[0], i[1], context.sequenceInfo.seqMap[i[2]].name, i[3]) for i in cluster] for cluster in clusters)
    infos = buscoutils.checkBuscoClusters(configs().buscoDir, iter(clusters))
    info = [context.matchInfo.dir, context.matchInfo.minWidth, context.matchInfo.rule, *infos]
    configs().metrics(" ".join(str(x) for x in info), pathSuffix = "busco_scores")

def buildClusteringDirBuscoScores(context, clusterDirs):
    clusters = {}
    for cdir in clusterDirs:
        clusters.update(clusterutils.readClustersFromDb(cdir, context.sequenceInfo.sequences))
    buildClustersBuscoScores(context, clusters)    
    
def buildClustersBuscoScores(context, clusters):
    clusters = ([(i[0], i[1], context.sequenceInfo.seqMap[i[2]].name, i[3]) for i in cluster] for cluster in clusters.values())
    infos = buscoutils.checkBuscoClusters(configs().buscoDir, clusters)
    info = [context.clusterInfo.strategy, context.clusterInfo.criterion, context.clusterInfo.parameter, *infos]
    configs().metrics(" ".join(str(x) for x in info), pathSuffix = "busco_scores")

def buildMatrixBuscoScores(context):
    seqs = sorted(context.sequenceInfo.sequences, key = lambda x : x.num)
    works = [(seqs[i], seqs[j], strand) for strand in (1, 0) for i in range(len(seqs)-1) for j in range(i+1, len(seqs))]
    infos = []
    mputils.runWorkers(workGenerator = iter(works), 
                       workTask = (buildMatrixInfoSparse, context), 
                       resultProcessor = (matrixBuscoProcessor, infos) )

    infos = np.array(infos, dtype = np.float32)
    infos = np.sum(infos, axis = 0)
    infos[0] = infos[0] / max(1, infos[2])
    infos[1] = infos[1] / max(1, infos[2])  
    #infos[3] = infos[3] / max(1, infos[4])  
    infos = infos[:3]
    #return infos
    info = [context.matrixInfo.dir, *infos]
    configs().metrics(" ".join(str(x) for x in info), pathSuffix = "busco_scores")
    

def matrixBuscoProcessor(infos, seq1, seq2, strand, result):
    print(result)
    if len(result) > 0:
        infos.append(result)

def buildMatrixInfoSparse(context, seq1, seq2, strand):
    matPath = matrixutils.getMatrixPath(context.matrixInfo.dir, seq1.num, seq2.num, strand)
    if not os.path.exists(matPath):
        matrix = None
        return []
    else:
        matrix = load_npz(matPath).todok()
    
    infos = buscoutils.checkBuscoMatrix(configs().buscoDir, matrix, strand, seq1.name, seq2.name, context.matrixInfo.patchSize) 
    return infos



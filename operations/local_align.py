'''
Created on Apr 8, 2022

@author: Vlad
'''

import os
import time
import heapq
from helpers import sequenceutils, stringutils, clusterutils, metricsutils, mputils
from helpers.intervalutils import getIntervalLength
from tools import external_tools
from data.config import configs


def selectClustersForAlignment(context, refs):
    if context.localAlignInfo.factor is not None:
        numgroups = len(set(context.seqGroup(s) for s in context.sequenceInfo.seqMap))
        context.localAlignInfo.depth = context.localAlignInfo.factor * numgroups
        configs().log("Align factor {}, groups {}, depth {}..".format(context.localAlignInfo.factor, numgroups, context.localAlignInfo.depth))
    context.localAlignInfo.depth = context.localAlignInfo.depth or min(100, len(context.sequenceInfo.seqMap))
    
    buckets = {}
    rset = set(refs)
    refGroups = set(context.seqGroup(ref) for ref in refs)
    for ref in refs:
        rc = clusterutils.readClustersFromDb(clusterutils.getClusterDbPath(context.matchInfo.dir, ref))
        for c in rc:
            if any(context.seqGroup(i[2]) not in refGroups for i in c):
                b = max(getIntervalLength(i) for i in c if i[2] in rset) // 100
                buckets[b] = buckets.get(b, [])
                buckets[b].append(c)
        configs().log("Found {} clusters for {}..".format(len(rc), ref))

    bs = sorted(buckets, reverse = True)
    lensum = sum(len(context.sequenceInfo.seqMap[ref]) for ref in refs)
    total, limit = 0, context.localAlignInfo.depth * lensum
    
    result = {}  
    done = False
    configs().log("Drawing clusters for depth {}, limit {}..".format(context.localAlignInfo.depth, limit))
    for b in bs:
        if done:
            break
        bclusters = sorted(buckets[b], key = lambda x : (-max(getIntervalLength(i) for i in x if i[2] in rset), clusterutils.clusterKey(x)))
        for c in bclusters:    
            result[clusterutils.clusterKey(c)] = c
            total = total + sum(getIntervalLength(i) for i in c if i[2] in rset)
            if total >= limit or len(result) >= context.localAlignInfo.limit:
                done = True
                break
        configs().log("Bucket {}: {} clusters, {} results..".format(b, len(bclusters), len(result)))
        
    configs().log("Using {} selected clusters..".format(len(result)))
    return result

def runAlignments(context, clusters, name):
    mputils.awaitRun("Starting alignments {}".format(name), clusterutils.consolidateAlignDb, context.localAlignInfo.dir)
    alignedClusters = clusterutils.getAlignedClusters(context.localAlignInfo.dir)
    unaligned = [c for c in clusters if c not in alignedClusters]
    configs().log("Aligning {} clusters, of which {} are unaligned..".format(len(clusters), len(unaligned)))
    
    context.localAlignInfo.clustersFinished = 0
    mputils.runWorkers(workGenerator = ((c, c, clusters[c]) for c in unaligned),
                       workTask = (runClusterAlignment, context), 
                       resultProcessor = (resultProcessor, context, len(unaligned)),
                       managedTasks = True)
    
    mputils.awaitRun("Finalizing alignments {}".format(name), clusterutils.consolidateAlignDb, context.localAlignInfo.dir)
    #clusterutils.consolidateAlignDb(context.localAlignInfo.dir)
    context.localAlignInfo.manifest = clusterutils.getAlignedClustersManifest(context.localAlignInfo.dir)
    configs().log("Found {} clusters in the alignment manifest..".format(len(clusters)))

def alignClusterGenerator(context, generator):
    alignedClusters = clusterutils.getAlignedClusters(context.localAlignInfo.dir)
    for c, cluster in generator:
        if c in alignedClusters:
            context.localAlignInfo.clustersFinished = context.localAlignInfo.clustersFinished + 1
        else:
            yield c, c, cluster

def resultProcessor(context, total, *results):
    context.localAlignInfo.clustersFinished = context.localAlignInfo.clustersFinished + 1
    fin = context.localAlignInfo.clustersFinished
    if total is not None and 100 * fin // total > 100 * (fin - 1) // total:
        context.status("Running cluster alignments..", 100 * fin // total)
    
def runClusterAlignment(context, c, cluster, writeToFinalDb = False): 
    outputPath = clusterutils.getAlignPath(context.localAlignInfo.dir, c)
    unalignedPath = os.path.join(os.path.dirname(outputPath), "unaligned_{}".format(os.path.basename(outputPath)))
    if not isNonEmptyFile(unalignedPath):
        writeUnalignedCluster(context.sequenceInfo, unalignedPath, cluster)
        configs().debug("Prepared unaligned file {}: {} / {}".format(os.path.basename(unalignedPath), tuple(getIntervalLength(x) for x in cluster), len(cluster)))
    alignDir = os.path.dirname(unalignedPath)
    
    tries = 3
    for i in range(tries):
        if os.path.exists(outputPath):
            os.remove(outputPath)
        try:
            external_tools.runMafftFast(unalignedPath, alignDir, outputPath, min(configs().threads, 8))
            if not isNonEmptyFile(outputPath):
                raise Exception("MAFFT output {} not found or is empty..".format(outputPath))
            break
        except Exception as exc:
            configs().log("Task for MAFFT {} threw an exception:\n{}".format(outputPath, exc))
            if i < tries - 1:
                configs().log("Retrying.. {}/{}".format(i+2, tries))
            else:
                raise
    
    clusterutils.writeAlignToDb(context.localAlignInfo.dir, c, outputPath, writeToFinalDb)
    os.remove(unalignedPath)
    os.remove(outputPath)

def writeUnalignedCluster(seqInfo, unalignedPath, cluster):
    unalignment = {} 
    for i1, i2, s, strand in cluster:
        seq = seqInfo.seqMap[s]
        tag = "{}_{}_{}_{}".format(seq.name, i1, i2, strand)
        with open(os.path.join(seq.binFile), 'rb') as file:
            file.seek(i1)
            buffer = file.read(i2-i1+1)    
        if strand != 1:
            buffer = stringutils.bytesReverseComplement(buffer)
        seqPortion = stringutils.bytesToSequence(buffer)
        unalignment[tag] = sequenceutils.Sequence(tag, seqPortion)          

    os.makedirs(os.path.dirname(unalignedPath), exist_ok=True)
    sequenceutils.writeFasta(unalignment, unalignedPath)    
    return unalignedPath

def isNonEmptyFile(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


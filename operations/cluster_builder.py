'''
Created on Jul 27, 2023

@author: Vlad
'''

import time
import os
import heapq
from operations import local_align, clustering, matrix_launcher
from helpers import mputils, metricsutils, clusterutils, intervalutils
from data.config import configs


def buildClusters(context):
    context.clusterInfo.dir = context.clusterInfo.dir or os.path.join(context.workingDir, "clusters")
    context.localAlignInfo.dir = context.localAlignInfo.dir or os.path.join(context.workingDir, "local_align")
    context.matrixInfo.dir = context.matrixInfo.dir or os.path.join(context.workingDir, "matrix")
    context.matchInfo.dir = context.matchInfo.dir or os.path.join(context.workingDir, "matches") 
    
    matrix_launcher.buildMatrix(context)
    
    if context.clusterInfo.parameter > 1:
        context.status("Building clusters..")
        t1 = time.time() 
        runClusterBuilder(context)
        t2 = time.time()
        mputils.awaitRun("Cluster builder timing", configs().metrics, "Clusters finished, took {} min..".format((t2-t1)/60.0), pathSuffix = "timings")
        context.status("Clusters built..")

def runClusterBuilder(context):
    mgr = mputils.WorkerManager(workGenerator = None,
                       workTask = (local_align.runClusterAlignment, context), 
                       resultProcessor = (local_align.resultProcessor, context, None),
                       managedTasks = True)
    context.localAlignInfo.clustersFinished = 0
    mgr.workGenerator = local_align.alignClusterGenerator(context, newClusterGenerator(context, mgr))
    mgr.run()
    
def newClusterGenerator(context, manager):
    for refSeq in context.sequenceInfo.refSequences: 
        dbPath = os.path.join(context.clusterInfo.dir, "clusters_{}.db".format(refSeq))
        if os.path.exists(dbPath) and not context.clusterInfo.update:
            configs().log("Existing clusters for {} detected, update flag not set. Using existing clusters..".format(refSeq))
            continue
        configs().log("No existing clusters for {} detected, or the update flag has been set. Generating new clusters..".format(refSeq))        
        matches = clustering.selectEdgeMatches(context, [refSeq])
        yield from generateClusters(context, manager, refSeq, matches)
            
def generateClusters(context, manager, refSeq, matches):
    clusterData = clustering.ClusterData(context)
    clusters = {}
    maxHeap = []
    waitHeap = []

    for cluster in clustering.generateClusters(context, clusterData, matches):
        if not any(i[2] == refSeq for i in cluster):
            continue
        
        cluster = [tuple(i) for i in cluster]
        val = abs(hash(tuple(cluster)))
        while str(val) in clusters:
            val = val + 1
        c = str(val)
        clusters[c] = cluster
        
        val = max(intervalutils.getIntervalLength(i) for i in cluster if i[2] == refSeq) #* len(cluster)
        if val > 0:
            while len(maxHeap) >= context.localAlignInfo.alignLimit and val >= maxHeap[0][0]:
                heapq.heappop(maxHeap)
            
            if len(maxHeap) < context.localAlignInfo.alignLimit:
                heapq.heappush(maxHeap, (val, c))
                heapq.heappush(waitHeap, (-val, c))
            
            elif not clusterData.windDown:   
                clusterData.windDown = True
                configs().log("Reached {} clusters.. Winding down the cluster generator.".format(len(clusters)))    
        
        while manager.executor.workQueue.qsize() == 0 and len(waitHeap) > 0:
            val, c = heapq.heappop(waitHeap)    
            yield c, clusters[c]    
                    
    configs().log("Ended up with {} clusters..".format(len(clusters)))
    mputils.awaitRun("Saving clusters for {}".format(refSeq), clusterutils.writeRefClustersToDb, context.clusterInfo.dir, clusters, refSeq)

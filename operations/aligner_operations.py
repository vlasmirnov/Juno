'''
Created on May 2, 2022

@author: Vlad
'''

import time
from operations import matrix_launcher, matching, clustering, local_align, maf, cluster_builder
import os
from data.config import configs
from data.context import Context
from helpers import metricsutils, mputils
from scripts import maf_metrics

def cliOperation():
    context = Context(configs().dir)
    context.initFromArgs()
    context.initContext()
    runOperation(context, configs().operation)

def runOperation(context, operation):
    context.status("{} operation started..".format(operation))
    t1 = time.time() 
    
    if operation.lower() == "matrix":
        matrix_launcher.buildMatrix(context)
        
    elif operation.lower() == "maf":
        maf.buildMafFile(context)
    
    elif operation.lower() == "maf_busco":
        psplit = os.path.splitext(configs().metricsPath)
        outPath = "{}_{}{}".format(psplit[0], "busco_scores", psplit[1])
        scores = maf_metrics.buildMafBuscoScores(context.mafInfo.path, configs().buscoDir, outPath)
        #namenums = {s.name.lower() : n for n, s in context.sequenceInfo.seqMap.items()}
        #print([namenums.get(s.lower(), None) for score, overlaps, total, s in scores])
    
    elif operation.lower() == "maf_coverage":
        refName = context.sequenceInfo.seqMap[context.sequenceInfo.refSequences[0]].name
        psplit = os.path.splitext(configs().metricsPath)
        outPath = "{}_{}{}".format(psplit[0], "coverage", psplit[1])
        maf_metrics.buildMafCoverage(context.mafInfo.path, outPath, refName, groupByBaseName = True)
    
    elif operation.lower() == "matrix_busco":
        metricsutils.buildMatrixBuscoScores(context)
    
    elif operation.lower() == "matching_busco":
        context.matchInfo.dir = context.matchInfo.dir or os.path.join(context.matrixInfo.dir, "matches_{}".format(context.matchInfo.rule))
        metricsutils.buildMatchingBuscoScores(context, [context.matchInfo.dir])
    
    elif operation.lower() == "cluster_busco":
        context.clusterInfo.dir = context.clusterInfo.dir or os.path.join(context.dir, "clustering_{}_{}".format(context.clusterInfo.strategy, context.clusterInfo.parameter))
        metricsutils.buildClusteringDirBuscoScores(context, [context.clusterInfo.dir])

    t2 = time.time()
    context.status("{} operation finished, took {} min..".format(operation, (t2-t1)/60.0))
    mputils.awaitRun("{} operation timing".format(operation), 
                     configs().metrics, "{} operation finished, took {} min..".format(operation, (t2-t1)/60.0), pathSuffix = "timings")
    
    #configs().metrics("{} operation finished, took {} min..".format(operation, (t2-t1)/60.0), pathSuffix = "timings")

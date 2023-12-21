'''
Created on May 2, 2022

@author: Vlad
'''

import time
from operations import matrix_launcher, maf
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
    operation = operation or "maf"
    context.status("{} operation started..".format(operation))
    t1 = time.time() 
    
    if operation.lower() == "maf":
        maf.buildMafFile(context)
    
    elif operation.lower() == "matrix":
        matrix_launcher.buildMatrix(context)
    
    elif operation.lower() == "maf_busco":
        psplit = os.path.splitext(configs().metricsPath)
        outPath = "{}_{}{}".format(psplit[0], "busco_scores", psplit[1])
        scores = maf_metrics.buildMafBuscoScores(context.mafInfo.path, configs().buscoDir, outPath)
        #namenums = {s.name.lower() : n for n, s in context.sequenceInfo.seqMap.items()}
        #print([namenums.get(s.lower(), None) for score, overlaps, total, s in scores])
    
    elif operation.lower() == "maf_coverage":
        psplit = os.path.splitext(configs().metricsPath)
        outPath = "{}_{}{}".format(psplit[0], "coverage", psplit[1])
        maf_metrics.buildMafCoverage(context.mafInfo.path, outPath)

    t2 = time.time()
    context.status("{} operation finished, took {} min..".format(operation, (t2-t1)/60.0))
    mputils.awaitRun("{} operation timing".format(operation), 
                     configs().metrics, "{} operation finished, took {} min..".format(operation, (t2-t1)/60.0), pathSuffix = "timings")
    
    #configs().metrics("{} operation finished, took {} min..".format(operation, (t2-t1)/60.0), pathSuffix = "timings")

'''
Created on Mar 30, 2023

@author: Vlad
'''

import os
from helpers import mafutils, buscoutils


def buildMafBuscoScores(mafPath, buscoDir, outputPath):
    files = []
    if os.path.isdir(mafPath):
        for filename in os.listdir(mafPath):
            if filename.endswith(".maf"):
                files.append(os.path.join(mafPath, filename))
    else:
        files.append(mafPath)
    
    scores = []
    for file in files:
        blocks =  mafutils.readMafLetterBlocks(file) 
        scores.extend(buscoutils.checkBuscoLetterBlocks(buscoDir, iter(blocks)))
    
    scores = aggregateScores(scores)  
    scores = [(tp / max(1, total), fp / max(1, np), tp, fp, total, np, s, rs) for rs, s, tp, fp, total, np in scores]  
    scores.sort(reverse=True)
    with open(outputPath, 'a') as outFile:
        outFile.write("Busco scores: {}\n".format(mafPath))
        ttp, tfp, tt, tn = 0, 0, 0, 0
        for tpf, fpf, tp, fp, total, np, s, rs in scores:
            outFile.write("{}    {}    {} / {}    {} / {}    {}    {}\n".format(tpf, fpf, tp, total, fp, np, s, rs))    
            ttp, tfp, tt, tn = ttp + tp, tfp + fp, tt + total, tn + np   
        outFile.write("Sum total: {}    {}    {} / {}    {} / {}\n".format(ttp / max(1, tt), tfp / max(1, tn), ttp, tt, tfp, tn))        
        outFile.write("\n")
    return scores

def buildMafCoverage(mafPath, outputPath):
    files = []
    if os.path.isdir(mafPath):
        for filename in os.listdir(mafPath):
            if filename.endswith(".maf"):
                files.append(os.path.join(mafPath, filename))
    else:
        files.append(mafPath)
    
    scores = []
    for file in files:
        blocks =  mafutils.readMafLetterBlocks(file) 
        scores.extend(buscoutils.checkMafCoverage(iter(blocks)))
    
    scores = aggregateScores(scores)  
    scores = [(c / max(1, rlen), c, rlen, s, rs) for rs, s, c, rlen in scores]  
    scores.sort(reverse=True)
    with open(outputPath, 'a') as outFile:
        outFile.write("MAF Coverage: {}\n".format(mafPath))
        tc, tl = 0, 0
        for fc, c, rlen, s, rs in scores:
            outFile.write("{}    {} / {}    {}    {}\n".format(fc, c, rlen, s, rs))    
            tc, tl = tc + c, tl + rlen  
        outFile.write("Sum total: {}    {} / {}\n".format(tc / max(1, tl), tc, tl))        
        outFile.write("\n")
    return scores
   
        
def aggregateScores(scores):
    agg = {}
    for line in scores:
        rs, s = line[0].split('.')[0], line[1].split('.')[0]
        agg[rs, s] = tuple(x+y for x,y in zip(agg.get((rs,s), [0]*len(line[2:])), line[2:]))
    return [(rs, s, *agg[rs,s]) for (rs, s) in agg]
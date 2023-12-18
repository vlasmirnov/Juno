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
            files.append(os.path.join(mafPath, filename))
    else:
        files.append(mafPath)
    
    scores = []
    for file in files:
        blocks =  mafutils.readMafLetterBlocks(file) 
        scores.extend(buscoutils.checkBuscoLetterBlocks(buscoDir, iter(blocks)))
    
    scores = aggregateBuscoScores(scores)  
    scores = [(tp / max(1, total), fp / max(1, total), tp, fp, total, s, rs) for rs, s, tp, fp, total in scores]  
    scores.sort(reverse=True)
    with open(outputPath, 'a') as outFile:
        outFile.write("Busco scores: {}\n".format(mafPath))
        ttp, tfp, tt = 0, 0, 0
        for tpf, fpf, tp, fp, total, s, rs in scores:
            outFile.write("{}    {}    {} / {}    {} / {}    {}    {}\n".format(tpf, fpf, tp, total, fp, total, s, rs))    
            ttp, tfp, tt = ttp + tp, tfp + fp, tt + total   
        outFile.write("Sum total: {}    {}    {} / {}    {} / {}\n".format(ttp / max(1, tt), tfp / max(1, tt), ttp, tt, tfp, tt))        
        outFile.write("\n")
    return scores

def aggregateBuscoScores(scores):
    agg = {}
    for rs, s, tp, fp, total in scores:
        rs, s = rs.split('.')[0], s.split('.')[0]
        agg[rs, s] = tuple(x+y for x,y in zip(agg.get((rs,s), (0,0,0)), (tp, fp, total)))
    return [(rs, s, *agg[rs,s]) for (rs, s) in agg]
        

def buildMafBuscoScores2(mafPath, buscoDir, outputPath, refName = None):
    clusters = mafutils.getMafClusters(mafPath)
    #refSeq = refSeq or context.sequenceInfo.seqMap[context.sequenceInfo.refSequences[0]]
    numClusters, scores = buscoutils.checkBuscoClustersRefSeq(buscoDir, iter(clusters), refName)    
    scores = [(overlaps / max(1, total), overlaps, total, s) for s, overlaps, total in scores]    
    scores.sort(reverse=True)

    with open(outputPath, 'a') as outFile:
        outFile.write("Busco scores: {}\n".format(mafPath))
        outFile.write("Total blocks: {}\n".format(numClusters))
        for score, overlaps, total, s in scores:
            outFile.write("{}    {} / {}    {}    {}\n".format(score, overlaps, total, s, refName))            
        outFile.write("\n")
    
def buildMafCoverage(mafPath, outputPath, refName = None, groupByBaseName = False):
    coverage = {}
    curL = 0
    for block in mafutils.readMafLetterBlocks(mafPath):
        rseq, rltrs, rlen, rc1, rc2, rstrand = block[0]
        #assert rseq.lower() == refName.lower()
        idxs = [n for n,c in enumerate(rltrs) if c not in ("-", "_")]
        blockCovers = {}
        for qseq, qltrs, qlen, qc1, qc2, qstrand in block[1:]:
            skey = qseq.split('.')[0] if groupByBaseName else qseq
            blockCovers[skey] = blockCovers.get(skey, set())
            blockCovers[skey].update(n for n in idxs if qltrs[n] not in ("-", "_"))
        for s, sltrs in blockCovers.items():
            coverage[s] = coverage.get(s, 0) + len(sltrs)
            
        curL = curL + len(idxs)
        if 100 * curL // rlen > 100 * (curL - len(idxs)) // rlen:
            print("{}%..".format(100 * curL // rlen))
    
    coverages = [(c / rlen, s) for s, c in coverage.items()]    
    coverages.sort(reverse=True)
    
    with open(outputPath, 'a') as outFile:
        outFile.write("MAF file: {}\n".format(mafPath))
        for coverage, s in coverages:
            outFile.write("MAF Coverage: {}    {}    {}\n".format(coverage, s, refName))
        outFile.write("\n")
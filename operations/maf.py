'''
Created on Dec 19, 2022

@author: Vlad
'''

import math
import time
import os
import numpy as np
from helpers import clusterutils, sequenceutils, intervalutils, stringutils, mputils, metricsutils
from data.config import configs
from operations import local_align, cluster_builder, matrix_launcher

def buildMafFile(context):
    #cluster_builder.buildClusters(context)
    context.localAlignInfo.dir = context.localAlignInfo.dir or os.path.join(context.workingDir, "local_align")
    context.matrixInfo.dir = context.matrixInfo.dir or os.path.join(context.workingDir, "matrix")
    context.matchInfo.dir = context.matchInfo.dir or os.path.join(context.workingDir, "matches") 
    context.matrixInfo.sketchDir = context.matrixInfo.sketchDir or os.path.join(context.workingDir, "kmers")
    context.mafInfo.dir = context.mafInfo.dir or os.path.join(context.dir, "maf")
    
    for rname in context.sequenceInfo.ref:
        if context.mafInfo.singleFile:
            baseName = "maf_{}_{}.maf".format(rname, int(context.localAlignInfo.factor or context.localAlignInfo.depth))
            mafPath = os.path.join(context.mafInfo.dir, baseName)
            if not os.path.exists(mafPath):
                rfiles = buildMafForReferences(context, rname)
                names = ", ".join([context.sequenceInfo.seqMap[s].name for s in context.sequenceInfo.refMap[rname]])
                mputils.awaitRun(mafPath, writeMafFileFromChunks, mafPath, rfiles, names, False)
        else:
            buildMafForReferences(context, rname)
        
    context.status("All MAF files finished..")
    matrix_launcher.cleanup(context.matrixInfo)

def buildMafForReferences(context, rname):
    t1 = time.time()     
    rfiles = []
    for ref in context.sequenceInfo.refMap[rname]:
        fname = context.sequenceInfo.seqMap[ref].name
        baseName = "maf_{}_{}.maf".format(fname, int(context.localAlignInfo.factor or context.localAlignInfo.depth))
        file = os.path.join(context.mafInfo.dir, baseName)
        rfiles.append(file)
        if not os.path.exists(file):
            buildMaf(context, ref, file)
    
    t2 = time.time()
    mputils.awaitRun("MAF files for {} timing".format(rname), 
                     configs().metrics, "MAF files for {} finished, took {} min..".format(rname, (t2-t1)/60.0), pathSuffix = "timings")
    return rfiles   

def buildMaf(context, ref, file):
    matrix_launcher.buildMatrix(context, ref, clean = False)
    clusters = getMafAlignments(context, ref)
    
    t1 = time.time()
    context.status("Building MAF file {} for reference {}..".format(file, ref))
    context.mafInfo.mapPatchSize = context.matrixInfo.patches[-1] #4096 #256 #1024 #16384  
    blocks = buildIntervalBlocks(context, clusters, context.mafInfo.mapPatchSize, [ref])
    configs().log("{} interval blocks built..".format(len(blocks)))
    blocks = consolidateIntervalBlocks(blocks)
    configs().log("Consolidated into {} interval blocks..".format(len(blocks)))
    header = None if context.mafInfo.singleFile else context.sequenceInfo.seqMap[ref].name
    buildMafFromBlocks(context, clusters, blocks, file, header)
    t2 = time.time()
    mputils.awaitRun("{} timing".format(file), 
                     configs().metrics, "{} finished, took {} min..".format(file, (t2-t1)/60.0), pathSuffix = "timings")
    
def getMafAlignments(context, ref):
    t1 = time.time() 
    context.status("Running alignments for {}..".format(ref))
    clusters = local_align.selectClustersForAlignment(context, [ref])
    #clusters = {c : clusters[c] for c in list(clusters)[:200000]}
    local_align.runAlignments(context, clusters, ref)
    t2 = time.time()
    mputils.awaitRun("Alignments for {} timing".format(ref), 
                     configs().metrics, "Alignments for {} finished, took {} min..".format(ref, (t2-t1)/60.0), pathSuffix = "timings")
    return clusters

def buildMafFromBlocks(context, clusters, iblocks, mafPath, refName): 
    context.mafInfo.chunksFinished = 0   
    sortedIntervals = sorted(iblocks)  
    chunkFiles = [mafPath[:-4] + "_chunk{}{}".format(t, mafPath[-4:]) for t in range(min(1000, max(1, len(sortedIntervals))))] 
    os.makedirs(context.mafInfo.dir, exist_ok=True)  
    
    mputils.runWorkers(workGenerator = mafWorkGenerator(sortedIntervals, iblocks, chunkFiles),
                       workTask = (buildMafFileChunk, context, clusters), 
                       resultProcessor = (mafResultProcessor, context, len(chunkFiles)),
                       managedTasks = True)
    
    mputils.awaitRun(mafPath, writeMafFileFromChunks, mafPath, chunkFiles, refName)

def mafWorkGenerator(sortedIntervals, iblocks, chunkFiles):
    chunkSize = math.ceil(len(sortedIntervals) / len(chunkFiles)) 
    for t, chunkFile in enumerate(chunkFiles):
        iclusters = [(interval, iblocks[interval]) for interval in sortedIntervals[t*chunkSize : (t+1)*chunkSize]]
        yield (chunkFile, chunkFile, iclusters)     

def mafResultProcessor(context, total, *results):
    context.mafInfo.chunksFinished = context.mafInfo.chunksFinished + 1
    #if (100 * context.mafInfo.chunksFinished // total) > (100 * (context.mafInfo.chunksFinished-1) // total):
    if (100 * context.mafInfo.chunksFinished / total) % 10 == 0:
        configs().log("Building MAF chunks.. {}%".format(100 * context.mafInfo.chunksFinished // total))

def buildMafFileChunk(context, clusters, outputPath, iclusters):
    chunkLines = []
    alignCache = {}
    kcounts = {}
    
    for interval, iblock in iclusters:
        ks = set(k for k, ri, qi in iblock)
        for k in ks:
            kcounts[k] = kcounts.get(k, 0) + 1
    
    for interval, iblock in iclusters:  
        if context.mafInfo.refGaps:
            blocks = buildBlockWithGaps(context, alignCache, clusters, interval, iblock)
        else:
            blocks = buildBlock(context, alignCache, clusters, interval, iblock)
            
        for refInterval, block in blocks:
            block = list(block.items())
            block.sort(key=lambda b : (b[0] != refInterval, b[0][2], b[0][0], b[0][1]))
            chunkLines.append("a\n")
            for interval, ltrs in block:
                seq = context.sequenceInfo.seqMap[interval[2]]
                strand = '+' if interval[3] == 1 else '-'
                line = "s {} {} {} {} {} {}\n".format(seq.name.lower(), interval[0], interval[1]-interval[0]+1, strand, len(seq), ltrs)
                chunkLines.append(line)
            chunkLines.append("\n")
        
        ks = set(k for k, ri, qi in iblock)
        for k in ks:
            kcounts[k] = kcounts[k] - 1
            if kcounts[k] == 0:
                alignCache.pop(k, None)
    
    chunkLines = ''.join(chunkLines)
    with mputils.sharedRcs().rwLock:
        with open(outputPath, 'w') as outFile:
            outFile.write(chunkLines)

def buildBlock(context, alignCache, clusters, si, iblock):
    ris = set((k, ri) for k, ri, qi in iblock)
    matchColsDict = {(k, ri) : getMatchColsFromCache(context, clusters, alignCache, k, ri, si) for k, ri in ris}
    matchSlices = [(0,-1)] if context.mafInfo.refGaps else getMatchSlices(list(matchColsDict.values()))
    blocks = []    
    
    for matchSlice in matchSlices:
        block = {} 
        sliceInterval = None
        for k, ri, qi in iblock:                
            strand = ri[3]
            matchCols = matchColsDict[k, ri]
            
            seqkey = checkInvertInterval(context.sequenceInfo, qi, strand)
            seqstr = getAlignSeqStrFromCache(context, clusters, alignCache, k, qi, strand)      
            ltrCounts = getLtrCountsFromCache(context, clusters, alignCache, k, qi, strand)
            c1 = int(ltrCounts[matchCols[matchSlice[0]]])
            c2 = int(ltrCounts[matchCols[matchSlice[-1]]+1])
            
            if c2 > c1:
                if qi[2] == ri[2] and qi != ri:
                    continue
                ltrs = seqstr[matchCols[matchSlice[0]] : matchCols[matchSlice[-1]]+1]
                key = (seqkey[0]+c1, seqkey[0]+c2-1, seqkey[2], seqkey[3])
                block[key] = ''.join(ltrs) 
                sliceInterval = key if qi == ri else sliceInterval     
        
        s1 = block[sliceInterval]
        if len(block) > 1 and len(s1) >= 1 and sequenceutils.checkHasACGT(s1):
            blocks.append((sliceInterval, block))   
        
    return blocks  

def buildBlockWithGaps(context, alignCache, clusters, si, iblock):
    ris = set((k, ri) for k, ri, qi in iblock)
    matchColsDict = {(k, ri) : getMatchColsFromCache(context, clusters, alignCache, k, ri, si) for k, ri in ris}
    gaps = getMatchGaps(list(matchColsDict.values()))
    
    blocks = []    
    block = {} 
    
    sliceInterval = None
    for k, ri, qi in iblock:                
        strand = ri[3]
        matchCols = matchColsDict[k, ri]
        
        seqkey = checkInvertInterval(context.sequenceInfo, qi, strand)
        seqstr = getAlignSeqStrFromCache(context, clusters, alignCache, k, qi, strand)      
        ltrCounts = getLtrCountsFromCache(context, clusters, alignCache, k, qi, strand)
        c1 = int(ltrCounts[matchCols[0]])
        c2 = int(ltrCounts[matchCols[-1]+1])
        
        if c2 > c1:
            if qi[2] == ri[2] and qi != ri:
                continue
            ltrs = []
            for n in range(len(matchCols)-1):
                g = gaps[n]
                ltrs.extend(seqstr[matchCols[n] : matchCols[n+1]])
                ltrs.extend(['-'] * (gaps[n] - (matchCols[n+1] - matchCols[n] - 1)))
            ltrs.append(seqstr[matchCols[-1]])
            
            key = (seqkey[0]+c1, seqkey[0]+c2-1, seqkey[2], seqkey[3])
            block[key] = ''.join(ltrs) 
            sliceInterval = key if qi == ri else sliceInterval     
    
    s1 = block[sliceInterval]
    if len(block) > 1 and len(s1) >= 1 and sequenceutils.checkHasACGT(s1):
        blocks.append((sliceInterval, block))   
        
    return blocks 

def buildIntervalBlocks(context, clusters, ps, refs):
    rMap, qMap = {}, {}
    context.mafInfo.distFinished = 0
    refGroups = set(context.seqGroup(ref) for ref in refs)
    mputils.runWorkers(workGenerator = ((c,) for c in clusters), 
                       workTask = (buildDists, context, clusters, ps, refGroups), 
                       resultProcessor = (distProcessor, context, clusters, ps, rMap, qMap),
                       managedTasks = False)
    
    policy = context.mafInfo.policy or ""
    if policy.lower() in ( "", "unidirectional", "ubh"):
        iblocks = {si : set(v[0] for v in rMap[si].values()) for si in rMap}
        for pi in qMap:
            for val in qMap[pi]:
                k, ri, qi, si = val[0]
                iblocks[si].add((k, ri, qi))        
    elif policy.lower() in ("reciprocal", "bidirectional", "rbh", "bbh"):
        rbests = set((*v[0], si) for si in rMap for v in rMap[si].values())
        iblocks = {}
        for pi in qMap:
            for val in qMap[pi]:
                if val[0] in rbests:
                    k, ri, qi, si = val[0]
                    iblocks[si] = iblocks.get(si, set())
                    iblocks[si].add((k, ri, qi))
    elif policy.lower() in ("ref", "refbest"):
        iblocks = {si : set(v[0] for v in rMap[si].values()) for si in rMap}
    
        
    for iset in iblocks.values():
        k, ri, qi = next(iter(iset))
        iset.add((k, ri, ri))
    
    return iblocks

def consolidateIntervalBlocks(iblocks):
    sortedIntervals = sorted(iblocks)
    curi, curb = None, None
    result = {}
    for i in sortedIntervals:
        block = iblocks[i]      
        if block == curb:
            curi = (curi[0], i[1], i[2])
        else:
            if curi is not None:
                result[curi] = curb
            curi, curb = i, iblocks[i]
    if curi is not None:
        result[curi] = curb
            
    return result

def buildDists(context, clusters, ps, refGroups, k):
    ris = [i for i in clusters[k] if context.seqGroup(i[2]) in refGroups]
    qis = [i for i in clusters[k] if context.seqGroup(i[2]) not in refGroups] 
    
    alignCache = {}
    results = {}
    
    for ri in ris:
        for qi in qis:            
            ltrCounts = getLtrCountsFromCache(context, clusters, alignCache, k, qi, ri[3])
            dist = getAlignIntervalDist(context, clusters, alignCache, k, ri, qi, ri)
            for si in subintervals(ri, ps):
                matchCols = getMatchColsFromCache(context, clusters, alignCache, k, ri, si)
                c1 = int(ltrCounts[matchCols[0]])
                c2 = int(ltrCounts[matchCols[-1]+1])
                seqkey = checkInvertInterval(context.sequenceInfo, qi, ri[3])
                proj = (seqkey[0]+c1, seqkey[0]+c2-1, seqkey[2], seqkey[3])
                proj = checkInvertInterval(context.sequenceInfo, proj, 1) 
                #dist = getAlignIntervalDist(context, clusters, alignCache, k, ri, qi, si)
                
                if dist <= context.mafInfo.maxDistance:
                    results[si] = results.get(si, {})
                    results[si][ri, qi] = (proj, dist)    
        
    return processDistResults(context, results, ps, k)
    #return results

def distProcessor(context, clusters, ps, rMap, qMap, k, results):
    nrMap, nqMap = results
    
    for si in nrMap:
        rMap[si] = rMap.get(si, {})
        for group in nrMap[si]:
            if group not in rMap[si] or nrMap[si][group][1] < rMap[si][group][1]:
                rMap[si][group] = nrMap[si][group]
    
    nqset = set(x for vals in nqMap.values() for x in vals)
    for x, dist, proj in nqset:
        qset = set(x2 for pi in subintervals(proj, ps) for x2 in qMap.get(pi, []))
        good = True
        for x2, dist2, proj2 in qset:
            if intervalutils.getIntervalOverlap(proj, proj2) > 0:
                if dist2 < dist:
                    good = False
                    break
                elif dist < dist2:
                    for pi in subintervals(proj2, ps):
                        qMap[pi].remove((x2, dist2, proj2))
        if good:
            for pi in subintervals(proj, ps):
                qMap[pi] = qMap.get(pi, set())
                qMap[pi].add( (x, dist, proj) )

    context.mafInfo.distFinished = context.mafInfo.distFinished + 1
    if (100 * context.mafInfo.distFinished // len(clusters)) > (100 * (context.mafInfo.distFinished-1) // len(clusters)):
        configs().log("Building min distance map.. {}%".format(100 * context.mafInfo.distFinished // len(clusters))) 

def processDistResults(context, results, ps, k):
    rMap, qMap = {}, {}
    for si in results:
        rMap[si] = rMap.get(si, {})
        
        for ri, qi in results[si]:
            proj, dist = results[si][ri, qi]
            group = context.seqGroup(qi[2])
            if group not in rMap[si] or dist < rMap[si][group][1]:
                rMap[si][group] = ((k, ri, qi), dist)
            
            qset = set(x for pi in subintervals(proj, ps) for x in qMap.get(pi, []))
            good = True
            for x, dist2, proj2 in qset:
                if intervalutils.getIntervalOverlap(proj, proj2) > 0:
                    if dist2 < dist:
                        good = False
                        break
                    elif dist < dist2:
                        for pi in subintervals(proj2, ps):
                            qMap[pi].remove((x, dist2, proj2))
            if good:
                for pi in subintervals(proj, ps):
                    qMap[pi] = qMap.get(pi, set())
                    qMap[pi].add( ((k, ri, qi, si), dist, proj) )
    return rMap, qMap

def retrieveAlign(context, clusters, k):
    try:
        align = clusterutils.readAlignFromDb(context.localAlignInfo.dir, context.localAlignInfo.manifest, k)
        assert len(align) > 0
        allength = len(next(iter(align.values())).seq)
        assert all(len(s.seq) == allength for s in align.values())
    except:
        local_align.runClusterAlignment(context, k, clusters[k], writeToFinalDb = True)
        context.localAlignInfo.manifest = clusterutils.getAlignedClustersManifest(context.localAlignInfo.dir)
        align = clusterutils.readAlignFromDb(context.localAlignInfo.dir, context.localAlignInfo.manifest, k)
    return align

def getAlignMatrixFromCache(context, clusters, alignCache, k):
    if k not in alignCache:
        alignCache[k] = {"matrix" : buildAlignMatrix(context, clusters, k)}
    alignCache[k]["used"] = 0
    return alignCache[k]["matrix"]

def getMatchColsFromCache(context, clusters, alignCache, k, interval, subInterval):
    if ("matchcols", interval) not in alignCache.get(k, {}):
        tagMap, matrix = getAlignMatrixFromCache(context, clusters, alignCache, k)
        alignCache[k]["matchcols", interval] = getMatrixMatchCols(tagMap, matrix, interval, interval[3])
    alignCache[k]["used"] = 0
    return alignCache[k]["matchcols", interval][max(0, subInterval[0]-interval[0]) : subInterval[1]-interval[0]+1]

def getLtrCountsFromCache(context, clusters, alignCache, k, interval, strand):         
    if ("ltrcounts", interval) not in alignCache.get(k, {}):
        tagMap, matrix = getAlignMatrixFromCache(context, clusters, alignCache, k)
        alignCache[k]["ltrcounts", interval] = getMatrixLtrCounts(tagMap, matrix, interval, 1)
    ltrCounts = alignCache[k]["ltrcounts", interval]
    if strand == 0:
        ltrCounts = np.flip(ltrCounts[-1] - ltrCounts)
    alignCache[k]["used"] = 0
    return ltrCounts

def getAlignSeqStrFromCache(context, clusters, alignCache, k, ri, strand):
    tagMap, matrix = getAlignMatrixFromCache(context, clusters, alignCache, k)
    b = matrix[tagMap[ri]].copy()
    b[b == 0] = ord('-')
    if strand == 0:
        b = stringutils.bufferReverseComplement(b)
    alignCache[k]["used"] = 0
    return bytes(b).decode('utf-8')
        
def getAlignDistFromCache(context, clusters, alignCache, k, ri, qi):
    if ("dist", ri, qi) not in alignCache.get(k, {}):
        tagMap, matrix = getAlignMatrixFromCache(context, clusters, alignCache, k)
        alignCache[k]["dist", ri, qi] = getAlignMatrixDist(tagMap, matrix, ri, qi)
    alignCache[k]["used"] = 0
    return alignCache[k]["dist", ri, qi]      

def buildAlignMatrix(context, clusters, k):
    align = retrieveAlign(context, clusters, k)
    mat = np.ndarray((len(align), len(next(iter(align.values())).seq)), dtype = np.uint8)
    for n, interval in enumerate(clusters[k]):
        tag = "{}_{}_{}_{}".format(context.sequenceInfo.seqMap[interval[2]].name, interval[0], interval[1], interval[3])
        mat[n] = np.frombuffer(bytes(align[tag].seq, "utf-8"), dtype = np.uint8)
    mat[mat == ord('-')] = 0
    return {interval : n for n, interval in enumerate(clusters[k])}, mat

def getAlignMatrixDist(tagMap, matrix, ri, qi):
    rrow, qrow = matrix[tagMap[ri]], matrix[tagMap[qi]]
    return np.count_nonzero(rrow - qrow) / np.count_nonzero(rrow + qrow)

def getAlignIntervalDist(context, clusters, alignCache, k, ri, qi, si):
    tagMap, matrix = getAlignMatrixFromCache(context, clusters, alignCache, k)
    mc = getMatchColsFromCache(context, clusters, alignCache, k, ri, si)
    rrow = matrix[tagMap[ri]] if ri[3] == 1 else matrix[tagMap[ri]][::-1]
    qrow = matrix[tagMap[qi]] if ri[3] == 1 else matrix[tagMap[qi]][::-1]
    rrow = rrow[mc[0] : mc[-1]+1]
    qrow = qrow[mc[0] : mc[-1]+1]
    return np.count_nonzero(rrow - qrow) / max(1, np.count_nonzero(rrow + qrow))

def getMatrixMatchCols(tagMap, matrix, ri, strand):
    if strand == 1:
        return np.nonzero(matrix[tagMap[ri]])[0]
    else: 
        return np.nonzero(matrix[tagMap[ri]][::-1])[0]

def getMatrixLtrCounts(tagMap, matrix, ri, strand):
    row = matrix[tagMap[ri]] if strand == 1 else matrix[tagMap[ri]][::-1]
    ltrCounts = np.zeros(len(row)+1)#, dtype = np.uint64)
    ltrCounts[1:] = np.cumsum(row != 0)#, dtype = np.uint64)
    return ltrCounts
    
def checkInvertInterval(seqInfo, interval, strand):
    s = seqInfo.seqMap[interval[2]]
    if strand == interval[3]:
        return (interval[0], interval[1], interval[2], 1) 
    else:
        return (len(s)-1-interval[1], len(s)-1-interval[0], interval[2], 0) 

def getMatchSlices(matchColsList):
    matchSlices = []
    matches = len(matchColsList[0]) if len(matchColsList) > 0 else 0       
    n1 = 0
    for n2 in range(matches):
        if n2 == matches - 1 or max(matchCols[n2+1] - matchCols[n2] - 1 for matchCols in matchColsList) > 0:
            matchSlices.append( list(range(n1, n2 + 1)) )
            n1 = n2 + 1   
    return matchSlices

def getMatchGaps(matchColsList):
    matches = len(matchColsList[0]) if len(matchColsList) > 0 else 0       
    matchSlices = [ max(matchCols[n2+1] - matchCols[n2] - 1 for matchCols in matchColsList) for n2 in range(matches-1)]
    matchSlices.append(0)
    return matchSlices

def subintervals(interval, ps):
    return ( (p, p+ps-1, interval[2]) for p in range((interval[0] // ps) * ps, interval[1] + 1, ps) )

def writeMafFileFromChunks(mafPath, chunkFiles, ref = None, deleteChunks = True):
    with open(mafPath, 'w') as outFile:
        if ref is not None:
            outFile.write("##maf version=1\n")
            outFile.write("# Reference: {}\n".format(ref))
            outFile.write("\n")
        
        for chunkFile in chunkFiles:
            if os.path.exists(chunkFile):
                with open(chunkFile, 'r') as cFile:
                    outFile.write(cFile.read())
                if deleteChunks:
                    os.remove(chunkFile)

    
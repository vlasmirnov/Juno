'''
Created on Apr 4, 2022

@author: Vlad
'''

import itertools
import os
#from helpers.intervalutils import *
from helpers import clusterutils, intervalutils, sequenceutils

    
def checkBuscoClusters(buscoDir, clusters):
    print("Checking busco clusters..")
    buscoClusters = readBuscoFiles(buscoDir)
    print("Found {} busco clusters..".format(len(buscoClusters)))
    
    cmap = sequenceutils.SequenceNameDict()
    cmapPath = os.path.join(buscoDir, "chrom_mapping.txt")
    if os.path.exists(cmapPath):
        cmap.readChromMapping(cmapPath)
    else:
        for cluster in buscoClusters.values():
            for i in cluster:
                cmap.add(i[2])
    print(cmap)
    buscoClusters = {b : [(i[0], i[1], cmap[i[2]], i[3]) for i in cluster if i[2] in cmap] for b, cluster in buscoClusters.items()}
    buscoIntervalClusters = clusterutils.buildIntervalMap(buscoClusters)
    
    crosspairs = [set(), set()]
    overpairs = [set(), set()]
    crossgroups = set()
    overgroups = set()
    seqs = set()
    
    sliceSize = 100000
    totalClusters = 0
    while True:
        clusterSlice = list(itertools.islice(clusters, 0, sliceSize))
        if len(clusterSlice) == 0:
            break
        print("Next chunk of {} clusters..".format(len(clusterSlice)))
        totalClusters = totalClusters + len(clusterSlice)
        clusterSlice = {m : [(i[0], i[1], cmap[i[2]], i[3]) for i in cluster if i[2] in cmap] for m, cluster in enumerate(clusterSlice)}
        intervalClusters = clusterutils.buildIntervalMap(clusterSlice)
        seqs.update(i[2] for i in intervalClusters)
        overlaps = intervalutils.buildIntervalSetOverlaps(buscoIntervalClusters, intervalClusters)
        
        crossMap = {i : set() for i in buscoIntervalClusters}
        overMap = {i : set() for i in buscoIntervalClusters}
        for i1 in buscoIntervalClusters:
            bs = buscoIntervalClusters[i1][0][1]
            for i2 in overlaps[i1]:
                for c, cs in intervalClusters.get(i2, []):
                    ms = 1 if cs == bs else 0
                    crossMap[i1].add((c, ms))
                    if i2[0] <= i1[0] and i2[1] >= i1[1]:
                        overMap[i1].add((c, ms))
        
        for c, cluster in buscoClusters.items():
            crossSet, overSet = set(), set()
            for i in range(len(cluster)):
                i1 = (cluster[i][0], cluster[i][1], cluster[i][2])
                crossSet = crossMap[i1] if i == 0 else crossSet.intersection(crossMap[i1])
                overSet = overMap[i1] if i == 0 else overSet.intersection(overMap[i1])
                for j in range(i+1, len(cluster)):
                    i2 = (cluster[j][0], cluster[j][1], cluster[j][2])
                    pstrand = 1 if cluster[i][3] == cluster[j][3] else 0
                    if any(e in crossMap[i2] for e in crossMap[i1]):
                        crosspairs[pstrand].add((c, i, j))
                    if any(e in overMap[i2] for e in overMap[i1]):
                        overpairs[pstrand].add((c, i, j))
            if len(crossSet) > 0:
                crossgroups.add(c)
            if len(overSet) > 0:
                overgroups.add(c)
    
    totalgroups = len(buscoClusters)
    #totalpairs = sum(len(cluster) * (len(cluster) - 1) / 2 for cluster in buscoClusters.values())
    totalpairs = sum(1 for c in buscoClusters.values() for i in range(len(c)) for j in range(i+1, len(c)) if c[i][2] in seqs and c[j][2] in seqs)
    print("Found {} total clusters..".format(totalClusters))
    print("Found {} / {} crossing pairs total..".format(len(crosspairs[0]) + len(crosspairs[1]), totalpairs))
    print("Found {} / {} over pairs total..".format(len(overpairs[0]) + len(overpairs[1]), totalpairs))
    print("Found {} / {} crossing groups..".format(len(crossgroups), totalgroups))
    print("Found {} / {} over groups..".format(len(overgroups), totalgroups))
    return totalClusters, (len(crosspairs[0]) + len(crosspairs[1]))/totalpairs, (len(overpairs[0]) + len(overpairs[1]))/totalpairs, totalpairs, \
        len(crossgroups)/totalgroups, len(overgroups)/totalgroups, totalgroups



def checkBuscoClustersRefSeq(buscoDir, clusters, refName):
    buscoClusters = readBuscoFiles(buscoDir)
    print("Found {} busco clusters..".format(len(buscoClusters)))
    
    cmap = sequenceutils.SequenceNameDict()
    cmapPath = os.path.join(buscoDir, "chrom_mapping.txt")
    if os.path.exists(cmapPath):
        cmap.readChromMapping(cmapPath)
    else:
        for cluster in buscoClusters.values():
            for i in cluster:
                cmap.add(i[2])
    refName = cmap.get(refName, refName.lower())
    print(cmap)
    
    buscoClusters = {b : [(i[0], i[1], cmap[i[2]], i[3]) for i in cluster if i[2] in cmap] for b, cluster in buscoClusters.items()}
    buscoClusters = {b : cluster for b, cluster in buscoClusters.items() if any(i[2] == refName for i in cluster)}
    print("Found {} busco clusters against ref sequence..".format(len(buscoClusters)))
    
    buscoIntervalClusters = clusterutils.buildIntervalMap(buscoClusters)
    refIntervals = [i for i in buscoIntervalClusters if i[2] == refName]
    refIntervals.sort()
    nextRI = 0
    
    seqOverlaps, seqTotals = {}, {} # = {s.num : set() for s in sequences}
    
    buscoSeqIntervals = {b : {} for b in buscoClusters}
    for b, cluster in buscoClusters.items():
        for i in cluster:
            buscoSeqIntervals[b][i[2]] = buscoSeqIntervals[b].get(i[2], [])
            buscoSeqIntervals[b][i[2]].append(i)
            seqOverlaps[i[2]] = seqOverlaps.get(i[2], set())
            seqTotals[i[2]] = seqTotals.get(i[2], set())
            seqTotals[i[2]].add(b)
    
    for cn, cluster in enumerate(clusters):
        if cn % 100000 == 0 and cn > 0:
            print("Checked {} clusters..".format(cn))
        i1, i2, s, rstrand = cluster[0]
        s = cmap.get(s, s.lower())
        assert s == refName
        
        bClusters = []
        while nextRI < len(refIntervals) and refIntervals[nextRI][1] < i1:
            nextRI = nextRI + 1
        curRI = nextRI
        while curRI < len(refIntervals) and i2 >= refIntervals[curRI][0]:
            bClusters.extend(buscoIntervalClusters[refIntervals[curRI]])
            curRI = curRI + 1
        if len(bClusters) == 0:
            continue
        
        for i in cluster:
            i1, i2, s, strand = i
            s = cmap.get(s, s.lower())
            if s == refName:
                continue
            for b, bstr in bClusters:
                for bi in buscoSeqIntervals[b].get(s, []):
                    if (bstr == bi[3]) == (rstrand == strand):
                        if i[0] <= bi[1] and bi[0] <= i[1]:
                            seqOverlaps[s].add(b)
    
    scores = [(s, len(seqOverlaps[s]), len(seqTotals[s])) for s in seqOverlaps]
    print("Found {} total clusters..".format(cn+1))
    return cn+1, scores

def checkBuscoMatrix(buscoDir, matrix, strand, s1name, s2name, patchSize):
    #seq1, seq2 = context.sequenceInfo.seqMap[s1], context.sequenceInfo.seqMap[s2]
    #matrix = matrixutils.enrichMatrix3(matrix, strand)
    print("Checking busco clusters..")
    buscoClusters = readBuscoFiles(buscoDir)
    print("Found {} busco clusters..".format(len(buscoClusters)))
    cmap = sequenceutils.SequenceNameDict()
    cmapPath = os.path.join(buscoDir, "chrom_mapping.txt")
    if os.path.exists(cmapPath):
        cmap.readChromMapping(cmapPath)
    else:
        for cluster in buscoClusters.values():
            for i in cluster:
                cmap.add(i[2])
    #print(cmap)
    buscoClusters = {b : [(i[0], i[1], cmap[i[2]], i[3]) for i in cluster if i[2] in cmap] for b, cluster in buscoClusters.items()}
    s1name = cmap.get(s1name, s1name.lower())
    s2name = cmap.get(s2name, s2name.lower())
    
    totalpairs = 0
    clusteringpairs = 0    
    coveringpairs = 0    
    coverage = matrix.nnz * patchSize * patchSize
    for b, cluster in buscoClusters.items():
        b1 = [i for i in cluster if i[2] == s1name and (i[2], i[3]) != (s2name, 0)]
        b2 = [i for i in cluster if i[2] == s2name and (i[2], i[3]) != (s1name, 1)]
        
        for start1, end1, name1, strand1,  in b1:
            for start2, end2, name2, strand2,  in b2:
                #if strand != 1:
                #    start2, end2 = (len(seq2)-1-end2, len(seq2)-1-start2)
            
                if (strand == 1) != (strand1 == strand2):
                    continue     
            
                totalpairs = totalpairs + 1
                clusterFound = False
                coverFound = True
                for i1 in range(start1 // patchSize, end1 // patchSize + 1):
                    patchMatchFound = False
                    for i2 in range(start2 // patchSize, end2 // patchSize + 1):
                        if matrix[i1, i2] > 0:
                            patchMatchFound = True
                            break
                    coverFound = coverFound and patchMatchFound
                    clusterFound = clusterFound or patchMatchFound
                
                if clusterFound:
                    clusteringpairs = clusteringpairs + 1
                if coverFound:
                    coveringpairs = coveringpairs + 1
                
    print("Found {} / {} clustering pairs..".format(clusteringpairs, totalpairs))
    print("Found {} / {} covering pairs..".format(coveringpairs, totalpairs))
    return clusteringpairs, coveringpairs, totalpairs, coverage

def checkBuscoLetterBlocks(buscoDir, blocks):
    buscoClusters = readBuscoFiles(buscoDir)
    print("Found {} busco clusters..".format(len(buscoClusters)))
    cmap = readCmap(buscoDir, buscoClusters)
    rs = None
    ltrBuscoMap = None
    tp, fp, np = {}, {}, {}
        
    for block in blocks:
        rseq, rltrs, rlen, rc1, rc2, rstrand = block[0]
        rseq = cmap[rseq]
        
        if ltrBuscoMap is None:
            rs = rseq
            buscoClusters = {b : cluster for b, cluster in buscoClusters.items() if any(i[2] == rs for i in cluster)}
            print("Found {} busco clusters against ref sequence..".format(len(buscoClusters)))
            ltrBuscoMap = {}
            for b, cluster in buscoClusters.items():
                for i in cluster:
                    ltrBuscoMap[i[2]] = ltrBuscoMap.get(i[2], {})
                    for l in range(i[0], i[1]+1): 
                        ltrBuscoMap[i[2]][l] = (b, i[3])
            tp = {s : set() for s in ltrBuscoMap if s != rs}
            fp = {s : 0 for s in ltrBuscoMap if s != rs}
            np = {s : 0 for s in ltrBuscoMap if s != rs}
        
        idxs = [n for n,c in enumerate(rltrs) if c not in ("-", "_")]
        idxs = {n : rc1+x if rstrand == 1 else rc2-x for x,n in enumerate(idxs)}
        bidxs = set(n for n in idxs if idxs[n] in ltrBuscoMap.get(rseq, {}))
        if len(bidxs) == 0:
            continue
        #print(idxs)
        for qseq, qltrs, qlen, qc1, qc2, qstrand in block[1:]:
            if qseq not in cmap:
                continue      
            qseq = cmap[qseq]      
            qidxs = [n for n,c in enumerate(qltrs) if c not in ("-", "_")]
            qidxs = {n : qc1+x if qstrand == 1 else qc2-x for x,n in enumerate(qidxs)}
            bqidxs = set(n for n in qidxs if qidxs[n] in ltrBuscoMap.get(qseq, {}))
            for n in bqidxs:
                if n in idxs:
                    np[qseq] = np[qseq] + 1
                    fp[qseq] = fp[qseq] + 1
                    if n in bidxs and qidxs[n] not in tp[qseq]:
                        rb, rstr = ltrBuscoMap[rseq][idxs[n]]
                        qb, qstr = ltrBuscoMap[qseq][qidxs[n]]
                        if rb == qb and (rstr == qstr) == (rstrand == qstrand):
                            tp[qseq].add(qidxs[n])
                            fp[qseq] = fp[qseq] - 1
    
    tp = {s : len(tp[s]) for s in tp}   
    scores = [(rs, s, tp[s], fp[s], len(ltrBuscoMap[s]), np[s]) for s in tp]
    return scores

def checkMafCoverage(blocks):
    coverage = {}
    curL = 0
    for block in blocks:
        rseq, rltrs, rlen, rc1, rc2, rstrand = block[0]
        idxs = [n for n,c in enumerate(rltrs) if c not in ("-", "_")]
        blockCovers = {}
        for qseq, qltrs, qlen, qc1, qc2, qstrand in block[1:]:
            skey = qseq.split('.')[0]
            blockCovers[skey] = blockCovers.get(skey, set())
            blockCovers[skey].update(n for n in idxs if qltrs[n] not in ("-", "_"))
        for s, sltrs in blockCovers.items():
            coverage[s] = coverage.get(s, 0) + len(sltrs)
            
        curL = curL + len(idxs)
        if 100 * curL // rlen > 100 * (curL - len(idxs)) // rlen:
            print("{}%..".format(100 * curL // rlen))
    
    coverages = [(rseq, s, c, rlen) for s, c in coverage.items()]    
    return coverages

def readBuscoFiles(bdir):
    buscoMap = {}
    keys = set()
    for filename in os.listdir(bdir):
        if filename.endswith(".busco"):
            filebase = os.path.splitext(filename)[0].replace(".", "_")
            with open(os.path.join(bdir, filename)) as file:
                for line in file:
                    tokens = line.strip().split()
                    if len(tokens) <= 5:
                        continue
                    
                    name, chrom, start, stop, orient = tokens[0], tokens[2].split(':')[0], int(tokens[3]), int(tokens[4]), tokens[5]
                    key = "{}.{}".format(filebase, chrom)
                    keys.add(key)                                            
                    buscoMap[name] = buscoMap.get(name, [])                    
                    buscoMap[name].append( [start, stop, key, 1 if orient == '+' else 0] )
                        
    buscoMap = {k : v for k,v in buscoMap.items() if len(v) > 1}
    
    print("")
    print("Found busco sequences: ")
    for key in keys:
        print(key)
    print("")
    return buscoMap

def readCmap(buscoDir, buscoClusters):
    cmap = sequenceutils.SequenceNameDict()
    cmapPath = os.path.join(buscoDir, "chrom_mapping.txt")
    if os.path.exists(cmapPath):
        cmap.readChromMapping(cmapPath)
    else:
        for cluster in buscoClusters.values():
            for i in cluster:
                cmap.add(i[2])
    print(cmap)
    
    for b, cluster in buscoClusters.items():
        buscoClusters[b] = [(i[0], i[1], cmap[i[2]], i[3]) for i in cluster if i[2] in cmap]
    return cmap
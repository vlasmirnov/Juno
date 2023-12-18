'''
Created on Mar 30, 2022

@author: Vlad
'''

import os
import time
import numpy as np
from scipy.sparse import *
from helpers import clusterutils, matrixutils
from data.config import configs


def buildMatches(matchInfo, matrixInfo, matrix, seq1, seq2, strand):
    s1, s2 = seq1.num, seq2.num
    configs().debug("Building matches for sequences {} and {}, strand {}..".format(s1, s2, strand))    
    clusters, weights = buildRawMatches(matchInfo, matrixInfo, matrix, seq1, seq2, strand)
    configs().debug("Saving {} matches for sequences {} and {}, strand {}..".format(len(clusters), s1, s2, strand))
    #clusterutils.writeClustersToTempDb(matchInfo.dir, clusters, bucket = matrixInfo.curRef)
    db = clusterutils.getClusterDbPath(matchInfo.dir, matrixInfo.curRef)
    clusterutils.writeClustersToDb(db, clusters, "{}_{}_{}".format(s1, s2, strand))

def buildRawMatches(matchInfo, matrixInfo, matrix, seq1, seq2, strand):
    s1, s2 = seq1.num, seq2.num
    if matrix is None:
        matrix = matrixutils.readPairMatrixFromDb(matrixInfo.dir, s1, s2, strand, enrich = False)
    configs().debug("Sequences {} and {}, strand {}: matrix {} nnz..".format(s1, s2, strand, matrix.nnz if matrix is not None else None))    
    matches = buildMatchesFromMatrix(matchInfo, matrixInfo, matrix, strand) 
    configs().debug("Sequences {} and {}, strand {}: found {} matches..".format(s1, s2, strand, len(matches)))
    interval1 = (0, len(seq1)-1, s1)
    interval2 = (0, len(seq2)-1, s2)
    matches = normalizeMatches(matrixInfo, matches, interval1, interval2, pad = 1)
    
    clusters = {}
    weights = []
    for m11, m12, m21, m22, weight in matches:
        clusters[len(clusters)] = [(int(m11), int(m12), int(s1), 1), (int(m21), int(m22), int(s2), strand)]
        weights.append(weight)
    return clusters, weights

def buildMatchesFromMatrix(matchInfo, matrixInfo, matrix, strand):
    if matrix is None:
        return []
    
    maxGap =  matchInfo.maxGap / matrixInfo.patches[-1]
    minLen = matchInfo.minWidth / matrixInfo.patches[-1]
    maxLen = matchInfo.maxWidth / matrixInfo.patches[-1]
    minRatio = matchInfo.minWidthRatio
    
    matrix = matrix.todok()
    keys = set(matrix.keys())
    sortkeys = sorted(keys)
    preqs = {}
    active = set()
    matchesList = []
    for i,j in sortkeys:
        if matrix[i,j] <= 0:
            continue
        merged = False

        idxes = set()
        for pp in (j//maxGap, j//maxGap + (1 if strand == 0 else -1)):
            if pp in preqs:
                preqs[pp] = set(ix for ix in preqs[pp] if ix in active)
                idxes.update(preqs[pp])
        idxes = sorted(idxes)
        
        for idx in idxes:
            minI, maxI, minJ, maxJ, weight = matchesList[idx]
            if i <= maxI + maxGap:
                if max(i, maxI) - min(i, minI) <= maxLen and max(j, maxJ) - min(j, minJ) <= maxLen:
                    
                    if strand == 1 and j >= minJ and j <= maxJ + maxGap:
                        l1, l2 = i - minI, j - minJ
                        if l1 >= minRatio * l2 and l2 >= minRatio * l1:
                            matchesList[idx] = min(i,minI), max(i,maxI), min(j,minJ), max(j,maxJ), weight + matrix[i, j]
                            p = j//maxGap
                            preqs[p] = preqs.get(p, set())
                            preqs[p].add(idx)
                            merged = True
                            break
                        
                    elif strand == 0 and j <= maxJ and minJ <= j + maxGap:
                        l1, l2 = i - minI, maxJ - j
                        if l1 >= minRatio * l2 and l2 >= minRatio * l1:
                            matchesList[idx] = min(i,minI), max(i,maxI), min(j,minJ), max(j,maxJ), weight + matrix[i, j]
                            p = j//maxGap
                            preqs[p] = preqs.get(p, set())
                            preqs[p].add(idx)
                            merged = True
                            break
            else:
                active.remove(idx)        
        if not merged:
            p, idx = j//maxGap, len(matchesList)
            preqs[p] = preqs.get(p, set())
            preqs[p].add(idx)
            active.add(idx)
            matchesList.append([i, i, j, j, matrix[i, j]]) 
    
    matchesList = [m for m in matchesList if m[1] - m[0] + 1 >= minLen and m[3] - m[2] + 1 >= minLen]            
    return matchesList

def normalizeMatches(matrixInfo, matches, interval1, interval2, pad = 1):  
    if len(matches) == 0:
        return np.zeros((0,5))
    normMatches = np.stack(matches)
    normMatches[:, (0,2)] = (normMatches[:, (0,2)] - pad) * matrixInfo.patches[-1]
    normMatches[:, (0,2)] = np.maximum(normMatches[:, (0,2)], [interval1[0], interval2[0]])
    
    normMatches[:, (1,3)] = (normMatches[:, (1,3)] + 1 + pad) * matrixInfo.patches[-1] - 1
    normMatches[:, (1,3)] = np.minimum(normMatches[:, (1,3)], [interval1[1], interval2[1]])
    return normMatches



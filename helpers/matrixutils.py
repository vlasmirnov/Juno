'''
Created on Jul 4, 2022

@author: Vlad
'''

from collections import defaultdict
import os
from scipy.sparse import *
import numpy as np
import io
import shutil
from helpers import dbutils, mputils


def enrichMatrix3(matrix, strand):
    smult = 1 if strand == 1 else -1
    if isinstance(matrix, np.ndarray):
        zmatrix = np.zeros_like(matrix)
        zmatrix[:,:-1] = np.maximum(zmatrix[:,:-1], matrix[:,1:])
        zmatrix[:,1:] =  np.maximum(zmatrix[:,1:], matrix[:,:-1])
        zmatrix[:-1,:] = np.maximum(zmatrix[:-1,:], matrix[1:,:])
        zmatrix[1:,:] =  np.maximum(zmatrix[1:,:], matrix[:-1,:])
        if smult == 1:
            zmatrix[:-1,:-1] = np.maximum(zmatrix[:-1,:-1], matrix[1:,1:])
            zmatrix[1:,1:] =  np.maximum(zmatrix[1:,1:], matrix[:-1,:-1])
        else:
            zmatrix[:-1,1:] = np.maximum(zmatrix[:-1,1:], matrix[1:,:-1])
            zmatrix[1:,:-1] =  np.maximum(zmatrix[1:,:-1], matrix[:-1,1:])
        zmatrix[matrix > 0] = matrix[matrix > 0]
    else:    
        #print("Enriching matrix with {} entries..".format(matrix.nnz))
        matrix = matrix.tocoo()    
        row1, col1 = np.array(matrix.row)+1, np.array(matrix.col)
        row2, col2 = np.array(matrix.row)-1, np.array(matrix.col)
        row3, col3 = np.array(matrix.row), np.array(matrix.col)+1
        row4, col4 = np.array(matrix.row), np.array(matrix.col)-1
        row5, col5 = np.array(matrix.row)+1, np.array(matrix.col)+smult
        row6, col6 = np.array(matrix.row)-1, np.array(matrix.col)-smult
        allrows = np.concatenate((row1, row2, row3, row4, row5, row6))
        allcols = np.concatenate((col1, col2, col3, col4, col5, col6))
        idxes = (allcols >= 0) & (allcols < matrix.shape[1]) & (allrows >= 0) & (allrows < matrix.shape[0])
        allrows, allcols = allrows[idxes], allcols[idxes]
        ones = np.ones_like(allrows)
        zmatrix = coo_matrix((ones,(allrows,allcols)),shape=matrix.shape)
        #zmatrix = matrix.maximum(zmatrix).todok()
        zmatrix = matrix.maximum(zmatrix)
        #print("Enriched matrix to {} entries..".format(zmatrix.nnz))
    return zmatrix

def countIslands(matrix):
    print("Counting islands..")
    islandMap = defaultdict(set)
    used = set()
    
    for i, j in matrix.keys():
        if matrix[i,j] == 0 or (i,j) in used:
            continue
        stack = [(i,j)]
        curGroup = []
        minI, maxI, minJ, maxJ = i, i, j, j
        while len(stack) > 0:
            ci, cj = stack.pop()
            used.add((ci, cj))
            curGroup.append((ci, cj))
            minI, maxI, minJ, maxJ = min(ci, minI), max(ci, maxI), min(cj, minJ), max(cj, maxJ)
            #for ni, nj in [(ci-1, cj), (ci+1, cj), (ci, cj-1), (ci, cj+1), (ci-1, cj-1), (ci-1, cj+1), (ci+1, cj-1), (ci+1, cj+1)]:
            for ni, nj in [(ci-1, cj), (ci+1, cj), (ci, cj-1), (ci, cj+1), (ci-1, cj-1), (ci+1, cj+1)]:
                if matrix.get((ni, nj),0) > 0 and (ni, nj) not in used:
                    stack.append((ni, nj))
        
        checkAddIsland((minI, maxI, minJ, maxJ), islandMap)
                
    islandList = set()
    for iset in islandMap.values():
        islandList.update(iset)
    print("Found {} islands..".format(2*len(islandList)))   
    totalIslandSize = sum(i[1] - i[0] + i[3] - i[2] + 2 for i in islandList)
    print("Average island size {}".format(totalIslandSize / max(1, 2*len(islandList)))) 
    return 2*len(islandList), totalIslandSize
                
def checkAddIsland(island, islandMap):
    c1, c2, d1, d2 = island
    
    for j in range(d1, d2+1):
        for island2 in list(islandMap[j]):  
            e1, e2, f1, f2 = island2              
            if e1 <= c1 and e2 >= c2 and f1 <= d1 and f2 >= d2:
                return 
            elif c1 <= e1 and c2 >= e2 and d1 <= f1 and d2 >= f2:
                islandMap[j].remove(island2)  
    for j in range(d1, d2+1):
        islandMap[j].add(island)
        
        

def getPairsWithExistingMatrices(matrixDir):
    keys = dbutils.getExistingKeys(matrixDir)
    keys = set(tuple(int(x) for x in k.split('_')) for k in keys)
    return keys

def getMatrixManifest(matrixDir):
    manifest = dbutils.getManifest(matrixDir)
    manifest = {tuple(int(x) for x in k.split('_')) : v for k, v in manifest.items()}
    return manifest

def writePairMatrixToDb(matrix, matrixDir, s1, s2, strand):
    os.makedirs(matrixDir, exist_ok = True)
    s1, s2 = sorted((s1, s2))
    data = scipyToBytes(matrix)
    dbutils.writeDataToDb(matrixDir, "{}_{}_{}".format(s1, s2, strand), data)
        
def readPairMatrixFromDb(matrixDir, manifest, s1, s2, strand, enrich = False):
    s1, s2 = sorted((s1, s2))
    data = dbutils.readDataFromDb(matrixDir, manifest, (s1, s2, strand))
    matrix = bytesToScipy(data)
    if enrich:
        matrix = enrichMatrix3(matrix, strand)
    return matrix

def consolidateMatrixDb(matrixDir):
    dbutils.consolidateDb(matrixDir)

def cleanMatrixDb(matrixDir):
    dbutils.cleanDb(matrixDir)    
    

def scipyToBytes(arr):
    out = io.BytesIO()
    save_npz(out, arr)
    out.seek(0)
    return out.read()

def bytesToScipy(bs):
    out = io.BytesIO(bs)
    out.seek(0)
    return load_npz(out)
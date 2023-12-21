'''
Created on Mar 30, 2022

@author: Vlad
'''

import math
import numpy as np
import os
import time
from scipy.sparse import *
from data.config import configs
from helpers import matrixutils, stringutils
from operations import sketch


def buildMatrix(matrixInfo, seq1, seq2, strand, istr, jstr):
    if (seq1.num, seq2.num, strand) in matrixInfo.existingPairs: 
        return matrixutils.readPairMatrixFromDb(matrixInfo.dir, matrixInfo.existingPairs, seq1.num, seq2.num, strand, enrich = False)
    
    matrix = buildMatrixLevel(matrixInfo, len(matrixInfo.patches)-1, seq1, seq2, strand, istr, jstr)
    matrixutils.writePairMatrixToDb(matrix, matrixInfo.dir, seq1.num, seq2.num, strand)
    return matrix

def buildMatrixLevel(matrixInfo, level, seq1, seq2, strand, istr, jstr):
    pmatrix = None if level == 0 else buildMatrixLevel(matrixInfo, level-1, seq1, seq2, strand, istr, jstr)    
    pmatrix = None if pmatrix is None else matrixutils.enrichMatrix3(pmatrix, strand) 
    
    #matrixInfo.sketchCache = {(s, snd) : matrixInfo.sketchCache.get((s, snd), None) for s in (seq1.num, seq2.num) for snd in (1, 0)}
    matrixInfo.sketchCache = {s : matrixInfo.sketchCache.get(s, None) for s in [(seq1.num, istr), (seq2.num, jstr)]}
    for seq, seqstrand in [(seq1, istr), (seq2, jstr)]:
        if matrixInfo.sketchCache[seq.num, seqstrand] is None:
            matrixInfo.sketchCache[seq.num, seqstrand] = [sketch.readSequenceKmerSketches(matrixInfo, seq, k, seqstrand) for k in matrixInfo.kmers]
    kmers1 = matrixInfo.sketchCache[seq1.num, istr][level]
    kmers2 = matrixInfo.sketchCache[seq2.num, jstr][level] 
    
    matrix = buildMatrixFromKmers(matrixInfo, level, seq1, seq2, strand, kmers1, kmers2, pmatrix)
    return matrix

def buildMatrixFromKmers(matrixInfo, level, seq1, seq2, strand, kmers1, kmers2, pmatrix = None):
    p, pp = matrixInfo.patches[level], matrixInfo.patches[level-1] if level > 0 else None
    mat1, mat2 = buildKmerMatrices(matrixInfo, level, seq1, seq2, kmers1, kmers2)  
    configs().debug("Built kmer matrices of size {} and {}..".format(mat1.shape, mat2.shape))
    length1, length2 = math.ceil(len(seq1) / p), math.ceil(len(seq2) / p)  
    matrix = buildSparseMatrix(matrixInfo, level, mat1, mat2, pmatrix, p, pp, length1, length2).tocoo()
    matrix = trimMatrix(matrixInfo, level, matrix, strand)
    
    #drawer = visutils.Viewer()
    #path = os.path.join(matrixInfo.dir, "{}_{}_{}.png".format(s1, s2, strand))
    #drawer.drawMatrixAlt(coo_matrix(matrix), path, (1, 0, 0.2), 4)
    
    configs().debug("Final matrix of size {}, {} nnz..".format(matrix.shape, matrix.nnz))     
    configs().debug("Average node degree {}".format( 2*matrix.nnz/(matrix.shape[0]+matrix.shape[1]) )) 
    return matrix

def buildSparseMatrix(matrixInfo, level, mat1, mat2, pmatrix, p, pp, length1, length2):
    if pmatrix is not None:
        pmatrix = pmatrix.tocoo()
        submatrices = []
        mrows, mcols = set(mat1.tocoo().row * p // pp), set(mat2.tocoo().col * p // pp)
        for i in range(len(pmatrix.row)):
            if pmatrix.row[i] in mrows and pmatrix.col[i] in mcols:
                res = mat1[pmatrix.row[i] * pp // p : (pmatrix.row[i] + 1) * pp // p].dot(mat2[:, pmatrix.col[i] * pp // p : (pmatrix.col[i] + 1) * pp // p]).tocoo()
                res.row = res.row + pmatrix.row[i] * pp // p
                res.col = res.col + pmatrix.col[i] * pp // p
                submatrices.append(res)
        
        I, J, V = [], [], []
        if len(submatrices) > 0:        
            I = np.concatenate([res.row for res in submatrices])
            J = np.concatenate([res.col for res in submatrices])
            V = np.concatenate([res.data for res in submatrices]) 
            I, J, V = I[V > 0], J[V > 0], V[V > 0]
        matrix = coo_matrix((V,(I,J)),shape=(length1, length2), dtype = np.float32)
    else:
        matrix = matrixMultiply(matrixInfo, level, mat1, mat2)
    configs().debug("Built sparse similarity matrix of size {}, {} nnz..".format(matrix.shape, matrix.nnz))
    return matrix

def matrixMultiply(matrixInfo, level, mat1, mat2):
    if matrixInfo.chunkSize is None or mat1.shape[0] * mat2.shape[1] <= matrixInfo.chunkSize ** 2:
        return mat1.dot(mat2)
    
    submatrices = []
    for i in range(0, mat1.shape[0], matrixInfo.chunkSize):
        for j in range(0, mat2.shape[1], matrixInfo.chunkSize):
            res = mat1[i : i + matrixInfo.chunkSize].dot(mat2[:, j : j + matrixInfo.chunkSize])
            res = trimMatrixDegree(res, matrixInfo.trimDegrees[level])
            res.row = res.row + i
            res.col = res.col + j
            submatrices.append(res)
            
    I, J, V = [], [], []
    if len(submatrices) > 0:        
        I = np.concatenate([res.row for res in submatrices])
        J = np.concatenate([res.col for res in submatrices])
        V = np.concatenate([res.data for res in submatrices]) 
        I, J, V = I[V > 0], J[V > 0], V[V > 0]
    return coo_matrix((V,(I,J)),shape=(mat1.shape[0], mat2.shape[1]), dtype = np.float32)

def buildKmerMatrices(matrixInfo, level, seq1, seq2, kmers1, kmers2):
    uniqueKmers1, indexes1, starts1 = kmers1
    uniqueKmers2, indexes2, starts2 = kmers2
    configs().debug("Kmers {}, {}, {}..".format(len(uniqueKmers1), len(indexes1), len(starts1)))
    configs().debug("Kmers {}, {}, {}..".format(len(uniqueKmers2), len(indexes2), len(starts2)))
    
    sharedKmers, sharedIndexes1, sharedIndexes2 = np.intersect1d(uniqueKmers1, uniqueKmers2, assume_unique = True, return_indices = True)
    p = matrixInfo.patches[level]
    length1, length2 = math.ceil(len(seq1) / p), math.ceil(len(seq2) / p)
    
    mat1 = buildSparseKmerMatrix(indexes1, starts1, sharedIndexes1, length1, p)
    mat2 = buildSparseKmerMatrix(indexes2, starts2, sharedIndexes2, length2, p).T
    
    return mat1, mat2

def buildKmerCounts(indexes1, starts1, sharedIndexes1, indexes2, starts2, sharedIndexes2):
    counts1 = np.zeros(len(starts1), dtype = np.int64)
    counts1[:-1] = starts1[1:] - starts1[:-1]
    counts1[-1] = len(indexes1) - starts1[-1]
    sharedCounts1 = counts1[sharedIndexes1]

    counts2 = np.zeros(len(starts2), dtype = np.int64)
    counts2[:-1] = starts2[1:] - starts2[:-1]
    counts2[-1] = len(indexes2) - starts2[-1]
    sharedCounts2 = counts2[sharedIndexes2]
    return sharedCounts1, sharedCounts2

def buildSparseKmerMatrix(indexes, starts, sharedIndexes, length, patchSize):
    if len(sharedIndexes) == 0:
        return csr_matrix((length, 0), dtype = np.float32)
    
    counts = np.zeros(len(starts), dtype = np.int64)
    counts[:-1] = starts[1:] - starts[:-1]
    counts[-1] = len(indexes) - starts[-1]
    
    sharedStarts = starts[sharedIndexes]
    sharedCounts = counts[sharedIndexes]
    scounts1 = sharedCounts[:-1]
    reset_index = np.cumsum(scounts1)
    incr = np.ones(sharedCounts.sum(), dtype=np.int64)
    incr[0] = 0
    incr[reset_index] = 1 - scounts1
    idxes = incr.cumsum() + np.repeat(sharedStarts, sharedCounts)
    
    I = indexes[idxes] // patchSize
    J = np.repeat(np.arange(len(sharedIndexes)), sharedCounts)
    V = np.repeat(1 / sharedCounts, sharedCounts)
    #V = np.ones(len(I))
    
    matrix = coo_matrix((V,(I,J)),shape=(length, len(sharedIndexes)), dtype = np.float32).tocsr()
    #matrix.data = 1 / matrix.data
    return matrix

def trimMatrix(matrixInfo, level, matrix, strand):
    matrix = trimMatrixDegree(matrix, matrixInfo.trimDegrees[level])
    if matrixInfo.trimIslands is None or matrixInfo.trimIslands[level]:
        matrix = trimMatrixIslands(matrix, strand)
    return matrix

def trimMatrixFraction(matrix, fraction):
    if fraction is None:
        return matrix
    
    matrix = matrix.tocoo()
    limit = int(fraction*matrix.shape[0]*matrix.shape[1])
    if len(matrix.data) > limit:
        keepArgs = np.argpartition(-1 * matrix.data, limit)[: limit]
        #idxs = matrix.data >= np.percentile(matrix.data, 100-threshold)
        matrix.data = matrix.data[keepArgs]
        matrix.row = matrix.row[keepArgs]
        matrix.col = matrix.col[keepArgs]
    
    matsize = matrix.nnz
    configs().debug("Matrix has {} / {} entries..".format(matsize, matrix.shape[0] * matrix.shape[1]))     
    configs().debug("Average node degree {}".format(matsize/matrix.shape[0])) 
    return matrix

def trimMatrixDegree(matrix, threshold):
    if threshold is None:
        return matrix
    matrix = matrix.tolil()
    limit = max(threshold, 1)
    result1 = matrix.copy()
    
    for i in range(matrix.shape[0]):
        if len(matrix.data[i]) > limit:
            row = np.array(matrix.data[i])
            rowixes = np.array(matrix.rows[i])
            keepArgs = np.argpartition(-1 * row, limit)[: limit]
            result1.data[i] = list(row[keepArgs])
            result1.rows[i] = list(rowixes[keepArgs])
    result1 = result1.tocsr()
    
    matrix = matrix.T
    result2 = matrix.copy()
    for i in range(matrix.shape[0]):
        if len(matrix.data[i]) > limit:
            row = np.array(matrix.data[i])
            rowixes = np.array(matrix.rows[i])
            keepArgs = np.argpartition(-1 * row, limit)[: limit]
            result2.data[i] = list(row[keepArgs])
            result2.rows[i] = list(rowixes[keepArgs])
    result2 = result2.T.tocsr()
    
    result = result1.maximum(result2).tocoo()
    return result

def trimMatrixIslands(matrix, strand):
    matrix = matrix.tocoo()
    smult = 1 if strand == 1 else -1
    row1, col1 = np.array(matrix.row)+1, np.array(matrix.col)
    row2, col2 = np.array(matrix.row)-1, np.array(matrix.col)
    row3, col3 = np.array(matrix.row), np.array(matrix.col)+1
    row4, col4 = np.array(matrix.row), np.array(matrix.col)-1
    row5, col5 = np.array(matrix.row)+1, np.array(matrix.col)+smult
    row6, col6 = np.array(matrix.row)-1, np.array(matrix.col)-smult
    #row7, col7 = np.array(matrix.row)+1, np.array(matrix.col)-1
    #row8, col8 = np.array(matrix.row)-1, np.array(matrix.col)+1
    allrows = np.concatenate((row1, row2, row3, row4, row5, row6)) #, row7, row8))
    allcols = np.concatenate((col1, col2, col3, col4, col5, col6)) #, col7, col8))
    idxes = (allcols >= 0) & (allcols < matrix.shape[1]) & (allrows >= 0) & (allrows < matrix.shape[0])
    allrows, allcols = allrows[idxes], allcols[idxes]
    ones = np.ones_like(allrows)
    checkMatrix = coo_matrix((ones,(allrows,allcols)),shape=matrix.shape)
    matrix = matrix.multiply(checkMatrix).tocoo()
    return matrix


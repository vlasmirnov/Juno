'''
Created on Mar 30, 2022

@author: Vlad
'''

import time
import numpy as np
import os
#import pickle
#import lzma
#import gzip
#import zlib
import io
from helpers import stringutils, mputils
from data.config import configs

def buildSketches(matrixInfo, sequenceInfo, seqs, batchName = "Kmer sketches"):
    configs().debug("Counting Kmers..")
    #t1 = time.time() 
    
    matrixInfo.sketchDir = matrixInfo.sketchDir or os.path.join(matrixInfo.dir, "kmers")
    #matrixInfo.sketchDir = matrixInfo.sketchDir or os.path.join(context.workingDir, "kmers")
    os.makedirs(matrixInfo.sketchDir, exist_ok = True)
    
    missingSeqs = set()
    for s, strand in seqs:
        for k in matrixInfo.kmers:
            dr = os.path.join(matrixInfo.sketchDir, "{}_{}".format(s, strand), "kmers_{}.kmr".format(k))
            if not os.path.exists(dr):
                missingSeqs.add(("{} kmers: {} {} {}".format(batchName, s, strand, k), sequenceInfo.seqMap[s], strand, k))
    runSketchGenerators(matrixInfo, missingSeqs)
    
    #t2 = time.time()
    #mputils.awaitRun("Kmer timing", configs().metrics, "Kmers finished, took {} min..".format((t2-t1)/60.0), pathSuffix = "timings")
    configs().debug("Kmers counted..")

def runSketchGenerators(matrixInfo, missingSeqs):
    matrixInfo.sketchesFinished = 0
    mputils.runWorkers(workGenerator = iter(missingSeqs), 
                       workTask = (sketchGenerator, matrixInfo), 
                       resultProcessor = (sketchResultProcessor, matrixInfo, len(missingSeqs)),
                       managedTasks = True)

def sketchResultProcessor(matrixInfo, total, *results):
    matrixInfo.sketchesFinished = matrixInfo.sketchesFinished + 1
    if (100 * matrixInfo.sketchesFinished // total) > (100 * (matrixInfo.sketchesFinished-1) // total):
        configs().debug("Counting kmers.. {}%".format(100 * matrixInfo.sketchesFinished // total))  

def sketchGenerator(matrixInfo, sequence, strand, k):
    uniqueKmers, isort, nz = buildSequenceKmerSketches(sequence, k, strand)
    dr = os.path.join(matrixInfo.sketchDir, "{}_{}".format(sequence.num, strand))
    
    os.makedirs(dr, exist_ok = True)
    writeArray(uniqueKmers, os.path.join(dr, "kmers_{}.kmr".format(k) ))
    writeArray(isort, os.path.join(dr, "idxes_{}.kmr".format(k) ))
    writeArray(nz, os.path.join(dr, "idxes_split_{}.kmr".format(k) ))
    
def writeArray(array, filePath):
    #data = gzip.compress(pickle.dumps(array), compresslevel=1)
    #data = zlib.compress(pickle.dumps(array), 1)
    
    out = io.BytesIO()
    np.save(out, arr=array)
    out.seek(0)
    #data = zlib.compress(out.read(), 1)
    #data = gzip.compress(out.read(), compresslevel=1)
    #data = lzma.compress(out.read(), preset = 1)
    data = out.read()
    
    with mputils.sharedRcs().rwLock:
        with open(filePath, 'wb') as f:
            f.write(data)
            

def loadArray(filePath):
    with mputils.sharedRcs().rwLock:
        with open(filePath, 'rb') as f:
            #data = f.read()
            return np.load(f)
    
    #return np.load(io.BytesIO(gzip.decompress(data)))
    #return np.load(io.BytesIO(zlib.decompress(data)))
    #return np.load(io.BytesIO(lzma.decompress(data)))

def readSequenceKmerSketches(matrixInfo, sequence, k, strand):
    matrixInfo.sketchDir = matrixInfo.sketchDir or os.path.join(matrixInfo.dir, "kmers")
    dr = os.path.join(matrixInfo.sketchDir, "{}_{}".format(sequence.num, strand))
    if os.path.exists(dr):
        uniqueKmers = loadArray(os.path.join(dr, "kmers_{}.kmr".format(k)))
        isort = loadArray(os.path.join(dr, "idxes_{}.kmr".format(k))) 
        nz = loadArray(os.path.join(dr, "idxes_split_{}.kmr".format(k))) 
        
        #arrays = loadArrays(os.path.join(dr, "kmers.kmr"))
        #uniqueKmers, isort, nz = arrays["uniqueKmers"], arrays["isort"], arrays["nz"]
        
        configs().debug("Read {} kmers, {} idxes, {} breakpoints..".format(len(uniqueKmers), len(isort), len(nz)))
    else:
        #print("NOOOT FFFFOOOFFOOUND", sequence.num, strand, matrixInfo.kmerSize)
        configs().debug("Kmers {} not found, loading buffer..".format((sequence.num, strand, k)))
        uniqueKmers, isort, nz = buildSequenceKmerSketches(sequence, k, strand)
        
    return uniqueKmers, isort, nz
    

def buildSequenceKmerSketches(sequence, k, strand, i1 = None, i2 = None): 
    i1, i2 = i1 or 0, i2 or len(sequence)-1
    length = i2 - i1 + 1
    configs().debug("Building kmer sketches from sequence {}, strand {}, pos {} - {}.. ".format(sequence.name, strand, i1, i2))   
    buffer = np.fromfile(sequence.binFile, dtype=np.byte, offset = i1, count = length)
    if strand != 1:
        buffer = stringutils.bufferReverseComplement(buffer)
    
    buffer, mask = stringutils.compressBuffer(buffer, k)
    kmerArray = stringutils.buildKmerArray(buffer, k, i1, i2)
    
    #kmerArray = np.zeros(i2 - i1 - k + 3, dtype = np.dtype((np.void, k)))
    #for i in range(k):
    #    ct = (len(buffer) - i) // k
    #    idxs = np.arange(ct) * k + i
    #    kmerArray[idxs] = np.frombuffer(buffer, dtype = np.dtype((np.void, k)), offset = i, count = ct)
    #configs().debug("Sequence {}, strand {}: building kmer mask..".format(sequence.name, strand))
    #kmerZeros = np.where(stringutils.buildKmerMask(buffer, k)[:len(kmerArray)] == 0)[0]
    #kmerArray[kmerZeros] = bytes(0) #kmerArray[-1]
    
    kmerZeros = np.where(mask[:len(kmerArray)] == 0)[0]
    kmerArray[kmerZeros] = 0 #kmerArray[-1]
    configs().debug("Sequence {}, strand {}: ignoring {} invalid kmers..".format(sequence.name, strand, len(kmerZeros)))
    
    if strand != 1:
        kmerArray = kmerArray[::-1]
    
    isort = np.argsort(kmerArray)
    ksort = kmerArray[isort]
    nz = np.nonzero(ksort[1:] != ksort[:-1])[0] + 1
    uniqueKmers = ksort[nz]
    isort = isort[nz[0]:]
    nz = nz - nz[0]
    
    return uniqueKmers, isort.astype(np.uint32), nz.astype(np.uint32)
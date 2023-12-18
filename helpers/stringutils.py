'''
Created on Oct 8, 2021

@author: Vlad
'''

import math
import numpy as np

def sequenceToNums(sequence):
    idxs = {'N' : 0, 'A' : 1, 'C' : 2, 'G' : 3, 'T' : 4}
    nums = [idxs[c.upper()] for c in sequence]
    return nums

def numsToSequence(nums):
    idxs = ['N', 'A', 'C', 'G', 'T']
    seq = ''.join(idxs[n] if n is not None else 'NONE' for n in nums)
    return seq     

def sequenceToBytes(sequence):
    return bytes(sequence, 'utf-8')

def bytesToSequence(buffer):
    return buffer.decode('utf-8')

def buildKmerMask(buffer, k):
    mask = np.zeros(len(buffer), dtype = np.uint8)  
    #ct = len(mask) - k + 1  
    A, C, G, T = ord('A'), ord('C'), ord('G'), ord('T')
    iA, iC, iG, iT = buffer == A, buffer == C, buffer == G, buffer == T
    mask[iA], mask[iC], mask[iG], mask[iT] = 1, 1, 1, 1
    inv = np.where(mask == 0)[0]
    for i in range(k-1):
        inv = inv - 1
        inv = inv[inv >= 0]
        mask[inv] = 0
    #mask[ct : ] = 0  
    #idxs = np.arange(ct)
    #for i in range(k):
    #    mask[idxs] = mask[idxs] * mask[idxs + i]
    return mask

def compressBuffer(buffer, k):
    datype = np.uint16 if k <= 8 else np.uint32 if k <= 16 else np.uint64
    cbuf = np.zeros(len(buffer), dtype = datype)  
    mask = np.zeros(len(buffer), dtype = np.uint8)  
    A, C, G, T = ord('A'), ord('C'), ord('G'), ord('T')
    iA, iC, iG, iT = buffer == A, buffer == C, buffer == G, buffer == T
    cbuf[iA], cbuf[iC], cbuf[iG], cbuf[iT] = 0, 1, 2, 3
    mask[iA], mask[iC], mask[iG], mask[iT] = 1, 1, 1, 1
    inv = np.where(mask == 0)[0]
    for i in range(k-1):
        inv = inv - 1
        inv = inv[inv >= 0]
        mask[inv] = 0
    return cbuf, mask
        
def buildKmerArray(buffer, k, i1, i2):   
    kmerArray = np.zeros(i2 - i1 - k + 2, dtype = buffer.dtype) 
    for i in range(k):
        kmerArray = kmerArray | (buffer[i:len(kmerArray)+i] << (2 * (k-1-i)))  
    return np.append(kmerArray, 0)

def reverseComplementKmerArray(buffer, k):
    kmerArray = np.zeros_like(buffer)
    buffer = ~buffer
    for i in range(k):
        kmerArray = kmerArray | (((buffer >> 2*i) & 3) << 2*(k-1-i))
    return kmerArray

def bufferReverseComplement(buffer):
    buffer[:] = buffer[::-1]
    A, C, G, T = ord('A'), ord('C'), ord('G'), ord('T')
    iA, iC, iG, iT = buffer == A, buffer == C, buffer == G, buffer == T
    buffer[iA], buffer[iC], buffer[iG], buffer[iT] = T, G, C, A
    return buffer

def bytesReverseComplement(bs):
    buffer = np.frombuffer(bs, dtype = np.byte).copy()
    return bytes(bufferReverseComplement(buffer))

def stringReverseComplement(s):
    bs = sequenceToBytes(s)
    bs = bytesReverseComplement(bs)
    return bytesToSequence(bs)

def sequenceTo4Bit(sequence):
    b = 0
    nums = {'N' : 15, 'A' : 8, 'C' : 4, 'G' : 2, 'T' : 1}
    ints = []
    for i, c in enumerate(sequence):
        b = (nums[c.upper()] << 4) if i % 2 == 0 else b | nums[c.upper()]
        if i % 2 == 1 or i == len(sequence) - 1:
            ints.append(b)
    return bytes(ints)

def bytesToSequence1(bs):
    nums = {15 : 'N', 8 : 'A', 4 : 'C', 2 : 'G', 1 : 'T'}
    letters = []
    for b in bs:
        l1, l2 = b >> 4, b & 15
        if l1 in nums:
            letters.append(nums[l1])
        if l2 in nums:
            letters.append(nums[l2])
    return ''.join(letters)

def bytesIntervalToSequence(bs, i1, i2):
    nums = {15 : 'N', 8 : 'A', 4 : 'C', 2 : 'G', 1 : 'T'}
    letters = []
    for i in range(i1, i2+1):
        thebyte = bs[int(i/2)]
        letter =  thebyte >> 4 if i % 2 == 0 else thebyte & 15
        if letter in nums:
            letters.append(nums[letter])
    return ''.join(letters)

def buildKmerList(k):
    #nums = {15 : 'N', 8 : 'A', 4 : 'C', 2 : 'G', 1 : 'T'}
    nums = {8 : 'A', 4 : 'C', 2 : 'G', 1 : 'T'}
    masks = [[n << (4*i) for n in nums] for i in range(k)]
    stack = [(0, 0)]
    #while len(stack) > 0:
    
def get4BitLetter(theBytes, byteLen, idx):
    if byteLen % 2 == idx % 2:
        return theBytes[int(idx/2)+(idx%2)] >> 4
    else:
        return theBytes[int(idx/2)] & 15 
        
    
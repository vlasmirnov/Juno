'''
Created on Apr 25, 2022

@author: Vlad
'''

import os

def getMafClusters(filePath):
    curBlock = None
    with open(filePath) as f:
        for line in f:
            tokens = line.strip().split()
            if len(tokens) > 0:
                if tokens[0] == 'a':
                    if curBlock is not None:
                        yield curBlock
                    curBlock = []
                if tokens[0] == 's':
                    name = tokens[1]
                    strand = 1 if tokens[4] == '+' else 0
                    slen = int(tokens[5])
                    c1, c2 = int(tokens[2]), int(tokens[2]) + int(tokens[3]) - 1
                    if strand != 1:
                        c1, c2 = slen-1-c2, slen-1-c1 
                    curBlock.append( (c1, c2, name, strand) )
    
    if curBlock is not None:
        yield curBlock
        
def getMafMatches(filePath, seqMap):
    gap = 16384
    nameMap = {s.name.lower() : num for num, s in seqMap.items()}
    result = {}
    seqLists = {}
    
    for cluster in getMafClusters(filePath):
        cluster = [(c1, c2, nameMap.get(c3.lower(), None), c4) for c1, c2, c3, c4 in cluster]
        refseq = cluster[0][2]
        for i in cluster:
            if i[2] != refseq and i[2] is not None:
                if i[2] not in seqLists:
                    seqLists[i[2]] = [cluster[0], i]
                else:
                    pc, pi = seqLists[i[2]]
                    if pi[3] == i[3] and ((i[3] == 1 and i[0] > pi[1] and i[0] - pi[1] <= gap) or (i[3] == 0 and pi[0] > i[1] and pi[0] - i[1] <= gap)):
                        #print("yep..")
                        seqLists[i[2]] = [(pc[0], cluster[0][1], pc[2], pc[3]), (min(i[0], pi[0]), max(i[1], pi[1]), i[2], i[3])]
                    else:
                        result[str(len(result))] = seqLists[i[2]]
                        seqLists[i[2]] = [cluster[0], i]
    for c in seqLists.values():
        result[str(len(result))] = c
    print("Found {} MAF matches..".format(len(result)))
    return result

def readMafLetterBlocks(mafPath):
    curBlock = None    
    with open(mafPath) as f:
        for line in f:
            tokens = line.strip().split()
            if len(tokens) > 0:
                if tokens[0] == 'a':
                    if curBlock is not None:
                        yield curBlock
                    curBlock = []
                if tokens[0] == 's': 
                    name = tokens[1]
                    strand = 1 if tokens[4] == '+' else 0
                    slen = int(tokens[5])
                    ltrs = tokens[-1]
                    c1, c2 = int(tokens[2]), int(tokens[2]) + int(tokens[3]) - 1
                    if strand != 1:
                        c1, c2 = slen-1-c2, slen-1-c1 
                    curBlock.append( (name, ltrs, slen, c1, c2, strand) )
    if curBlock is not None:
        yield curBlock

'''
Created on May 26, 2021

@author: Vlad
'''

import os
import shutil
import re
from collections import UserDict

class Sequence:
    def __init__(self, tag, seq):
        self.tag = tag
        self.seq = seq

class SequenceNameDict(UserDict):
    
    def __init__(self, *args, **kwargs):
        super(SequenceNameDict, self).__init__(*args, **kwargs)
        self.strict = False
    
    def makeTags(self, name):
        baseName, chrName = name.split('.', 1)
        specName = '_'.join(baseName.split('_')[:2])
        sname = "{}.{}".format(specName, chrName)
        tags = (name, sname, baseName, specName)
        return tags
    
    def storeTag(self, tag, value):
        tag = re.sub('[^A-Za-z0-9]+', '', tag)
        self.data[tag] = self.data.get(tag, set())
        self.data[tag].add(value)
    
    def __getitem__(self, key):
        name = key.strip().lower()        
        tags = (name,) if self.strict else self.makeTags(name)
        for tag in tags:
            tag = re.sub('[^A-Za-z0-9]+', '', tag)
            result = self.data.get(tag, [])
            if len(result) == 1:
                return list(result)[0]            
        raise KeyError(key)
    
    def __setitem__(self, key, value):
        name = key.strip().lower()
        for tag in self.makeTags(name):
            self.storeTag(tag, value or name)

    def __contains__(self, key):
        try:
            self.__getitem__(key)
            return True
        except:
            return False
        
    def add(self, key):
        self[key] = None
    
    def readChromMapping(self, cmapPath):
        if cmapPath is not None and os.path.exists(cmapPath):
            with open(cmapPath, 'r') as file:
                for line in file:
                    tokens = line.strip().lower().split()
                    species, baseNames, chrNames, seqName = tokens
                    baseNames, chrNames = baseNames.split(','), chrNames.split(',')
                                        
                    self.storeTag(species, seqName)
                    for chrName in chrNames:
                        self.storeTag("{}.{}".format(species, chrName), seqName)
                        for baseName in baseNames:
                            self.storeTag("{}.{}".format(baseName, chrName), seqName)        
    
    
def readFromFasta(filePath, removeDashes = False):
    sequences = {}
    currentSequence = None

    with open(filePath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):                    
                tag = line[1:]
                currentSequence = Sequence(tag, "")
                sequences[tag] = currentSequence
            else :
                if(removeDashes):
                    line = line.replace("-", "")
                currentSequence.seq = currentSequence.seq + line

    #print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")
    return sequences

def readFromFastaString(fstring, removeDashes = False):
    sequences = {}
    currentSequence = None
    
    lines = fstring.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith('>'):                    
            tag = line[1:]
            currentSequence = Sequence(tag, "")
            sequences[tag] = currentSequence
        else :
            if(removeDashes):
                line = line.replace("-", "")
            currentSequence.seq = currentSequence.seq + line

    return sequences

def readFromFastaFull(filePath, removeDashes = False, taxa = None):
    sequences = {}

    with open(filePath) as f:
        lines = f.read().splitlines()
        print("Read {} lines..".format(len(lines)))
        
    for n,line in enumerate(lines):
        line = line.strip()
        if line.startswith('>'):                    
            tag = line[1:]
            sequences[tag] = []
        else :
            if(removeDashes):
                line = line.replace("-", "")
            sequences[tag].append(line)

    sequences = {tag : Sequence(tag, "".join(sequenceStrings)) for tag, sequenceStrings in sequences.items()}
    #print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")
    return sequences

def readFromFasta2(filePath, removeDashes = False, taxa = None):
    sequences = {}

    with open(filePath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):                    
                tag = line[1:]
                sequences[tag] = []
            else :
                if(removeDashes):
                    line = line.replace("-", "")
                sequences[tag].append(line)

    sequences = {tag : Sequence(tag, "".join(sequenceStrings)) for tag, sequenceStrings in sequences.items()}
    #print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")
    return sequences

def readFromFastaOrdered(filePath, removeDashes = False):
    sequences = []
    currentSequence = None

    with open(filePath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):                    
                tag = line[1:]
                currentSequence = Sequence(tag, "")
                sequences.append(currentSequence)
            else :
                if(removeDashes):
                    line = line.replace("-", "")
                currentSequence.seq = currentSequence.seq + line

    print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")
    return sequences

def readFromFastaOrderedFull(filePath, removeDashes = False):
    sequences = []
    sequenceStrings = {}
    currentSequence = None

    with open(filePath) as f:
        lines = f.read().splitlines()
        print("Read {} lines..".format(len(lines)))
        
    for n,line in enumerate(lines):
        line = line.strip()
        if line.startswith('>'):                    
            tag = line[1:]
            #print(tag)
            currentSequence = Sequence(tag, "")
            sequences.append(currentSequence)
            sequenceStrings[currentSequence] = []
        else :
            if(removeDashes):
                line = line.replace("-", "")
            sequenceStrings[currentSequence].append(line)
            #currentSequence.seq = currentSequence.seq + line
    
    for sequence, strings in sequenceStrings.items():
        sequence.seq = ''.join(strings)

    print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")
    return sequences

def readTaxaFromFasta(filePath):
    with open(filePath) as f:
        taxa = [line.strip()[1:] for line in f if line.startswith('>')]
    print("Read " + str(len(taxa)) + " taxa from " + filePath + " ..")
    return taxa

def readTaxaLengthsFromFasta(filePath):
    sequenceLengths = {}

    with open(filePath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):                    
                tag = line[1:]
                sequenceLengths[tag] = 0
            else :
                line = line.replace("-", "")
                sequenceLengths[tag] = sequenceLengths[tag] + len(line)

    print("Read " + str(len(sequenceLengths)) + " sequence lengths from " + filePath + " ..")
    return sequenceLengths

def readFromPhylip(filePath, removeDashes = False):
    sequences = {}    

    with open(filePath) as f:
        firstLine = f.readline().strip()
        
        for line in f:
            #print(line)
            tokens = line.split()
            if len(tokens) == 2:
                tag = tokens[0]
                seq = tokens[1]
                
                if(removeDashes):
                    seq = seq.replace("-", "")
                   
                if tag in sequences:
                    sequences[tag].seq = sequences[tag].seq + seq
                else:
                    sequences[tag] = Sequence(tag, seq)
                
    
    print("Read " + str(len(sequences)) + " sequences from " + filePath + " ..")                                
    return sequences

#reads cluster columns only
def readFromStockholm(filePath, includeInsertions = False):
    sequences = {}
    
    with open(filePath, 'r') as stockFile:
        for line in stockFile:
            line = line.strip()
            if line == "//":
                break
            elif line == "" or line[0] == "#":
                pass
            else:  
                key, seq = line.split()
                if key not in sequences:
                    sequences[key] = Sequence(key, "")
                    
                for c in seq:
                    #if includeInsertions or not (c == '.' or c in string.ascii_lowercase):
                    if includeInsertions or (c == c.upper() and c != '.'):
                        sequences[key].seq = sequences[key].seq + c    
    return sequences

def writeFasta(alignment, filePath, taxa = None, append = False):
        with open(filePath, 'a' if append else 'w') as textFile:
            if taxa is not None:
                for tag in taxa:
                    if tag in alignment:
                        textFile.write('>' + tag + '\n' + alignment[tag].seq + '\n')
            else:
                for tag in alignment:
                    textFile.write('>' + tag + '\n' + alignment[tag].seq + '\n')
      
                    
def writePhylip(alignment, filePath, taxa = None):
    maxChars = 0
    lines = []
    for tag in alignment:
        if taxa is None or tag in taxa:
            lines.append("{} {}\n".format(tag, alignment[tag].seq))
            maxChars = max(maxChars, len(alignment[tag].seq))
    
    with open(filePath, 'w') as textFile:
        textFile.write("{} {}\n".format(len(lines), maxChars))
        for line in lines:
            textFile.write(line)

def writeSubsetsToDir(subsetsDir, alignmentPath, subsets):
    if os.path.exists(subsetsDir):
        shutil.rmtree(subsetsDir)
    os.makedirs(subsetsDir) 

    subsetPaths = {os.path.join(subsetsDir, "subset_{}.txt".format(n+1)) : subset for n, subset in enumerate(subsets)}
    writeSubsetsToFiles(alignmentPath, subsetPaths)                 
    return subsetPaths
            
def writeSubsetsToFiles(alignmentPath, subsetPaths):
    fileHandles = {subsetPath : open(subsetPath, "w") for subsetPath in subsetPaths}
    taxonFiles = {}
    for path, subset in subsetPaths.items():
        for taxon in subset:
            taxonFiles[taxon] = fileHandles[path]
            
    with open(alignmentPath) as rf:    
        for line in rf:
            if line.startswith('>'):                    
                tag = line.strip()[1:]
                if tag in taxonFiles:
                    taxonFiles[tag].write(line)    
            elif tag in taxonFiles:
                taxonFiles[tag].write(line)
    
    for path, handle in fileHandles.items():
        handle.close()                    
    return subsetPaths

def cleanGapColumns(filePath, cleanFile = None):
    align = readFromFasta(filePath, False)
    values = list(align.values())
    keepCols = []
    for i in range(len(values[0].seq)):
        for j in range(len(values)):
            if values[j].seq[i] != '-':
                keepCols.append(i)
                break
            
    print("Removing gap columns.. Kept {} out of {}..".format(len(keepCols), len(values[0].seq)))
    for s in values:
        s.seq = ''.join(s.seq[idx] for idx in keepCols)
    
    if cleanFile is None:
        cleanFile = filePath
        
    writeFasta(align, cleanFile)
    
def convertRnaToDna(filePath, destFile = None):
    align = readFromFasta(filePath, False)
    for taxon in align:
        align[taxon].seq = align[taxon].seq.replace('U', 'T')
    if destFile is None:
        destFile = filePath
    writeFasta(align, destFile)

def inferDataType(filePath):
    sequences = readFromFasta(filePath, removeDashes=True)
    acg, t, u, total = 0, 0, 0, 0
    for taxon in sequences:
        letters = sequences[taxon].seq.upper()
        for letter in letters:
            total = total + 1
            
            if letter in ('A', 'C', 'G', 'N'):
                acg = acg + 1
            elif letter == 'T':
                t = t + 1
            elif letter == 'U':
                u = u + 1
    
    if u == 0 and (acg + t)/total > 0.9:
        print("Found {}% ACGT-N, assuming DNA..".format(int(100*(acg + t)/total)))
        dataType = "dna"
    elif t == 0 and (acg + u)/total > 0.9:
        print("Found {}% ACGU-N, assuming RNA..".format(int(100*(acg + u)/total)))
        dataType = "rna"
    else:
        print("Assuming protein..")
        dataType = "protein"
          
    return dataType

def readSequenceLengthFromFasta(filePath):
    with open(filePath) as f:
        length = 0
        readSequence = False
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if readSequence:
                    return length
                readSequence = True
            else:
                length = length + len(line)
    if readSequence:
        return length

def countGaps(alignFile):
    counts = []
    currentSequence = ""

    with open(alignFile) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'): 
                
                if currentSequence is not None:
                    if len(counts) == 0:
                        counts = [0] * len(currentSequence)
                    for i in range(len(counts)):
                        if currentSequence[i] == '-':
                            counts[i] = counts[i] + 1
                                             
                currentSequence = ""
            else:
                currentSequence = currentSequence + line
        if currentSequence is not None:
            if len(counts) == 0:
                counts = [0] * len(currentSequence)
            for i in range(len(counts)):
                if currentSequence[i] == '-':
                    counts[i] = counts[i] + 1
    
    return counts

def checkHasACGT(s1):
    for c in s1:
        if c in ('A', 'C', 'G', 'T'):
            return True
    return False

def pDistance(s1, s2):
    sites = 0
    diff = 0
    for i in range(len(s1)):
        if s1[i] not in ('-', '_') and s2[i] not in ('-', '_'):
            sites = sites + 1
            if s1[i] != s2[i]:
                diff = diff + 1
    
    return diff / sites if sites > 0 else 1.0

def pDistanceAll(s1, s2):
    sites = 0
    diff = 0
    for i in range(len(s1)):
        if s1[i] not in ('-', '_') or s2[i] not in ('-', '_'):
            sites = sites + 1
            if s1[i] != s2[i]:
                diff = diff + 1
    
    return diff / sites if sites > 0 else 1.0
    
def basePairs(s1):
    gaps = 0
    for i in range(len(s1.seq)):
        if s1.seq[i] in ('-', '_'):
            gaps = gaps + 1            
    return len(s1.seq) - gaps, gaps / len(s1.seq)
        
def checkFastaStats(filePath):
    align = readFromFasta(filePath)
    values = list(align.values())
    avgGappiness, avgbp, pdist, maxdist, maxbp, minbp = 0, 0, 0, 0, 0, float('inf')
    num = 0
    
    for i in range(len(values)):
        bp, gappiness = basePairs(values[i])
        avgGappiness = avgGappiness + gappiness
        avgbp = avgbp + bp
        maxbp = max(maxbp, bp)
        minbp = min(minbp, bp)
        
        for j in range(i+1, len(values)):
            dist1 = pDistance(values[i].seq, values[j].seq)
            num = num + 1
            pdist = pdist + dist1
            maxdist = max(dist1, maxdist)
        
        #print(i+1, pdist / num, maxdist, avgGappiness / (i+1), avgbp / (i+1))

    pdist = pdist / num
    avgGappiness = avgGappiness / len(values)
    avgbp = avgbp / len(values)
    
    return(len(values), pdist, maxdist, avgGappiness, avgbp, maxbp, minbp)

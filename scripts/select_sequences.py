'''
Created on Dec 7, 2022

@author: Vlad
'''

import argparse
import os
import shutil
import sys
import json
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from helpers import sequenceutils
from data import sequence


def writeChromosomeMapping():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-s", "--species_list", type=str, required=True)
    appParser.add_argument("-d", "--data_folder", type=str, required=True)
    appParser.add_argument("-o", "--output_file", type=str, required=True)
    args = appParser.parse_args()
    
    speciesList = []
    with open(args.species_list) as f:
        firstLine = f.readline().strip()
        for line in f:
            tokens = line.split()
            assembly = tokens[-1]
            species = tokens[-2]
            #assembly = tokens[0].split('.', 1)[-1]
            #species = tokens[-1]
            speciesList.append( (assembly, species) )
    for p in speciesList:
        print(p)
    print("")
    
    dataDir = os.path.abspath(args.data_folder)
    
    with open(os.path.abspath(args.output_file), 'w') as outFile:
        for assembly, species in speciesList:
            speciesDir = os.path.join(dataDir, species)
            if os.path.exists(os.path.join(speciesDir, assembly)):
                speciesDir = os.path.join(speciesDir, assembly)
            
                
            reportFile = os.path.join(speciesDir, "{}_assembly_report.txt".format(assembly))
            stdName = "{}_{}".format(species, assembly.replace("_","").replace(".", "v"))
            assemblyNames = set([assembly]) 
            with open(reportFile, 'r') as report:
                for line in report:
                    if "assembly accession:" in line:
                        assemblyNames.add(line.split("assembly accession:")[-1].strip())
                    
                    tokens = line.strip().split()
                    if len(tokens) > 2 and tokens[1] in ('assembled-molecule', 'unlocalized-scaffold', 'unplaced-scaffold'):                        
                        seqName = "{}.{}".format(stdName, tokens[2])
                        baseNames = ",".join("{}_{}".format(species, assembly.replace("_","").replace(".", "v")) for assembly in assemblyNames)
                        chrNames = ",".join([tokens[4], tokens[6], tokens[2], "chr{}".format(tokens[2])])
                        outFile.write("{} {} {} {}\n".format(species, baseNames, chrNames, seqName))  

def writeChromosomeMapping2():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-s", "--species_list", type=str, required=True)
    appParser.add_argument("-d", "--data_folder", type=str, required=True)
    appParser.add_argument("-o", "--output_file", type=str, required=True)
    args = appParser.parse_args()
    
    speciesList = []
    with open(args.species_list) as f:
        #firstLine = f.readline().strip()
        for line in f:
            tokens = line.split(',')
            species = tokens[5].strip()
            tolid = tokens[0].strip()
            assembly = tokens[9].strip()
            speciesList.append( (species, tolid, assembly) )
    for p in speciesList:
        print(p)
    print("")
    
    dataDir = os.path.abspath(args.data_folder)
    
    with open(os.path.abspath(args.output_file), 'w') as outFile:
        for species, tolid, assembly in speciesList:
            speciesDir = os.path.join(dataDir, species, "assembly", "release", tolid, "insdc")
            if not os.path.exists(speciesDir):
                speciesDir = os.path.join("/lustre/scratch123/tol/teams/durbin/users/cb46/darwin", species)
                
            report = os.path.join(speciesDir, "{}_assembly_report.txt".format(assembly))
            #stdName = "{}_{}".format(species, assembly.replace("_","").replace(".", "v"))
            stdName = "{}_{}".format(species, assembly)
            assemblyNames = set([assembly]) 
            names, chroms = readAssemblyReport(report)
            assemblyNames.update(names)
            for tokens in chroms:
                if tokens[1] == "Chromosome":                        
                    seqName = "{}.{}".format(stdName, tokens[0])
                    #baseNames = ",".join("{}_{}".format(species, assembly.replace("_","").replace(".", "v")) for assembly in assemblyNames)
                    baseNames = ",".join("{}_{}".format(species, assembly) for assembly in assemblyNames)
                    chrNames = ",".join([tokens[0], tokens[2], "chr{}".format(tokens[0])])
                    outFile.write("{} {} {} {}\n".format(species, baseNames, chrNames, seqName))  


def readAssemblyReport(reportFile):
    assemblyNames = set()
    chroms = []
    with open(reportFile, 'r') as report:
        for line in report:
            if "assembly accession:" in line:
                assemblyNames.add(line.split("assembly accession:")[-1].strip())
            
            tokens = line.strip().split()
            if len(tokens) > 2 and tokens[1] in ('assembled-molecule', 'unlocalized-scaffold', 'unplaced-scaffold'):  
                chroms.append((tokens[2], tokens[3], tokens[4]))                   
    return assemblyNames, chroms

def writeSequenceData():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-s", "--species_list", type=str, required=True)
    appParser.add_argument("-d", "--data_folder", type=str, required=True)
    appParser.add_argument("-o", "--output_folder", type=str, required=True)
    appParser.add_argument("-c", "--chromosome", type=str, required=False, default = None)
    args = appParser.parse_args()
    
    speciesList = []
    with open(args.species_list) as f:
        firstLine = f.readline().strip()
        for line in f:
            tokens = line.split()
            assembly = tokens[0].split('.', 1)[-1]
            species = tokens[-1]
            speciesList.append( (assembly, species) )
    for p in speciesList:
        print(p)
    print("")
    
    outputDir = args.output_folder
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    os.makedirs(outputDir)
    
    dataDir = os.path.abspath(args.data_folder)
    for assembly, species in speciesList:
        speciesDir = os.path.join(dataDir, species)
        if os.path.exists(os.path.join(speciesDir, assembly)):
            speciesDir = os.path.join(speciesDir, assembly)
        seqFile = os.path.join(speciesDir, "{}.rnd.fasta".format(assembly))
        seqs = sequenceutils.readFromFasta2(seqFile, removeDashes=True)
        if args.chromosome is not None:
            cseqs = {args.chromosome : seqs[args.chromosome]}
        else:
            cseqs = {k : v for k,v in seqs.items() if k.isalnum()}
                    
        outFile = os.path.join(outputDir, "{}_{}.fasta".format(species, assembly.replace("_","").replace(".", "v")))
        sequenceutils.writeFasta(cseqs, outFile)   

def writeSequenceData2():
    import gzip
    import traceback
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-s", "--species_list", type=str, required=True)
    appParser.add_argument("-d", "--data_folder", type=str, required=True)
    appParser.add_argument("-o", "--output_folder", type=str, required=True)
    args = appParser.parse_args()
    
    
    speciesList = []
    with open(args.species_list) as f:
        #firstLine = f.readline().strip()
        for line in f:
            tokens = line.split(',')
            species = tokens[5].strip()
            tolid = tokens[0].strip()
            assembly = tokens[9].strip()
            speciesList.append( (species, tolid, assembly) )
    for p in speciesList:
        print(p)
    print("")
    
    outputDir = args.output_folder
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    os.makedirs(outputDir)
    
    dataDir = os.path.abspath(args.data_folder)
    for species, tolid, assembly in speciesList:
        speciesDir = os.path.join(dataDir, species, "assembly", "release", tolid, "insdc")
        if not os.path.exists(speciesDir):
            speciesDir = os.path.join("/lustre/scratch123/tol/teams/durbin/users/cb46/darwin", species)
        fgz = os.path.join(speciesDir, "{}.fasta.gz".format(assembly))
        report = os.path.join(speciesDir, "{}_assembly_report.txt".format(assembly))
        #if os.path.exists(os.path.join(speciesDir, assembly)):
        #    speciesDir = os.path.join(speciesDir, assembly)
        #seqFile = os.path.join(speciesDir, "{}.rnd.fasta".format(assembly))
        tmpfst = os.path.join(outputDir, "tmp_{}_{}.fasta".format(species, assembly))
        outfst = os.path.join(outputDir, "{}_{}.fasta".format(species, assembly))
        with gzip.open(fgz, 'rb') as fin:
            with open(tmpfst, 'wb') as fout:
                shutil.copyfileobj(fin, fout)
        
        names, chroms = readAssemblyReport(report)
        chroms = {c[2] : c[0] for c in chroms if c[1] == "Chromosome"}
        seqs = sequenceutils.readFromFasta2(tmpfst, removeDashes=True)
        seqs = {k.split()[0] : v for k, v in seqs.items()}
        seqs = {chroms[k] : v for k,v in seqs.items() if k in chroms}           
        sequenceutils.writeFasta(seqs, outfst)   
        os.remove(tmpfst) 

def readSequenceStats():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-s", "--species_list", type=str, required=True)
    args = appParser.parse_args()
    baseNames = {}
    
    with open(args.species_list) as file:
        for line in file.readlines():
            info = json.loads(line.strip())
            newSeq = sequence.Sequence(**info)
            baseNames[newSeq.baseName] = baseNames.get(newSeq.baseName, [])
            baseNames[newSeq.baseName].append(newSeq)
    
    numSpecies = len(baseNames)
    minChroms = min(len(baseNames[x]) for x in baseNames)
    maxChroms = max(len(baseNames[x]) for x in baseNames)
    minLen = min(len(s) for x in baseNames for s in baseNames[x])
    maxLen = max(len(s) for x in baseNames for s in baseNames[x])
    avgLen = sum(len(s) for x in baseNames for s in baseNames[x]) / sum(1 for x in baseNames for s in baseNames[x])     
    print("{} {} {} {} {} {}".format(numSpecies, minChroms, maxChroms, minLen, maxLen, avgLen))

if __name__ == '__main__':
    #writeChromosomeMapping()
    writeSequenceData2()
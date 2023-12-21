'''
Created on Dec 19, 2023

@author: Vlad
'''


import argparse
import os
import shutil
import sys
import json
import dendropy
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from helpers import sequenceutils, visutils
from data import sequence



def graphBuscoScores():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-t", "--tree", type=str, required=True)
    appParser.add_argument("-b", "--busco", type=str, required=False)
    appParser.add_argument("-o", "--output", type=str, required=False)
    args = appParser.parse_args()
    
    tdist = getTaxonDists(args.tree, "inachis_io_gca905147045v1")
    
    bscores = {}
    with open(args.busco) as f:
        curset = {}
        for line in f:
            line = line.strip()
            if line.startswith('Busco scores: '):
                name = line.split('Busco scores: ')[1]
            elif line.startswith('Sum total: '):
                bscores[name] = curset
                curset = {}
            else:
                tokens = line.split('    ')
                if len(tokens) == 4:
                    species = '_'.join(tokens[2].split('_')[:2])
                    curset[species] = float(tokens[0])
    
    for name in bscores:
        print(name)
        for s, f in bscores[name].items():
            print(s, f)
        print("")
    
    staxons = sorted([t for t in tdist if all(t in bset for bset in bscores.values())], key = lambda x: tdist[x])
    print(staxons)
    
    lines = []
    for name in bscores:
        x = [tdist[s] for s in staxons]
        y = [bscores[name][s] for s in staxons]
        label, color, linestyle, marker = name, None, "", "o"
        lines.append((x,y,label, color, linestyle, marker))
    
    visutils.saveLineGraph(args.output, lines, "BUSCO Recall", "Distance from Inachis Io", "Recall")
    
    '''
    outputDir = args.output_folder
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    os.makedirs(outputDir)
    '''

def graphCoverage():
    appParser = argparse.ArgumentParser()
    appParser.add_argument("-t", "--tree", type=str, required=True)
    appParser.add_argument("-c", "--coverage", type=str, required=False)
    appParser.add_argument("-o", "--output", type=str, required=False)
    args = appParser.parse_args()
    
    tdist = getTaxonDists(args.tree, "inachis_io_gca905147045v1")
    
    bscores = {}
    with open(args.coverage) as f:
        curset = {}
        for line in f:
            line = line.strip()
            if line.startswith('MAF Coverage: '):
                name = line.split('MAF Coverage: ')[1]
            elif line.startswith('Sum total: '):
                bscores[name] = curset
                curset = {}
            else:
                tokens = line.split('    ')
                if len(tokens) == 4:
                    species = '_'.join(tokens[2].split('_')[:2])
                    curset[species] = float(tokens[0])
    
    for name in bscores:
        print(name)
        for s, f in bscores[name].items():
            print(s, f)
        print("")
    
    staxons = sorted([t for t in tdist if all(t in bset for bset in bscores.values())], key = lambda x: tdist[x])
    print(staxons)
    
    lines = []
    for name in bscores:
        x = [tdist[s] for s in staxons]
        y = [bscores[name][s] for s in staxons]
        label, color, linestyle, marker = name, None, "", "o"
        lines.append((x,y,label, color, linestyle, marker))
    
    visutils.saveLineGraph(args.output, lines, "Alignment Coverage", "Distance from Inachis Io", "Coverage")
    
    '''
    outputDir = args.output_folder
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    os.makedirs(outputDir)
    '''

def getTaxonDists(treePath, reflabel):
    tree = loadTree(treePath)
    pdc = tree.phylogenetic_distance_matrix()
    ref = tree.taxon_namespace.get_taxon(reflabel)
    taxons = sorted(tree.taxon_namespace, key=lambda x: pdc(ref, x), reverse=False)
    for t2 in taxons:
        print("'%s' to '%s': %s" % (ref.label, t2.label, pdc(ref, t2)))
    
    return {'_'.join(t2.label.split('_')[:2]) : pdc(ref, t2) for t2 in taxons}

def loadTree(treePath, nameSpace=None):
    tree = dendropy.Tree.get(path=treePath, schema="newick", preserve_underscores=True)
    if nameSpace is None:
        nameSpace = tree.taxon_namespace
    else:
        tree.migrate_taxon_namespace(nameSpace)
    #tree.is_rooted = False
    #tree.resolve_polytomies(limit=2)
    #tree.collapse_basal_bifurcation()
    #tree.update_bipartitions()
    return tree


if __name__ == '__main__':
    graphCoverage()
    #graphBuscoScores()
'''
Created on May 20, 2022

@author: Vlad
'''

import os
import json
from helpers import dbutils, sequenceutils, intervalutils, mputils


def getClusterDbPath(clusterDir, ref):
    dbPath = os.path.join(clusterDir, str(ref))
    return dbPath

def getClusterKeys(clusterDir):
    keys = dbutils.getExistingKeys(clusterDir)
    keys = set(tuple(int(x) for x in k.split('_')) for k in keys)
    return keys

def getClusterManifest(clusterDir):
    manifest = dbutils.getManifest(clusterDir)
    manifest = {tuple(int(x) for x in k.split('_')) : v for k, v in manifest.items()}
    return manifest

def readClustersFromDb(clusterDir):
    clusters = {}
    if os.path.exists(clusterDir):
        data = dbutils.readDataFromDb(clusterDir, None, None, mode = 'text')
        rows = data.splitlines()
        clusters = [json.loads(row) for row in rows]
        clusters = [[tuple(i) for i in cluster] for cluster in clusters]
        clusters = {clusterKey(cluster) : cluster for cluster in clusters}
    return clusters

def writeClustersToDb(clusterDir, clusters, key = None):
    os.makedirs(clusterDir, exist_ok = True)
    if isinstance(clusters, dict):
        data = "".join(json.dumps(cluster) + "\n" for cid, cluster in clusters.items())
    else:
        data = "".join(json.dumps(cluster) + "\n" for cluster in clusters)
    dbutils.writeDataToDb(clusterDir, key, data, mode = 'text')    

def consolidateClusterDb(clusterDir):
    dbutils.consolidateDb(clusterDir)   
            
            
def getAlignPath(alignDir, c):
    alignPath = os.path.join(alignDir, "{}.fasta".format(c))
    return alignPath            

def getAlignedClusters(alignDir):
    return dbutils.getExistingKeys(alignDir)

def getAlignedClustersManifest(alignDir):
    return dbutils.getManifest(alignDir)

def writeAlignToDb(alignDir, c, sourcePath, writeToFinalDb = False):
    with open(sourcePath) as src:
        data = src.read()
    if writeToFinalDb:
        with mputils.FileLock(os.path.join(alignDir, "db.lock")):
            dbutils.writeDataToDb(alignDir, c, data, mode = 'text', suffix = 'all')
    else:
        dbutils.writeDataToDb(alignDir, c, data, mode = 'text')

def readAlignFromDb(alignDir, manifest, c):
    data = dbutils.readDataFromDb(alignDir, manifest, c, mode = 'text')
    return sequenceutils.readFromFastaString(data)

def consolidateAlignDb(alignDir):
    dbutils.consolidateDb(alignDir)   



def clusterKey(cluster):
    if len(cluster) <= 2:
        return "_".join(str(x) for c in cluster for x in c)
    else:
        #return tuple(tuple(i) for i in cluster)
        return str(abs(hash(tuple(cluster))))

def normalizeCluster(cluster):
    cluster = sorted(cluster, key= lambda c: (c[2],c[0],c[1]))
    if cluster[0][3] == 0:
        cluster = [(c[0],c[1],c[2],1-c[3]) for c in cluster]
    return cluster
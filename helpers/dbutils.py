'''
Created on Nov 15, 2023

@author: Vlad
'''

import os
import shutil
from helpers import mputils

def getExistingKeys(dbDir):
    result = set()
    if os.path.exists(dbDir):
        for filename in os.listdir(dbDir):
            if filename.startswith("manifest_"):
                ac = readManifest(os.path.join(dbDir, filename))
                result.update(c[0] for c in ac)
    return result 

def getFullManifest(dbDir):
    result = {}
    if os.path.exists(dbDir):
        for filename in os.listdir(dbDir):
            if filename.startswith("manifest_"):
                ac = readManifest(os.path.join(dbDir, filename))
                result.update({c[0] : (os.path.join(dbDir, filename), c[1], c[2]) for c in ac})
    return result 

def getManifest(dbDir):
    result = {}
    mpath = os.path.join(dbDir, "manifest_all.txt")
    if os.path.exists(mpath):
        result = readManifest(mpath)
        result = {c[0] : (c[1], c[2]) for c in result}
    return result

def readManifest(mpath):
    with open(mpath) as file:
        lines = file.readlines()
    lines = [l.split(" ") for l in lines]
    result = [(l[0], int(l[1]), int(l[2])) for l in lines]
    return result

def writeDataToDb(dbDir, key, data, mode = 'bytes', suffix = None):
    suffix = suffix if suffix is not None else os.getpid()
    dbPath = os.path.join(dbDir, "data_{}.txt".format(suffix))
    m = 'ab' if mode == 'bytes' else 'a'
    with open(dbPath, m) as file:
        start = file.tell()
        slen = file.write(data)
    mpath = os.path.join(dbDir, "manifest_{}.txt".format(suffix))
    with open(mpath, 'a') as file:
        file.write("{} {} {}\n".format(key, start, slen))
        
def readDataFromDb(dbDir, manifest, key, mode = 'bytes', suffix = None):
    suffix = suffix if suffix is not None else os.getpid()
    dbPath = os.path.join(dbDir, "data_all.txt")
    m = 'rb' if mode == 'bytes' else 'r'
    if manifest is None or key is None:
        with open(dbPath, m) as file:
            return file.read()
    start, slen = manifest[key]
    with open(dbPath, m) as file:
        file.seek(start)
        return file.read(slen)

def consolidateDb(dbDir):
    if os.path.exists(dbDir):
        with mputils.FileLock(os.path.join(dbDir, "db.lock")):
            allDataPath = os.path.join(dbDir, "data_all.txt")
            allManifestPath = os.path.join(dbDir, "manifest_all.txt")
            
            for filename in os.listdir(dbDir):
                if filename.startswith("manifest_") and filename != "manifest_all.txt":
                    b = filename.split("_")[1].split(".")[0]
                    mfile = os.path.join(dbDir, filename)
                    afile = os.path.join(dbDir, "data_{}.txt".format(b))
                    ac = readManifest(mfile)
                    with open(allDataPath, 'ab') as dest:
                        mstart = dest.tell()
                        with open(afile, 'rb') as src:
                            shutil.copyfileobj(src, dest, length = 1024 * 1024)                
                    with open(allManifestPath, 'a') as file:
                        for c, start, slen in ac:
                            file.write("{} {} {}\n".format(c, mstart + start, slen))
                    os.remove(mfile)
                    os.remove(afile)

def cleanDb(dbDir):
    if os.path.exists(dbDir):
        with mputils.FileLock(os.path.join(dbDir, "db.lock")):
            for filename in os.listdir(dbDir):
                if filename.startswith("manifest_") and filename != "manifest_all.txt":
                    os.remove(os.path.join(dbDir, filename))
                if filename.startswith("data_") and filename != "data_all.txt":
                    os.remove(os.path.join(dbDir, filename))
                    
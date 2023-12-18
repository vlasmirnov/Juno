'''
Created on Jan 12, 2023

@author: Vlad
'''

import os
import pathlib


def getRelativePath(path, basePath):
    posixPath = pathlib.PurePosixPath(pathlib.Path(path).resolve())
    rootPath = pathlib.PurePosixPath(pathlib.Path(basePath).resolve())
    try:
        return str(posixPath.relative_to(rootPath))
    except:
        return str(posixPath)

def getAbsolutePath(path, basePath):
    if os.path.exists(os.path.join(basePath, path)) or not os.path.exists(path):
        return os.path.join(basePath, path)
    else:
        return path

def choosePath(baseDir, baseName, findNew = True):
    n = 0
    fileName = baseName
    while findNew and os.path.exists(os.path.join(baseDir, fileName)):
        n = n + 1
        tokens = baseName.split('.')
        fileName = "{}_{}.{}".format(tokens[0], n, tokens[1]) if len(tokens) > 1 else "{}_{}".format(tokens[0], n)
    return os.path.join(baseDir, fileName)

def checkUpdatePath(path, update):
    if os.path.exists(path) and update in (None, False, "false"):
        return False
    isDir = len(os.path.basename(path).split('.')) == 1
    '''
    if update == "clean":
        if isDir:
            shutil.rmtree(path, ignore_errors = True) 
        else:
            os.remove(path)  
    '''
    if isDir and not os.path.exists(path):
        os.makedirs(path)  
    elif not isDir and not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    return True
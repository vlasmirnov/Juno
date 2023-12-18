'''
Created on Feb 10, 2022

@author: Vlad
'''

import os
import shutil
import subprocess
import platform
from data.config import configs

mafftPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mafft", "mafft")
mclPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcl", "bin", "mcl")
if platform.system() == 'Windows':
    #mafftArgs = ["wsl.exe", "$(wsl wslpath {})".format(mafftPath)]
    #mafftPath = "wsl.exe $(wsl wslpath {})".format(mafftPath)
    mafftPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mafft", "windows", "mafft.bat") 

def runCommand(**kwargs):
    command = kwargs["command"]
    configs().debug("Running an external tool, command: {}".format(command))
    runner = subprocess.run(command, shell = True, cwd = kwargs["workingDir"], universal_newlines = True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:    
        runner.check_returncode()
    except:
        configs().error("Command encountered error: {}".format(command))
        configs().error("Exit code: {}".format(runner.returncode))
        configs().error("Output: {}".format(runner.stdout))
        raise
    for srcPath, destPath in kwargs.get("fileCopyMap", {}).items():
        shutil.move(srcPath, destPath)

def runMafft(fastaPath, subtablePath, workingDir, outputPath, threads = 1):
    tempPath = os.path.join(os.path.dirname(outputPath), "temp_{}".format(os.path.basename(outputPath)))
    args = [mafftPath, "--localpair", "--maxiterate", "1000", "--ep", "0.123", 
            "--quiet", "--thread", str(threads), "--anysymbol"]
    if subtablePath is not None:
        args.extend(["--merge", subtablePath])
    args.extend([fastaPath, ">", tempPath])
    taskArgs = {"command" : subprocess.list2cmdline(args), "fileCopyMap" : {tempPath : outputPath}, "workingDir" : workingDir}
    #return Task(taskType = "runCommand", outputFile = outputPath, taskArgs = taskArgs)
    runCommand(**taskArgs)

def runMafftAuto(fastaPath, workingDir, outputPath, threads = 1):
    #tempPath = os.path.join(workingDir, os.path.basename(outputPath))
    tempPath = os.path.join(os.path.dirname(outputPath), "temp_{}".format(os.path.basename(outputPath)))
    
    args = [mafftPath, "--auto", "--ep", "0.123", "--quiet", "--thread", str(threads), "--anysymbol"]
    args.extend([fastaPath, ">", tempPath])
    taskArgs = {"command" : subprocess.list2cmdline(args), "fileCopyMap" : {tempPath : outputPath}, "workingDir" : workingDir}
    runCommand(**taskArgs)

def runMafftMedium(fastaPath, subtablePath, workingDir, outputPath, threads = 1):
    tempPath = os.path.join(os.path.dirname(outputPath), "temp_{}".format(os.path.basename(outputPath)))
    args = [mafftPath, "--maxiterate", "2", "--ep", "0.123", 
            "--quiet", "--thread", str(threads), "--anysymbol"]
    if subtablePath is not None:
        args.extend(["--merge", subtablePath])
    args.extend([fastaPath, ">", tempPath])
    taskArgs = {"command" : subprocess.list2cmdline(args), "fileCopyMap" : {tempPath : outputPath}, "workingDir" : workingDir}
    #return Task(taskType = "runCommand", outputFile = outputPath, taskArgs = taskArgs)
    runCommand(**taskArgs)    
    
def runMafftFast(fastaPath, workingDir, outputPath, threads = 1):
    #tempPath = os.path.join(workingDir, os.path.basename(outputPath))
    tempPath = os.path.join(os.path.dirname(outputPath), "temp_{}".format(os.path.basename(outputPath)))
    
    args = [mafftPath, "--retree", "1", "--ep", "0.123", "--quiet", "--thread", str(threads), "--anysymbol"]
    args.extend([fastaPath, ">", tempPath])
    taskArgs = {"command" : subprocess.list2cmdline(args), "fileCopyMap" : {tempPath : outputPath}, "workingDir" : workingDir}
    runCommand(**taskArgs)

def runMcl(matrixPath, inflation, workingDir, outputPath, threads = 1):
    tempPath = os.path.join(os.path.dirname(outputPath), "temp_{}".format(os.path.basename(outputPath)))
    args = [mclPath, matrixPath, "--abc", "-te", str(threads), "-o", tempPath]
    if inflation is not None:
        args.extend(["-I", str(inflation)])
    taskArgs = {"command" : subprocess.list2cmdline(args), "fileCopyMap" : {tempPath : outputPath}, "workingDir" : workingDir}
    #return Task(taskType = "runCommand", outputFile = outputPath, taskArgs = taskArgs)
    runCommand(**taskArgs)

def writeMclGraphToFile(matrix, filePath):
    print("Writing matrix to {}".format(filePath))
    count = 0
    with open(filePath, 'w') as textFile:
        for i in range(len(matrix)):
            for k in matrix[i]:
                textFile.write("{} {} {}\n".format(i, k, matrix[i][k]))
                count = count + 1
    print("Wrote {} matrix entries to {}".format(count, filePath))

def readMclClustersFromFile(filePath):
    print("Reading MCL clusters from {}".format(filePath))
    clusters = []
    with open(filePath) as f:
        for line in f:
            tokens = [int(token) for token in line.strip().split()]
            if len(tokens) > 1:
                clusters.append(tokens) 
    print("Found {} clusters in {}".format(len(clusters), filePath))
    return clusters

def writeClustersToFile(self, filePath):
    with open(filePath, 'w') as textFile:
        for cluster in self.clusters:
            textFile.write("{}\n".format(" ".join([str(c) for c in cluster])))
        


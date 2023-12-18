'''
Created on Nov 9, 2022

@author: Vlad
'''

import argparse
import configparser
import os
import time
import re
import shlex
import sys

CONFIGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")
CONFIGS = None

def initConfigs(argParsers):
    global CONFIGS
    CONFIGS = Configs()
    CONFIGS.loadConfigs(argParsers)

def configs():
    return CONFIGS

def writeMsg(msg, path, pathSuffix = None):
    if path is not None:
        if pathSuffix is not None:
            psplit = os.path.splitext(path)
            path = "{}_{}{}".format(psplit[0], pathSuffix, psplit[1])
        with open(path, 'a') as logFile:
            logFile.write("{}    {}    {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), os.getpid(), msg))


class Configs:

    argParsers = {}

    def __init__(self):
        self.mode = "cli"
        self.configFile= None
        self.operation = None
        
        self.threads = 1
        self.loggingEnabled = True
        self.signalCallbacks = {}
        
        self.dir = None
        self.logPath = None
        self.errorPath = None
        self.debugPath = None
        self.metricsPath = None
        #self.tasksPath = None
        self.taskManager = None
        
        self.buscoDir = None
        
        self.argLists = []
    
            
    def loadConfigs(self, argParsers):
        Configs.argParsers = argParsers
        self.argLists.append(self.loadConfigsFromFile(CONFIGS_PATH))
        args, rest = argParsers["APP"].parse_known_args()
        if vars(args).get("config_file") is not None:
            self.argLists.append(self.loadConfigsFromFile(vars(args)["config_file"]))
        self.argLists.append(None)
        
        self.validateArgs()
        self.initAppConfigs()
    
    def initObjectFromArgs(self, obj, section):
        for arglist in self.argLists:
            Configs.argParsers[section].parse_known_args(arglist, namespace = obj)
        return obj

    def loadConfigsFromFile(self, path):
        argTokens = []
        iniparser = configparser.ConfigParser()
        if os.path.exists(path):
            iniparser.read(path)
            for section in iniparser:
                for k, v in dict(iniparser[section]).items():
                    #if v.lower() not in ('none', 'null'):
                        argTokens.append("--{}".format(k.lower()))
                        argTokens.extend(shlex.split(v))
        return argTokens

    def initAppConfigs(self):
        self.initObjectFromArgs(self, "APP")       
        
        self.dir = os.path.abspath(self.dir or os.path.join(os.getcwd(), "aligner"))
        self.threads = {None : 1, 0 : 1, -1 : os.cpu_count()}.get(self.threads, self.threads)
        self.mode = "cli" if self.operation is not None else self.mode
        #self.update = self.update.lower() if self.update is not None else None
        self.setWorkspace(self.dir)
        
    def validateArgs(self):
        ns = {s : argparse.Namespace() for s in Configs.argParsers}
        for arglist in self.argLists:
            args, rest = None, arglist
            for section, parser in Configs.argParsers.items():
                args, rest = parser.parse_known_args(rest, namespace = ns[section])
            Configs.argParsers["APP"].parse_args(rest)
        return ns

    def printAppConfigs(self):
        cp = configparser.ConfigParser()
        ns = self.validateArgs()
        cpdict = {s : {k : str(v) for k, v in vars(ns[s]).items()} for s in ns}
        cp.read_dict(cpdict)
        cp.write(sys.stdout)
    
    def connectSignal(self, signal, callback):
        if callback is None:
            return
        self.signalCallbacks[signal] = self.signalCallbacks.get(signal, [])
        self.signalCallbacks[signal].append(callback) 
    
    def emitSignal(self, signal, data, **kwargs):
        for callback in self.signalCallbacks.get(signal, []):
            callback(data, **kwargs)
    
    def setWorkspace(self, workDir):
        self.closeWorkspace()
        os.makedirs(workDir, exist_ok = True)
        self.dir = workDir
        self.logPath = os.path.join(workDir, "log.txt")    
        self.errorPath = os.path.join(workDir, "log_errors.txt")
        self.debugPath = os.path.join(workDir, "log_debug.txt")
        self.metricsPath = os.path.join(workDir, "log_metrics.txt")
        
        #self.tasksPath = os.path.join(logDir, "z_tasks.txt")
    
    def closeWorkspace(self):
        if self.taskManager is not None:
            self.taskManager.shutdown()
            self.taskManager = None
        
    
    def log(self, msg, path = None, pathSuffix = None):
        print(msg)
        self.debug(msg)
        writeMsg(msg, path or self.logPath, pathSuffix)
    
    def error(self, msg, path = None, pathSuffix = None):
        self.log(msg)
        writeMsg(msg, path or self.errorPath, pathSuffix)
    
    def debug(self, msg, path = None, pathSuffix = None):
        writeMsg(msg, path or self.debugPath, pathSuffix)
    
    def metrics(self, msg, path = None, pathSuffix = None):
        self.log(msg)
        writeMsg(msg, path or self.metricsPath, pathSuffix)
    
    
def resolvePathList(pathList):
    result = []
    for p in pathList:
        if p is None or p.lower() in ('null', 'none'):
            result.append(None)
            continue
        path = os.path.abspath(p)
        if os.path.isdir(path):
            for filename in os.listdir(path):
                result.append(os.path.join(path, filename))
        else:
            result.append(path)
    return result
    
def camelCase(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])

def cleanString(s):
    return re.sub(r"(_|-| )+", "", s)
    


def none_or_str(value):
    if value.lower() in ('null', 'none'):
        return None
    return value

def none_or_int(value):
    if value.lower() in ('null', 'none'):
        return None
    return int(value)

def none_or_float(value):
    if value.lower() in ('null', 'none'):
        return None
    return float(value)

def none_or_path(value):
    if value.lower() in ('null', 'none'):
        return None
    return os.path.abspath(value)

'''
class PathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        values = os.path.abspath(values) if values is not None else values
        #print(self.dest, values)
        setattr(namespace, self.dest, values)
'''

class PathListAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        values = resolvePathList(values) if values is not None else values
        #print(self.dest, values)
        setattr(namespace, self.dest, values)

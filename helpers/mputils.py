'''
Created on Mar 7, 2023

@author: Vlad
'''

import os
import concurrent.futures
import traceback
import multiprocessing
import time
import signal
import random as rnd
from data import config
from data.config import configs

 
def taskManager():
    if configs().taskManager is None:
        configs().taskManager = TaskManager(os.path.join(configs().dir, "z_tasks.txt") , configs().threads)
    return configs().taskManager

def awaitRun(taskName, fn, *fnargs, **fnkwargs):
    task = Task(taskName, fn, *fnargs, **fnkwargs)
    task.awaitRun()
    return task

def joinRun(taskName, fn, *fnargs, **fnkwargs):
    task = Task(taskName, fn, *fnargs, **fnkwargs)
    task.awaitRun(join = True)
    return task

def checkRun(taskName, fn, *fnargs, **fnkwargs):
    task = Task(taskName, fn, *fnargs, **fnkwargs)
    task.checkRun()
    return task

def pullStatus(taskName):
    if taskManager() is None:
        return None
    status = taskManager().pullStatus(Task(taskName, None))
    if status != "finished":
        with taskManager().taskLock:
            status = taskManager().pullStatus(Task(taskName, None), grabUpdates = True)
    return status
    
def awaitNextTask(awaitingTasks):    
    return taskManager().awaitNextTask(awaitingTasks)
        
def runWorkers(*args, **kwargs):
    mgr = WorkerManager(*args, **kwargs)
    mgr.run()  


class WorkerManager:
        
    def __init__(self, workGenerator, workTask, resultProcessor, managedTasks = False, batchSize = None):
        self.executor = None
        self.preparingTasks = set()
        self.awaitingTasks = set()
        
        self.workGenerator = workGenerator
        self.workFn, self.workArgs = workTask[0], workTask[1:]
        self.resultFn, self.resultArgs = resultProcessor[0], resultProcessor[1:]    
        
        self.managedTasks = managedTasks
        self.batchSize = batchSize or configs().threads #* 2
        self.waiting = False
       
    def run(self):
        with WorkerExecutor(globalArgs = self.workArgs, max_workers = configs().threads) as self.executor:    
            try:
                while True:
                    self.submitWork()
                    
                    if self.waiting and self.executor.workRunning + len(self.awaitingTasks) == 0:
                        break
                    
                    if self.waiting or self.executor.resultQueue.qsize() > 0:
                        task = self.awaitTask()
                        if task.status == "finished":
                            self.resultFn(*self.resultArgs, *task.fnargs, task.result)
                        else:                
                            self.preparingTasks.add(task)
            finally:
                if self.managedTasks:
                    taskManager().flush()    
                self.executor.sendStopSignals()
                
    def submitWork(self):          
        work = next(self.workGenerator, None) if self.executor.workQueue.qsize() < 2 * self.batchSize else None
        self.waiting = work in (None, "wait")
        if not self.waiting:
            task = Task(work[0], self.workFn, *work[1:]) if self.managedTasks else Task(max([t.task for t in self.preparingTasks], default=0)+1, self.workFn, *work)
            self.preparingTasks.add(task)
        
        if self.waiting or len(self.preparingTasks) >= self.batchSize:
            if self.managedTasks:
                reserved = taskManager().reserveTaskBatch(self.preparingTasks) 
            while len(self.preparingTasks) > 0:  
                task = self.preparingTasks.pop()  
                if not self.managedTasks or task in reserved:
                    self.executor.addWork(task)
                else:
                    self.awaitingTasks.add(task)  
            
    def awaitTask(self):
        if self.executor.workRunning > 0:
            task = self.executor.awaitResults()    
            if self.managedTasks:
                taskManager().finishReservedTask(task, self.batchSize)  
        else:
            if self.managedTasks:
                taskManager().flush()         
            if len(self.awaitingTasks) > 0:
                task = awaitNextTask(self.awaitingTasks)
                self.awaitingTasks.remove(task)
        return task
    
    
class WorkerExecutor(concurrent.futures.ProcessPoolExecutor):
    
    def __init__(self, globalArgs, *args, **kwargs):
        super(WorkerExecutor, self).__init__(*args, **kwargs)
        
        self.workQueue = sharedRcsMgr().Queue()
        self.resultQueue = sharedRcsMgr().Queue()
        self.workers = []
        self.workRunning = 0
        self.globalArgs = globalArgs
        self.isStopped = False
        self.finished = 0
    
    def addWork(self, task):
        self.workQueue.put(task)
        self.workRunning = self.workRunning + 1
        if len(self.workers) < min(self.workRunning, self._max_workers):
            self.workers.append(self.submit(doWork, sharedRcs(), self.globalArgs, self.workQueue, self.resultQueue))
            #print("WORKERS: ",  len(self.workers))
    
    def awaitResults(self):
        result = self.resultQueue.get()    
        self.workRunning = self.workRunning - 1
        if isinstance(result, Exception):
            raise result
        return result
    
    def sendStopSignals(self):
        self.isStopped = True
        for worker in self.workers:
            try:
                self.workQueue.put(None)
            except:
                continue

def doWork(sharedResources, globalArgs, workQueue, resultQueue):
    try:
        sharedResources.initSharedResources()
        setSigHandlers()
                
        while True:
            task = workQueue.get()
            if task is None:
                break      
            fnargs = task.fnargs
            task.fnargs = (*globalArgs, *fnargs)
            task.run()
            task.fnargs = fnargs
            #print(task.status)
            resultQueue.put(task)
            
    except Exception as e:
        resultQueue.put(e)
        configs().error("Worker thread aborted with an exception..")
        configs().error(traceback.format_exc())
        

class TaskManager:
    
    def __init__(self, tasksPath, batchSize = 1):
        self.tasksPath = tasksPath     
        self.pid = os.getpid() 
        self.pids = set()
        self.batchSize = batchSize
        
        self.taskLock = FileLock(os.path.splitext(tasksPath)[0] + ".lock", None) #sharedRcsMgr().Lock())
        self.seekPos = 0
        self.taskStatuses = {}
        self.reservedTasks = set()
        self.finishedTasks = set()
        
        self.joinRun()
                
    def joinRun(self):
        os.makedirs(os.path.dirname(self.tasksPath), exist_ok = True)
        with self.taskLock:
            if os.path.exists(self.tasksPath):
                self.grabLatestChanges()        
                
            if len(self.pids) == 0:
                open(self.tasksPath, 'w').close()
                self.seekPos = 0
                self.taskStatuses = {}
                configs().log("Starting run..")
            else:
                configs().log("Joining active run..")
            self.pids.add(self.pid)
            self.pushRunStatus("started")
    
    def grabLatestChanges(self):
        taskStatuses = {}        
        with open(self.tasksPath, 'r') as reader:
            reader.seek(self.seekPos)
            for line in reader:
                tokens = line.strip().split("    ")
                if tokens[3].lower() == "run":
                    pid, runFinished = tokens[1], tokens[2].lower() == "finished"
                    if runFinished:
                        self.pids.discard(pid)
                    else:
                        self.pids.add(pid)
                else:
                    status, task = tokens[2].lower(), tokens[3]
                    taskStatuses[task] = status
            self.seekPos = reader.tell()
        self.taskStatuses.update(taskStatuses)   
        return taskStatuses

    def pushStatus(self, tasks):
        with open(self.tasksPath, 'a') as writer:
            for task in tasks:
                self.taskStatuses[task.task] = task.status
                tokens = [time.strftime("%Y-%m-%d %H:%M:%S"), self.pid, task.status.upper(), task.task]
                writer.write("{}\n".format("    ".join(str(x) for x in tokens)))

    def pullStatus(self, task, grabUpdates = False):
        if grabUpdates:
            self.grabLatestChanges()
        task.status = self.taskStatuses.get(task.task, None)
        return task.status
        
    def pushRunStatus(self, status):
        with open(self.tasksPath, 'a') as writer:
            tokens = [time.strftime("%Y-%m-%d %H:%M:%S"), self.pid, status.upper(), "RUN"]
            writer.write("{}\n".format("    ".join(str(x) for  x in tokens)))
    
    def reserveTask(self, task):
        reserved = self.reserveTaskBatch([task])   
        return task in reserved
    
    def reserveTaskBatch(self, tasks):
        reserved = set()
        remaining = []
        
        for task in tasks:
            if task in self.reservedTasks:
                reserved.add(task)
                task.status = "pending"
            elif self.pullStatus(task) != "finished":
                remaining.append(task)
        
        if len(remaining) > 0:
            with self.taskLock:
                self.grabLatestChanges()
                for task in remaining:
                    if self.pullStatus(task) not in ("pending", "finished"):
                        reserved.add(task)
                        task.status = "pending"
                self.pushStatus(reserved)
                self.reservedTasks.update(reserved)          
        return reserved
    
    def finishReservedTask(self, task, batchSize = 1):
        #self.reservedTasks.pop(task, None)
        if task in self.reservedTasks:
            self.finishedTasks.add(task)
            if len(self.finishedTasks) >= batchSize:
                self.flush()
        
    def flushFinishedTasks(self):
        self.pushStatus(self.finishedTasks)
        self.reservedTasks.difference_update(self.finishedTasks)
        self.finishedTasks = set()
    
    def awaitNextTask(self, awaitingTasks):
        task = next(iter(awaitingTasks))     
        while True:
            if self.pullStatus(task) not in (None, "pending"):
                return task
            with self.taskLock:
                if self.pullStatus(task, True) != "pending":
                    return task
            time.sleep(0.1)
    
    def flush(self):
        if len(self.finishedTasks) > 0:
            with self.taskLock:
                self.flushFinishedTasks()
    
    def shutdown(self):        
        with self.taskLock:        
            self.grabLatestChanges()
            self.flushFinishedTasks()
            for task in self.reservedTasks:
                task.status = "failed"
            self.pushStatus(self.reservedTasks) 
            self.pushRunStatus("finished")     
    

class Task:
    
    def __init__(self, task, fn, *fnargs, **fnkwargs):
        self.task = task
        self.fn = fn
        self.fnargs = fnargs
        self.fnkwargs = fnkwargs
        self.result = None
        self.status = None
    
    def __hash__(self):
        return hash(self.task)
    
    def __eq__(self, other):
        return isinstance(other, Task) and self.task == other.task
    
    def awaitRun(self, join = False):
        while self.status != "finished":
            self.checkRun(join)
            if self.status == "pending":
                self.status = taskManager().awaitNextTask([self])
    
    def checkRun(self, join = False):
        if taskManager().reserveTask(self) or (join and self.status != "finished"):
            try:
                self.run()
            finally:
                taskManager().finishReservedTask(self)
        elif join and self.status == "finished":
            configs().log("{} already finished..".format(self.task))
            
    def run(self):
        try:
            self.result = self.fn(*self.fnargs, **self.fnkwargs)
            self.status = "finished"
        except:
            self.status = "failed"
            raise           


class SharedRcs:
    
    MGR = None
    RCS = None
    
    def __init__(self):
        self.cfg = configs()
        self.rwLock = sharedRcsMgr().Lock()
        #self.dir = None
        #self.taskManager = None
    
    def initSharedResources(self):
        SharedRcs.RCS = self
        config.CONFIGS = self.cfg
     
        
def sharedRcs():
    if SharedRcs.RCS is None:
        SharedRcs.RCS = SharedRcs()
    return SharedRcs.RCS

def sharedRcsMgr():
    if SharedRcs.MGR is None:
        SharedRcs.MGR = multiprocessing.Manager()
    return SharedRcs.MGR

        
class FileLock:
    
    def __init__(self, filePath, mpLock = None, sleep = 0.1):
        self.filePath = filePath
        self.mpLock = mpLock
        self.sleep = sleep
    
    def __enter__(self):
        if self.mpLock is not None:
            self.mpLock.acquire()
        while True:
            try:
                lock = open(self.filePath, 'x')
                lock.close()
                return self
            except:
                #time.sleep(self.sleep)
                time.sleep(rnd.random()*self.sleep + self.sleep)
            
    def __exit__(self, excType, excVal, excTb):
        os.remove(self.filePath)
        if self.mpLock is not None:
            self.mpLock.release()
    

def handler(sig, frame):
    for child in multiprocessing.active_children():
        child.terminate()
    raise KeyboardInterrupt
    
def setSigHandlers():
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def clearSigHandlers():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
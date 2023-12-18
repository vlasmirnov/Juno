'''
Created on Mar 30, 2022

@author: Vlad
'''

import numpy as np

def getPatchesInInterval(interval, patchSize):
    return int(interval[1]/patchSize) - int(interval[0]/patchSize) + 1

def checkSubinterval(i1, i2):
    if i1[0] <= i2[0] and i2[1] <= i1[1]:
        return 1
    elif i2[0] <= i1[0] and i1[1] <= i2[1]:
        return -1
    return 0

def getIntervalOverlap(i1, i2):
    if i1[0] > i2[1] or i2[0] > i1[1]:
        return 0
    return min(i1[1], i2[1]) - max(i1[0], i2[0]) + 1

def getIntervalNonOverlap(i1, i2):
    nonoverlap = i1[1] - i1[0] + 1 + i2[1] - i2[0] + 1 - 2*getIntervalOverlap(i1, i2)
    return nonoverlap

def getIntervalUnion(i1, i2):
    if i1[0] > i2[1] or i2[0] > i1[1]:
        return None
    return (min(i1[0], i2[0]), max(i1[1], i2[1]))

def getIntervalLength(i1):
    return i1[1] - i1[0] + 1

def getIntervalIntersection(i1, i2):
    if i1[0] > i2[1] or i2[0] > i1[1]:
        return None
    return (max(i1[0], i2[0]), min(i1[1], i2[1]))

def getIntervalProjection(i1, p1, i2):
    a1, a2 = i1[0], i1[1]
    b1, b2 = i2[0], i2[1]
    pa1, pa2 = p1[0], p1[1]
    
    pb1 = b1 + int( (b2-b1+1)*(pa1-a1)/(a2-a1+1) )
    pb2 = b2 - int( (b2-b1+1)*(a2-pa2)/(a2-a1+1) )
    return (pb1, pb2)

def getIntervalOverlapPortion(i1, i2):
    return 2*getIntervalOverlap(i1, i2)/(2 + i1[1] - i1[0] + i2[1] - i2[0])     

def mergeIntervals(intervals, combineEndToEnd = False):
    breaks = np.nonzero((intervals[1:,2] != intervals[:-1,2]) | (intervals[1:,3] != intervals[:-1,3]))[0] + 1
    if len(breaks) == len(intervals)-1:
        return intervals
    bcords = np.zeros(len(breaks) + 2, dtype = np.int64)
    bcords[-1] = len(intervals)
    bcords[1:-1] = breaks
    results = []
    for a, b in zip(bcords[:-1], bcords[1:]):
        chunk = intervals[a:b]
        starts = chunk[:,0]
        ends = np.maximum.accumulate(chunk[:,1])
        valid = np.zeros(len(chunk) + 1, dtype=bool)
        valid[0] = True
        valid[-1] = True
        valid[1:-1] = starts[1:] > ends[:-1]
        mergedIntervals =  chunk[valid[:-1],:]
        mergedIntervals[:,1] = ends[:][valid[1:]] #chunk[valid[1:],1]
        results.append(mergedIntervals)
    return np.vstack(results)

def mergeIntervalLists(list1, list2):
    return mergeIntervals(sortIntervals(np.vstack((list1, list2))) )

def sortIntervals(intervals):
    idx = np.lexsort((intervals[:,1],intervals[:,0],intervals[:,3],intervals[:,2]))
    intervals[:] = intervals[idx]
    return intervals

def buildIntervalOverlaps(intervals, minOverlap = 1):    
    overlaps = {}
    sortedIntervals = sorted(intervals, key = lambda i : (i[2], i[0], i[1]))
    preqs = set()
    for i1 in sortedIntervals:
        overlaps[i1] = {}
        for i2 in list(preqs):
            if i2[1] < i1[0] + minOverlap - 1 or i2[2] != i1[2]:
                preqs.remove(i2)
            else:
                overlaps[i1][i2] = getIntervalOverlap(i1, i2)
                overlaps[i2][i1] = overlaps[i1][i2]
        preqs.add(i1)        
    return overlaps

def buildIntervalOverlapsMinFraction(intervals, minOverlap = 1, minFraction = 0):    
    overlaps = {}
    sortedIntervals = sorted(intervals, key = lambda i : (i[2], i[0], i[1]))
    preqs = set()
    for i1 in sortedIntervals:
        overlaps[i1] = {}
        for i2 in list(preqs):
            if i2[1] < i1[0] + minOverlap - 1 or i2[2] != i1[2]:
                preqs.remove(i2)
            else:
                over = getIntervalOverlap(i1, i2)
                if over >= minFraction * getIntervalLength(i1) and over >= minFraction * getIntervalLength(i2):
                    overlaps[i1][i2], overlaps[i2][i1] = over, over
        preqs.add(i1)        
    return overlaps

def buildIntervalSetOverlaps1(fromSet, toSet, minOverlap = 1, minFraction = 0):    
    overlaps = {}
    sortedIntervals = list(set(fromSet).union(set(toSet)))
    sortedIntervals = sorted(sortedIntervals, key = lambda i : (i[2], i[0], i[1]))
    preqs = set()
    for i1 in sortedIntervals:
        if i1 in fromSet:
            overlaps[i1] = {}
            if i1 in toSet:
                overlaps[i1][i1] = getIntervalLength(i1)
        for i2 in list(preqs):
            if i2[1] < i1[0] + minOverlap - 1 or i2[2] != i1[2]:
                preqs.remove(i2)
            else:
                if i1 in fromSet and i2 in toSet:
                    over = getIntervalOverlap(i1, i2)
                    if over >= minFraction * getIntervalLength(i1) and over >= minFraction * getIntervalLength(i2):
                        overlaps[i1][i2] = over
                if i1 in toSet and i2 in fromSet:
                    over = getIntervalOverlap(i1, i2)
                    if over >= minFraction * getIntervalLength(i1) and over >= minFraction * getIntervalLength(i2):
                        overlaps[i2][i1] = over
        preqs.add(i1)
        
    return overlaps

def buildIntervalSetOverlaps(fromSet, toSet, minOverlap = 1, minFraction = 0):    
    intervals = np.vstack(list(set(fromSet).union(set(toSet))))
    idx = np.lexsort((intervals[:,1],intervals[:,0],intervals[:,2]))
    intervals[:] = intervals[idx]
    lb = intervals[:,0] + np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1)*minFraction)
    rb = intervals[:,1] - np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1)*minFraction)
    #ti = intervals.copy()
    #ti[:,0] = lb
    #ti[:,1] = rb
    
    overlaps = {}
    preqs = set()
    for n1, i1 in enumerate(intervals):
        i1 = tuple(i1)
        if i1 in fromSet:
            overlaps[i1] = {}
            if i1 in toSet:
                overlaps[i1][i1] = getIntervalLength(i1)
        rm = []
        for n2 in preqs:
            i2 = tuple(intervals[n2])
            if rb[n2] < i1[0] - 1 or i2[2] != i1[2]:
                rm.append(n2)
            elif i2[1] + 1 >= lb[n1]:
                if i1 in fromSet and i2 in toSet:
                    overlaps[i1][i2] = getIntervalOverlap(i1, i2)
                if i1 in toSet and i2 in fromSet:
                    overlaps[i2][i1] = getIntervalOverlap(i1, i2)
        preqs.add(n1)
        for n2 in rm:
            preqs.remove(n2)
        
    return overlaps

def genIntervalOverlaps1(intervals, bounds, idx, offset):
    if offset == 0:
        nidx = np.where(bounds[:, 1] + 1 >= intervals[:, 0])[0]
    else:
        if idx[-1]+offset >= len(intervals):
            idx = idx[:-1] 
        nidx = np.where(bounds[idx, 1] + 1 >= intervals[idx+offset, 0])[0]
        nidx = idx[nidx]
    ridx = np.where(intervals[nidx, 1] + 1 >= bounds[nidx+offset, 0])[0]
    ridx = nidx[ridx]
    #overlaps = np.minimum(intervals[ridx, 1], intervals[ridx+offset, 1]) - np.maximum(intervals[ridx, 0], intervals[ridx+offset, 0]) + 1
    return nidx, ridx #, overlaps

def buildIntervalMatrix1(intervals, minOverlap = 1, minFraction = 0):    
    intervals = np.vstack(list(intervals))
    intervals = intervals[np.lexsort((intervals[:,1],intervals[:,0]))]
    bounds = intervals[:,:2].copy()
    bounds[:,0] = intervals[:,0] + np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1) * minFraction)
    bounds[:,1] = intervals[:,1] - np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1) * minFraction)
    return intervals, bounds

def genIntervalOverlaps2(intervals, hitSet, minOverlap = 1, minFraction = 0):
    intervals, hitflag = buildIntervalMatrix2(intervals, hitSet, minOverlap, minFraction)
    il = intervals[:, 1] - intervals[:, 0] + 1
    offset = 0
    
    idx = np.where(il >= minOverlap)[0]
    while len(idx) > 0:
        ov = intervals[idx, 1] - intervals[idx+offset, 0] + 1        
        ridx = idx[np.where((ov >= minFraction * il[idx]) & (ov >= minFraction * il[idx+offset]) & (hitflag[idx] + hitflag[idx+offset] > 0))[0]]
        for i in ridx:
            i1, i2 = tuple(intervals[i]), tuple(intervals[i+offset])
            if hitflag[i] == 1:
                yield i1, i2, getIntervalOverlap(i1, i2)
            if offset > 0 and hitflag[i+offset] == 1:
                yield i2, i1, getIntervalOverlap(i1, i2)
        
        offset = offset + 1        
        if idx[-1]+offset >= len(intervals):
            idx = idx[:-1] 
        idx = idx[np.where(intervals[idx, 1] >= intervals[idx+offset, 0] + minOverlap - 1)[0]]
    
def buildIntervalMatrix2(intervals, hitSet, minOverlap = 1, minFraction = 0):    
    intervals = np.vstack([x for x in hitSet if x in intervals] + [x for x in intervals if x not in hitSet])
    hitflag = np.zeros(len(intervals))
    hitflag[:len(hitSet)] = 1
    
    sortix = np.lexsort((intervals[:,1],intervals[:,0]))
    intervals = intervals[sortix]
    hitflag = hitflag[sortix]
    
    return intervals, hitflag

def genIntervalOverlaps(intervals, hitSet, minOverlap = 1, minFraction = 0):
    if len(intervals) == 0 or len(hitSet) == 0:
        return
    intervals, bounds, hitflag = buildIntervalMatrix(intervals, hitSet, minOverlap, minFraction)
    offset = 0
    idx = np.where(bounds[:, 1] + 1 >= intervals[:, 0])[0]
    while len(idx) > 0:
        ridx = idx[np.where((intervals[idx, 1] + 1 >= bounds[idx+offset, 0]) & (hitflag[idx] + hitflag[idx+offset] > 0))[0]]
        for i in ridx:
            i1, i2 = tuple(intervals[i]), tuple(intervals[i+offset])
            over = getIntervalOverlap(i1, i2)
            if over >= max(minOverlap, 0.5 * getIntervalLength(i1), 0.5 * getIntervalLength(i2)):
                yield i1, i2, over
        
        offset = offset + 1        
        if idx[-1]+offset >= len(intervals):
            idx = idx[:-1] 
        idx = idx[np.where(bounds[idx, 1] + 1 >= intervals[idx+offset, 0])[0]]
        
    #overlaps = np.minimum(intervals[ridx, 1], intervals[ridx+offset, 1]) - np.maximum(intervals[ridx, 0], intervals[ridx+offset, 0]) + 1
    
def buildIntervalMatrix(intervals, hitSet, minOverlap = 1, minFraction = 0):    
    intervals = np.vstack([x for x in hitSet if x in intervals] + [x for x in intervals if x not in hitSet])
    sortix = np.lexsort((intervals[:,1],intervals[:,0]))
    intervals = intervals[sortix]
    
    bounds = intervals[:,:2].copy()
    bounds[:,0] = intervals[:,0] + np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1) * minFraction)
    bounds[:,1] = intervals[:,1] - np.maximum(minOverlap, (intervals[:,1] - intervals[:,0] + 1) * minFraction)
    
    hitflag = np.zeros(len(intervals))
    hitflag[:len(hitSet)] = 1
    hitflag = hitflag[sortix]
    
    return intervals, bounds, hitflag    

def buildIntervalTree(intervals):
    intervals = np.vstack(list(intervals))
    intervals = intervals[np.lexsort((intervals[:,1],intervals[:,0]))]
    tree = np.zeros((len(intervals), 3), dtype = intervals.dtype)
    tree[:,:2] = intervals[:,:2]
    tree[:,2] = np.maximum.accumulate(tree[:,1])
    intervals = tree
    tree = np.zeros_like(intervals)
    buildIntervalSubtree(intervals, tree, 0, 0, len(intervals)-1)
    return tree

def buildIntervalSubtree(intervals, tree, c, x, y):
    mid = (x + y) // 2
    tree[c] = intervals[mid]
    if mid-1 >= x:
        buildIntervalSubtree(intervals, tree, c+1, x, mid-1)
    if y >= mid+1:
        buildIntervalSubtree(intervals, tree, c+1+mid-x, mid+1, y)
    
def findOverlappingIntervals(tree, i, minOverlap = 1, minFraction = 0):
    b = (i[0] + max(minOverlap, (i[1] - i[0] + 1) * minFraction), i[1] - max(minOverlap, (i[1] - i[0] + 1) * minFraction))
    return findOverlappingIntervalsSub(tree, i, b, 0, 0, len(tree)-1, minOverlap, minFraction)

def findOverlappingIntervalsSub(tree, i, b, c, x, y, minOverlap = 1, minFraction = 0):
    mid = (x + y) // 2
    result = set()
    node = tree[c]
    if node[0] <= b[1] + 1 and y >= mid+1:
        result.update(findOverlappingIntervalsSub(tree, i, b, c+1+mid-x, mid+1, y, minOverlap, minFraction))
    if node[2] + 1 >= b[0] and mid-1 >= x:
        result.update(findOverlappingIntervalsSub(tree, i, b, c+1, x, mid-1, minOverlap, minFraction))
    if getIntervalOverlap(i, node) >= max(minOverlap, minFraction * getIntervalLength(i), minFraction * getIntervalLength(node)):
        result.add(tuple((*node[:2], i[2])))
    return result

def buildIntervalTree1(intervals, lenseq):
    intervals = np.vstack(list(intervals))
    intervals = intervals[np.lexsort((intervals[:,1],intervals[:,0]))]
    return buildIntervalSubtree(intervals, 0, lenseq-1)

def buildIntervalSubtree1(intervals, x, y):
    if len(intervals) == 0:
        return None
    ctr = (x + y) / 2
    lints = intervals[intervals[:,1] < ctr]
    rints = intervals[intervals[:,0] > ctr]
    lt = buildIntervalSubtree(lints, x, ctr)
    rt = buildIntervalSubtree(rints, ctr, y)    
    clints = intervals[(intervals[:,0] <= ctr) & (intervals[:,1] >= ctr)]
    crints = clints[np.lexsort((clints[:,0], clints[:,1]))][::-1]    
    return (ctr, clints, crints, lt, rt)

def findOverlappingIntervals1(itree, interval,  minOverlap = 1, minFraction = 0):
    ls = findOverlappingIntervalsPoint(itree, interval[0], minOverlap, minFraction)
    rs = findOverlappingIntervalsPoint(itree, interval[1], minOverlap, minFraction)
    return ls.union(rs)

def findOverlappingIntervals2(itree, x, minOverlap = 1, minFraction = 0):
    if itree is None:
        return set()
    
    ctr, clints, crints, lt, rt = itree
    if x[0] <= ctr and x[1] >= ctr:
        result = set(tuple(i) for i in clints)
    elif x < ctr:
        result = findOverlappingIntervalsPoint(lt, x, minOverlap, minFraction)
        for qi in clints:
            if qi[0] <= x:
                result.add(tuple(qi))
            else:
                break
    elif x > ctr:
        result = findOverlappingIntervalsPoint(rt, x, minOverlap, minFraction)
        for qi in crints:
            if qi[1] >= x:
                result.add(tuple(qi))
            else:
                break    
    return result    

def findOverlappingIntervalsPoint(itree, x, minOverlap = 1, minFraction = 0):
    if itree is None:
        return set()
    
    ctr, clints, crints, lt, rt = itree
    if x == ctr:
        result = set(tuple(i) for i in clints)
    elif x < ctr:
        result = findOverlappingIntervalsPoint(lt, x, minOverlap, minFraction)
        for qi in clints:
            if qi[0] <= x:
                result.add(tuple(qi))
            else:
                break
    elif x > ctr:
        result = findOverlappingIntervalsPoint(rt, x, minOverlap, minFraction)
        for qi in crints:
            if qi[1] >= x:
                result.add(tuple(qi))
            else:
                break    
    return result    
        

def compareIntervalLists(block1, block2):
    #if len(block1) != len(block2):
    #    return None
    
    p1, p2 = 0, 0
    bigger, smaller = True, True
    while p1 < len(block1) and p2 < len(block2):
        c1, c2 = block1[p1], block2[p2]
        
        if c1[0] == c2[0] and c1[1] == c2[1]:
            p1 = p1 + 1
            p2 = p2 + 1
        elif c1[0] <= c2[0] and c1[1] >= c2[1]:
            p2 = p2 + 1
            smaller = False
            if not bigger:
                return None
        elif c2[0] <= c1[0] and c2[1] >= c1[1]:
            p1 = p1 + 1
            bigger = False
            if not smaller:
                return None
        elif c2[0] > c1[0]:
            p1 = p1 + 1
            smaller = False
            if p1 == len(block1) or not bigger:
                return None
        elif c1[0] > c2[0]:
            p2 = p2 + 1
            bigger = False
            if p2 == len(block2) or not smaller:
                return None
        else:
            return None
    
    if bigger and smaller:
        return 0
    elif bigger:
        return 1
    elif smaller:
        return -1

def checkIntervalListsCross(block1, block2):
    p1, p2 = 0, 0
    while p1 < len(block1) and p2 < len(block2):
        c1, c2 = block1[p1], block2[p2]
        if c1[1] >= c2[0] and c1[0] <= c2[1]:
            return True
        elif c1[0] > c2[1]:
            p2 = p2 + 1
        elif c2[0] > c1[1]:
            p1 = p1 + 1
            
    return False

def findContainedIntervals(list1, list2):
    i1, i2 = 0, 0
    result = []
    while i1 < len(list1) and i2 < len(list2):
        c1, c2 = list1[i1], list2[i2]
        if c1[0] >= c2[0] and c1[1] <= c2[1]:
            result.append(i1)
            i1 = i1 + 1
        elif c1[0] < c2[0]:
            i1 = i1 + 1
        else:
            i2 = i2 + 1
        
    return result
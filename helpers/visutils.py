
'''
Created on Feb 14, 2022

@author: Vlad
'''

import random
import math
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import os
from tools import external_tools


class Viewer:

    def __init__(self):
        self.fig = None  
        self.lines = []
        self.s1max = None
        self.s2max = None
        #self.polygons = []
   
    def showPicture(self):
        #matplotlib.use("Qt5Agg")
        figManager = plt.get_current_fig_manager()
        figManager.window.state('zoomed')
        #plt.show()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def closePicture(self):
        plt.close(self.fig)

    def savePicture(self, filePath):
        #figManager = plt.get_current_fig_manager()
        #figManager.window.state('zoomed')
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        #fig.savefig(outputFile, bbox_inches = 'tight', pad_inches = 0, dpi=300)
        #fig.savefig(outputFile.replace(".png", ".pdf"), bbox_inches = 'tight', pad_inches = 0)
        #fig.savefig(outputFile.replace(".png", ".eps"), bbox_inches = 'tight', pad_inches = 0)
        self.fig.savefig(filePath, facecolor = self.fig.get_facecolor(), dpi=300)
        print("Saved figure to {}".format(filePath))

    def drawLines(self):
        self.fig.clear()
        for line in self.lines:
            self.fig.add_artist(line)
    
    def drawMatrix(self, matrix, filePath, scolor1, scolor2 = None):
        self.s1max = matrix.shape[0]
        self.s2max = matrix.shape[1]
        self.lines = []
        #self.fig = plt.figure(figsize=(10*self.s2max/self.s1max, 10), facecolor=(0.0,0.0,0.0))
        self.fig = plt.figure(facecolor=(0.0,0.0,0.0))
        #self.buildGrid()
        if scolor2 is None:
            self.fillGrid(matrix.row, matrix.col, matrix.data, scolor1)
        else:
            self.fillGrid2(matrix.row, matrix.col, matrix.data, scolor1, scolor2)
        self.drawLines()
        self.savePicture(filePath)

    def drawMatrixAlt(self, matrix, filePath, scolor1, blowup = None):
        matrix = matrix.toarray()
        if blowup is not None:
            matrix = matrix.repeat(blowup, axis = 0).repeat(blowup, axis = 1)
        maxval = matrix.max()
        #imatrix = matrix / maxval
        #imatrix = np.zeros((matrix.shape[0], matrix.shape[1], 3))
        imatrix = np.array(scolor1) * matrix[:,:,None]/maxval
        #imatrix = np.multiply(np.array(scolor1), matrix[:,:,None]/maxval)
        plt.imsave(filePath, imatrix, origin = 'lower')

    def seqToScenePos(self, s1x, s2x):
        sx = (0.02 + 0.96 * s1x/self.s1max)
        sy = (0.02 + 0.96 * s2x/self.s2max)
        return sx, sy
    
    def buildGrid(self):
        scolor = (0,0.5,0.6)
        for s1 in range(self.s1max+1):
            x1, y1 = self.seqToScenePos(s1, 0)
            x2, y2 = self.seqToScenePos(s1, self.s2max)
            self.lines.append(plt.Line2D([x1, x2], 
                           [y1, y2], 
                           linewidth = 1, 
                           color = scolor,
                           zorder=100))
            break
    
    def fillGrid(self, xs, ys, vals, scolor):
        maxval = max(vals)
        for i in range(len(xs)):
            x, y = xs[i], ys[i]
            self.lines.append(Polygon([self.seqToScenePos(x,y), 
                                       self.seqToScenePos(x,y+1), 
                                       self.seqToScenePos(x+1,y+1), 
                                       self.seqToScenePos(x+1,y)], 
                                       color = scolor,
                                       alpha = vals[i]/maxval,
                                       zorder = 20))
    
    def fillGrid2(self, xs, ys, vals, scolor1, scolor2):
        maxval = max(vals)
        minval = min(vals)
        #acolor = ((scolor1[0] + scolor2[0])*0.5, (scolor1[1] + scolor2[1])*0.5, (scolor1[2] + scolor2[2])*0.5)
        acolor = (0,0,0)
        for i in range(len(xs)):
            x, y = xs[i], ys[i]
            if vals[i] >= 0:
                a = vals[i]/maxval
                c = (scolor1[0]*a + acolor[0]*(1-a), scolor1[1]*a + acolor[1]*(1-a), scolor1[2]*a + acolor[2]*(1-a))
            else:
                a = vals[i]/minval
                c = (scolor2[0]*a + acolor[0]*(1-a), scolor2[1]*a + acolor[1]*(1-a), scolor2[2]*a + acolor[2]*(1-a))
                
            self.lines.append(Polygon([self.seqToScenePos(x,y), 
                                       self.seqToScenePos(x,y+1), 
                                       self.seqToScenePos(x+1,y+1), 
                                       self.seqToScenePos(x+1,y)], 
                                       color = c,
                                       alpha = a,
                                       zorder = 20))
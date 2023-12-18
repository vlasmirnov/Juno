'''
Created on Dec 8, 2021

@author: Vlad
'''

import sqlite3
import os
import time
import numpy as np
import random as rnd
from scipy.sparse import *
import io
from data.config import configs
from helpers import mputils

def getExistingTables(dbPath):
    if not os.path.exists(dbPath):
        return set()
    return runWithRetries(10, 0.1, getExistingTablesSql, dbPath)

def readRowsFromTable(dbPath, table):
    if table not in getExistingTables(dbPath):
        return []
    return runWithRetries(10, 0.1, readRowsFromTableSql, dbPath, table)

def insertRowsIntoTable(dbPath, table, structure, deleteExisting, rows, journalModeOff = True):
    if len(rows) > 0:
        with mputils.FileLock(dbPath + ".lock"):
            runWithRetries(10, 0.1, insertRowsIntoTableSql, dbPath, table, structure, deleteExisting, rows, journalModeOff)

def readFullDb(dbPath):   
    dest = dbIntoMemory(dbPath)
    rows = dest.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = set(row[0] for row in rows)
    data = {table : dest.execute("SELECT * FROM {}".format(table)).fetchall() for table in tables}
    dest.close()
    return data

def dbIntoMemory(dbPath):
    #dest = sqlite3.connect(':memory:')
    #source.backup(dest)
    #source.close() 
    source = sqlite3.connect(dbPath)
    tempfile = io.StringIO()
    for line in source.iterdump():
        tempfile.write('%s\n' % line)
    source.close()
    tempfile.seek(0)

    dest = sqlite3.connect(":memory:")
    dest.cursor().executescript(tempfile.read())
    dest.commit()
    return dest
    
def getExistingTablesSql(dbPath):
    con = sqlite3.connect(dbPath)
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    con.close()
    tables = set(row[0] for row in rows)
    return tables

def readRowsFromTableSql(dbPath, table):
    con = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
    rows = con.execute("SELECT * FROM {}".format(table)).fetchall()  
    con.close()
    return rows

def insertRowsIntoTableSql(dbPath, table, structure, deleteExisting, rows, journalModeOff = True):
    con = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
    #con.isolation_level = None
    con.execute("BEGIN TRANSACTION")
    if journalModeOff:
        con.execute("PRAGMA journal_mode = OFF")
    if structure is not None:
        con.execute("CREATE TABLE IF NOT EXISTS {} ({})".format(table, structure))
    if deleteExisting:
        con.execute("DELETE FROM {}".format(table))
    qMarks = ", ".join('?' for i in range(len(rows[0]))) 
    con.executemany("INSERT INTO {} VALUES ({})".format(table, qMarks), rows)
    con.execute("COMMIT")    
    con.close()

def deleteDb(dbPath):
    if os.path.exists(dbPath):
        os.remove(dbPath)

def vacuumdb(dbPath):
    clustersCon = sqlite3.connect(dbPath) 
    clustersCon.execute("VACUUM")
    clustersCon.commit()
    clustersCon.close()

def runWithRetries(tries, interval, fn, *args, **kwargs):
    for x in range(tries):
        try:
            return fn(*args, **kwargs)
            break
        except Exception as exc:
            if x < tries - 1:
                configs().log("Exception in {}:\n{}".format(fn.__name__, exc))
                configs().log("Retrying.. {}/{}".format(x+2, tries))
                time.sleep(rnd.random()*interval + interval)
                interval = interval * 2
            else:
                raise
    
def numpyToSqlite(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def sqliteToNumpy(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

def scipyToSqlite(arr):
    out = io.BytesIO()
    save_npz(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def sqliteToScipy(text):
    out = io.BytesIO(text)
    out.seek(0)
    return load_npz(out)

sqlite3.register_adapter(np.ndarray, numpyToSqlite)
sqlite3.register_converter("nparray", sqliteToNumpy)
sqlite3.register_adapter(coo_matrix, scipyToSqlite)
sqlite3.register_converter("sparray", sqliteToScipy)
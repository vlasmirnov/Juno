'''
Created on Jan 4, 2022

@author: Vlad
'''

from multiprocessing import set_start_method
import argparse
from data import config
from data.config import configs, none_or_str, none_or_int, none_or_float, none_or_path
import traceback
from operations import aligner_operations
from helpers import mputils


def main(argParsers):
    mputils.setSigHandlers()
    config.initConfigs(argParsers)
    configs().printAppConfigs()
    
    try:
        if configs().mode == "gui":
            from gui import display
            display.launchDisplay()
        else:
            aligner_operations.cliOperation()
    except:
        configs().error("Aborted with an exception..")
        configs().error(traceback.format_exc())                   
        raise
    finally:
        configs().closeWorkspace()


if __name__ == '__main__':
    set_start_method("spawn")
    argParsers = {}
    
    #Application arguments
    appParser = argparse.ArgumentParser()
    argParsers["APP"] = appParser
    
    appParser.add_argument("-d", "--dir", type=none_or_path, help="Path to working directory", required=False)
    appParser.add_argument("-m", "--mode", type=none_or_str, help="Application mode (gui or cli)", required=False)    
    appParser.add_argument("-c", "--config_file", type=none_or_path, help="Path to user config file", required=False)    
    appParser.add_argument("--operation", type=none_or_str, required=False)    
    appParser.add_argument("-t", "--threads", type=none_or_int, help="Number of threads to use", required=False)
    appParser.add_argument("-u", "--update", type=none_or_str, required=False)
    appParser.add_argument("--log", dest = "loggingEnabled", type=none_or_str, required=False)    
    appParser.add_argument("--busco_dir", dest = "buscoDir", type=none_or_path, help="(debugging) Path to busco directory", required=False)
    
    
    #Sequence arguments
    sequenceParser = argparse.ArgumentParser()
    argParsers["SEQUENCES"] = sequenceParser

    sequenceParser.add_argument("-s", "--sequence_paths", dest = "sequencePaths", type=none_or_str, nargs="+",
                        help="Paths to input sequences files", required=False, action = config.PathListAction)
    sequenceParser.add_argument("-r", "--ref", dest = "ref", type=none_or_str, nargs="+", required=False)
    sequenceParser.add_argument("-q", "--query", dest = "query", type=none_or_str, nargs="+", required=False)
    
    #Matrix arguments
    matrixParser = argparse.ArgumentParser()
    argParsers["MATRIX"] = matrixParser

    matrixParser.add_argument("--matrix_sketch_limit", dest = "sketchLimit", type=none_or_int, required=False)
    matrixParser.add_argument("--matrix_keep_kmers", dest = "keepKmers", action='store_true')
    matrixParser.add_argument("--matrix_chunk_size", dest = "chunkSize", type=none_or_int, required=False)
    
    matrixParser.add_argument("--matrix_patches", dest = "patches", type=none_or_int, nargs="+", required=False)
    matrixParser.add_argument("--matrix_kmers", dest = "kmers", type=none_or_int, nargs="+", required=False)
    matrixParser.add_argument("--matrix_trim_degrees", dest = "trimDegrees", type=none_or_int, nargs="+", required=False)
    matrixParser.add_argument("--matrix_trim_islands", dest = "trimIslands", type=none_or_int, nargs="+", required=False)

    #Match arguments
    matchParser = argparse.ArgumentParser()
    argParsers["MATCH"] = matchParser
    matchParser.add_argument("--match_min_width", dest = "minWidth", type=none_or_int, required=False)
    matchParser.add_argument("--match_max_width", dest = "maxWidth", type=none_or_int, required=False)
    matchParser.add_argument("--match_max_gap", dest = "maxGap", type=none_or_int, required=False)
    matchParser.add_argument("--match_min_width_ratio", dest = "minWidthRatio", type=none_or_float, required=False)
    
    #Cluster arguments
    clusterParser = argparse.ArgumentParser()
    argParsers["CLUSTER"] = clusterParser
    clusterParser.add_argument("--cluster_parameter", dest = "parameter", type=none_or_int, required=False)
    clusterParser.add_argument("--cluster_policy", dest = "policy", type=none_or_str, required=False)
    clusterParser.add_argument("--cluster_limit", dest = "climit", type=none_or_int, required=False)
    
    #Cluster arguments
    alignParser = argparse.ArgumentParser()
    argParsers["ALIGN"] = alignParser
    alignParser.add_argument("--align_limit", dest = "limit", type=none_or_int, required=False)
    alignParser.add_argument("--align_factor", dest = "factor", type=none_or_float, required=False)
    
    #MAF arguments
    mafParser = argparse.ArgumentParser()
    argParsers["MAF"] = mafParser
    mafParser.add_argument("--maf_policy", dest = "policy", type=none_or_str, required=False)
    mafParser.add_argument("--maf_path", dest = "path", type=none_or_path, required=False)
    mafParser.add_argument("--maf_max_distance", dest = "maxDistance", type=none_or_float, required=False)
    mafParser.add_argument("--maf_seq_filter", dest = "seqFilter", type=none_or_str, required=False)
    mafParser.add_argument("--maf_single_file", dest = "singleFile", action='store_true')
    mafParser.add_argument("--maf_ref_gaps", dest = "refGaps", action='store_true')
    
    main(argParsers)
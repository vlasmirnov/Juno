# Juno
Quick and Scalable Reference-Based Genome Alignment

- - - -

## Overview
Juno is a tool for scalable multiple genome alignment. The basic procedure is outlined below.

1. The input is a set of FASTA files. Each file is assumed to correspond to an assembly containing one or more chromosome-level sequences.
2. The tool scans the genomes to enumerate kmer counts and positions.
3. The kmer counts are used to build telescoping similarity matrices between the reference and query sequences. 
4. The similarity matrices are used to compiled a set of locally-colinear blocks (LCBs)
5. A subset of the longest LCBs (based on alignment factor parameter) is selected and locally aligned with MAFFT.
6. The aligned LCBs are collated into the final MAF file.

- - - -

## Installing and running Juno
  
You can download and extract the code from this repository to a directory of your choice.  
Then, you can run Juno with 

**Linux**  
*python3 <directory_path>/juno.py <arguments>*

**Windows**  
*python <directory_path>/juno.py <arguments>*

- - - -

## Dependencies
* Python 3
* MAFFT (windows and linux versions are included)

The bundled MAFFT can be switched out for a local aligner of your choice.

- - - -

## Getting Started
The "example" directory contains a small dataset of 4 chromosomes. 
You can navigate your terminal to the example directory and try a few ways of running Juno:
(on Windows, replace "python3" with "python")

**Using basic command line arguments**  
*python3 "../juno.py" -s sequences -d output -r Inachis_io -t 6 --align_factor 0.03*

*-s* is the path(s) to the input sequence file(s) or directory(ies)  
*-d* specifies the output directory  
*-r* specifies the reference species or sequences to use  
*-t* specifies how many threads to use (-1 for all)  
*--align_factor* controls how aggressive the alignment will be (default 1) . It (very) roughly represents the alignment coverage to target. 0.03 is a tiny value that allows the example to finish quickly and produce a very sparse alignment file.

**Using user-defined config file**  
python3 "../juno.py" -c user.ini -d output -r Vanessa_atalanta

The example config file sets the same parameters as above. Nevertheless, they can still be overriden on the command-line: in this case, we set a different reference species.   

- - - -

## Program Arguments

Juno accepts program arguments from three sources. 
The defaults are set in Juno's base config.ini file, and can be overriden in an optional user .ini file specified by the "-c" flag: "-c user.ini". 
Finally, individual arguments can be set by the user through the command line: "--<arg_name> <value>". This will override their values in the .ini files, if any.
For example, "--sequence_paths <path>" will set the SEQUENCE_PATHS parameter, and "--align_factor 2" will set the ALIGN_FACTOR parameter.

The most important parameters are explained below.

DIR ("-d"): Sets the output directory.  
SEQUENCE_PATHS ("-s"): List of files and/or directories containing input sequences in FASTA format.  
REF ("-r"): List of species and/or chromosomes to set as alignment reference. (A reference species will generate alignments for each of its chromosomes.)  
THREADS ("-t"): Number of threads to recruit. (-1 to use all available.)  
CONFIG_FILE ("-c"): Points to optional user config file.

**Matrix generation**  
MATRIX_PATCHES: List of interval sizes for telescoping similarity matrices.  
MATRIX_KMERS: List of kmer sizes for telescoping similarity matrices.  
MATRIX_TRIM_DEGREES: List of trim degrees (max number of best cells to keep in each row/column) for telescoping similarity matrices.  
MATRIX_SKETCH_LIMIT: The number of kmer sketch files to cache on disk. Reduce if there is not enough disk space.  
MATRIX_CHUNK_SIZE: Breaks the similarity matrices into smaller pieces for dot product. Lower values reduce RAM usage, at a modest cost of runtime.  

**LCB generation**  
MATCH_MIN_WIDTH: Minimum LCB width  
MATCH_MAX_WIDTH: Maximum LCB width (longer LCBs are broken into chunks of this size)  
MATCH_MAX_GAP: Maximum gap allowed within a single LCB.  
MATCH_MIN_WIDTH_RATIO: Minimum allowable ratio between the two sequence lengths within a single LCB. (Prevents LCBs between very uneven sequence lengths.)  

**LCB alignment**  
ALIGN_FACTOR: Governs how many of the largest LCBs will be recruited and aligned with MAFFT. Larger values produce a larger, more aggressive alignment.  
The align factor roughly represents the amount of coverage to target, the default being 1. Setting it to 0.5, for example, would use half as much LCB sequence, and 2 would use twice as much.  
ALIGN_LIMIT: Upper bound number of LCBs to be aligned, hedges against weird situations where too many blocks have been recruited.  

**MAF**  
MAF_POLICY: Determines how to compile the final MAF file. "unidirectional" (default) will use both ref-to-query best hits and query-to-ref best hits. "ref" will only use ref-to-query best hits. "bidirectional" will use only those hits that are belong to both sets.   
MAF_MAX_DISTANCE: Don't include blocks with p-distance below this value.  
MAF_SEQ_FILTER: "species" (default) will treat entire species as queries for the MAF_POLICY, while "chromosome" will treat individual chromosomes as queries.  

- - - -

## Things to Keep in Mind

* Juno works best with chromosome-level assemblies. Very fragmented assemblies with large numbers of separate sequences will run much more slowly.
* ALIGN_FACTOR is the main parameter that controls alignment size and aggressiveness. If the resulting alignment is too heavy/noisy, try reducing the ALIGN_FACTOR to 0.5, 0.25, etc. Conversely, try 2, 3, 5, etc. for a more aggressive alignment.
* Juno will not overwrite existing MAF files, or existing matrix/match/LCB alignments from the databases in the "working_data" directory.
* If Juno crashes or is stopped abnormally, please delete the "z_tasks.txt" file to ensure a clean run.


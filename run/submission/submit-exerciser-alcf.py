#!/usr/bin/env python
#COBALT -A CSC250STDM10
##COBALT -n 128
##COBALT -t 30

# Load python modules
import subprocess
import argparse
import os
import sys
print("Using Python version: "+str(sys.version_info[0]))

# Machine Specific
machine   = "theta"
srcroot   = "/home/zamora/hdf5_root_dir"
fsroot    = "/projects/CSC250STDM10/rzamora"
ppn       = 32
#machine   = "other"
#srcroot   = "/Users/rzamora/IO"
#fsroot    = "/Users/rzamora/IO/CCIO/scratch"
#ppn       = 4

# Important Benchmarking Settings
benchname = "exerciser-hdf5-devlop-20190107"
ccio      = False
runroot   = fsroot + "/benchscratch"
benchroot = srcroot + "/ExaHDF5BenchMarks"
outroot   = benchroot + "/run/results/" + benchname
execname  = benchroot + "/exerciser/hdf5Exerciser"

# Parse command line inputs
parser = argparse.ArgumentParser()
parser.add_argument("--machine", dest="machine", default=machine,
                    help="system name -- Available: theta, vesta, other [default="+machine+"]")
parser.add_argument("--execname", dest="execname", default=execname,
                    help="Path to Exerciser executable [default="+execname+"]")
parser.add_argument("--ppn", dest="ppn", type=int, default=ppn,
                    help="Processes to use per node [default="+str(ppn)+"]")
parser.add_argument("--ccio", dest="ccio", action="store_true", default=ccio,
                    help="Using the CCIO version of HDF5 (Set CCIO Env Vars) [default="+str(ccio)+"]")
args = parser.parse_args()
machine   = args.machine
execname  = args.execname
ppn       = args.ppn
use_ccio  = args.ccio

# Hard-coded Inputs
cb_mult   = 1
cb_div    = 1
rshift    = True
dim       = 2
dimranks  = [ 32, 32 ]
minb      = 1024
bmult     = 4
nsizes    = 1
lfs_count = 52           # Number of Stripes in LUSTRE (Number of Aggs in CCIO)
lfs_size  = 16           # Size of Stripes in LUSTRE (Size of Aggs in CCIO)
nodes     = 1            # Ignored if machine is "vesta" or "theta"
nocheck   = False        # Can turn off data validation in exerciser
if machine == "theta":
    fd_agg = False       # Don't use file-domain aggregator mapping on LUSTRE
else:
    fd_agg = True

# Check that machine is supported
if not machine in ["theta", "vesta", "other"]:
    print("Error - machine "+machine+" not recongnized")
    sys.exit(1)

# Define Env vars that we wont change here
envs_const = [ ]
if machine in ["theta", "vesta"]:
    nodes  = int(os.environ['COBALT_JOBSIZE'])
nranks     = ppn * nodes
cb_nodes   = (lfs_count * cb_mult) / cb_div
cb_stride  = (nranks) / cb_nodes
fsb_size   = lfs_size * (1024 * 1024)
fsb_count  = lfs_count
if machine == "theta":
    # Allow module load/swap/list etc:
    execfile(os.environ['MODULESHOME']+'/init/python.py')
    #os.environ['MPICH_MPIIO_HINTS'] = '*:cray_cb_write_lock_mode=1'
    os.environ['MPICH_NEMESIS_ASYNC_PROGRESS'] = 'ML'
    os.environ['MPICH_MAX_THREAD_SAFETY'] = 'multiple'
    #module('unload','darshan')
elif machine == "vesta":
    envs_const.append("BGLOCKLESSMPIO_F_TYPE=0x47504653")
else:
    if use_ccio:
        if ppn>0: os.environ['HDF5_CCIO_TOPO_PPN'] = str(ppn)
if use_ccio:
    if fd_agg: os.environ['HDF5_CCIO_FD_AGG']='yes'

# Env Var Helper Funciton
def export_envs( envs_dyn ):

    for env in envs_dyn:
        env_split  = env.split("=")
        env_name   = env_split[0]
        env_value  = env_split[1]
        subprocess.call(["echo","Setting "+env_name+" to "+env_value+"."], stdout=outf)
        os.environ[ env_name ] = env_value

# Run-command Helper Funciton
def get_runjob_cmd( envs_dyn ):

    if machine == "vesta":
        cmd = ["runjob"]
        cmd.append("--np");    cmd.append(str(nranks))
        cmd.append("-p");      cmd.append(str(ppn))
        cmd.append("--block"); cmd.append(os.environ['COBALT_PARTNAME'])

        # Environment variables added here
        for env in envs_const:
            cmd.append("--envs");  cmd.append(env)
        for env in envs_dyn:
            cmd.append("--envs");  cmd.append(env)

        # Exerciser args
        cmd.append(":"); cmd.append(execname)
        cmd.append("--numdims"); cmd.append(str(dim))
        cmd.append("--minels")
        for i in range(dim): cmd.append(str(minb))
        cmd.append("--bufmult");
        for i in range(dim): cmd.append(str(bmult));
        cmd.append("--nsizes"); cmd.append(str(nsizes))
        if not (dimranks==None):
            cmd.append("--dimranks")
            for i in range(dim): cmd.append(str(dimranks[i]))
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
        if nocheck:
            cmd.append("--maxcheck");cmd.append("0")

    elif machine == "theta":
        export_envs( envs )
        # Define env and part of aprun command that wont change
        #os.environ["MPICH_MPIIO_TIMERS"]="1"
        #os.environ["MPICH_MPIIO_STATS"]="1"
        #os.environ["MPICH_MPIIO_AGGREGATOR_PLACEMENT_DISPLAY"]="1"
        #os.environ["PMI_LABEL_ERROUT"]="1"
        #os.environ["MPICH_MPIIO_CB_ALIGN"]="2"
        #os.environ["MPICH_MPIIO_HINTS"]="*:romio_ds_write=disable"
        subprocess.Popen('ulimit -c unlimited', shell=True)
        cmd = ["aprun"]
        cmd.append("-n"); cmd.append(str(nranks)); cmd.append("-N"); cmd.append(str(ppn))
        cmd.append("-d"); cmd.append("1"); cmd.append("-j"); cmd.append("1")
        cmd.append("-cc"); cmd.append("depth"); cmd.append(execname)
        cmd.append("--numdims"); cmd.append(str(dim))
        cmd.append("--minels")
        for i in range(dim): cmd.append(str(minb))
        cmd.append("--bufmult");
        for i in range(dim): cmd.append(str(bmult));
        cmd.append("--nsizes"); cmd.append(str(nsizes))
        if not (dimranks==None):
            cmd.append("--dimranks")
            for i in range(dim): cmd.append(str(dimranks[i]))
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
        if nocheck:
            cmd.append("--maxcheck");cmd.append("0")

    else:
        export_envs( envs )
        cmd = ["mpirun"]
        cmd.append("-n"); cmd.append(str(nranks))
        cmd.append(execname)
        cmd.append("--numdims"); cmd.append(str(dim))
        cmd.append("--minels")
        for i in range(dim): cmd.append(str(minb))
        cmd.append("--bufmult");
        for i in range(dim): cmd.append(str(bmult));
        cmd.append("--nsizes"); cmd.append(str(nsizes))
        if not (dimranks==None):
            cmd.append("--dimranks")
            for i in range(dim): cmd.append(str(dimranks[i]))
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
        if nocheck:
            cmd.append("--maxcheck");cmd.append("0")
        #cmd.append("--keepfile")
        cmd.append("--derivedtype")
        cmd.append("--metacoll")
        cmd.append("--addattr")
        cmd.append("--memblock");cmd.append("8")

    return cmd

def print_cmd( cmd ):
    sys.stdout.write('Using Run Command:\n')
    for val in cmd:
        sys.stdout.write('%s ' % (val))
    sys.stdout.write('\n')

# Create top "scratch" directory (runroot):
if not os.path.isdir(runroot): subprocess.call(["mkdir",runroot])

# Create "scratch" directory for current benchmark campaign (runbench):
runbench = runroot + "/" + benchname
if not os.path.isdir(runbench): subprocess.call(["mkdir",runbench])

# Create directory for actual I/O operations (rundir):
rundir = runbench+"/count."+str(lfs_count)+".size."+str(lfs_size)+".nodes."+str(nodes)+".ppn."+str(ppn)
if not os.path.isdir(rundir): subprocess.call(["mkdir",rundir])

# Create "output" directory for current benchmark campaign (outroot):
if not os.path.isdir(outroot): subprocess.call(["mkdir",outroot])

# Create directory for actual results (outdir):
outdir = outroot+"/count."+str(lfs_count)+".size."+str(lfs_size)+".nodes."+str(nodes)+".ppn."+str(ppn)
if not os.path.isdir(outdir): subprocess.call(["mkdir",outdir])

# Determine the "jobid"
if machine == "other":
    jobid_i = 0
    while os.path.exists( outdir+"/results."+str(jobid_i) ):
        jobid_i += 1
    jobid = str(jobid_i)
else: jobid = os.environ['COBALT_JOBID']

# Go to run directory
os.chdir(rundir)

# Now, run the job (with output written to "outdir/results.<jobid>")
with open(outdir+"/results."+jobid, "a") as outf:

    if machine == "theta":
        # Set lustre stripe properties
        subprocess.call(["lfs","setstripe","-c",str(lfs_count),"-S",str(lfs_size)+"m","."])

    if use_ccio:

        # CCIO (Default)
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[EXPERIMENT] [0] [Default-CCIO]:"], stdout=outf)
        envs = [
        "HDF5_CCIO_CB_SIZE="+str(fsb_size),
        "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
        "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
        "HDF5_CCIO_DEBUG=no",
        "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
        "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=no",
        "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=0",
        "HDF5_CCIO_TOPO_CB_SELECT=no"
        ]
        cmd = list( get_runjob_cmd( envs ) ); print_cmd(cmd)
        subprocess.call(cmd, stdout=outf)

        # Topology-aware CCIO (Data)
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[EXPERIMENT] [1] [Topology-Aware-CCIO-Data]:"], stdout=outf)
        envs = [
        "HDF5_CCIO_CB_SIZE="+str(fsb_size),
        "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
        "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
        "HDF5_CCIO_DEBUG=no",
        "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
        "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=no",
        "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=0",
        "HDF5_CCIO_TOPO_CB_SELECT=data"
        ]
        cmd = list( get_runjob_cmd( envs ) ); print_cmd(cmd)
        subprocess.call(cmd, stdout=outf);

    else:

        # HDF5 Default Independent
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[EXPERIMENT] [0] [Independent]:"], stdout=outf)
        envs = [ ]
        cmd = list( get_runjob_cmd( envs ) ); cmd.append("--indepio"); print_cmd(cmd)
        subprocess.call(cmd, stdout=outf)

        # HDF5 Default Collective
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[EXPERIMENT] [0] [Collective]:"], stdout=outf)
        envs = [ ]
        cmd = list( get_runjob_cmd( envs ) ); print_cmd(cmd)
        subprocess.call(cmd, stdout=outf)

# ---------------------------------------------------------------------------- #
#  Done.
# ---------------------------------------------------------------------------- #

cmd = ["echo","done"]
subprocess.call(cmd)

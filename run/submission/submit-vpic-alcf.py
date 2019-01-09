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
benchname = "vpic-hdf5-devlop-20190107"
runroot   = fsroot + "/benchscratch"
benchroot = srcroot + "/ExaHDF5BenchMarks"
outroot   = benchroot + "/run/results/" + benchname
execname  = benchroot + "/vpicio_hdf5/bin/vpicio_uni_h5_"

# Parse command line inputs
parser = argparse.ArgumentParser()
parser.add_argument("--machine", dest="machine", default=machine,
                    help="system name -- Available: theta, vesta, other [default="+machine+"]")
parser.add_argument("--execname", dest="execname", default=execname,
                    help="Path to Exerciser executable [default="+execname+"]")
parser.add_argument("--ppn", dest="ppn", type=int, default=ppn,
                    help="Processes to use per node [default="+str(ppn)+"]")
parser.add_argument("--ntrials", dest="ntrials", type=int, default=10,
                    help="Number of trials for both Ind and Col [default=10]")
args = parser.parse_args()
machine   = args.machine
execname  = args.execname
ppn       = args.ppn
ntrials   = args.ntrials

# Hard-coded Inputs
lfs_count = 52
lfs_size  = 16

# Env vars that we wont change here:
envs_const = [ ]
if machine == "other":
    nodes      = 1
else:
    nodes      = int(os.environ['COBALT_JOBSIZE'])
nranks     = ppn * nodes

if machine == "theta":
    # Allow module load/swap/list etc:
    execfile(os.environ['MODULESHOME']+'/init/python.py')
    #os.environ['MPICH_MPIIO_HINTS'] = '*:cray_cb_write_lock_mode=1'
    os.environ['MPICH_NEMESIS_ASYNC_PROGRESS'] = 'ML'
    os.environ['MPICH_MAX_THREAD_SAFETY'] = 'multiple'
    #module('unload','darshan')
elif machine == "vesta":
    envs_const.append("BGLOCKLESSMPIO_F_TYPE=0x47504653")

def export_envs( envs_dyn ):

    for env in envs_dyn:
        env_split  = env.split("=")
        env_name   = env_split[0]
        env_value  = env_split[1]
        subprocess.call(["echo","Setting "+env_name+" to "+env_value+"."], stdout=outf)
        os.environ[ env_name ] = env_value

def get_runjob_cmd( envs_dyn, exec_tag ):

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

        # Binary
        cmd.append(":"); cmd.append(execname+exec_tag)
        cmd.append("testfile")

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
        cmd.append("-cc"); cmd.append("depth"); cmd.append(execname+exec_tag)
        cmd.append("testfile")

    else:

        export_envs( envs )
        cmd = ["mpirun"]
        cmd.append("-n"); cmd.append(str(nranks))
        cmd.append(execname+exec_tag)
        cmd.append("testfile")

    return cmd

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

    for itrial in range(ntrials):
        # INDEPENDENT
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[TRIAL] ["+str(itrial)+"] [INDEPENDENT]:"], stdout=outf)
        envs = [ ]
        cmd = list( get_runjob_cmd( envs, "ind" ) ); print(cmd)
        subprocess.call(cmd, stdout=outf)

    for itrial in range(ntrials):
        # COLLECTIVE
        subprocess.call(["echo",""], stdout=outf)
        subprocess.call(["echo","[TRIAL] ["+str(itrial)+"] [COLLECTIVE]:"], stdout=outf)
        envs = [ ]
        cmd = list( get_runjob_cmd( envs, "col" ) ); print(cmd)
        subprocess.call(cmd, stdout=outf)

# ---------------------------------------------------------------------------- #
#  Done.
# ---------------------------------------------------------------------------- #

cmd = ["echo","done"]
subprocess.call(cmd)

EXE=hdf5Exerciser

# Mac
HDF5_ROOT=/Users/rzamora/IO/CCIO
BLD_DIR=mpich
MPICC=mpicc

default: ${EXE}

HDF5_INSTALL_DIR=${HDF5_ROOT}/library/install/${BLD_DIR}

exerciser.o: exerciser.c
	${MPICC} -c -g -O3 -I${HDF5_INSTALL_DIR}/include exerciser.c -o exerciser.o

${EXE}: exerciser.o
	${MPICC} exerciser.o -o ${EXE} -L${HDF5_INSTALL_DIR}/lib -lhdf5 -lz

clean:
	rm -f exerciser.o
	rm -f ${EXE}

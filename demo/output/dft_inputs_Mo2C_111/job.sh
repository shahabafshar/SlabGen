#!/bin/bash
#SBATCH --job-name=Mo2C_111_relax
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=36
#SBATCH --time=24:00:00
#SBATCH --partition=default

module load vasp
mpirun vasp_std

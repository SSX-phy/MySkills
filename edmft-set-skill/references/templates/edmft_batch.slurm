#!/bin/bash
#SBATCH -J edmft ##!! 作业名称，用户可修改
#SBATCH -p batch ##!! 队列名称，用户可修改
#SBATCH -N 2 --ntasks-per-node=64 ##!!这里节点数只能是1。–ntasks-per-node=64不修改
#SBATCH --time=2-0:0:0 ##!! 作业时间，格式为days-hours:minutes:seconds
#SBATCH --mem=224G ##!! 每节点可用内存，不超过256G
##SBATCH -d afterok:$jobid ##!!设置作业依赖关系，待任务号为jobid的作业完成后开始
#SBATCH -o out.%j ##!! 标准输出，文件名为out.jobid
#SBATCH -e err.%j ##!! 标准错误，文件名为err.jobid

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export FI_PROVIDER=verbs   ##!! IB 网络参数，不能修改
export UCX_NET_DEVICES=mlx5_0:1 ##!! IB 网络参数，不能修改
cd $SLURM_SUBMIT_DIR
scontrol show hostname $SLURM_NODELIST > host.txt

echo "mpirun -np $SLURM_NTASKS" > mpi_prefix.dat
run_dmft.py -p -so>& nohup.dat

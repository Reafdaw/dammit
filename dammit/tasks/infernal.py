#!/usr/bin/env python
from __future__ import print_function
import os

from doit.action import CmdAction
from doit.task import clean_targets

from ..profile import profile_task
from ..utils import which, doit_task
from ..parallel import parallel_fasta


@doit_task
@profile_task
def get_cmpress_task(db_filename, params=None, task_dep=None):
    '''Run Infernal's `cmpress` on a covariance model database.

    Args:
        db_filename (str): Path to the covariance model database.
        params (list): Extra parameters to pass to the executable.
        task_dep (str): Task dep to give doit task.

    Returns:
        dict: A doit task.
    '''

    cmd = [which('cmpress')]
    if params is not None:
        cmd.extend([str(p) for p in params])
    cmd.append(db_filename)
    cmd = ' '.join(cmd)

    task_d = {'name': 'cmpress:' + os.path.basename(db_filename),
              'actions': [cmd],
              'targets': [db_filename + ext for ext in ['.i1f', '.i1i', '.i1m', '.i1p']],
              'uptodate': [True],
              'clean': [clean_targets]}

    if task_dep is not None:
        task_d['task_dep'] = task_dep

    return task_d


@doit_task
@profile_task
def get_cmscan_task(input_filename, output_filename, db_filename,
                    cutoff=0.00001, n_threads=1, pbs=False, params=None):
    '''Run Infernal's `cmscan` on the given FASTA and covariance model database.

    Args:
        input_filename (str): Path to the input FASTA.
        output_filename (str): Path to store results.
        db_filename (str): Path to formatted covariance model database.
        cutoff (float): e-value cutoff to filter by.
        n_threads (int): Number of threads to run with via gnu-parallel.
        pbs (bool): If True, pass parameters to gnu-parallel for running on
            a cluster.
        params (list): Extra parameters to pass to executable.

    Returns:
        dict: A doit task.
    '''

    name = 'cmscan:' + os.path.basename(input_filename) + '.x.' + \
           os.path.basename(db_filename)
    stat = output_filename + '.cmscan.out'

    exc = which('cmscan')
    cmd = [exc]
    if params is not None:
        cmd.extend([str(p) for p in params])
    cmd.extend(['--cpu', '1', '--rfam', '--nohmmonly',
           '-E', str(cutoff), '--tblout', '/dev/stdout', '-o', stat,
           db_filename, '/dev/stdin'])
    cmd = parallel_fasta(input_filename, output_filename, cmd, n_threads,
                         pbs=pbs)

    return {'name': name,
            'actions': [cmd],
            'file_dep': [input_filename, db_filename, db_filename + '.i1p'],
            'targets': [output_filename, stat],
            'clean': [clean_targets]}
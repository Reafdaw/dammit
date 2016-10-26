#!/usr/bin/enb python
from __future__ import print_function

import logging
import os
from os import path
import sys

from doit.dependency import Dependency, SqliteDB
from shmlast.last import lastdb_task as get_lastdb_task

from . import ui
from .handler import TaskHandler
from .tasks.hmmer import get_hmmpress_task
from .tasks.infernal import get_cmpress_task
from .tasks.shell import (get_download_and_gunzip_task,
                          get_download_and_untar_task)

def get_handler(config):
    '''Build the TaskHandler for the database prep pipeline. The
    handler will not have registered tasks when returned.

    Args:
        config (dict): Config dictionary, which contains the command
            line arguments and the entries from the config file.
        databases (dict): The database dictionary from `databases.json`.

    Returns:
        handler.TaskHandler: A constructed TaskHandler.
    '''

    logger = logging.getLogger('DatabaseHandler')
    logger.debug('get_handler')

    handler = TaskHandler(config['database_dir'],
                          logger, 
                          db='databases',
                          backend=config['doit_backend'],
                          verbosity=config['verbosity'])

    return handler


def default_database_dir(logger):
    '''Get the default database directory: checks the environment
    for a DAMMIT_DB_DIR variable, and if it is not found, returns
    the default location of `$HOME/.dammit/databases`.

    Args:
        logger (logging.logger): Logger to write to.
    Returns:
        str: Path to the database directory.
    '''

    try:
        directory = os.environ['DAMMIT_DB_DIR']
        logger.debug('found DAMMIT_DB_DIR env variable')
    except KeyError:
        logger.debug('no DAMMIT_DB_DIR or --database-dir, using'\
                     'default')
        directory = path.join(os.environ['HOME'], '.dammit', 'databases')
    return directory


def print_meta(handler):
    '''Print metadata about the database pipeline.

    Args:
        handler (handler.TaskHandler): The database task handler.
    '''

    print(ui.header('Info', level=4))
    info = {'Doit Database': handler.dep_file,
            'Database Directory': handler.directory}
    print(ui.listing(info))

def install(handler):
    '''Run the database prep pipeline from the given handler.
    '''

    print(ui.header('Database Install', level=3))
    print_meta(handler)
    msg = '*All database tasks up-to-date.*'
    uptodate, statuses = handler.print_statuses(uptodate_msg=msg)
    if not uptodate:
        print('Installing...')
        handler.run()
    else:
        print('Nothing to install!')
        sys.exit(0)


def check_or_fail(handler):
    '''Check that the handler's tasks are complete, and if not, exit
    with status 2.
    '''

    print(ui.header('Database Check', level=3))
    print_meta(handler)
    msg = '*All database tasks up-to-date.*'
    uptodate, statuses = handler.print_statuses(uptodate_msg=msg)
    if not uptodate:
        print(ui.paragraph('Must install databases to continue. To do so,'
                           ' run `dammit databases --install`. If you have'
                           ' already installed them, make sure you\'ve given'
                           ' the correct location to `--database-dir` or have'
                           ' exported the $DAMMIT_DB_DIR environment'
                           ' variable.'))
        sys.exit(2)


def build_default_pipeline(handler, config, databases, with_uniref=False):
    '''Register tasks for dammit's builtin database prep pipeline.

    Args:
        handler (handler.TaskHandler): The task handler to register on.
        config (dict): Config dictionary, which contains the command
            line arguments and the entries from the config file.
        databases (dict): The dictionary of files from `databases.json`.
        with_uniref (bool): If True, download and install the uniref90
            database. Note that this will take 16+Gb of RAM and a looong
            time to prepare with `lastdb`.
    Returns:
        handler.TaskHandler: The handler passed in.
    '''

    register_pfam_tasks(handler, config['hmmer']['hmmpress'], databases)
    register_rfam_tasks(handler, config['infernal']['cmpress'], databases)
    register_orthodb_tasks(handler, config['last']['lastdb'], databases)
    register_busco_tasks(handler, config['busco'], databases)
    if with_uniref:
        register_uniref90_tasks(handler, config['last']['lastdb'], databases)

    return handler
                          

def register_pfam_tasks(handler, params, databases):
    pfam_A = databases['Pfam-A']
    filename = path.join(handler.directory, pfam_A['filename'])
    task = get_download_and_gunzip_task(pfam_A['url'],
                                        filename)
    handler.register_task('download:Pfam-A', task,
                          files={'Pfam-A': filename})
    handler.register_task('hmmpress:Pfam-A',
                          get_hmmpress_task(filename, 
                                            params=params,
                                            task_dep=[task.name]))
    return handler


def register_rfam_tasks(handler, params, databases):
    rfam = databases['Rfam']
    filename = path.join(handler.directory, rfam['filename'])
    task = get_download_and_gunzip_task(rfam['url'], 
                                        filename)
    handler.register_task('download:Rfam', task,
                           files={'Rfam': filename})
    handler.register_task('cmpress:Rfam',
                          get_cmpress_task(filename,
                                           task_dep=[task.name],
                                           params=params))
    return handler


def register_orthodb_tasks(handler, params, databases):
    orthodb = databases['OrthoDB']
    filename = path.join(handler.directory, orthodb['filename'])
    task = get_download_and_gunzip_task(orthodb['url'], 
                                        filename)
    handler.register_task('download:OrthoDB', task,
                          files={'OrthoDB': filename})
    handler.register_task('lastdb:OrthoDB',
                          get_lastdb_task(filename, 
                                          filename, 
                                          prot=True,
                                          params=params,
                                          task_dep=[task.name]))
    return handler


def register_busco_tasks(handler, config, databases):
    busco = databases['BUSCO']
    busco_dir = path.join(handler.directory, config['db_dir'])
    for group_name in busco:
        group = busco[group_name]
        files = {'BUSCO-{0}'.format(group_name): path.join(busco_dir, group_name)}
        handler.register_task('download:BUSCO-{0}'.format(group_name),
                              get_download_and_untar_task(group['url'],
                                                         busco_dir,
                                                         label=group_name),
                              files=files)
    return handler


def register_uniref90_tasks(handler, params, databases):
    uniref90 = databases['uniref90']
    task = get_download_and_gunzip_task(uniref90['url'],
                                        uniref90['filename'])
    filename = path.join(handler.directory, uniref90['filename'])
    handler.register_task('download:uniref90',
                          task,
                          files={'uniref90': filename})
    handler.register_task('lastdb:uniref90',
                          get_lastdb_task(filename,
                                          filename,
                                          prot=True,
                                          params=params,
                                          task_dep=[task.name]))
    return handler


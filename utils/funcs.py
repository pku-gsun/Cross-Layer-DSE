# utils.py
# Define useful functions to leverage across the project.

import os
import sys
import shutil
import yaml
import json
import time
from datetime import datetime
import subprocess
import hashlib
from .exceptions import NotFoundException


# logging operations


def info(msg: str):
    """
        msg: message
    """
    print("[INFO]: {}".format(msg))


def debug(msg: str):
    """
        msg: message
    """
    print("[DEBUG]: {}".format(msg))


def warn(msg: str):
    """
        msg: message
    """
    print("[WARN]: {}".format(msg))


def error(msg: str):
    """
        msg: message
    """
    print("[ERROR]: {}".format(msg))
    exit(1)


def assert_error(msg: str):
    return "[ERROR] {}".format(msg)


class StdoutDuplexer(object):
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, 'w')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

class StdoutDuplexContext(object):
    def __init__(self, file_path):
        self.duplexer = StdoutDuplexer(file_path)
        self.old_output = sys.stdout

    def __enter__(self):
        sys.stdout = self.duplexer

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_output

# file operations


def if_exist(path: str, strict: bool = False, quiet: bool = True):
    """
    Check if a file or directory exists at the given path.

    Args:
        path (str): The path to check.
        strict (bool, optional): If True, raise an error and exit if the file or directory does not exist. 
                                 If False, return False instead. Default is False.
        quiet (bool, optional): If True, suppress warning messages. Default is True.

    Returns:
        bool: True if the file or directory exists, False otherwise.
    """
    try:
        if os.path.exists(path):
            return True
        else:
            raise NotFoundException(path)
    except NotFoundException as e:
        if not quiet:
            warn(e)
        if not strict:
            return False
        else:
            error("file not found: %s" % path)
            exit(1)


def mkdir(path: str):
    """
    Create a directory at the specified path if it doesn't already exist.

    Args:
        path (str): The path of the directory to be created.

    Returns:
        None
    """
    if not if_exist(path):
        info("create directory: %s" % path)
        os.makedirs(path, exist_ok=True)


def remove(path: str):
    """
    Remove a file or directory at the given path.

    Args:
        path (str): The path of the file or directory to be removed.

    Returns:
        None
    """
    if if_exist(path):
        if os.path.isfile(path):
            os.remove(path)
            info("remove {}".format(path))
        elif os.path.isdir(path):
            if not os.listdir(path):
                # empty directory
                os.rmdir(path)
            else:
                shutil.rmtree(path)
            info("remove {}".format(path))


def copy(src, dst):
    """
    Copy a file or directory from source to destination.

    Args:
        src (str): The path of the source file or directory.
        dst (str): The path of the destination directory.

    Returns:
        None
    """
    if if_exist(src):
        if os.path.isfile(src):
            info("copy from {} to {}".format(src, dst))
            shutil.copy(src, dst)
        elif os.path.isdir(src):
            info("copy from {} to {}".format(src, dst))
            shutil.copytree(src, dst)


def get_dir(path: str):
    return os.path.dirname(path)


# timing


def timestamp():
    return time.time()


class Timer(object):
    def __init__(self, msg, file=None):
        super(Timer, self).__init__()
        self.msg = msg
        self.time = None
        self.duration = 0
        self.file = file

    @property
    def now(self):
        return time.time()

    def __enter__(self):
        self.time = self.now

    def __exit__(self, type, value, trace):
        self.duration = self.now - self.time
        msg = "[{}]: duration: {} s".format(
            self.msg,
            self.duration
        )
        info(msg)
        if self.file is not None:
            with open(self.file, 'w') as f:
                f.write("{}: {}\n".format(
                        datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                        msg
                    )
                )


# executing processes
                
def execute(cmd: str, verbose: bool = True, wait: bool = True):
    """
    Executes a command in the shell and returns the process object.

    Args:
        cmd (str): The command to be executed.
        verbose (bool, optional): If True, the command output will be displayed. Defaults to True.
        wait (bool, optional): If True, the function will wait for the command to finish executing. Defaults to True.

    Returns:
        subprocess.Popen: The process object representing the executed command.
    """
    info("executing: {}".format(cmd))
    stdout = None if verbose else subprocess.PIPE
    stderr = None if verbose else subprocess.PIPE
    process = subprocess.Popen(["/bin/bash", "-c", cmd], stdout=stdout, stderr=stderr)
    if wait: process.wait()
    return process

def init_worker():
    """
    Initialize worker process so that it does not print anything to stdout.
    """
    devnull = open(os.devnull, 'w')
    sys.stdout = devnull
    sys.stderr = devnull

# Yaml-related operations
    
def read_yaml(path):
    assert if_exist(path, strict=True), assert_error("file not found: {}".format(path))
    info("Read yaml from {}".format(path))
    with open(path, 'r') as f:
        return yaml.load(f, Loader=yaml.FullLoader)
    

def dump_yaml(contents, path):
    info("Dump yaml to {}".format(path))
    with open(path, 'w') as f:
        yaml.dump(contents, f)


# JSON-related operations

def read_json(path):
    assert if_exist(path, strict=True), assert_error("file not found: {}".format(path))
    info("Read json from {}".format(path))
    with open(path, 'r') as f:
        return json.load(f)
    
def dump_json(context, path):
    info("Dump json to {}".format(path))
    with open(path, 'w') as f:
        json.dump(context, f, indent=4)

# consistent hashing
def create_hash(obj):
    hash_hex = hashlib.sha256(obj.encode('utf-8')).hexdigest()
    return hash_hex
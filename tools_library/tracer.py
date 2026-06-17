import time
import os
import inspect
from tools_library.drive_variables import log_folder
from tools_library.dbs import PROGRAM_DIR

log_folder_path = os.path.join(PROGRAM_DIR, log_folder)

# Trace levels range 1 (very verbose, e.g. per-file hashing) to 5 (high-signal,
# e.g. files actually deleted). Only lines at or below this threshold are written.
TRACE_LEVEL = 3


def pid(path):
    """Return a short '#<id>' token referencing path in the directory-tree DB.

    Use this instead of interpolating a raw path into a log message so log files
    never store full paths directly (see tools_library/path_db.py).
    """
    if not path:
        return ""
    from tools_library import path_db
    return f"#{path_db.get_path_id(path)}"


def current_log_path():
    """Return the info log file path for the current UTC minute."""
    minute_str = time.strftime("%Y%m%d%H%M", time.gmtime())
    return os.path.join(log_folder_path, f"tracer_{minute_str}.log")


def current_error_log_path():
    """Return the error log file path for the current UTC minute."""
    minute_str = time.strftime("%Y%m%d%H%M", time.gmtime())
    return os.path.join(log_folder_path, f"error_{minute_str}.log")


def log_folder_size():
    """Return total size of all files in the log folder, in bytes."""
    total = 0
    try:
        for entry in os.scandir(log_folder_path):
            if entry.is_file():
                total += entry.stat().st_size
    except FileNotFoundError:
        pass
    return total


def timestamp():
    return time.strftime("%y%m%d%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"


def _write_log(path, caller_file, caller_name, line, level=None):
    os.makedirs(log_folder_path, exist_ok=True)
    level_tag = f"L{level} " if level is not None else ""
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"{timestamp()} {level_tag}{caller_file}>{caller_name} {line} \n")


def log(line, trace_level=1):
    if trace_level > TRACE_LEVEL:
        return
    frame = inspect.currentframe().f_back
    _write_log(current_log_path(), frame.f_code.co_filename, frame.f_code.co_name, line,
               level=trace_level)


def log_error(line):
    """Write to both the main info log (tagged ERROR) and the error-only log.

    Errors are always written regardless of TRACE_LEVEL.
    """
    frame = inspect.currentframe().f_back
    caller_file = frame.f_code.co_filename
    caller_name = frame.f_code.co_name
    _write_log(current_log_path(), caller_file, caller_name, f"ERROR {line}")
    _write_log(current_error_log_path(), caller_file, caller_name, line)


def clear_log(filename):
    fullpath = os.path.join(log_folder_path, filename)
    if os.path.exists(fullpath):
        os.remove(fullpath)


def log_to_report(line, filename):
    path = os.path.join(log_folder_path, filename)
    os.makedirs(log_folder_path, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as file:
        file.write(line)
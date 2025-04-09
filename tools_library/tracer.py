import time
import os
import inspect
from tools_library.drive_variables import log_folder, log_tracer
from tools_library.dbs import PROGRAM_DIR

# Get the directory where the program is running
log_folder_path = os.path.join(PROGRAM_DIR, log_folder)
log_file_path = os.path.join(log_folder_path, log_tracer)
TRACE_LEVEL = 10

def timestamp():
    return time.strftime("%y%m%d%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"

def log(line, trace_level=0):
    if trace_level > TRACE_LEVEL:
        return
    caller_name = inspect.currentframe().f_back.f_code.co_name#Get the name of the caller function
    if not os.path.exists(log_file_path):
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as file:
            file.write('')
    with open(log_file_path, 'a') as file:
        file.write(f"{timestamp()} {caller_name} {line} \n")

def clear_log(filename):
    filename_fullpath = os.path.join(log_folder_path, filename)
    if os.path.exists(filename_fullpath):
        os.remove(filename_fullpath)

def log_to_report(line, filename):
    log_file_path = os.path.join(log_folder_path, filename)
    if not os.path.exists(log_file_path):
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as file:
            file.write('')
    with open(log_file_path, 'a') as file:
        file.write(line)
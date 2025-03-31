import time
import os
import inspect


# Get the directory where the program is running
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(current_dir, "backup_gui.log")


def timestamp():
    return time.strftime("%y%m%d%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"

def log(line):
    caller_name = inspect.currentframe().f_back.f_code.co_name#Get the name of the caller function
    if not os.path.exists(log_file_path):
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as file:
            file.write('')
    with open(log_file_path, 'a') as file:
        file.write(f"{timestamp()} {caller_name} {line} \n")

def clear_log(filename):
    log_file_path = os.path.join(current_dir, filename)
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

def log_to_report(line, filename):
    log_file_path = os.path.join(current_dir, filename)
    if not os.path.exists(log_file_path):
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as file:
            file.write('')
    with open(log_file_path, 'a') as file:
        file.write(line)
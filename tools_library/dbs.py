import os
import json
from tools_library.drive_variables import drives_file, config_folder

PROGRAM_DIR = os.getcwd()
print("Program Directory:", PROGRAM_DIR)
CONFIGFOLDER_PATH = os.path.join(PROGRAM_DIR, config_folder)
DRIVESPATH_FILE = os.path.join(CONFIGFOLDER_PATH, drives_file)
config_data = {}

def initialize_drives():
    if not os.path.exists(DRIVESPATH_FILE):
        with open(DRIVESPATH_FILE, 'w') as f:
            json.dump(config_data, f, indent=1)


def get_saved_drives():
    if os.path.exists(DRIVESPATH_FILE):
        with open(DRIVESPATH_FILE, 'r') as f:
            return json.load(f)
    else:
        return []

def initialize_drives():
    if not os.path.exists(DRIVESPATH_FILE):
        with open(DRIVESPATH_FILE, 'w') as f:
            json.dump([], f, indent=1)


def update_drives_list(drives):
    with open(DRIVESPATH_FILE, 'w') as f:
        json.dump(drives, f, indent=1)
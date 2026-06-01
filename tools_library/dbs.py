import os
import sys
import json
from tools_library.drive_variables import drives_file, vaults_file, config_folder

if getattr(sys, 'frozen', False):
    # Running as a PyInstaller executable — use the directory that holds the exe
    PROGRAM_DIR = os.path.dirname(sys.executable)
else:
    # Running as a script — project root is one level above tools_library/
    PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGFOLDER_PATH = os.path.join(PROGRAM_DIR, config_folder)
DRIVESPATH_FILE = os.path.join(CONFIGFOLDER_PATH, drives_file)
VAULTSPATH_FILE = os.path.join(CONFIGFOLDER_PATH, vaults_file)
config_data = {}


def initialize_vaults():
    try:
        os.makedirs(os.path.dirname(VAULTSPATH_FILE), exist_ok=True)
        if not os.path.exists(VAULTSPATH_FILE):
            with open(VAULTSPATH_FILE, 'w') as f:
                json.dump([], f, indent=1)
    except (IOError, PermissionError) as e:
        raise Exception(f"Failed to initialize vaults file: {e}.")


def get_saved_vaults():
    if os.path.exists(VAULTSPATH_FILE):
        with open(VAULTSPATH_FILE, 'r') as f:
            data = json.load(f)
            # Migrate legacy format [{"location": "..."}] -> ["..."]
            if data and isinstance(data[0], dict):
                return [d['location'] for d in data if 'location' in d]
            return data
    return []


def update_vaults_list(vaults):
    with open(VAULTSPATH_FILE, 'w') as f:
        json.dump(vaults, f, indent=1)


# Legacy aliases (kept so toolbox.py and old backupGUImain.py still import cleanly)
def initialize_drives():
    try:
        os.makedirs(os.path.dirname(DRIVESPATH_FILE), exist_ok=True)
        if not os.path.exists(DRIVESPATH_FILE):
            with open(DRIVESPATH_FILE, 'w') as f:
                json.dump([], f, indent=1)
    except (IOError, PermissionError) as e:
        raise Exception(f"Failed to initialize drives file: {e}.")


def get_saved_drives():
    if os.path.exists(DRIVESPATH_FILE):
        with open(DRIVESPATH_FILE, 'r') as f:
            return json.load(f)
    return []


def update_drives_list(drives):
    with open(DRIVESPATH_FILE, 'w') as f:
        json.dump(drives, f, indent=1)
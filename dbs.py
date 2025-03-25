import os
import json

config_data = {}

def initialize_configurations():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "Configuration.json")
    if not os.path.exists(config_file_path):
        with open(config_file_path, 'w') as f:
            json.dump(config_data, f, indent=1)


def get_saved_drives():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "drives.json")
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            return json.load(f)
    else:
        return { 'locations' : [] }

def initialize_drives():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drives_file_path = os.path.join(current_dir, "drives.json")
    if not os.path.exists(drives_file_path):
        with open(drives_file_path, 'w') as f:
            json.dump({ 'locations' : [] }, f, indent=1)


def update_drives_list(drives):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drives_file_path = os.path.join(current_dir, "drives.json")
    with open(drives_file_path, 'w') as f:
        json.dump(drives, f, indent=1)
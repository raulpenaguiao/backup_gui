import time
start_time = time.time()

import os
import hashlib
import pandas as pd
import json


def list_files_in_folder(folder_path, verbose = False):
    count = 0
    list_of_files = []
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    checksum = hashlib.md5(file_data).hexdigest()
                    size = os.path.getsize(file_path)
                    extention = os.path.splitext(file_path)[1]
                    datem = os.path.getmtime(file_path)
                    datec = os.path.getctime(file_path)
                    datea = os.path.getatime(file_path)

                    list_of_files.append({
                        'file_path': file_path,
                        'checksum': checksum,
                        'size': size,
                        'extention': extention,
                        'date-changed': datec,
                        'date-created': datem,
                        'date-accessed': datea
                    })
                    count += 1
                    datec_formatted = time.strftime('%Y-%m-%d', time.localtime(datem))
                    if(verbose):
                        print("count:", count, 'and size', size, 'and date of last change', datec_formatted)
    except Exception as e:
        print(f"An error occurred: {e}")
    return list_of_files

def save_dic_to_json(dic, path):
    try:
        with open(path, 'w') as f:
            json.dump(dic, f, indent=4)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    folder_path = input()
    if folder_path[0] == '"':
        folder_path = folder_path[1:-1]
    
    dic = list_files_in_folder(folder_path)
    drive_path = os.path.join(folder_path, '.driveinfo')
    if not os.path.isdir(drive_path):
        os.mkdir(drive_path)
    
    json_path = os.path.join(drive_path,  '.fileinfo.json')
    if os.path.exists(json_path):
        os.remove(json_path)

    save_dic_to_json(dic, json_path)



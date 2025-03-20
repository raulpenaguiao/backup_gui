import time
start_time = time.time()
#Should take about 250 seconds

import os
import hashlib
import pandas as pd
import json

def list_files_in_folder(folder_path):
    count = 0
    list_of_files = []
    try:
        for root, dirs, files in os.walk(folder_path):
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
                    print("count: ", count, ' and size', size, ' and date of last change', datec_formatted)
    except Exception as e:
        print(f"An error occurred: {e}")
    return list_of_files

def save_dic_to_json(dic, path):
    try:
        with open(path, 'w') as f:
            json.dump(dic, f, indent=4)
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage:
folder_path =  "D:\\DEVELOP\\projects\\backup_enterprise\\test"
folder_path =  "D:\\DEVELOP\\projects\\backup_enterprise\\00_data\\raw_copy\\ubuntu_huawei"
folder_path =  "D:\\DEVELOP\\projects\\backup_enterprise\\00_data"
folder_path =  "D:\\DEVELOP\\projects\\backup_enterprise\\03_files_sorted_into_half_buckets"

json_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data.json'
dic = list_files_in_folder(folder_path)
print("Number of files processed:", len(dic))
save_dic_to_json(dic, json_path)
end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")
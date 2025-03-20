import time
start_time = time.time()
# should take about 20 seconds to run

import json
import pandas as pd
import filecmp

def save_dic_to_json(dic, path):
    try:
        with open(path, 'w') as f:
            json.dump(dic, f, indent=4)
    except Exception as e:
        print(f"An error occurred: {e}")

def split_different_files(files):
    split_files = []
    for file in files:
        flag = False
        file_path = file['file_path']
        for i in range(len(split_files)):
            file_path_to_compare = split_files[i][0]['file_path']
            if filecmp.cmp(file_path, file_path_to_compare, shallow=False):
                split_files[i].append(file)
                flag = True
                break
        if not flag:
            split_files.append([file])
    return split_files

json_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data.json'
json_cleaned_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data_cleaned.json'
dic = json.load(open(json_path))
len_dic = len(dic)

dic_files = {file['checksum']: [] for file in dic}

counter = 0
for file in dic:
    if counter%(len_dic//13) == 23:
        print("Creating registrer - ", counter, " / " , len_dic)
    counter += 1
    checksum = file['checksum']
    dic_files[checksum].append(file)
end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")


list_checksums_to_be_deleted = [ ]
list_checksums_to_be_added = [ ]
counter = 0
len_dic = len(dic_files)
max_size = 1
for checksum, files in dic_files.items():
    if counter%(len_dic//103) == 23:
        print("Deleting copies - ", counter, " / " , len_dic)
    counter += 1
    if len(files) > 1:
        #print("There are ", len(files), "file paths.")
        max_size = max(len(files), max_size)
        split_files = split_different_files(files)
        #print("There are ", len(split_files), "different files.")
        if len(split_files) > 1:
            for index, split in enumerate(split_files):
                list_checksums_to_be_added.append((str(checksum) + "_" + str(index), split))
            list_checksums_to_be_deleted.append(checksum)

for checksum in list_checksums_to_be_deleted:
    del dic_files[checksum]
for checksum_string, path in list_checksums_to_be_added:
    dic_files[checksum_string] = [path]

new_dic = {checksum: files[0] for checksum, files in dic_files.items()}
for checksum, files in dic_files.items():
    new_dic[checksum]['locations'] = "$".join([file['file_path'] for file in files])

save_dic_to_json(new_dic, json_cleaned_path)

end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")
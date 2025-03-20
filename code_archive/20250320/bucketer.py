import time
start_time = time.time()
# should take about 80 seconds to run
#This was a bad idea, sorting everything by extention completely destroys the idea that some files belong together


import json
import os
import shutil


json_cleaned_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data_cleaned.json'
folder_staging = 'D:\\DEVELOP\\projects\\backup_enterprise\\01_tosort'
dic = json.load(open(json_cleaned_path))

dic_extentions = {file['extention']: [] for file in dic.values()}
print("dictionary created")

for extention in dic_extentions:
    os.makedirs(folder_staging, exist_ok=True)
    for extention in dic_extentions:
        ext_folder = os.path.join(folder_staging, extention)
        os.makedirs(ext_folder, exist_ok=True)
print("folder structure created")

counter = 0
len_dic = len(dic)
print(len_dic)
for file in dic.values():
    if counter%(len_dic//103) == 23:
        print(counter, " / ", len_dic)
    counter += 1
    file_extention = file['extention']
    src_path = file['file_path']
    dest_path = os.path.join(folder_staging, file_extention, str(file['checksum']) + "_" + os.path.basename(src_path))

    if not os.path.exists(dest_path):
        shutil.move(src_path, dest_path)


end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")
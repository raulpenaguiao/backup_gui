import time
start_time = time.time()
# should take about 80 seconds to run


import json
import os
import shutil


json_cleaned_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data_cleaned.json'
folder_staging = 'D:\\DEVELOP\\projects\\backup_enterprise\\01_tosort'
dic = json.load(open(json_cleaned_path))

dic_extentions = {file['extention']: [] for file in dic.values()}
print("dictionary created")

counter = 0
len_dic = len(dic)
print(len_dic)
for file in dic.values():
    if counter%(len_dic//103) == 23:
        print(counter, " / ", len_dic)
    counter += 1
    src_path = file['file_path']
    file_extention = file['extention']
    
    dest_path = os.path.join(folder_staging, file_extention, str(file['checksum']) + "_" + os.path.basename(src_path))

    if not os.path.exists(dest_path):
        shutil.move(src_path, dest_path)


end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")
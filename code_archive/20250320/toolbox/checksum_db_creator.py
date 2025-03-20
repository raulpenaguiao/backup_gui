import json
import os
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

if __name__ == "__main__":
    folder_path = input()
    if folder_path[0] == '"':
        folder_path = folder_path[1:-1]
    
    drive_path = os.path.join(folder_path, '.driveinfo')
    checksum_db_path = os.path.join(drive_path,  '.checksuminfo.json')
    json_path = os.path.join(drive_path,  '.fileinfo.json')

    list_files = json.load(open(json_path))
    dic_checksums = {file['checksum']: [] for file in list_files}

    for file in list_files:
        checksum = file['checksum']
        if not checksum in dic_checksums:
            dic_checksums[checksum] = []
        dic_checksums[checksum].append(file)

    for checksum in dic_checksums:
        locations_for_files = split_different_files(dic_checksums[checksum])
        dic_checksums[checksum] = [files[-1] for files in locations_for_files]
        #makes sure to take the one file that arrises last
        for file, locations in zip(dic_checksums[checksum], locations_for_files):
            file['locations'] = [other_file['file_path'] for other_file in locations]
        

    if os.path.exists(checksum_db_path):
        os.remove(checksum_db_path)
    save_dic_to_json(dic_checksums, checksum_db_path)

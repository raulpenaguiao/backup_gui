import json
import os
import shutil

if __name__ == "__main__":
    folder_path = input()
    if folder_path[0] == '"':
        folder_path = folder_path[1:-1]

    parent_folder_path = os.path.dirname(folder_path)
    folder_name = os.path.basename(os.path.normpath(folder_path))
    target_folder_path = os.path.join(parent_folder_path, folder_name + "__cleared")
    
    drive_path = os.path.join(folder_path, '.driveinfo')
    checksum_db_path = os.path.join(drive_path,  '.checksuminfo.json')
    

    checksums_list = json.load(open(checksum_db_path))

    for checksum in checksums_list:
        for file in checksums_list[checksum]:
            file_path = file['file_path']
            appendage_path = file_path[len(folder_path):]
            target_file_path = target_folder_path + appendage_path
            target_dir_path = os.path.dirname(target_file_path)


            os.makedirs(target_dir_path, exist_ok=True)
            shutil.copy(file_path, target_file_path)
            #print("Copying ", file_path, " to ",  file_path[len(folder_path):], " located in ", target_file_path)
    print("Done")
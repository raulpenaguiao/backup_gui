import json
import pandas as pd
import os
from collections import Counter
import matplotlib.pyplot as plt
import filecmp
import time
import hashlib
import shutil
import tracer
import drive_variables

def save_dic_to_json(dic, json_path):
    """
    Save a dictionary to a JSON file.
    Args:
        dic (dict): The dictionary to save.
        path (str): The file path where the JSON file will be saved.
    Raises:
        Exception: If an error occurs during file writing.
    """
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(dic, f, indent=1)
    except Exception as e:
        tracer.log(f"An error occurred: {e}")

def split_different_files(files):
    """
    Splits a list of files into groups of identical files.
    This function takes a list of file dictionaries, each containing a 'file_path' key,
    and groups them into sublists where each sublist contains files that are identical
    to each other. The comparison is done using the filecmp.cmp function with shallow=False
    to ensure a deep comparison.
    Args:
        files (list): A list of dictionaries, where each dictionary contains a 'file_path' key.
    Returns:
        list: A list of lists, where each sublist contains dictionaries of identical files.
    """
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

def create_statistics_pictures(drive_path):
    """
    Creates statistics pictures based on the files in the database.
    This function generates a pie chart and a histogram to visualize the distribution of file sizes
    and extensions in the database. The data is read from a JSON file containing file metadata.
    """
    drive_info_folder_full_path = os.path.join(drive_path, drive_variables.drive_folder_info)
    tracer.log("drive_info_folder_full_path" + drive_info_folder_full_path)
    drive_info_json_full_path = os.path.join(drive_info_folder_full_path, drive_variables.fileinfo_json)
    tracer.log("drive_info_json_full_path" + drive_info_json_full_path)

    # Read the JSON file containing file metadata
    with open(drive_info_json_full_path, 'r') as f:
        data = json.load(f)
    tracer.log("json opened, it has " + str(len(data)) + " files")
    files = [file_list[0][0] for checksum, file_list in data.items()]
    tracer.log("files created, it has " + str(len(files)) + " files")
    
    # Create a DataFrame from the JSON data
    df = pd.DataFrame(files)
    tracer.log("dataframe created, it has " + str(len(df)) + " files")
    # Create a pie chart for top 15 file extensions
    extension_counts = Counter(df['extention'])
    extension_counts = dict(extension_counts.most_common(15))
    plt.figure(figsize=(10, 6))
    plt.pie(extension_counts.values(), labels=extension_counts.keys(), autopct='%1.1f%%')
    plt.title('File Extensions Distribution')
    plt.savefig(os.path.join(drive_info_folder_full_path, drive_variables.extension_distribution))
    plt.close()
    tracer.log("extention pie chart created, saved in " + str(os.path.join(drive_info_folder_full_path, drive_variables.extension_distribution)))

    # Create a histogram for file sizes
    plt.figure(figsize=(10, 6))
    plt.hist(df['size'], bins=50, color='blue', alpha=0.7)
    plt.title('File Size Distribution')
    plt.xlabel('Size (bytes)')
    plt.ylabel('Frequency')
    plt.savefig(os.path.join(drive_info_folder_full_path, drive_variables.file_size_histogram))
    plt.close()
    tracer.log("file size histogram created, saved in " + str(os.path.join(drive_info_folder_full_path, drive_variables.file_size_histogram)))
    
    #Create a record of all the number of copies for each file
    file_repetitions = []
    for _, file_list in data.items():
        file_repetitions += [len(fl) for fl in file_list]

    repetition_counts = {}
    for c in file_repetitions:
        if c not in repetition_counts:
            repetition_counts[c] = 0
        repetition_counts[c] += 1
    tracer.log("repetitions = " + str(repetition_counts))
    plt.figure(figsize=(10, 6))
    plt.bar(repetition_counts.keys(), repetition_counts.values(), color='green', alpha=0.7)
    plt.title('File Repetition Count')
    plt.xlabel('Number of Copies')
    plt.ylabel('Frequency')
    plt.savefig(os.path.join(drive_info_folder_full_path, drive_variables.file_repetition_count))
    plt.close()
    tracer.log("repetition histogram created, saved in " + str(os.path.join(drive_info_folder_full_path, drive_variables.file_repetition_count)))

    # Create a histogram for file creation times
    creation_times = pd.to_datetime(df['date-created'], unit='s')
    plt.figure(figsize=(10, 6))
    plt.hist(creation_times, bins=50, color='purple', alpha=0.7)
    plt.title('File Creation Time Distribution')
    plt.xlabel('Creation Time')
    plt.ylabel('Frequency')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(drive_info_folder_full_path, drive_variables.file_creation_time_histogram))
    plt.close()
    tracer.log("creatin time histogram created, saved in " + str(os.path.join(drive_info_folder_full_path, drive_variables.file_creation_time_histogram)))

def list_files_in_folder(folder_path, verbose=False):
    """
    Lists all files in the given folder and its subfolders, along with their metadata.
    Args:
        folder_path (str): The path to the folder to list files from.
        verbose (bool, optional): If True, prints detailed information about each file. Defaults to False.
    Returns:
        list: A list of dictionaries, each containing metadata for a file:
            - file_path (str): The full path to the file.
            - checksum (str): The MD5 checksum of the file.
            - size (int): The size of the file in bytes.
            - extention (str): The file extension.
            - date-changed (float): The time of last metadata change.
            - date-created (float): The time of creation.
            - date-accessed (float): The time of last access.
    Raises:
        Exception: If an error occurs during file processing, it prints the error message.
    """
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
                    extention = os.path.splitext(file_path)[1].lower()
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
                        tracer.log("count:", count, 'and size', size, 'and date of last change', datec_formatted)
    except Exception as e:
        tracer.log(f"An error occurred: {e}")
    return list_of_files

def initialize_database(path_to_dir):
    """
    Initializes a database of files in the given directory by deleting all database files on it
    Args:
        path_to_dir (str): The path to the directory to create the database from.
    """
    drive_path = os.path.join(path_to_dir, drive_variables.drive_folder_info)
    if os.path.exists(drive_path):
        shutil.rmtree(drive_path)
    os.mkdir(drive_path)
    return

def create_comparison_report(path_to_dir_1, path_to_dir_2):
    """
    Compares two lists of files and generates a report of the differences.
    Args:
        files_1 (list): The path to the first directory file to compare.
        files_2 (list): The path to the second directory file to compare.
    Returns:
        list: A list of files containing the differences between the two lists of files.
    """

    drive_info_folder_full_path_1 = os.path.join(path_to_dir_1, drive_variables.drive_folder_info)
    drive_info_json_full_path_1 = os.path.join(drive_info_folder_full_path_1, drive_variables.fileinfo_json)
    tracer.log("drive 1 info full path " + drive_info_json_full_path_1)

    # Read the JSON file containing file metadata
    with open(drive_info_json_full_path_1, 'r') as f:
        files_1 = json.load(f)
        
    drive_info_folder_full_path_2 = os.path.join(path_to_dir_2, drive_variables.drive_folder_info)
    drive_info_json_full_path_2 = os.path.join(drive_info_folder_full_path_2, drive_variables.fileinfo_json)
    tracer.log("drive 2 info full path " + drive_info_json_full_path_2)

    # Read the JSON file containing file metadata
    with open(drive_info_json_full_path_2, 'r') as f:
        files_2 = json.load(f)
    
    comparison = []
    for checksum in files_2:
        if checksum not in files_1:
            print("checksum not in files_1, adding", files_2[checksum])
            comparison += [file[0] for file in files_2[checksum]]
        else:
            for file in files_2[checksum]:
                if file not in files_1[checksum]:
                    comparison.append(file[0])#We only take the first file of the list, because they are identical
    print("comparison: list of files that only exist in the second drive:", comparison)
    return comparison

def dic_of_checksums(list_of_files):
    dic = {file["checksum"]: [] for file in list_of_files}
    for file in list_of_files:
        dic[file["checksum"]].append(file)
    return dic

def create_copies_report(path_to_drive):
    drive_info_folder_full_path = os.path.join(path_to_drive, drive_variables.drive_folder_info)
    drive_info_json_full_path = os.path.join(drive_info_folder_full_path, drive_variables.fileinfo_json)
    # Read the JSON file containing file metadata
    with open(drive_info_json_full_path, 'r') as f:
        data = json.load(f)
    
    repeated_files = []
    for checksum in data:
        for file_list in data[checksum]:
            if len(file_list) > 1:
                repeated_files.append(file_list)
    return repeated_files
                
def create_database(path):
    initialize_database(path)
    tracer.log("Database is going to be initialized")
    list_of_files = list_files_in_folder(path)
    tracer.log(f"list of files explored, there are {len(list_of_files)} files")
    dic_of_checksum_files = dic_of_checksums(list_of_files)
    tracer.log(f"checksums computed, there are {len(dic_of_checksum_files)} checksums")
    dic_of_files = {checksum: split_different_files(files) for checksum, files in dic_of_checksum_files.items()}
    tracer.log(f"files are now split into {sum([len(dic_of_files[checksum]) for checksum in dic_of_files])} distinct files")
    json_path = os.path.join(path, drive_variables.drive_folder_info, drive_variables.fileinfo_json)
    save_dic_to_json(dic_of_files, json_path)




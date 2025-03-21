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
    drive_path = os.path.join(path_to_dir, drive_variables.drive_info)
    if os.path.exists(drive_path):
        shutil.rmtree(drive_path)
    os.mkdir(drive_path)
    return


def dic_of_checksums(list_of_files):
    dic = {file["checksum"]: [] for file in list_of_files}
    for file in list_of_files:
        dic[file["checksum"]].append(file)
    return dic
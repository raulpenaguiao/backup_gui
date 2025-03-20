import os
import time
import hashlib

def count_files_in_directory(directory):
    checksums = {}
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                file_data = f.read()
                checksum = hashlib.md5(file_data).hexdigest()
                if not checksum in checksums:
                    checksums[checksum] = []
                checksums[checksum] += [file_path]
    return file_count, len(checksums), max(len(files) for files in checksums.values())

OUTPUT_PATH = "C:\\Users\\rpenaguiao\\Desktop\\passport_stats"

if __name__ == "__main__":
    directory_path = input("Enter the directory path: ")
    start_time = time.time()
    total_files, total_checksums, largest_checksum_class = count_files_in_directory(directory_path)
    print(f"Total number of files in '{directory_path}' and its subfolders: {total_files}")
    print(f"Total number of different files: {total_checksums}")
    print(f"Largest class of files with the same checksum: {largest_checksum_class}")
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")
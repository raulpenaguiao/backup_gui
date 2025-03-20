import os
import shutil

DIRNAME = os.path.join("D:\\", "DEVELOP", "projects", "backup_enterprise", "data")
TARGET_DIRNAME = os.path.join("D:\\", "DEVELOP", "projects", "backup_enterprise", "backup_stage1")
print(DIRNAME)
print(TARGET_DIRNAME)


def create_target_dirs(target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    if not os.path.exists(os.path.join(target_dir, "pdfs")):
        os.makedirs(os.path.join(target_dir, "pdfs"))
    if not os.path.exists(os.path.join(target_dir, "media")):
        os.makedirs(os.path.join(target_dir, "media"))
    if not os.path.exists(os.path.join(target_dir, "notes")):
        os.makedirs(os.path.join(target_dir, "notes"))
    if not os.path.exists(os.path.join(target_dir, "media", "videos")):
        os.makedirs(os.path.join(target_dir, "media", "videos"))
    if not os.path.exists(os.path.join(target_dir, "media", "images")):
        os.makedirs(os.path.join(target_dir, "media", "images"))
    if not os.path.exists(os.path.join(target_dir, "media", "audio")):
        os.makedirs(os.path.join(target_dir, "media", "audio"))
    if not os.path.exists(os.path.join(target_dir, "other")):
        os.makedirs(os.path.join(target_dir, "other"))


def sort_files(dirname, target_dir):
    for root, dirs, files in os.walk(dirname):
        for file in files:
            filepath = os.path.join(root, file)
            print(f"Processing file: {filepath}")
            relative_path = os.path.relpath(filepath, dirname).replace("\\", "_")
            print(f"Processing from folder: {relative_path}")
            # Add your file processing logic here
            # For example, you might want to move the file to a new directory
            if file.lower().endswith('.pdf'):
                target_path = os.path.join(target_dir, "pdfs", f"{relative_path}_{file}")
            elif file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.ico', '.webp')):
                target_path = os.path.join(target_dir, "media", "images", f"{relative_path}_{file}")
            elif file.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv')):
                target_path = os.path.join(target_dir, "media", "videos", f"{relative_path}_{file}")
            elif file.lower().endswith(('.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.wma', '.aiff', '.au', '.mid', '.midi', '.m3u', '.m3u8', '.pls', '.cda', '.m4b', '.m4p', '.m4r', '.m4v', '.mpa', '.mpc', '.mp+', '.oga', '.ogg', '.opus', '.spx', '.tta', '.wv', '.wvc')):
                target_path = os.path.join(target_dir, "media", "audio", f"{relative_path}_{file}")
            elif file.lower().endswith(('txt', 'md', 'markdown', 'log')):
                target_path = os.path.join(target_dir, "notes", f"{relative_path}_{file}")
            else:
                print(filepath + " was not processed")
                continue
            print(f"Moving file to: {target_path}")
            copy_file(filepath, target_path)
            # os.rename(filepath, os.path.join(target_dir, file))

def copy_file(filepath, target_path):
    end_target_path = target_path
    try_number = 0
    while os.path.exists(end_target_path):
        try_number += 1
        end_target_path = target_path.replace(".", f"_{try_number}.")
    shutil.copyfile(filepath, end_target_path)


def is_folder_empty(folder_path):
    # Check if folder is empty by recursively looking for any files
    for root, dirs, files in os.walk(folder_path):
        if files:  # If there are any files in this directory or subdirectories
            return False
    return True  # No files found in directory or subdirectories

if __name__ == "__main__":
    create_target_dirs(TARGET_DIRNAME)
    sort_files(DIRNAME, TARGET_DIRNAME)
    if is_folder_empty(DIRNAME):
        print("Done, deleting source folder")
        # We need to import shutil at the top of the file
        # shutil.rmtree() recursively deletes a directory and all its contents
        shutil.rmtree(DIRNAME)
    else:
        print("Done, source folder is not empty")

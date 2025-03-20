import os

folder_path = input("Enter the folder path: ")

for root, dirs, files in os.walk(folder_path):
    for filename in files:
        old_file = os.path.join(root, filename)
        file_name, file_extension = os.path.splitext(filename)
        file_name = file_name.split("_")[-1]
        new_file_path = file_name + file_extension
        #print(os.path.join(root, new_file_path))
        new_file = os.path.join(root, new_file_path)
        try:
            if not old_file == new_file:
                os.rename(old_file, new_file)
        except FileExistsError:
            print(f"File {new_file} already exists. Skipping...")
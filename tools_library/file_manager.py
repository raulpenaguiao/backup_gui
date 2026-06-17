import os
import tools_library.drive_variables as drive_variables
import tools_library.tracer as tracer
from pathlib import Path
import shutil


def create_unique_files(path_to_drive, list_of_paths):
    #Create a folder called path_to_drive+unique_files in the current directory
    drive_name = os.path.basename(path_to_drive)
    drive_parent = str(Path(path_to_drive).parent.absolute())
    unique_files_path = os.path.join(drive_parent, "." + drive_name + drive_variables.unique_files_folder_name)
    tracer.log("Parent folder name: " + drive_parent, trace_level=2)
    tracer.log("Drive name: " + drive_name, trace_level=2)
    tracer.log("Unique files name: " + unique_files_path, trace_level=2)

    for path in list_of_paths:
        #Check if it starts with path_to_drive
        if not path.startswith(path_to_drive):
            raise ValueError(f"Path {path} does not start with {path_to_drive}")
        remove_prefix_path = path[len(path_to_drive)+1:]#don't forget the +1 for the /
        new_path = os.path.join(unique_files_path, remove_prefix_path)
        tracer.log(f"prefix {remove_prefix_path}", trace_level=2)
        tracer.log(f"Move {path} to {new_path}", trace_level=2)
        #Create the folder if it does not exist
        if not os.path.exists(os.path.dirname(new_path)):
            tracer.log(f"Creating a directory in {new_path}", trace_level=2)
            os.makedirs(os.path.dirname(new_path), exist_ok=True)

        tracer.log(f"Directory of {new_path} exists", trace_level=2)
        #Create the file if it does not exist
        if not os.path.exists(new_path):
            tracer.log(f"Creating a file in {new_path}", trace_level=2)
            with open(new_path, 'w') as f:
                f.write('')
        tracer.log(f"File of {new_path} exists", trace_level=2)
        #Copy the file to the new path
        shutil.copy2(path, new_path)
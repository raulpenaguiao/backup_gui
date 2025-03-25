import tkinter as tk
from tkinter import ttk
from tkinter import Menu
import toolbox
import tracer
import os
import drive_variables
import dbs

class BackupGUI:
    def __init__(root):
        root.rootTK = tk.Tk()
        root.rootTK.title("Backup GUI")
        root.rootTK.geometry("900x600")
        root.InitializeComponents()
    
    def InitializeComponents(root):
        # Create menu bar
        menu_bar = Menu(root.rootTK)
        root.rootTK.config(menu=menu_bar)

        # Create menus
        file_menu = Menu(menu_bar, tearoff=0)
        edit_menu = Menu(menu_bar, tearoff=0)
        help_menu = Menu(menu_bar, tearoff=0)

        # Add menus to menu bar
        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        # Add menu items
        file_menu.add_command(label="New")
        file_menu.add_command(label="Open")
        file_menu.add_command(label="Save")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.rootTK.quit)

        edit_menu.add_command(label="Undo")
        edit_menu.add_command(label="Redo")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut")
        edit_menu.add_command(label="Copy")
        edit_menu.add_command(label="Paste")

        help_menu.add_command(label="About")

        # Create labels
        label1 = tk.Label(root.rootTK, text="New entry")
        label1.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        label2 = tk.Label(root.rootTK, text="Database")
        label2.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        label3 = tk.Label(root.rootTK, text="Files to backup")
        label3.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Create text fields
        text_field1 = tk.Entry(root.rootTK)
        text_field1.grid(row=0, column=1, padx=5, pady=5)
        text_field1.config(width=100)

        text_box1 = ttk.Combobox(root.rootTK)
        text_box1['values'] = [d for d in drive_variables.drives if os.path.exists(d)]
        text_box1.grid(row=1, column=1, padx=5, pady=5)
        text_box1.config(width=100)

        text_field2 = tk.Entry(root.rootTK)
        text_field2.grid(row=2, column=1, padx=5, pady=5)
        text_field2.config(width=100)


        # Create click functionality
        def buttonCreateDatabase_click():
            try:
                print("Button 1 was clicked")
                tracer.log(f"The button1 was clicked")
                path = get_text_field(text_box1)
                tracer.log(f"The path was fetched at {path}")
                toolbox.initialize_database(path)
                tracer.log("Database initialized")
                list_of_files = toolbox.list_files_in_folder(path)
                tracer.log(f"list of files explored, there are {len(list_of_files)} files")
                dic_of_checksum_files = toolbox.dic_of_checksums(list_of_files)
                tracer.log(f"checksums computed, there are {len(dic_of_checksum_files)} checksums")
                dic_of_files = {checksum: toolbox.split_different_files(files) for checksum, files in dic_of_checksum_files.items()}
                tracer.log(f"files are now split into {sum([len(dic_of_files[checksum]) for checksum in dic_of_files])} distinct files")
                json_path = os.path.join(path, drive_variables.drive_info, drive_variables.fileinfo_json)
                toolbox.save_dic_to_json(dic_of_files, json_path)
            except Exception as e:
                tracer.log(f"An error occurred {e}")
        root.buttonCreateDatabase_click = buttonCreateDatabase_click
        def buttonCopyDatabase_click():
            print("Copy Database clicked")
        root.buttonCopyDatabase_click = buttonCopyDatabase_click
        def buttonStatistics_click():
            print("Button create statistics clicked")
        root.buttonStatistics_click = buttonStatistics_click
        def buttonAddDriveLocation_click():
            new_location = text_field1.get()
            if len(new_location) == 0 or not os.path.exists(new_location):
                tracer.log(f"Path <'{new_location}'> does not exist")
                return
            print(drive_variables.drives['locations'])
            drive_variables.drives['locations'].append(new_location)
            print(drive_variables.drives['locations'])
            text_box1['values'] = [d for d in drive_variables.drives if os.path.exists(d)]
            print(drive_variables.drives['locations'])
            print(text_box1['values'])
            dbs.update_drives_list(drive_variables.drives)
            print("Button add drive location clicked")
        root.buttonAddDriveLocation_click = buttonAddDriveLocation_click

        # Create buttons
        buttonCreateDatabase = tk.Button(root.rootTK, text="Create database")#Create cold storage database
        buttonCreateDatabase.grid(row=3, column=0, padx=5, pady=5)
        buttonCreateDatabase.config(command=root.buttonCreateDatabase_click)
        
        buttonCopyDatabase = tk.Button(root.rootTK, text="Copy to database")#Copy files to cold storage database
        buttonCopyDatabase.grid(row=3, column=1, padx=5, pady=5)
        buttonCopyDatabase.config(command=root.buttonCopyDatabase_click)

        buttonStatistics = tk.Button(root.rootTK, text="Statistics from database")#Create statistics from cold storage
        buttonStatistics.grid(row=3, column=2, padx=5, pady=5)
        buttonStatistics.config(command=root.buttonStatistics_click)

        buttonAddDriveLocation = tk.Button(root.rootTK, text="Add drive")#Create statistics from cold storage
        buttonAddDriveLocation.grid(row=0, column=2, padx=5, pady=5)
        buttonAddDriveLocation.config(command=root.buttonAddDriveLocation_click)

    
    def mainloop(root):
        root.rootTK.mainloop()


def get_text_field(text_field):
    path = text_field.get()
    if not os.path.isdir(path):
        raise ValueError(f"Path '{path}' does not exist or is not a directory")
    return path

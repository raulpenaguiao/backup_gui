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
        root.rootTK.geometry("1200x600")
        root.InitializeComponents()
        root.InitializeDatabase()
    
    #region Initialization functions


    def InitializeComponents(root):
        # Create menu bar
        menu_bar = Menu(root.rootTK)
        root.rootTK.config(menu=menu_bar)

        #region Top bar
        # Top left: Button "index database"
        buttonIndexDatabase = tk.Button(root.rootTK, text="Index Database")
        buttonIndexDatabase.grid(row=0, column=0, padx=12, pady=12, sticky="nw")
        buttonIndexDatabase.config(command=root.buttonCreateDatabase_click)
        root.buttonIndexDatabase = buttonIndexDatabase

        # Top center: Dropdown box with values from drive_variables.drives
        dropdownDrives = ttk.Combobox(root.rootTK)
        dropdownDrives.grid(row=0, column=1, padx=12, pady=12, sticky="nwe")
        dropdownDrives.config(width=75)
        root.dropdownDrives = dropdownDrives

        # Top right: Buttons "add drive" and "remove drive"
        buttonAddDrive = tk.Button(root.rootTK, text="Add Drive")
        buttonAddDrive.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        buttonAddDrive.config(command=root.buttonAddDriveLocation_click)
        root.buttonAddDrive = buttonAddDrive

        buttonRemoveDrive = tk.Button(root.rootTK, text="Remove Drive")
        buttonRemoveDrive.grid(row=0, column=3, padx=5, pady=5, sticky="e")
        buttonRemoveDrive.config(command=root.buttonRemoveDrive_click)
        root.buttonRemoveDrive = buttonRemoveDrive
        #endregion

        #region separators
        # Create a horizontal separator
        separator1 = ttk.Separator(root.rootTK, orient="horizontal")
        separator1.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=10)
        root.separator1 = separator1
        #endregion

        #region actions tab
        buttonCreateUniques = tk.Button(root.rootTK, text="Index Database")
        buttonCreateUniques.grid(row=2, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateUniques.config(command=root.buttonCreateUniques_click)
        root.buttonCreateUniques = buttonCreateUniques
        
        buttonCreateStatistics = tk.Button(root.rootTK, text="Index Database")
        buttonCreateStatistics.grid(row=3, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateStatistics.config(command=root.buttonCreateStatistics_click)
        root.buttonCreateStatistics = buttonCreateStatistics
        #endregion

    def InitializeDatabase(root):
        root.dropdownDrives['values'] = [d for d in drive_variables.drives if os.path.exists(d)]

    #region Button click functions
    def buttonCreateDatabase_click():
        print("buttonCreateDatabase was clicked")

    def buttonAddDriveLocation_click():
        print("buttonAddDriveLocation was clicked")
    
    def buttonRemoveDrive_click():
        print("buttonRemoveDrive was clicked")
    
    def buttonCreateUniques_click():
        print("buttonCreateUniques was clicked")
    
    def buttonCreateStatistics_click():
        print("buttonCreateStatistics was clicked")
    #endregion
    
    
    def mainloop(root):
        root.rootTK.mainloop()


def get_text_field(text_field):
    path = text_field.get()
    if not os.path.isdir(path):
        raise ValueError(f"Path '{path}' does not exist or is not a directory")
    return path

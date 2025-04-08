import tkinter as tk
from tkinter import ttk
from tkinter import Menu
import toolbox
import tracer
import os
import drive_variables
import dbs
from widgets.file_selection_popup import FileSelectionPopup
import send2trash
import file_manager


def get_text_field(text_field):
    path = text_field.get()
    if not os.path.isdir(path):
        raise ValueError(f"Error 93182: Path '{path}' does not exist or is not a directory")
    return path


class BackupGUI:
    def __init__(root):
        root.rootTK = tk.Tk()
        root.rootTK.title("Backup GUI")
        root.rootTK.geometry("1050x600")
        root.InitializeComponents()
        root.InitializeDatabase()
        root.InitializeButtons()
    
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
        dropdownDrives.set('') 
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
        buttonDBCopies = tk.Button(root.rootTK, text="Analyse copies from database")
        buttonDBCopies.grid(row=2, column=0, padx=12, pady=12, sticky="nw")
        buttonDBCopies.config(command=root.buttonDBCopies_click)
        root.buttonDBCopies = buttonDBCopies

        buttonCreateUniques = tk.Button(root.rootTK, text="Create unique files")
        buttonCreateUniques.grid(row=3, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateUniques.config(command=root.buttonCreateUniques_click)
        root.buttonCreateUniques = buttonCreateUniques
        
        buttonCreateStatistics = tk.Button(root.rootTK, text="Create statistics")
        buttonCreateStatistics.grid(row=4, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateStatistics.config(command=root.buttonCreateStatistics_click)
        root.buttonCreateStatistics = buttonCreateStatistics
        #endregion

        #region panel
        # Create a panel frame
        panel_frame = tk.Frame(root.rootTK, borderwidth=2, relief="groove")
        panel_frame.grid(row=2, column=1, rowspan=10, columnspan=3, padx=10, pady=10, sticky="nsew")
        root.panel_frame = panel_frame

        # Configure grid weights for resizing
        root.rootTK.grid_rowconfigure(2, weight=1)
        root.rootTK.grid_columnconfigure(1, weight=1)
        #endregion

        #region footer
        footer_label = tk.Label(root.rootTK, text="Backup GUI © 2025", anchor="center")
        footer_label.grid(row=12, column=0, columnspan=4, pady=10, sticky="ew")
        root.footer_label = footer_label
        #endregion

    def InitializeDatabase(root):
        root.dropdownDrives['values'] = [d['location'] for d in drive_variables.drives if os.path.exists(d['location'])]
        if len(root.dropdownDrives['values']) > 0:
            root.dropdownDrives.set(root.dropdownDrives['values'][0])
    
    def InitializeButtons(root):
        try:
            path = root.dropdownDrives.get()
            full_path = os.path.join(path, drive_variables.drive_folder_info)
            root.set_drive_buttons(os.path.exists(full_path))
        except Exception as e:
            tracer.log(f"Error 32101: {e}")
    #endregion

    #region design manipulation
    def set_drive_buttons(root, state):
        tracer.log("")
        if state:
            state = "active"
        else:
            state = "disabled"
        try:
            root.buttonDBCopies.config(state=state)
            root.buttonCreateUniques.config(state=state)
            root.buttonCreateStatistics.config(state=state)
        except Exception as e:
            tracer.log(f"Error 83102: {e}")
    #endregion

    #region Button click functions
    def buttonCreateDatabase_click(root):
        tracer.log("")
        try:
            path = root.dropdownDrives.get()
            tracer.log(f"The path was fetched at {path}")
            toolbox.create_database(path)
            tracer.log(f"Database created at {path}")
            root.set_drive_buttons(True)
        except Exception as e:
            tracer.log(f"An error occurred {e}")

    def buttonAddDriveLocation_click(root):
        tracer.log("")
        try:
            # Create a new popup window
            popup = tk.Toplevel(root.rootTK)
            popup.title("Add Drive Location")
            popup.geometry("400x200")

            # Add a label and text entry field
            label = tk.Label(popup, text="Enter Drive Path:")
            label.grid(row=0, column=0, columnspan=2, pady=10)

            text_field = tk.Entry(popup, width=50)
            text_field.grid(row=1, column=0, columnspan=2, pady=10)
            #print(f"Label grid info: {label.grid_info()}")
            #print(f"Text field grid info: {text_field.grid_info()}")

            # Add a button to confirm the drive addition
            def confirm_add_drive():
                try:
                    drive_path = get_text_field(text_field)
                    tracer.log(f"Drive '{drive_path}' to be added.")
                    drive_variables.drives.append({'location':drive_path})
                    root.dropdownDrives['values'] = [d['location'] for d in drive_variables.drives if os.path.exists(d['location'])]
                    dbs.update_drives_list(drive_variables.drives)
                    tracer.log(f"Drive '{drive_path}' added successfully.")
                except ValueError as e:
                    tracer.log(str(e))
                popup.destroy()

            button_confirm = tk.Button(popup, text="Add", command=confirm_add_drive)
            button_confirm.grid(row=2, column=0, columnspan=2, pady=10)

            # Add a cancel button to close the popup  
            button_cancel = tk.Button(popup, text="Cancel", command=popup.destroy)
            button_cancel.grid(row=3, column=0, columnspan=2, pady=10)
        except Exception as e:
            tracer.log(f"Error 16425: {e}")
    
    def buttonRemoveDrive_click(root):
        tracer.log("")
        try:
            #Get selected drive name
            selected_drive = root.dropdownDrives.get()
            if selected_drive:
                tracer.log(f"Selected drive: {selected_drive}")
            else:
                tracer.log("No drive selected.")
                return

            # Create a confirmation popup
            confirm_popup = tk.Toplevel(root.rootTK)
            confirm_popup.title("Confirm Deletion")
            confirm_popup.geometry("400x250")

            # Add a label to confirm the deletion
            label = tk.Label(confirm_popup, text=f"Are you sure you want to delete '{selected_drive}'?")
            label.grid(row=0, column=0, columnspan=2, pady=10)

            # Add a button to confirm the deletion
            def confirm_delete():
                try:
                    drive_variables.drives = [d for d in drive_variables.drives if d['location'] != selected_drive]
                    root.dropdownDrives['values'] = [d['location'] for d in drive_variables.drives if os.path.exists(d['location'])]
                    dbs.update_drives_list(drive_variables.drives)
                    tracer.log(f"Drive '{selected_drive}' removed successfully.")
                except Exception as e:
                    tracer.log(f"Error removing drive: {str(e)}")
                confirm_popup.destroy()

            button_confirm = tk.Button(confirm_popup, text="Delete", command=confirm_delete)
            button_confirm.grid(row=2, column=0, columnspan=2, pady=10)

            # Add a cancel button to close the popup
            button_cancel = tk.Button(confirm_popup, text="Cancel", command=confirm_popup.destroy)
            button_cancel.grid(row=3, column=0, columnspan=2, pady=10)
            #print(f"Button ancel info: {button_cancel.grid_info()}")
            #print(f"Button confirm info: {button_confirm.grid_info()}")

        except Exception as e:
            tracer.log(f"Error 26425: {e}")
    
    def buttonDBCopies_click(root):
        tracer.log("")
        try:
            root.repeated_files = toolbox.create_copies_report(get_text_field(root.dropdownDrives))
            root.repeated_files = [file for file in root.repeated_files if not file[0]['leave_copies']]
            root.number_of_repetitions = len(root.repeated_files)

            #Create report
            tracer.clear_log(drive_variables.copies_report_txt)
            for _, repetition in enumerate(root.repeated_files):
                message = "Files in these locations are the same:\n"
                for file in repetition:
                    message += (" "*4) + file['file_path'] + "\n"
                tracer.log_to_report(message, drive_variables.copies_report_txt)
            tracer.log("Report created")

            #Create popups
            def process_files():
                tracer.log("")
                try:
                    result = root.fileSelectionPopup.result
                    tracer.log(f"Result from file selection popup: {result}")
                    if result == None:
                        raise ValueError(f"Error 93183: Invalid result from file selection popup")
                    elif result[0] == "keep this":
                        for file in root.repetition:
                            if not file['file_path'] == root.fileSelectionPopup.result[1]:
                                tracer.log(f"Deleting file in {file['file_path']}")
                                send2trash.send2trash(file['file_path'])
                        return False
                    elif result[0] == "keep all":
                        tracer.log("Keeping all files in this repetition.")
                    elif result[0] == "delete all":
                        tracer.log("Deleting all files in this repetition.")
                        for file in root.repetition:
                            tracer.log(f"Deleting file in {file['file_path']}")
                            send2trash.send2trash(file['file_path'])
                        return False
                    elif result[0] == "leave":
                        for file in root.repetition:
                            file['leave_copies'] = True
                        tracer.log("Leaving selection menu without changes.")
                        return True
                    else:
                        raise ValueError(f"Error 93182: Invalid result from file selection popup: {result}")
                except Exception as e:
                    tracer.log(f"Error 93192: {e}")

            def on_popup_close():
                tracer.log("")
                try:
                    leaveQ = process_files()
                    if leaveQ or root.index == root.number_of_repetitions - 1:
                        return
                    root.index += 1
                    root.repetition = root.repeated_files[root.index]
                    root.fileSelectionPopup = FileSelectionPopup(
                        root.rootTK, 
                        root.repetition, 
                        root.index, 
                        root.number_of_repetitions, 
                        on_close = on_popup_close,
                        drive_full_path = get_text_field(root.dropdownDrives)
                    )
                except Exception as e:
                    tracer.log(f"Error 56325: {e}")

            if root.number_of_repetitions > 0:
                tracer.log(f"Number of repetitions: {root.number_of_repetitions}")
                root.index = 0
                root.repetition = root.repeated_files[root.index]
                root.fileSelectionPopup = FileSelectionPopup(
                    root.rootTK, 
                    root.repetition, 
                    root.index, 
                    root.number_of_repetitions, 
                    on_close = on_popup_close,
                    drive_full_path = get_text_field(root.dropdownDrives)
                )
                tracer.log(f"Popup created")

        except Exception as e:
            tracer.log(f"Error 56425: {e}")

    def buttonCreateUniques_click(root):
        tracer.log("")
        try:
            # Clear the panel_frame
            for widget in root.panel_frame.winfo_children():
                widget.destroy()

            # Add a label to the panel_frame
            label = tk.Label(root.panel_frame, text="Creation of new and unique files", font=("Arial", 16))
            label.grid(row=0, column=0, columnspan=4, pady=10)

            # Add a label and text input field
            label_input = tk.Label(root.panel_frame, text="Location of new drive")
            label_input.grid(row=1, column=0, columnspan=4, pady=5)

            text_input = tk.Entry(root.panel_frame, width=50)
            text_input.grid(row=2, column=1, columnspan=2, pady=5)

            def compareWithDatabase_click():
                tracer.log("")
                backup_drive_path = get_text_field(root.dropdownDrives)
                additional_drive_path = get_text_field(text_input)
                comparison = toolbox.create_comparison_report(backup_drive_path, additional_drive_path)
                files_to_copy = [file['file_path'] for file in comparison]
                file_manager.create_unique_files(additional_drive_path, files_to_copy)

            def createNewDatabase_click():
                tracer.log("")
                toolbox.create_database(get_text_field(text_input))


            # Add buttons for unique menu actions
            button_initialize_drive = tk.Button(root.panel_frame, 
                text="Initialize Drive", 
                command= createNewDatabase_click)
            button_initialize_drive.grid(row=3, column=0, columnspan=2, pady=5)

            button_comparewithdatabase = tk.Button(root.panel_frame, 
                text="Create comparison report", command = compareWithDatabase_click)
            button_comparewithdatabase.grid(row=4, column=0, columnspan=2, pady=5)
        except Exception as e:
            tracer.log(f"Error 83103: {e}")
    
    def buttonCreateStatistics_click(root):
        tracer.log("")
        try:
            #Create statistic pictures
            drive_path = get_text_field(root.dropdownDrives)
            toolbox.create_statistics_pictures(drive_path)
            tracer.log("Pictures created")

            # Clear the panel_frame
            for widget in root.panel_frame.winfo_children():
                widget.destroy()

            #Add a reference to the images
            drive_info_folder_full_path = os.path.join(drive_path, drive_variables.drive_folder_info)
            root.image_names = [drive_variables.extension_distribution, drive_variables.file_size_histogram, drive_variables.file_repetition_count, drive_variables.file_creation_time_histogram]
            root.image_index = 0

            def fill_image():
                tracer.log("")
                try:
                    index = root.image_index
                    tracer.log(f"Fill image {index}")
                    # Clear the panel_frame
                    for widget in root.panel_frame.winfo_children():
                        if widget not in [root.panel_frame.winfo_children()[0],  # Label
                                        root.panel_frame.winfo_children()[1],  # Left button
                                        root.panel_frame.winfo_children()[2]]: # Right button
                            widget.destroy()
                    # Add an image to the panel_frame, make sure to strech to fit the panel
                    image_path = os.path.join(drive_info_folder_full_path, root.image_names[index])
                    from PIL import Image, ImageTk
                    original_image = Image.open(image_path)
                    image_width = root.panel_frame.winfo_width()
                    image_height = root.panel_frame.winfo_height() - 50  # Leave some space for the buttons and label
                    resized_image = ImageTk.PhotoImage(
                        original_image.resize((image_width, image_height), Image.Resampling.LANCZOS)
                    )
                    root.images = resized_image  # Keep a reference to avoid garbage collection

                    # Create a label for the image and place it in a grid
                    image_label = tk.Label(root.panel_frame, image=resized_image)
                    image_label.grid(row=1, column=0, columnspan=5, padx=5, pady=5)
                except Exception as e:
                    tracer.log(f"Error loading image {index}: {str(e)}")

            def on_button_left_click():
                tracer.log("")
                try:
                    root.image_index -= 1
                    if root.image_index < 0:     
                        root.image_index = len(root.image_names) - 1
                    fill_image()
                except Exception as e: 
                    tracer.log(f"Error 83103: {e}")
            
            def on_button_right_click():
                tracer.log("")
                try:
                    root.image_index += 1
                    if root.image_index >= len(root.image_names):     
                        root.image_index = 0
                    fill_image()
                except Exception as e: 
                    tracer.log(f"Error 83104: {e}")

            # Add a label to the panel_frame
            label = tk.Label(root.panel_frame, text="Statistics Menu", font=("Arial", 16))
            label.grid(row=0, column=0, columnspan=2, pady=10)

            # Add left and right arrow buttons
            button_left = tk.Button(root.panel_frame, text="←", command=on_button_left_click)
            button_left.grid(row=0, column=2, pady=10, padx=5, sticky="e")

            button_right = tk.Button(root.panel_frame, text="→", command=on_button_right_click)
            button_right.grid(row=0, column=3, pady=10, padx=5, sticky="w")
            fill_image()
        except Exception as e:
            tracer.log(f"Error 83101: {e}")
    #endregion
    
    def mainloop(root):
        root.rootTK.mainloop()
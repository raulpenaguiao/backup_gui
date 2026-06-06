import tkinter as tk
from tkinter import ttk
from tkinter import Menu
import platform
import tools_library.toolbox as toolbox
import tools_library.tracer as tracer
import os
import tools_library.drive_variables as drive_variables
import tools_library.dbs as dbs
from widgets_library.file_selection_popup import FileSelectionPopup
import send2trash
import tools_library.file_manager as file_manager
from widgets_library.loading_popup import LoadingPopup
from tools_library.progress_tracker import ProgressTracker
import data_clean


def _set_busy_cursor(*widgets):
    name = "watch" if platform.system() != "Windows" else "wait"
    for w in widgets:
        try:
            w.config(cursor=name)
        except Exception:
            pass


def _clear_cursor(*widgets):
    for w in widgets:
        try:
            w.config(cursor="")
        except Exception:
            pass


def get_text_field(text_field):
    path = text_field.get()
    if not os.path.isdir(path):
        raise ValueError(f"Error 93182: Path '{path}' does not exist or is not a directory")
    return path


class _Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self._tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, background="#ffffe0", relief="solid",
                 borderwidth=1, wraplength=320, justify="left",
                 font=("Arial", 9)).pack(ipadx=4, ipady=2)

    def _hide(self, _event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


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
        _Tooltip(buttonIndexDatabase,
                 "Scans every file in the selected drive and builds a database storing each "
                 "file's checksum, size, extension, and timestamps. This must be run before "
                 "any other action can be performed on this drive.")
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
        _Tooltip(buttonAddDrive,
                 "Register a new folder or drive path with this application. "
                 "The path must already exist on your filesystem. "
                 "Once added it will appear in the drive dropdown.")
        root.buttonAddDrive = buttonAddDrive

        buttonRemoveDrive = tk.Button(root.rootTK, text="Remove Drive")
        buttonRemoveDrive.grid(row=0, column=3, padx=5, pady=5, sticky="e")
        buttonRemoveDrive.config(command=root.buttonRemoveDrive_click)
        _Tooltip(buttonRemoveDrive,
                 "Remove the currently selected drive from the application's list. "
                 "No files are deleted — this only unregisters the drive path.")
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
        _Tooltip(buttonDBCopies,
                 "Reads the drive's database and finds every group of files that share "
                 "identical content (same checksum). Opens an interactive dialog for each "
                 "duplicate group so you can choose to keep one copy, keep all, or delete all.")
        root.buttonDBCopies = buttonDBCopies

        buttonCreateUniques = tk.Button(root.rootTK, text="Create unique files")
        buttonCreateUniques.grid(row=3, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateUniques.config(command=root.buttonCreateUniques_click)
        _Tooltip(buttonCreateUniques,
                 "Compare a second folder against the selected drive's database and copy "
                 "over only the files that do not already exist in the backup. "
                 "Useful for merging new content without introducing duplicates.")
        root.buttonCreateUniques = buttonCreateUniques

        buttonCreateStatistics = tk.Button(root.rootTK, text="Create statistics")
        buttonCreateStatistics.grid(row=4, column=0, padx=12, pady=12, sticky="nw")
        buttonCreateStatistics.config(command=root.buttonCreateStatistics_click)
        _Tooltip(buttonCreateStatistics,
                 "Generate visual charts from the drive's database: file extension breakdown, "
                 "file size distribution, number-of-copies histogram, and file creation time "
                 "distribution. Charts are displayed in the panel and saved to the drive's "
                 "info folder.")
        root.buttonCreateStatistics = buttonCreateStatistics

        buttonCleanFiles = tk.Button(root.rootTK, text="Clean files")
        buttonCleanFiles.grid(row=5, column=0, padx=12, pady=12, sticky="nw")
        buttonCleanFiles.config(command=root.buttonCleanFiles_click)
        _Tooltip(buttonCleanFiles,
                 "Remove junk files from the selected drive. You can choose which file "
                 "extensions to target (e.g. .log, .tmp, .bak), specific folder names to "
                 "delete entirely, and optionally remove all empty folders. "
                 "A confirmation dialog lets you review and adjust every option before anything is deleted.")
        root.buttonCleanFiles = buttonCleanFiles
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
        loading_popup = None
        try:
            _set_busy_cursor(root.rootTK)
            root.rootTK.update_idletasks()  # flush cursor change before heavy work starts
            progress_tracker = ProgressTracker(name="File Listing", unit="files")
            tracer.log(progress_tracker.name)
            tracer.log(progress_tracker.unit)
            tracer.log(progress_tracker.loaded)
            loading_popup = LoadingPopup(root.rootTK, progress_tracker)
            _set_busy_cursor(loading_popup.popup)  # propagate to popup window
            tracer.log("")
            root.rootTK.update()

            tracer.log("")
            path = root.dropdownDrives.get()
            tracer.log(f"The path was fetched at {path}")
            toolbox.create_database(path, progress_tracker)
            tracer.log(f"Database created at {path}")
            root.set_drive_buttons(True)
        except Exception as e:
            tracer.log(f"An error occurred {e}")
        finally:
            if loading_popup is not None:
                loading_popup.popup.destroy()
            _clear_cursor(root.rootTK)

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
    
    def buttonCleanFiles_click(root):
        tracer.log("")
        try:
            popup = tk.Toplevel(root.rootTK)
            popup.title("Clean Files")
            popup.geometry("480x580")
            popup.resizable(True, True)

            outer = ttk.Frame(popup, padding=12)
            outer.pack(fill=tk.BOTH, expand=True)

            tk.Label(outer, text="Clean Files", font=("Arial", 14, "bold")).pack(anchor="w")
            tk.Label(outer, text="Select what to remove from the chosen drive.",
                     font=("Arial", 9), foreground="#555555").pack(anchor="w", pady=(0, 8))

            ttk.Separator(outer, orient="horizontal").pack(fill=tk.X, pady=(0, 8))

            # ── Extensions ──────────────────────────────────────────────────
            tk.Label(outer, text="File extensions to delete:", font=("Arial", 10, "bold")).pack(anchor="w")

            ext_canvas = tk.Canvas(outer, height=140, borderwidth=1, relief="sunken")
            ext_scrollbar = ttk.Scrollbar(outer, orient="vertical", command=ext_canvas.yview)
            ext_inner = ttk.Frame(ext_canvas)
            ext_inner.bind("<Configure>",
                           lambda e: ext_canvas.configure(scrollregion=ext_canvas.bbox("all")))
            ext_canvas.create_window((0, 0), window=ext_inner, anchor="nw")
            ext_canvas.configure(yscrollcommand=ext_scrollbar.set)
            ext_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ext_scrollbar.pack(side=tk.LEFT, fill=tk.Y)

            ext_vars = {}

            def _add_ext_row(ext):
                var = tk.BooleanVar(value=True)
                ext_vars[ext] = var
                tk.Checkbutton(ext_inner, text=ext, variable=var).pack(anchor="w", padx=6)

            for ext in sorted(data_clean.DEFAULT_DELETE_EXTENSIONS):
                _add_ext_row(ext)

            ext_add_frame = ttk.Frame(outer)
            ext_add_frame.pack(fill=tk.X, pady=4)
            ext_entry = tk.Entry(ext_add_frame, width=18)
            ext_entry.pack(side=tk.LEFT, padx=(0, 4))
            ext_entry.insert(0, ".ext")

            def _add_extension():
                raw = ext_entry.get().strip()
                if not raw or raw == ".ext":
                    return
                ext = raw if raw.startswith('.') else f'.{raw}'
                if ext not in ext_vars:
                    _add_ext_row(ext)
                    ext_canvas.configure(scrollregion=ext_canvas.bbox("all"))
                ext_entry.delete(0, tk.END)

            tk.Button(ext_add_frame, text="Add extension", command=_add_extension).pack(side=tk.LEFT)

            ttk.Separator(outer, orient="horizontal").pack(fill=tk.X, pady=8)

            # ── Empty folders ────────────────────────────────────────────────
            delete_empty_var = tk.BooleanVar(value=False)
            tk.Checkbutton(outer, text="Delete empty folders",
                           variable=delete_empty_var).pack(anchor="w")

            ttk.Separator(outer, orient="horizontal").pack(fill=tk.X, pady=8)

            # ── Folder names ─────────────────────────────────────────────────
            tk.Label(outer, text="Folder names to delete entirely:", font=("Arial", 10, "bold")).pack(anchor="w")

            folder_listbox = tk.Listbox(outer, height=5, selectmode=tk.EXTENDED)
            folder_listbox.pack(fill=tk.X, pady=4)
            for d in sorted(data_clean.DEFAULT_DELETE_DIRS):
                folder_listbox.insert(tk.END, d)

            folder_btn_frame = ttk.Frame(outer)
            folder_btn_frame.pack(fill=tk.X)
            folder_entry = tk.Entry(folder_btn_frame, width=22)
            folder_entry.pack(side=tk.LEFT, padx=(0, 4))

            def _add_folder():
                name = folder_entry.get().strip()
                if name:
                    folder_listbox.insert(tk.END, name)
                    folder_entry.delete(0, tk.END)

            def _remove_folder():
                for i in reversed(folder_listbox.curselection()):
                    folder_listbox.delete(i)

            tk.Button(folder_btn_frame, text="Add", command=_add_folder).pack(side=tk.LEFT, padx=(0, 4))
            tk.Button(folder_btn_frame, text="Remove selected", command=_remove_folder).pack(side=tk.LEFT)

            ttk.Separator(outer, orient="horizontal").pack(fill=tk.X, pady=8)

            # ── Action buttons ───────────────────────────────────────────────
            action_frame = ttk.Frame(outer)
            action_frame.pack(fill=tk.X)

            def _run_clean():
                try:
                    path = root.dropdownDrives.get()
                    if not os.path.isdir(path):
                        tracer.log(f"Clean aborted: invalid path '{path}'")
                        return
                    selected_exts = {ext for ext, var in ext_vars.items() if var.get()}
                    selected_folders = set(folder_listbox.get(0, tk.END))
                    popup.destroy()
                    _set_busy_cursor(root.rootTK)
                    root.rootTK.update()
                    freed = data_clean.clean(
                        path,
                        extensions=selected_exts,
                        folder_names=selected_folders,
                        delete_empty_folders=delete_empty_var.get()
                    )
                    tracer.log(f"Clean finished. Freed: {data_clean.format_size(freed)}")
                except Exception as e:
                    tracer.log(f"Error 72502: {e}")
                finally:
                    _clear_cursor(root.rootTK)

            tk.Button(action_frame, text="Cancel", command=popup.destroy).pack(side=tk.RIGHT, padx=(4, 0))
            tk.Button(action_frame, text="Run Clean", command=_run_clean,
                      bg="#c0392b", fg="white", activebackground="#922b21",
                      activeforeground="white").pack(side=tk.RIGHT)

        except Exception as e:
            tracer.log(f"Error 72501: {e}")

    def mainloop(root):
        root.rootTK.mainloop()
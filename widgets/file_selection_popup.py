import tkinter as tk
import tracer
from tkinter import ttk


class FileSelectionPopup:

    def __init__(self, root, repetition, trial, number_of_repetitions, on_close=None, drive_full_path = ""):
        self.popup = tk.Toplevel(root)
        tracer.log("Initializing FileSelectionPopup with parameters:")
        tracer.log(f"root: {root}")
        tracer.log(f"repetition: {repetition}")
        tracer.log(f"trial: {trial}")
        tracer.log(f"number_of_repetitions: {number_of_repetitions}")
        tracer.log(f"on_close: {on_close}")
        tracer.log(f"drive_full_path: {drive_full_path}")

        # Center the popup window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 1200
        window_height = 800
        x_coordinate = (screen_width - window_width) // 2
        y_coordinate = (screen_height - window_height) // 2
        self.popup.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self.popup.title("Select files to keep")
        self.result = None

        label_text = f"File {trial + 1} for {number_of_repetitions}.\nSelect which of these files to keep:"
        label = tk.Label(self.popup, text=label_text)
        label.pack(pady=10)

        
        len_drive_full_path = len(drive_full_path)

        # Add a scrollbar to the Treeview
        scrollbar = ttk.Scrollbar(self.popup, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Configure the Treeview to use the scrollbar
        columns = ("File Path",)
        list_of_files = ttk.Treeview(self.popup, columns=columns, show="headings", height=15, yscrollcommand=scrollbar.set)
        scrollbar.config(command=list_of_files.yview)
        columns = ("File Path",)
        #list_of_files = ttk.Treeview(self.popup, columns=columns, show="headings", height=len(repetition))
        list_of_files.heading("File Path", text="File Path")
        list_of_files.column("File Path", width=750, anchor="w")

        for file in repetition:
            list_of_files.insert("", "end", values=(file['file_path'][len_drive_full_path:],))
        list_of_files.pack(pady=10)
        #list_of_files.set(repetition[0]['file_path'][len_drive_full_path:])  # Set default selection

        def keep_this():
            selected_item = list_of_files.selection()
            if selected_item:
                selected_file = drive_full_path + list_of_files.item(selected_item, "values")[0]
            else:
                selected_file = None
            tracer.log(f"Keeping file: {selected_file}")
            self.result = tuple(["keep this", selected_file])
            if not on_close == None:
                on_close()
            self.popup.destroy()

        def keep_all():
            tracer.log("Keeping all files in this repetition.")
            self.result = tuple(["keep all"])
            if not on_close == None:
                on_close()
            self.popup.destroy()

        def delete_all():
            tracer.log("Deleting all of these files.")
            self.result = tuple(["delete all"])
            if not on_close == None:
                on_close()
            self.popup.destroy()

        def leave_selection_menu():
            tracer.log("Leaving selection menu without changes.")
            self.result = tuple(["leave"])
            if not on_close == None:
                on_close()
            self.popup.destroy()

        button_keep_this = tk.Button(self.popup, text="Keep This", command=keep_this)
        button_keep_this.pack(side="left", padx=10, pady=10)

        button_keep_all = tk.Button(self.popup, text="Keep All", command=keep_all)
        button_keep_all.pack(side="left", padx=10, pady=10)

        button_delete_all = tk.Button(self.popup, text="Delete All", command=delete_all)
        button_delete_all.pack(side="left", padx=10, pady=10)

        button_leave = tk.Button(self.popup, text="Leave Selection Menu", command=leave_selection_menu)
        button_leave.pack(side="left", padx=10, pady=10)
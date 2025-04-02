import tkinter as tk
import tracer
from tkinter import ttk


class FileSelectionPopup:

    def __init__(self, root, repetition, trial, number_of_repetitions, on_close=None, drive_full_path = ""):
        tracer.log(f"FileSelectionPopup created", trace_level = 3)
        tracer.log(f"root: {root}", trace_level = 3)
        tracer.log(f"repetition: {repetition}", trace_level = 3)
        tracer.log(f"trial: {trial}", trace_level = 3)
        tracer.log(f"number of repetitions: {number_of_repetitions}", trace_level = 3)
        self.popup = tk.Toplevel(root)

        # Center the popup window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 800
        window_height = 300
        x_coordinate = (screen_width - window_width) // 2
        y_coordinate = (screen_height - window_height) // 2
        self.popup.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self.popup.title("Select files to keep")
        self.result = None

        label_text = f"File {trial + 1} for {number_of_repetitions}.\nSelect which of these files to keep:"
        label = tk.Label(self.popup, text=label_text)
        label.pack(pady=10)

        len_drive_full_path = len(drive_full_path)
        dropdown = ttk.Combobox(self.popup, values=[file['file_path'][len_drive_full_path:] for file in repetition], width=150)
        dropdown.pack(pady=10)
        dropdown.set(repetition[0]['file_path'][len_drive_full_path:])  # Set default selection

        def keep_this():
            selected_file = len_drive_full_path + dropdown.get()
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

        button_leave = tk.Button(self.popup, text="Leave Selection Menu", command=leave_selection_menu)
        button_leave.pack(side="left", padx=10, pady=10)
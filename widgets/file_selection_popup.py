import tkinter as tk
import tracer
from tkinter import ttk


class FileSelectionPopup:
    def __init__(self, root, repetition, trial, number_of_repetitions, result):
        popup = tk.Toplevel(root)
        tracer.log("Popup initialization started.")
        tracer.log(repetition)
        popup.title("Select files to keep")
        popup.geometry("800x300")

        label_text = f"File {trial + 1} for {number_of_repetitions}.\nSelect which of these files to keep:"
        label = tk.Label(popup, text=label_text)
        label.pack(pady=10)
        tracer.log(repetition)

        dropdown = ttk.Combobox(popup, values=[file['file_path'] for file in repetition], width=150)
        dropdown.pack(pady=10)
        dropdown.set(repetition[0]['file_path'])  # Set default selection
        tracer.log("Combobox created")

        def keep_this():
            selected_file = dropdown.get()
            tracer.log(f"Keeping file: {selected_file}")
            result = tuple(["keep this", selected_file])
            popup.destroy()

        def keep_all():
            tracer.log("Keeping all files in this repetition.")
            result = tuple(["keep all"])
            popup.destroy()

        def leave_selection_menu():
            tracer.log("Leaving selection menu without changes.")
            result = tuple(["leave"])
            popup.destroy()

        button_keep_this = tk.Button(popup, text="Keep This", command=keep_this)
        button_keep_this.pack(side="left", padx=10, pady=10)
        tracer.log("Button keep this created")

        button_keep_all = tk.Button(popup, text="Keep All", command=keep_all)
        button_keep_all.pack(side="left", padx=10, pady=10)
        tracer.log("Button keep all created")

        button_leave = tk.Button(popup, text="Leave Selection Menu", command=leave_selection_menu)
        button_leave.pack(side="left", padx=10, pady=10)
        tracer.log("Button leave created")

import os
import tkinter as tk
import tools_library.tracer as tracer
from tkinter import ttk
from PIL import Image, ImageTk


class FileSelectionPopup:

    def __init__(self, root, repetition, trial, number_of_repetitions, on_close=None, drive_full_path = ""):
        self.popup = tk.Toplevel(root)
        tracer.log("Initializing FileSelectionPopup with parameters:", trace_level=2)
        tracer.log(f"root: {root}", trace_level=2)
        tracer.log(f"repetition: {repetition}", trace_level=2)
        tracer.log(f"trial: {trial}", trace_level=2)
        tracer.log(f"number_of_repetitions: {number_of_repetitions}", trace_level=2)
        tracer.log(f"on_close: {on_close}", trace_level=2)
        tracer.log(f"drive_full_path: {drive_full_path}", trace_level=2)

        # Center the popup window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 1200
        window_height = 800
        x_coordinate = (screen_width - window_width) // 2
        y_coordinate = (screen_height - window_height) // 2
        self.popup.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self.popup.title("Pigmy Backup Application")
        self.result = None
        tracer.log(f"Center the popup window at x={x_coordinate}, y={y_coordinate}", trace_level=2)

        tk.Label(self.popup, text="Select files to keep",
                 font=("Helvetica", 15, "bold"), anchor="w").pack(fill=tk.X, padx=14, pady=(10, 0))
        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=14, pady=(6, 0))

        label_text = f"File {trial + 1} of {number_of_repetitions}. Select which file to keep:"
        label = tk.Label(self.popup, text=label_text, anchor="w")
        label.pack(fill=tk.X, padx=14, pady=(6, 0))

        
        len_drive_full_path = len(drive_full_path)

        # Create main container frame for horizontal layout
        main_container = ttk.Frame(self.popup)
        main_container.pack(expand=True, fill='both', pady=10)

        # Create a frame to hold the Treeview and scrollbars
        frame = ttk.Frame(main_container)
        frame.pack(side='left', expand=True, fill='both')
        frame.pack(pady=10)

        # Create frame for side panel (right side)
        side_panel = ttk.Frame(main_container, width=220)
        side_panel.pack(side='right', fill='y', padx=5)
        side_panel.pack_propagate(False)
        tracer.log(f"Create a frame to hold the Treeview and scrollbars", trace_level=2)

        # Create scrollbars
        scrollbar = ttk.Scrollbar(frame, orient="horizontal")
        tracer.log(f"Create scrollbars", trace_level=2)
        
        # Create Treeview
        columns = ("File Path",)
        list_of_files = ttk.Treeview(frame, columns=columns, show="headings", height=30,
                        xscrollcommand=scrollbar.set)
        tracer.log(f"Create Treeview with columns: {columns}", trace_level=2)


        # Add items to Treeview
        selected_text = FileSelectionPopup.populate_treeview(list_of_files, len_drive_full_path, repetition)

        # Configure scrollbars
        scrollbar.config(command=list_of_files.xview)
        tracer.log(f"Configure scrollbars", trace_level=2)

        # Configure Treeview columns
        list_of_files.heading("File Path", text="File Path")
        # Calculate the maximum width based on the content
        max_width = 0
        for item in list_of_files.get_children():
            file_path = list_of_files.item(item)['values'][0]
            text_width = len(file_path) * 7  # Approximate width per character
            max_width = max(max_width, text_width)
        
        list_of_files.column("File Path", width=max_width, anchor="w")
        tracer.log(f"Configure Treeview columns", trace_level=2)

        # Configure frame grid
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        list_of_files.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=1, column=0, sticky='ew')
        tracer.log(f"Configure frame grid", trace_level=2)

        def _update_preview(_event=None):
            sel = list_of_files.selection()
            if sel:
                rel_path = list_of_files.item(sel[0], "values")[0]
                FileSelectionPopup.populate_side_panel(side_panel, drive_full_path + rel_path)

        list_of_files.bind("<<TreeviewSelect>>", _update_preview)
        _update_preview()


        def keep_this():
            tracer.log("", trace_level=2)
            try:
                selected_item = list_of_files.selection()
                if selected_item:
                    selected_file = drive_full_path + list_of_files.item(selected_item, "values")[0]
                else:
                    selected_file = None
                tracer.log(f"Keeping file: {selected_file}", trace_level=2)
                self.result = tuple(["keep this", selected_file])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log_error(f"Error in keep_this: {e}")

        def keep_all():
            tracer.log("", trace_level=2)
            try:
                self.result = tuple(["keep all"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log_error(f"Error in keep_all: {e}")

        def delete_all():
            tracer.log("", trace_level=2)
            try:
                self.result = tuple(["delete all"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log_error(f"Error in delete_all: {e}")

        def leave_selection_menu():
            tracer.log("", trace_level=2)
            try:
                self.result = tuple(["leave"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log_error(f"Error in leave_selection_menu: {e}")

        button_keep_this = tk.Button(self.popup, text="Keep This", command=keep_this)
        button_keep_this.pack(side="left", padx=10, pady=10)

        button_keep_all = tk.Button(self.popup, text="Keep All", command=keep_all)
        button_keep_all.pack(side="left", padx=10, pady=10)

        button_delete_all = tk.Button(self.popup, text="Delete All", command=delete_all)
        button_delete_all.pack(side="left", padx=10, pady=10)

        button_leave = tk.Button(self.popup, text="Leave Selection Menu", command=leave_selection_menu)
        button_leave.pack(side="left", padx=10, pady=10)

        


        # Log the dimensions of the Treeview after it has been rendered
        def log_treeview_dimensions():
            tracer.log(f"Treeview width: {list_of_files.winfo_width()} pixels", trace_level=2)
            tracer.log(f"Treeview height: {list_of_files.winfo_height()} pixels", trace_level=2)

        self.popup.lift()
        self.popup.focus_set()

        # Schedule the logging after the popup window is rendered
        self.popup.after(100, log_treeview_dimensions)

        # Log window dimensions and position
        tracer.log(f"Window dimensions: {window_width}x{window_height}", trace_level=2)
        tracer.log(f"Window position: x={x_coordinate}, y={y_coordinate}", trace_level=2)

        # Log position and dimensions of each widget
        tracer.log(f"Label position: {label.winfo_geometry()}", trace_level=2)
        tracer.log(f"Frame position: {frame.winfo_geometry()}", trace_level=2)
        tracer.log(f"List position: {list_of_files.winfo_geometry()}", trace_level=2)
        tracer.log(f"Scrollbar position: {scrollbar.winfo_geometry()}", trace_level=2)
        tracer.log(f"Keep This button position: {button_keep_this.winfo_geometry()}", trace_level=2)
        tracer.log(f"Keep All button position: {button_keep_all.winfo_geometry()}", trace_level=2)
        tracer.log(f"Delete All button position: {button_delete_all.winfo_geometry()}", trace_level=2)
        tracer.log(f"Leave button position: {button_leave.winfo_geometry()}", trace_level=2)


    @staticmethod
    def populate_treeview(list_of_files, len_drive_full_path, repetition):
        tracer.log("", trace_level=2)
        try:
            file_path = None
            first_item = None
            for index, file in enumerate(repetition):
                tracer.log(f"Insert file into Treeview: {file['file_path']} trimmed by {len_drive_full_path}", trace_level=2)
                path_from_drive_to_file = file['file_path'][len_drive_full_path:]
                list_of_files.insert("", "end", values=(path_from_drive_to_file,), iid=index)
                if first_item is None:
                    first_item = index
                    file_path = file['file_path']
            tracer.log(f"Insert files into Treeview - Repetitions: {path_from_drive_to_file}", trace_level=2)
            list_of_files.selection_set(first_item)  # Set default selection
            tracer.log(f"Set default selection in Treeview as {repetition[0]['file_path'][len_drive_full_path:]}", trace_level=2)
            return file_path
        except Exception as e:
            tracer.log_error(f"Error 96426: in populate_treeview: {e}")
    

    @staticmethod
    def populate_side_panel(side_panel, file_path):
        for widget in side_panel.winfo_children():
            widget.destroy()

        tk.Label(side_panel, text=os.path.basename(file_path),
                 font=("Helvetica", 8, "bold"), anchor="w", wraplength=210).pack(fill="x", padx=4, pady=(6, 2))

        ext = os.path.splitext(file_path)[1].lower()
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        if ext in image_exts:
            try:
                img = Image.open(file_path)
                img.thumbnail((210, 280))
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(side_panel, image=photo)
                lbl.image = photo
                lbl.pack(padx=4, pady=4)
            except Exception as e:
                tracer.log_error(f"Image preview error: {e}")

        tk.Label(side_panel, text="First 100 chars:", font=("Helvetica", 8, "bold"),
                 anchor="w").pack(fill="x", padx=4, pady=(6, 0))
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                preview = f.read(100)
        except Exception:
            preview = "(cannot read file)"
        tk.Label(side_panel, text=preview or "(empty file)", wraplength=210,
                 anchor="nw", justify="left", font=("Courier", 8)).pack(fill="x", padx=4)

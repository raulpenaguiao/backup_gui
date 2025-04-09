import tkinter as tk
import tools_library.tracer as tracer
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
        tracer.log(f"Center the popup window at x={x_coordinate}, y={y_coordinate}")

        label_text = f"File {trial + 1} for {number_of_repetitions}.\nSelect which of these files to keep:"
        label = tk.Label(self.popup, text=label_text)
        label.pack(pady=10)

        
        len_drive_full_path = len(drive_full_path)

        # Create main container frame for horizontal layout
        main_container = ttk.Frame(self.popup)
        main_container.pack(expand=True, fill='both', pady=10)

        # Create frame for side panel
        side_panel = ttk.Frame(main_container, width=200)
        side_panel.pack(side='left', fill='y', padx=5)

        # Create a frame to hold the Treeview and scrollbars
        frame = ttk.Frame(main_container)
        frame.pack(side='left', expand=True, fill='both')
        frame.pack(pady=10)
        tracer.log(f"Create a frame to hold the Treeview and scrollbars")

        # Create scrollbars
        scrollbar = ttk.Scrollbar(frame, orient="horizontal")
        tracer.log(f"Create scrollbars")
        
        # Create Treeview
        columns = ("File Path",)
        list_of_files = ttk.Treeview(frame, columns=columns, show="headings", height=30,
                        xscrollcommand=scrollbar.set)
        tracer.log(f"Create Treeview with columns: {columns}")


        # Add items to Treeview
        selected_text = FileSelectionPopup.populate_treeview(list_of_files, len_drive_full_path, repetition)

        # Configure scrollbars
        scrollbar.config(command=list_of_files.xview)
        tracer.log(f"Configure scrollbars")

        # Configure Treeview columns
        list_of_files.heading("File Path", text="File Path")
        # Calculate the maximum width based on the content
        max_width = 0
        for item in list_of_files.get_children():
            file_path = list_of_files.item(item)['values'][0]
            text_width = len(file_path) * 7  # Approximate width per character
            max_width = max(max_width, text_width)
        
        list_of_files.column("File Path", width=max_width, anchor="w")
        tracer.log(f"Configure Treeview columns")

        # Configure frame grid
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        list_of_files.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=1, column=0, sticky='ew')
        tracer.log(f"Configure frame grid")

        FileSelectionPopup.populate_side_panel(side_panel, selected_text)


        def keep_this():
            tracer.log("")
            try:
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
            except Exception as e:
                tracer.log(f"Error in keep_this: {e}")

        def keep_all():
            tracer.log("")
            try:
                self.result = tuple(["keep all"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log(f"Error in keep_all: {e}")

        def delete_all():
            tracer.log("")
            try:
                self.result = tuple(["delete all"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log(f"Error in delete_all: {e}")

        def leave_selection_menu():
            tracer.log("")
            try:
                self.result = tuple(["leave"])
                if not on_close == None:
                    on_close()
                self.popup.destroy()
            except Exception as e:
                tracer.log(f"Error in leave_selection_menu: {e}")

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
            tracer.log(f"Treeview width: {list_of_files.winfo_width()} pixels")
            tracer.log(f"Treeview height: {list_of_files.winfo_height()} pixels")

        # Schedule the logging after the popup window is rendered
        self.popup.after(100, log_treeview_dimensions)

        # Log window dimensions and position
        tracer.log(f"Window dimensions: {window_width}x{window_height}")
        tracer.log(f"Window position: x={x_coordinate}, y={y_coordinate}")

        # Log position and dimensions of each widget
        tracer.log(f"Label position: {label.winfo_geometry()}")
        tracer.log(f"Frame position: {frame.winfo_geometry()}")
        tracer.log(f"List position: {list_of_files.winfo_geometry()}")
        tracer.log(f"Scrollbar position: {scrollbar.winfo_geometry()}")
        tracer.log(f"Keep This button position: {button_keep_this.winfo_geometry()}")
        tracer.log(f"Keep All button position: {button_keep_all.winfo_geometry()}")
        tracer.log(f"Delete All button position: {button_delete_all.winfo_geometry()}")
        tracer.log(f"Leave button position: {button_leave.winfo_geometry()}")


    @staticmethod
    def populate_treeview(list_of_files, len_drive_full_path, repetition):
        tracer.log("")
        try:
            file_path = None
            first_item = None
            for index, file in enumerate(repetition):
                tracer.log(f"Insert file into Treeview: {file['file_path']} trimmed by {len_drive_full_path}")
                path_from_drive_to_file = file['file_path'][len_drive_full_path:]
                list_of_files.insert("", "end", values=(path_from_drive_to_file,), iid=index)
                if first_item is None:
                    first_item = index
                    file_path = file['file_path']
            tracer.log(f"Insert files into Treeview - Repetitions: {path_from_drive_to_file}")
            list_of_files.selection_set(first_item)  # Set default selection
            tracer.log(f"Set default selection in Treeview as {repetition[0]['file_path'][len_drive_full_path:]}")
            return file_path
        except Exception as e:
            tracer.log(f"Error 96426: in populate_treeview: {e}")
    

    @staticmethod
    def populate_side_panel(side_panel, file_path):
        tracer.log("")
        try:
            extension = file_path.split(".")[-1]
            tracer.log(f"File extension: {extension}")
            #see if file is an image file
            isImage = extension in ["jpg", "jpeg", "png", "gif"]
            if isImage:
                # Add an image to the side panel (example with a placeholder image)
                image = tk.PhotoImage(file=file_path)  # Replace with actual image path
                # Resize image to fit within max dimensions
                img_width = image.width()
                img_height = image.height()
                scale = min(150/img_width, 600/img_height)
                if scale < 1:
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    image = image.subsample(int(1/scale))
                label = tk.Label(side_panel, image=image)
                label.image = image  # Keep a reference to avoid garbage collection
                label.pack(pady=5) 
            else:
                # Add a label to the side panel (example with text)
                # Read first few characters of the file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        preview = f.read(100)  # Read first 100 characters
                except Exception as e:
                    tracer.log(f"Error 96424: in populate_side_panel: {e}")
                    preview = "Error reading file."
                label = tk.Label(side_panel, text=f"File preview:\n{preview}", wraplength=150, width=20)
                label.pack(pady=5)
        except Exception as e:
            tracer.log(f"Error 96425: in populate_side_panel: {e}")

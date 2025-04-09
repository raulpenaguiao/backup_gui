import tkinter as tk
from tkinter import ttk
from widgets_library.square_small_button import SquareSmallButton  # Assuming this is also converted to tkinter
import tools_library.tracer as tracer
from tools_library.progress_tracker import ProgressTracker


def loading_info_to_title(ProgressTracker):
    """Convert ProgressTracker info to title"""
    if ProgressTracker.loaded:
        return f"{ProgressTracker.name} - {ProgressTracker.current_value} {ProgressTracker.unit} out of {ProgressTracker.total_value} processed"
    return f"{ProgressTracker.name} - Progress not started"

class LoadingPopup(tk.Toplevel):
    def __init__(self, root, progress_tracker):
        #super().__init__(root)
        self.popup = tk.Toplevel(root)
        self.progress_tracker = progress_tracker
        tracer.log("LoadingPopup initializing")
        tracer.log(f"ProgressTracker: {self.progress_tracker}")
        if not isinstance(self.progress_tracker, ProgressTracker):
            raise ValueError("Error 69957: ProgressTracker must be an instance of ProgressTracker")
        
        self.popup.title("Loading...")
        self.popup.geometry("600x400")
        tracer.log("Initializing LoadingPopup")
        self.popup.resizable(False, False)

        # Center the window
        self.popup.update_idletasks()
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 400) // 2
        self.popup.geometry(f"+{x}+{y}")
        tracer.log("Centered window")
        
        # Create main frame
        main_frame = ttk.Frame(self.popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        tracer.log("Main frame created")
        
        # Create label for file count
        self.popup.file_count_label = ttk.Label(main_frame, text=loading_info_to_title(self.progress_tracker))
        self.popup.file_count_label.pack(pady=(10, 20))

        # Create and configure progress bar style
        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar",
                       troughcolor='white',
                       background='#4CAF50',
                       bordercolor='#CCCCCC',
                       lightcolor='#4CAF50',
                       darkcolor='#4CAF50')
        tracer.log("Progress bar style configured")
        
        # Create progress bar
        self.popup.progress_bar = ttk.Progressbar(
            main_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.popup.progress_bar.pack(expand=True)
        tracer.log("Progress bar created")
        
        # Create bottom frame for button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(0, 12))
        tracer.log("Bottom frame created")
        
        # Add button to bottom right
        self.popup.close_button = SquareSmallButton(bottom_frame)
        self.popup.close_button.button.pack(side=tk.RIGHT, padx=12)
        tracer.log("Close button added")

        self.popup.loading_label = ttk.Label(main_frame, text="Loading, please wait...")
        self.popup.loading_label.pack(pady=(10, 0))
        tracer.log("Loading label added")

        progress_tracker.subscribe(self.update_text, "0")
        tracer.log("Subscribed to text update")

        
    
    def update_text(self):
        """Update the label text when progress tracker changes"""

        try:
            if self.progress_tracker.finished:
                tracer.log("Progress finished")
                return
            tracer.log("Update the label text")
            self.popup.file_count_label.config(text=loading_info_to_title(self.progress_tracker))
            self.popup.progress_bar["value"] = self.progress_tracker.current_value / self.progress_tracker.total_value * 100
            self.popup.update()
        except Exception as e:
            tracer.log(f"Error updating label: {e}")
            self.popup.file_count_label.config(text="Error updating progress")
            self.progress_tracker.unsubscribe("0")
            self.popup.update()

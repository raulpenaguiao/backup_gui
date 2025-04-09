import tkinter as tk
import tools_library.tracer as tracer
from tkinter import ttk


class SquareSmallButton:
    def __init__(self, parent=None, text="Button", command=None):
        self.parent = parent
        self.text = text
        self.command = command

        # Create button with custom style
        self.button = ttk.Button(
            self.parent,
            text=self.text,
            command=self.command,
            style="SquareSmallButton.TButton"
        )

        # Configure button style
        style = ttk.Style()
        style.configure("SquareSmallButton.TButton",
                        borderwidth=0,
                        relief="flat",
                        background="#4CAF50",
                        foreground="white",
                        padding=5)
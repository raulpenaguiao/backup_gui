import tkinter as tk
from tkinter import Menu




class BackupGUI:
    def __init__(root):
        
        root.rootTK = tk.Tk()
        root.rootTK.title("Backup GUI")
        root.rootTK.geometry("900x600")
        root.InitializeComponents()
    
    def InitializeComponents(root):
        # Create menu bar
        menu_bar = Menu(root.rootTK)
        root.rootTK.config(menu=menu_bar)

        # Create menus
        file_menu = Menu(menu_bar, tearoff=0)
        edit_menu = Menu(menu_bar, tearoff=0)
        help_menu = Menu(menu_bar, tearoff=0)

        # Add menus to menu bar
        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        # Add menu items
        file_menu.add_command(label="New")
        file_menu.add_command(label="Open")
        file_menu.add_command(label="Save")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.rootTK.quit)

        edit_menu.add_command(label="Undo")
        edit_menu.add_command(label="Redo")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut")
        edit_menu.add_command(label="Copy")
        edit_menu.add_command(label="Paste")

        help_menu.add_command(label="About")

        # Create labels
        label1 = tk.Label(root.rootTK, text="Database")
        label1.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        label2 = tk.Label(root.rootTK, text="Files to backup")
        label2.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Create text fields
        text_field1 = tk.Entry(root.rootTK)
        text_field1.grid(row=0, column=1, padx=5, pady=5)
        text_field1.config(width=100)

        text_field2 = tk.Entry(root.rootTK)
        text_field2.grid(row=1, column=1, padx=5, pady=5)
        text_field2.config(width=100)


        def button1_click():
            print("Button 1 clicked")
        root.button1_click = button1_click
        def button2_click():
            print("Button 2 clicked")
        root.button2_click = button2_click
        def button3_click():
            print("Button 3 clicked")
        root.button3_click = button3_click

        # Create buttons
        button1 = tk.Button(root.rootTK, text="Create database")#Create cold storage database
        button1.grid(row=2, column=0, padx=5, pady=5)
        button1.config(command=root.button1_click)
        
        button2 = tk.Button(root.rootTK, text="Copy to database")#Copy files to cold storage database
        button2.grid(row=2, column=1, padx=5, pady=5)
        button2.config(command=root.button2_click)

        button3 = tk.Button(root.rootTK, text="Statistics from database")#Create statistics from cold storage
        button3.grid(row=2, column=2, padx=5, pady=5)
        button3.config(command=root.button3_click)

    
    def mainloop(root):
        root.rootTK.mainloop()
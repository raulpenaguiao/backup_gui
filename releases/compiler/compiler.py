import os
import sys

import PyInstaller.__main__

#On terminal D:\DEVELOP\projects\backup_gui> python3 .\releases\compiler\compiler.py

def compile_backup():
    try:
        OS = "windows" # Replace with your actual version
        VERSION = "0.0.0" # Replace with your actual version
        # Set the path to your backup_py file
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backup_gui.py')
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), VERSION, OS)
        # PyInstaller options
        options = [
            f'--distpath={output_path}',  # Replace with your desired output folder
            '--onefile',  # Create a single executable file
            '--windowed',  # Hide console window when running
            '--name=BackupPal',  # Name of the output executable
            '--clean',  # Clean PyInstaller cache
            script_path  # Script to compile
        ]

        # Run PyInstaller
        PyInstaller.__main__.run(options)
        print("Compilation successful!")
        
    except Exception as e:
        print(f"Error during compilation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    compile_backup()
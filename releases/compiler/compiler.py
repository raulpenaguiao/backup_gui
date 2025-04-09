import os
import sys

import PyInstaller.__main__

def compile_backup():
    try:
        # Set the path to your backup_py file
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backup_py')
        
        # PyInstaller options
        options = [
            '--onefile',  # Create a single executable file
            '--windowed',  # Hide console window when running
            '--name=Backup helper',  # Name of the output executable
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
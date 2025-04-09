# Backup GUI

This repository implements a Python GUI that helps users create and manage a backup drive, allowing them to sort and organize files without the hassle of combing through repeated files. Safely store important documents in a designated ``cold storage`` drive. The program ensures file integrity through checksum verification and maintains a comprehensive database of all stored files. 

In this backup system, a unique copy of your files is kept in each drive in order to guarantee that the space is efficiently occupied.
This tool provides more security and efficiency in managing your backups by preventing duplicate files and maintaining data integrity, you will have more time to organize the files that are important to you.
Start organizing your backups with unique classification of documents by cloning and using this repository.


---

## Installation Steps


### Download installer and run binary

1. Go to [Releases](https://github.com/raulpenaguiao/backup_gui/tree/main/releases) page and select the version that you want to download
2. Download the latest release for your operating system:
    - `backup_gui_windows.exe` for Windows
    - `backup_gui_linux` for Linux
    - `backup_gui_mac` for macOS
3. Run the downloaded binary:
    - Windows: Double-click the `.exe` file
    - Linux/Mac: Open terminal and run `chmod +x backup_gui_*` then `./backup_gui_*`

### Clone and run the code locally

To get started with the backup GUI, follow these steps:

```bash
# Clone the repository
git clone git@github.com:raulpenaguiao/backup_gui.git
# Navigate to the project directory
cd backup_gui
# Create a virtual environment
python3 -m venv myenv
# Activate the virtual environment
source myenv/bin/activate  # On Windows, use `myenv\Scripts\activate`
# Install dependencies
pip install -r requirements.txt
# Run the application
python3 backup_gui
```

---

## Features

### 1. Create and Update a New Database Backup
Link your backup to the program. By providing the path to this GUI to start backing up your files to your ``cold storage``, all files will be indexed. This automatically creates file statistics and lookup table data in the cold storage, ensuring that your files are well-organized and easy to manage.

### 2. Copy New Files
Select a ``hot storage`` with new files that you want to add to your backup and copy all new files from this location to the ``cold storage``.
This functionality creates a new folder that only contains new files, that the user can manually add to the ``cold storage``.

### 3. Suggest Changes to Your Cold Storage (to be launched)
Analyze file extensions to identify files that may not be worth keeping. This feature can also detect if the file depth (folder hierarchy) is unnecessarily large, helping you optimize your storage structure.

### 4. Recovery (to be launched)
With quick configurations and a single click, recover all the files you need from your backup to your device. This ensures that your important files are always accessible when needed.

### 5. Trash Functionality
When creating the backup drive, a trash folder is automatically generated. This folder contains a copy of all files that go through the database. A copy is retained to provide a record of all files that have been processed.

---

## Good Backup Practices

- **Multiple Locations**: Ensure you have file backups in at least two physical locations and three different copies.
- **Online and Offline Backups**: Maintain at least one backup online and another offline for added security.
- **Regular Backups**: Schedule backups regularly to keep your data up to date.
- **Test Recovery**: Periodically test your recovery process to ensure it works as expected.
- **Trash Management**: Use the trash functionality to keep track of deleted or processed files.

---
## How It Works
The Backup GUI uses a combination of checksum verification and file content analysis to efficiently ensure that only unique files are stored in the cold storage. The application maintains a database of all files, including their paths, sizes, and checksums, to prevent duplication and ensure data integrity.

---

## Use Cases
1. **Personal Backup**: Safeguard your personal documents, photos, and videos by creating a reliable backup system.
2. **Business Backup**: Manage and organize critical business files with ease, ensuring compliance with data retention policies.
3. **File Organization**: Use the extension analysis and file depth analysis features to declutter and optimize your storage.

---

## Troubleshooting
If you encounter issues while using the Backup GUI, consider the following steps:
- **Dependencies**: Ensure all dependencies are installed correctly using `pip install -r requirements.txt`.
- **Permissions**: Verify that you have the necessary permissions to access the source and destination directories.
- **Logs**: Check the application logs for detailed error messages and troubleshooting tips.
- **Reach**: Contact the developer team for personalized troubleshooting.

---

## Issues and Future Features

### Current Issues
- Default behaviour when files are in the "trash" folder
- Comparison of empty files is silly
- Better logging system for errors and warnings
- Loading bar for the indexing process
- File depth analysis not yet implemented.
- Recovery of files according to predefined configurations is not implemented.
- Folder management: the program currently does not compare folders, only files.
- Create an installer for Windows, Linux, and MacOS.
- Save preferences when clicking "Keep all" in the copy analyser
- Ignore .git folders

### Planned Features
- **Unique File Copying**: Ensure that only unique files are copied to the backup.
- **Advanced Extension Analysis**: Provide detailed insights into file types and their relevance.
- **Improved File Depth Analysis**: Suggest optimizations for folder hierarchies.
- **Configurable Recovery**: Allow users to customize recovery settings for better flexibility.

---


## Contributing
We welcome contributions to improve the Backup GUI. To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of your changes.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

## Contact
For questions, suggestions, or support, please contact the project maintainer at [thecode_enthusiast@proton.me].

--

## Aknowledgments
- [Python](https://www.python.org/) - The programming language used for this project.
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - The GUI toolkit used for building the application interface.
- [Pandas](https://pandas.pydata.org/) - The data analysis library used for managing file statistics and database operations.
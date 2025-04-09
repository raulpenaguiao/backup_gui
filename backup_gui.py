from widgets_library.backupGUImain import BackupGUI
from tools_library.dbs import initialize_drives, initialize_drives, get_saved_drives
import tools_library.drive_variables as drive_variables

def create_gui():
    drive_variables.drives = get_saved_drives()
    initialize_drives()
    root = BackupGUI()
    root.mainloop()


if __name__ == "__main__":
    create_gui()

from backupGUImain import BackupGUI
from dbs import initialize_drives, initialize_configurations, get_saved_drives
import drive_variables

def create_gui():
    drive_variables.drives = get_saved_drives()
    print(drive_variables.drives)
    initialize_drives()
    root = BackupGUI()
    root.mainloop()


if __name__ == "__main__":
    create_gui()

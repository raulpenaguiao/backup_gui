import os

# Default targets — used when no overrides are passed to clean()
DEFAULT_DELETE_DIRS = {
    ".cache",
    ".android",
    "miniconda3",
    ".java",
    ".Wolfram"
}

DEFAULT_DELETE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".noname"
}

DEFAULT_DELETE_EXTENSIONS = {
    ".tmp",
    ".temp",
    ".log",
    ".swp",
    ".swo",
    ".bak",
    ".old"
}


def get_size(path):
    total = 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for dirpath, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except Exception:
                pass
    return total


def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


def _delete_path(path, state):
    try:
        size = get_size(path)
        if os.path.isfile(path):
            os.remove(path)
        else:
            for dirpath, dirs, files in os.walk(path, topdown=False):
                for f in files:
                    try:
                        os.remove(os.path.join(dirpath, f))
                    except Exception:
                        pass
                for d in dirs:
                    try:
                        os.rmdir(os.path.join(dirpath, d))
                    except Exception:
                        pass
            os.rmdir(path)
        state['total_freed'] += size
        _log(f"Deleted: {path}")
        _log(f"Total freed: {format_size(state['total_freed'])}\n")
    except Exception as e:
        _log(f"Error deleting {path}: {e}")


def _log(message):
    with open("out.log", "a") as log_file:
        log_file.write(message + "\n")


def clean(root_path, extensions=None, folder_names=None, file_names=None, delete_empty_folders=False):
    """Walk root_path and delete junk files/folders.

    Parameters default to the module-level DEFAULT_* sets when omitted.
    Pass empty sets to skip that category entirely.
    """
    if extensions is None:
        extensions = DEFAULT_DELETE_EXTENSIONS
    if folder_names is None:
        folder_names = DEFAULT_DELETE_DIRS
    if file_names is None:
        file_names = DEFAULT_DELETE_FILES

    # Normalise extensions so callers don't have to remember the dot
    extensions = {e if e.startswith('.') else f'.{e}' for e in extensions}

    state = {'total_freed': 0}

    def should_delete_file(filename):
        if filename in file_names:
            return True
        _, ext = os.path.splitext(filename)
        return ext.lower() in extensions

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        # Delete whole matched directories
        for d in list(dirnames):
            if d in folder_names:
                _delete_path(os.path.join(dirpath, d), state)
                dirnames.remove(d)

        # Delete matched files
        for f in filenames:
            if should_delete_file(f):
                _delete_path(os.path.join(dirpath, f), state)

    # Second pass: remove empty directories bottom-up
    if delete_empty_folders:
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
            if dirpath == root_path:
                continue
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    _log(f"Removed empty folder: {dirpath}")
            except Exception as e:
                _log(f"Error removing empty folder {dirpath}: {e}")

    return state['total_freed']


if __name__ == "__main__":
    target = input("Enter the directory to clean (default is current directory): ").strip()
    freed = clean(target)
    print(f"\nFINAL SPACE FREED: {format_size(freed)}")

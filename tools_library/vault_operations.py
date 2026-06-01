import os
import filecmp
import send2trash
import tools_library.tracer as tracer
from tools_library.pigmy_hash import compute_file_hash


def delete_empty_folders(vault_path):
    """
    Remove all empty directories inside vault_path. Returns list of deleted paths.
    os.listdir includes hidden files (dot-files on Unix, hidden-attribute files on
    Windows), so a folder is only considered empty when it truly has no contents.
    """
    deleted = []
    for dirpath, dirnames, filenames in os.walk(vault_path, topdown=False):
        if dirpath == vault_path:
            continue
        try:
            # os.listdir returns all entries including hidden files and folders
            if not os.listdir(dirpath):
                send2trash.send2trash(os.path.normpath(dirpath))
                deleted.append(dirpath)
                tracer.log(f"Deleted empty folder: {dirpath}")
        except Exception as e:
            tracer.log(f"Error deleting {dirpath}: {e}")
    return deleted


def get_repetitions(pigmyhash):
    """Return groups (list of paths) where more than one file shares the same content."""
    reps = []
    for groups in pigmyhash.values():
        for group in groups:
            files = [p for p in group if os.path.isfile(p)]
            if len(files) > 1:
                reps.append(files)
    return reps


def get_folder_repetitions(pigmyhash):
    """Return groups (list of folder paths) where folders have exactly identical contents."""
    reps = []
    for groups in pigmyhash.values():
        for group in groups:
            dirs = [p for p in group if os.path.isdir(p)]
            if len(dirs) > 1:
                reps.append(dirs)
    return reps


def filter_external_vault(pigmyhash, external_path):
    """
    Delete files in external_path that already exist in the vault described by pigmyhash.
    Returns list of deleted paths.
    """
    # Build hash -> flat list of vault file paths for quick lookup
    vault_files_by_hash = {}
    for h, groups in pigmyhash.items():
        paths = [p for group in groups for p in group if os.path.isfile(p)]
        if paths:
            vault_files_by_hash[h] = paths

    deleted = []
    for dirpath, _, filenames in os.walk(external_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            h = compute_file_hash(file_path)
            if h not in vault_files_by_hash:
                continue
            for vault_file in vault_files_by_hash[h]:
                try:
                    if filecmp.cmp(file_path, vault_file, shallow=False):
                        send2trash.send2trash(os.path.normpath(file_path))
                        deleted.append(file_path)
                        tracer.log(f"Filtered from external: {file_path}")
                        break
                except Exception as e:
                    tracer.log(f"Compare error {file_path} vs {vault_file}: {e}")
    return deleted

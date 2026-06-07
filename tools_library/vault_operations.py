import os
import filecmp
import send2trash
import tools_library.tracer as tracer
from tools_library.pigmy_hash import compute_file_hash


def paths_overlap(vault_path, external_path):
    """Return True if the two paths are the same or one contains the other.

    Uses os.path.normcase so the comparison is case-insensitive on Windows
    and case-sensitive on Unix, matching actual filesystem behaviour.
    """
    norm_vault = os.path.normcase(os.path.normpath(vault_path))
    norm_ext = os.path.normcase(os.path.normpath(external_path))
    return (
        norm_ext == norm_vault
        or norm_ext.startswith(norm_vault + os.sep)
        or norm_vault.startswith(norm_ext + os.sep)
    )


def delete_empty_folders(vault_path, progress_callback=None):
    """
    Two-phase algorithm to remove empty directories inside vault_path.

    Phase 1 (scan): walk bottom-up to find every directory that is empty or
    will become empty once its empty subdirectories are removed.  A directory
    qualifies when it contains no files and all of its subdirectories also
    qualify.

    Phase 2 (delete): send only the topmost qualifying directories to trash —
    their entire subtree goes with them in a single operation, avoiding one
    trash call per nested empty folder.

    Returns the list of all deleted paths (including nested ones).

    progress_callback(phase, deleted_count, current_path):
      phase="scan"   — emitted for every directory examined; deleted_count is 0
      phase="delete" — emitted after each top-level deletion; deleted_count is
                       the running total including all nested dirs
    """
    # ── Phase 1: identify directories that are (or will become) empty ─────────
    will_delete = set()

    for dirpath, dirnames, filenames in os.walk(vault_path, topdown=False):
        if dirpath == vault_path:
            continue
        if progress_callback:
            progress_callback("scan", 0, dirpath)
        if filenames:
            continue
        subdirs = [os.path.join(dirpath, d) for d in dirnames]
        if all(s in will_delete for s in subdirs):
            will_delete.add(dirpath)

    # ── Phase 2: delete only top-level empty dirs ─────────────────────────────
    # Top-level = parent is not itself being deleted.
    top_level = sorted(
        d for d in will_delete
        if os.path.dirname(d) not in will_delete
    )

    deleted = []
    for dirpath in top_level:
        try:
            send2trash.send2trash(os.path.normpath(dirpath))
            gone = [d for d in will_delete
                    if d == dirpath or d.startswith(dirpath + os.sep)]
            deleted.extend(gone)
            tracer.log(f"Deleted empty folder: {dirpath!r}")
        except Exception as e:
            tracer.log(f"Error deleting {dirpath!r}: {e}")
        if progress_callback:
            progress_callback("delete", len(deleted), dirpath)

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


def scan_external_vault(pigmyhash, external_path, stop_event=None,
                        progress_callback=None, match_callback=None):
    """
    Scan external_path for files that already exist in the vault. Does NOT delete anything.
    Returns (all_files, matched_files) — two lists of absolute paths.

    stop_event: threading.Event — scan stops when set.
    progress_callback(current, total): called as each file is evaluated.
    match_callback(file_path): called immediately when a match is confirmed.
    """
    vault_files_by_hash = {}
    for h, groups in pigmyhash.items():
        paths = [p for group in groups for p in group if os.path.isfile(p)]
        if paths:
            vault_files_by_hash[h] = paths

    all_ext_files = []
    for dirpath, _, filenames in os.walk(external_path):
        for filename in filenames:
            all_ext_files.append(os.path.join(dirpath, filename))

    total = len(all_ext_files)
    tracer.log(f"Scan external vault: {total} file(s) in {external_path!r}")
    if progress_callback:
        progress_callback(0, total)

    matched = []
    for i, file_path in enumerate(all_ext_files):
        if stop_event and stop_event.is_set():
            tracer.log(f"Scan cancelled after {i}/{total} files")
            break
        if progress_callback:
            progress_callback(i, total)

        tracer.log(f"Scanning external file {i+1}/{total}: {file_path!r}")
        h = compute_file_hash(file_path)
        if h is None or h not in vault_files_by_hash:
            continue

        for vault_file in vault_files_by_hash[h]:
            try:
                tracer.log(f"Comparing {file_path!r} vs {vault_file!r}")
                if filecmp.cmp(file_path, vault_file, shallow=False):
                    tracer.log(f"Match confirmed: {file_path!r} == {vault_file!r}")
                    matched.append(file_path)
                    if match_callback:
                        match_callback(file_path)
                    break
                else:
                    tracer.log(f"Hash collision (no byte match): {file_path!r} vs {vault_file!r}")
            except Exception as e:
                tracer.log(f"Compare error {file_path!r} vs {vault_file!r}: {e}")

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Scan complete: {len(matched)}/{total} match(es) found")
    return all_ext_files, matched


def filter_external_vault(pigmyhash, external_path, stop_event=None, progress_callback=None):
    """
    Delete files in external_path that already exist in the vault described by pigmyhash.
    Comparison is two-step: hash lookup first, then bit-by-bit via filecmp.
    Returns list of deleted paths.

    stop_event: threading.Event — scan stops cleanly when set.
    progress_callback(current, total): called after each file is evaluated.
    """
    vault_files_by_hash = {}
    for h, groups in pigmyhash.items():
        paths = [p for group in groups for p in group if os.path.isfile(p)]
        if paths:
            vault_files_by_hash[h] = paths

    all_ext_files = []
    for dirpath, _, filenames in os.walk(external_path):
        for filename in filenames:
            all_ext_files.append(os.path.join(dirpath, filename))

    total = len(all_ext_files)
    tracer.log(f"Filter external vault: {total} file(s) to scan in {external_path!r}")
    if progress_callback:
        progress_callback(0, total)

    deleted = []
    for i, file_path in enumerate(all_ext_files):
        if stop_event and stop_event.is_set():
            tracer.log(f"Scan cancelled after {i}/{total} files")
            break
        if progress_callback:
            progress_callback(i, total)

        tracer.log(f"Filtering external file {i+1}/{total}: {file_path!r}")
        h = compute_file_hash(file_path)
        if h is None or h not in vault_files_by_hash:
            continue

        tracer.log(f"Hash match for {file_path!r} — running byte-by-byte comparison")
        matched = False
        for vault_file in vault_files_by_hash[h]:
            try:
                if filecmp.cmp(file_path, vault_file, shallow=False):
                    tracer.log(f"Byte-by-byte match confirmed: {file_path!r} == {vault_file!r}")
                    matched = True
                    break
                else:
                    tracer.log(f"Hash collision (no byte match): {file_path!r} vs {vault_file!r}")
            except Exception as e:
                tracer.log(f"Compare error {file_path!r} vs {vault_file!r}: {e}")

        if matched:
            try:
                send2trash.send2trash(os.path.normpath(file_path))
                deleted.append(file_path)
                tracer.log(f"Filtered from external: {file_path!r}")
            except Exception as e:
                tracer.log(f"Error deleting {file_path!r}: {e}")

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Filter external vault complete: {len(deleted)}/{total} file(s) removed")
    return deleted

import os
import filecmp
import send2trash
import tools_library.tracer as tracer
from tools_library.pigmy_hash import compute_file_hash
from tools_library import deleted_files_db


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


def delete_empty_folders(vault_path, progress_callback=None, stop_event=None):
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
    stop_event: threading.Event — stops cleanly when set (between operations).
    """
    # ── Phase 1: identify directories that are (or will become) empty ─────────
    will_delete = set()

    for dirpath, dirnames, filenames in os.walk(vault_path, topdown=False):
        if stop_event and stop_event.is_set():
            break
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
        if stop_event and stop_event.is_set():
            break
        try:
            send2trash.send2trash(os.path.normpath(dirpath))
            gone = [d for d in will_delete
                    if d == dirpath or d.startswith(dirpath + os.sep)]
            deleted.extend(gone)
            tracer.log(f"Deleted empty folder: {tracer.pid(dirpath)}", trace_level=5)
        except Exception as e:
            tracer.log_error(f"Error deleting {tracer.pid(dirpath)}: {e}")
        if progress_callback:
            progress_callback("delete", len(deleted), dirpath)

    return deleted


def _is_path_stale(path, indexed_at):
    """Return True if path's mtime is newer than indexed_at."""
    try:
        return os.path.getmtime(path) > indexed_at
    except OSError:
        return False


def _folder_is_stale(folder_path, indexed_at):
    """Return True if any file in folder_path's subtree has mtime newer than indexed_at."""
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for fn in filenames:
                if _is_path_stale(os.path.join(dirpath, fn), indexed_at):
                    return True
    except OSError:
        pass
    return False


def get_repetitions(pigmyhash, indexed_at=None):
    """Return (groups, stale_count).

    groups: lists of paths where more than one file shares the same content.
    stale_count: number of paths skipped because their mtime is newer than indexed_at,
                 meaning the index may no longer reflect their content.
    """
    reps = []
    stale_count = 0
    for groups in pigmyhash.values():
        for group in groups:
            files = []
            for p in group:
                if not os.path.isfile(p):
                    continue
                if indexed_at is not None and _is_path_stale(p, indexed_at):
                    stale_count += 1
                    continue
                files.append(p)
            if len(files) > 1:
                reps.append(files)
    return reps, stale_count


def get_folder_repetitions(pigmyhash, indexed_at=None):
    """Return (groups, stale_count).

    groups: lists of folder paths where folders have exactly identical contents.
    stale_count: number of folders skipped because a file inside was modified after indexed_at.
    """
    reps = []
    stale_count = 0
    for groups in pigmyhash.values():
        for group in groups:
            dirs = []
            for p in group:
                if not os.path.isdir(p):
                    continue
                if indexed_at is not None and _folder_is_stale(p, indexed_at):
                    stale_count += 1
                    continue
                dirs.append(p)
            if len(dirs) > 1:
                reps.append(dirs)
    return reps, stale_count


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
    tracer.log(f"Scan external vault: {total} file(s) in {tracer.pid(external_path)}",
               trace_level=3)
    if progress_callback:
        progress_callback(0, total)

    matched = []
    for i, file_path in enumerate(all_ext_files):
        if stop_event and stop_event.is_set():
            tracer.log(f"Scan cancelled after {i}/{total} files", trace_level=4)
            break
        if progress_callback:
            progress_callback(i, total)

        tracer.log(f"Scanning external file {i+1}/{total}: {tracer.pid(file_path)}",
                   trace_level=1)
        h = compute_file_hash(file_path)
        if h is None or h not in vault_files_by_hash:
            continue

        for vault_file in vault_files_by_hash[h]:
            try:
                tracer.log(f"Comparing {tracer.pid(file_path)} vs {tracer.pid(vault_file)}",
                           trace_level=1)
                if filecmp.cmp(file_path, vault_file, shallow=False):
                    tracer.log(f"Match confirmed: {tracer.pid(file_path)} == {tracer.pid(vault_file)}",
                               trace_level=2)
                    matched.append(file_path)
                    if match_callback:
                        match_callback(file_path)
                    break
                else:
                    tracer.log(f"Hash collision (no byte match): "
                               f"{tracer.pid(file_path)} vs {tracer.pid(vault_file)}", trace_level=1)
            except Exception as e:
                tracer.log_error(f"Compare error {file_path!r} vs {vault_file!r}: {e}")

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Scan complete: {len(matched)}/{total} match(es) found", trace_level=3)
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
    tracer.log(f"Filter external vault: {total} file(s) to scan in {tracer.pid(external_path)}",
               trace_level=3)
    if progress_callback:
        progress_callback(0, total)

    deleted = []
    for i, file_path in enumerate(all_ext_files):
        if stop_event and stop_event.is_set():
            tracer.log(f"Scan cancelled after {i}/{total} files", trace_level=4)
            break
        if progress_callback:
            progress_callback(i, total)

        tracer.log(f"Filtering external file {i+1}/{total}: {tracer.pid(file_path)}",
                   trace_level=1)
        h = compute_file_hash(file_path)
        if h is None or h not in vault_files_by_hash:
            continue

        tracer.log(f"Hash match for {tracer.pid(file_path)} — running byte-by-byte comparison",
                   trace_level=1)
        matched_vault_file = None
        for vault_file in vault_files_by_hash[h]:
            try:
                if filecmp.cmp(file_path, vault_file, shallow=False):
                    tracer.log(f"Byte-by-byte match confirmed: "
                               f"{tracer.pid(file_path)} == {tracer.pid(vault_file)}", trace_level=2)
                    matched_vault_file = vault_file
                    break
                else:
                    tracer.log(f"Hash collision (no byte match): "
                               f"{tracer.pid(file_path)} vs {tracer.pid(vault_file)}", trace_level=1)
            except Exception as e:
                tracer.log_error(f"Compare error {file_path!r} vs {vault_file!r}: {e}")

        if matched_vault_file is not None:
            try:
                send2trash.send2trash(os.path.normpath(file_path))
                deleted.append(file_path)
                deleted_files_db.record_deletion(h, file_path, matched_vault_file)
                tracer.log(f"Filtered from external: {tracer.pid(file_path)}", trace_level=5)
            except Exception as e:
                tracer.log_error(f"Error deleting {file_path!r}: {e}")

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Filter external vault complete: {len(deleted)}/{total} file(s) removed",
               trace_level=3)
    return deleted


def find_copies_in_external(main_pigmyhash, ev_pigmyhash, stop_event=None,
                            progress_callback=None, match_callback=None):
    """
    Find EV files that are copies of files already in the main vault, without
    re-walking or re-hashing the EV — both pigmyhash dicts are assumed already
    indexed (one pass per vault). Only the hash-matching groups are verified
    byte-by-byte via filecmp.

    match_callback(ev_path, size, file_hash, copy_path): called for every EV file
    confirmed to be a copy of copy_path (a file still present in the main vault).
    """
    common_hashes = [h for h in ev_pigmyhash if h in main_pigmyhash]
    total = sum(len(ev_pigmyhash[h]) for h in common_hashes)
    tracer.log(f"Copies-in-EV detection: {len(common_hashes)} candidate hash(es), "
               f"{total} EV group(s) to verify", trace_level=3)
    processed = 0
    if progress_callback:
        progress_callback(0, total)

    for h in common_hashes:
        main_files = [p for g in main_pigmyhash[h] for p in g if os.path.isfile(p)]
        if not main_files:
            continue
        main_rep = main_files[0]

        for ev_group in ev_pigmyhash[h]:
            if stop_event and stop_event.is_set():
                return
            ev_files = [p for p in ev_group if os.path.isfile(p)]
            processed += 1
            if progress_callback:
                progress_callback(processed, total)
            if not ev_files:
                continue
            ev_rep = ev_files[0]
            try:
                if filecmp.cmp(ev_rep, main_rep, shallow=False):
                    for ev_path in ev_files:
                        try:
                            size = os.path.getsize(ev_path)
                        except OSError:
                            size = 0
                        tracer.log(f"Copy of vault file found in EV: "
                                   f"{tracer.pid(ev_path)} == {tracer.pid(main_rep)}",
                                   trace_level=3)
                        if match_callback:
                            match_callback(ev_path, size, h, main_rep)
                else:
                    tracer.log(f"Hash collision (no byte match): "
                               f"{tracer.pid(ev_rep)} vs {tracer.pid(main_rep)}", trace_level=1)
            except Exception as e:
                tracer.log_error(f"Compare error {ev_rep!r} vs {main_rep!r}: {e}")

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Copies-in-EV detection complete: {processed}/{total} group(s) verified",
               trace_level=3)


def find_internal_duplicates(ev_pigmyhash, stop_event=None,
                             progress_callback=None, match_callback=None):
    """
    Find duplicate files within the EV itself (purely internal — the main vault
    is not involved). For every hash group with more than one existing file,
    sort lexicographically and keep the first; every other file in the group
    is reported as a deletion candidate.

    match_callback(path, size, file_hash, copy_path): called for every file marked
    for deletion, where copy_path is the kept (lexicographically first) file in
    the same group.
    """
    groups = []
    for h, group_list in ev_pigmyhash.items():
        for g in group_list:
            files = [p for p in g if os.path.isfile(p)]
            if len(files) > 1:
                groups.append((h, files))

    total = len(groups)
    tracer.log(f"Double files in EV: {total} duplicate group(s) found", trace_level=3)
    if progress_callback:
        progress_callback(0, total)

    for i, (h, files) in enumerate(groups):
        if stop_event and stop_event.is_set():
            return
        sorted_files = sorted(files)
        keeper = sorted_files[0]
        for dup in sorted_files[1:]:
            try:
                size = os.path.getsize(dup)
            except OSError:
                size = 0
            tracer.log(f"Duplicate within EV: {tracer.pid(dup)} (keeping {tracer.pid(keeper)})",
                       trace_level=3)
            if match_callback:
                match_callback(dup, size, h, keeper)
        if progress_callback:
            progress_callback(i + 1, total)

    if progress_callback:
        progress_callback(total, total)
    tracer.log(f"Double files in EV complete: {total} group(s) processed", trace_level=3)


def delete_marked_files(suggestions, use_trash=True, progress_callback=None, stop_event=None):
    """
    Delete every suggestion (dict with at least "path", optionally "hash"/"copy_path")
    via the system trash (use_trash=True) or permanently (os.remove).

    Each successful deletion is recorded in the deleted-files DB (hash, path
    reference, copy-path reference, timestamp) instead of being written out as a
    plain-text log line.

    progress_callback(current, total): called after each item is processed.
    Returns (deleted, errors) — lists of paths.
    """
    total = len(suggestions)
    deleted = []
    errors = []
    for i, item in enumerate(suggestions):
        if stop_event and stop_event.is_set():
            break
        path = item["path"]
        try:
            normed = os.path.normpath(path)
            if use_trash:
                send2trash.send2trash(normed)
            else:
                os.remove(normed)
            deleted_files_db.record_deletion(item.get("hash"), path, item.get("copy_path"))
            tracer.log(f"Deleted suggested EV file: {tracer.pid(path)}", trace_level=5)
            deleted.append(path)
        except Exception as e:
            tracer.log_error(f"Error deleting {path!r}: {e}")
            errors.append(path)
        if progress_callback:
            progress_callback(i + 1, total)
    return deleted, errors

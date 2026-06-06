import os
import hashlib
import json
import filecmp
from collections import deque
import tools_library.tracer as tracer
from tools_library.progress_tracker import ProgressTracker
import tools_library.drive_variables as drive_variables

_SKIP_NAMES = {drive_variables.pigmy_hash_file, drive_variables.kept_file,
               drive_variables.rules_file, ".pigmy"}


def compute_file_hash(file_path):
    h, _ = _hash_file(file_path)
    return h


def _hash_file(file_path):
    """Return (hash_str, None) on success or (None, error_str) on failure."""
    try:
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            if size < 1_000:
                return hashlib.md5(f.read()).hexdigest(), None
            elif size < 1_000_000:
                return hashlib.sha1(f.read()).hexdigest(), None
            else:
                start = f.read(1_000_000)
                f.seek(-1_000_000, 2)
                end = f.read(1_000_000)
                return hashlib.sha256(start + end).hexdigest(), None
    except Exception as e:
        err = str(e)
        tracer.log(f"Cannot hash {file_path!r}: {err}")
        return None, err


def _compute_folder_hash(child_hashes):
    combined = "".join(sorted(h for h in child_hashes if h))
    return hashlib.sha256((combined or "empty").encode()).hexdigest()


def index_vault(vault_path, progress_tracker=None, cancel_token=None):
    """
    BFS enumeration (Phase 1) then bottom-up hash computation (Phase 2+3).
    Phase 1 drives progress_tracker.bfs_progress from 0.0 -> 1.0.
    Phase 2+3 use progress_tracker.current_value / total_value.

    Returns (pigmyhash, skipped) on success, or (None, skipped) if cancelled.
      skipped: list of (path, error_str) for every file/dir that could not be read.
    Folders that contain any skipped file are tainted — they are excluded from
    duplicate matching so they can never be falsely suggested for deletion.
    """
    pigmy_hash_path = os.path.join(vault_path, drive_variables.pigmy_hash_file)
    skipped = []   # (path, error_str)

    # ── Phase 1: BFS enumeration with running progress estimate ──────────────
    all_files = []
    all_dirs_bfs = []
    seen = {vault_path}
    queue = deque([vault_path])
    dirs_processed = 0
    dirs_in_queue = 1  # root is already in queue

    if progress_tracker:
        progress_tracker.phase = "bfs"

    while queue:
        if cancel_token and cancel_token.is_set():
            return None, skipped

        current = queue.popleft()
        dirs_processed += 1
        dirs_in_queue -= 1

        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except OSError as e:
            err = str(e)
            tracer.log(f"Cannot scan directory {current!r}: {err}")
            skipped.append((current, err))
            continue

        for entry in entries:
            if entry.name in _SKIP_NAMES or entry.path == pigmy_hash_path:
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.path not in seen:
                    seen.add(entry.path)
                    all_dirs_bfs.append(entry.path)
                    queue.append(entry.path)
                    dirs_in_queue += 1
            else:
                all_files.append(entry.path)

        if progress_tracker:
            bfs_total = dirs_processed + dirs_in_queue
            progress_tracker.bfs_progress = dirs_processed / bfs_total if bfs_total else 1.0
            avg_files = len(all_files) / max(dirs_processed, 1)
            est_total = int((dirs_processed + dirs_in_queue) * (1 + avg_files))
            found_so_far = len(all_files) + dirs_processed
            progress_tracker.current_file = current
            progress_tracker._scan_found = found_so_far
            progress_tracker._scan_estimate = max(est_total, found_so_far + 1)

    # ── Phase 2: Hash every file ──────────────────────────────────────────────
    total = len(all_files) + len(all_dirs_bfs)
    if progress_tracker:
        progress_tracker.phase = "hashing"
        progress_tracker.start_progress_tracker(total)

    path_to_hash = {}
    skipped_paths = set()   # paths that could not be read — used to taint parent dirs
    processed = 0

    for file_path in all_files:
        if cancel_token and cancel_token.is_set():
            return None, skipped
        if progress_tracker:
            progress_tracker.set_current_value(processed, current_file=file_path)
        h, err = _hash_file(file_path)
        if h is not None:
            path_to_hash[file_path] = h
        else:
            skipped.append((file_path, err or "unknown error"))
            skipped_paths.add(file_path)
        processed += 1

    # ── Phase 3: Hash folders bottom-up (reversed BFS = leaves before parents) ──
    # A folder is "tainted" if it contains any skipped file or tainted subfolder.
    # Tainted folders are excluded from path_to_hash so they can never be matched
    # as duplicates — protecting them from accidental deletion.
    tainted_dirs = set()

    for folder_path in reversed(all_dirs_bfs):
        if cancel_token and cancel_token.is_set():
            return None, skipped
        if progress_tracker:
            progress_tracker.set_current_value(processed, current_file=folder_path)
        try:
            child_hashes = []
            is_tainted = False
            for entry in os.scandir(folder_path):
                if entry.name in _SKIP_NAMES:
                    continue
                if entry.path in skipped_paths or entry.path in tainted_dirs:
                    is_tainted = True
                    break
                if entry.path in path_to_hash:
                    child_hashes.append(path_to_hash[entry.path])
            if is_tainted:
                tainted_dirs.add(folder_path)
                tracer.log(f"Folder tainted (contains unreadable content): {folder_path!r}")
            else:
                path_to_hash[folder_path] = _compute_folder_hash(child_hashes)
        except OSError as e:
            err = str(e)
            tracer.log(f"Cannot hash folder {folder_path!r}: {err}")
            skipped.append((folder_path, err))
            tainted_dirs.add(folder_path)
        processed += 1

    # ── Phase 4: Group by hash, then by bit-by-bit identity ──────────────────
    hash_to_paths = {}
    for path, h in path_to_hash.items():
        hash_to_paths.setdefault(h, []).append(path)

    pigmyhash = {}
    for h, paths in hash_to_paths.items():
        groups = []
        for path in paths:
            placed = False
            for group in groups:
                if _same_content(path, group[0]):
                    group.append(path)
                    placed = True
                    break
            if not placed:
                groups.append([path])
        pigmyhash[h] = groups

    if skipped:
        tracer.log(f"Indexing complete: {len(skipped)} file(s)/dir(s) skipped due to access errors.")

    return pigmyhash, skipped


def _same_content(path1, path2):
    try:
        if os.path.isfile(path1) and os.path.isfile(path2):
            return filecmp.cmp(path1, path2, shallow=False)
        if os.path.isdir(path1) and os.path.isdir(path2):
            return True
        return False
    except Exception:
        return False


def save_pigmy_hash(vault_path, pigmyhash):
    path = os.path.join(vault_path, drive_variables.pigmy_hash_file)
    with open(path, "w") as f:
        json.dump(pigmyhash, f)


def load_pigmy_hash(vault_path):
    path = os.path.join(vault_path, drive_variables.pigmy_hash_file)
    with open(path, "r") as f:
        data = json.load(f)
    # Normalize separators — tkinter returns forward-slash paths on Windows,
    # which mix with os.sep when scandir builds child paths, breaking send2trash.
    return {
        h: [[os.path.normpath(p) for p in group] for group in groups]
        for h, groups in data.items()
    }

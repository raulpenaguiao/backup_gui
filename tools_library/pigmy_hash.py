import os
import stat
import hashlib
import time
import filecmp
import threading
from collections import deque
import tools_library.tracer as tracer
from tools_library.progress_tracker import ProgressTracker
import tools_library.drive_variables as drive_variables
import tools_library.pigmy_hash_db as pigmy_hash_db

_IO_TIMEOUT = 60  # seconds before an I/O call is considered hung
_IO_RETRIES = 1   # extra attempts after a timeout, for file hashing


def _run_with_timeout(fn, timeout):
    """Run fn() in a daemon thread; return its result, or raise TimeoutError / the fn's exception."""
    result_box = [None]
    exc_box = [None]

    def _worker():
        try:
            result_box[0] = fn()
        except Exception as e:
            exc_box[0] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"timed out after {timeout}s")
    if exc_box[0] is not None:
        raise exc_box[0]
    return result_box[0]

_SKIP_NAMES = {drive_variables.pigmy_hash_file, drive_variables.kept_file,
               drive_variables.rules_file, ".pigmy",
               ".drive_info", ".filen.trash.local"}  # Filen sync metadata — not user data


def compute_file_hash(file_path):
    h, _ = _hash_file(file_path)
    return h


def _do_hash_file(file_path):
    """Raw I/O — may block on slow storage; always called via _run_with_timeout."""
    st = os.stat(file_path)
    if not stat.S_ISREG(st.st_mode):
        return None, f"not a regular file (mode={oct(st.st_mode)})"
    size = st.st_size
    tracer.log(f"Hashing {tracer.pid(file_path)} ({size:,} bytes)", trace_level=1)
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


def _hash_file(file_path):
    """Return (hash_str, None) on success or (None, error_str) on failure.
    Retries up to _IO_RETRIES times on timeout before giving up."""
    for attempt in range(_IO_RETRIES + 1):
        try:
            h, err = _run_with_timeout(lambda fp=file_path: _do_hash_file(fp), _IO_TIMEOUT)
            if err:
                tracer.log(f"Skipping {tracer.pid(file_path)}: {err}", trace_level=2)
            return h, err
        except TimeoutError:
            msg = f"timed out after {_IO_TIMEOUT}s"
            if attempt < _IO_RETRIES:
                tracer.log(f"Retrying {tracer.pid(file_path)}: {msg}", trace_level=2)
            else:
                tracer.log_error(f"Cannot hash {tracer.pid(file_path)}: {msg}")
                return None, msg
        except Exception as e:
            err = str(e)
            tracer.log_error(f"Cannot hash {tracer.pid(file_path)}: {err}")
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
            entries = _run_with_timeout(
                lambda c=current: sorted(os.scandir(c), key=lambda e: e.name),
                _IO_TIMEOUT,
            )
        except (OSError, TimeoutError) as e:
            err = str(e)
            tracer.log_error(f"Cannot scan directory {tracer.pid(current)}: {err}")
            skipped.append((current, err))
            continue

        for entry in entries:
            if entry.name in _SKIP_NAMES or entry.name.startswith(drive_variables.pigmy_hash_file):
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

    # ── Phase 2: Hash every file, skipping content reads when the cache db's ───
    # ── (folder, name, size, mtime) entry still matches what's on disk ─────────
    total = len(all_files) + len(all_dirs_bfs)
    if progress_tracker:
        progress_tracker.phase = "hashing"
        progress_tracker.start_progress_tracker(total)

    path_to_hash = {}
    skipped_paths = set()   # paths that could not be read — used to taint parent dirs
    processed = 0

    conn = pigmy_hash_db.connect(vault_path)
    seen_file_ids = set()
    try:
        for file_path in all_files:
            if cancel_token and cancel_token.is_set():
                return None, skipped
            if progress_tracker:
                progress_tracker.set_current_value(processed, current_file=file_path)

            rel_dir = os.path.relpath(os.path.dirname(file_path), vault_path)
            rel_parts = [] if rel_dir == "." else rel_dir.split(os.sep)
            folder_id = pigmy_hash_db.get_or_create_folder_id(conn, rel_parts)
            filename = os.path.basename(file_path)

            cached = None
            size = mtime = None
            try:
                st = _run_with_timeout(lambda fp=file_path: os.stat(fp), _IO_TIMEOUT)
                size, mtime = st.st_size, st.st_mtime
                cached = pigmy_hash_db.lookup_file(conn, folder_id, filename)
            except (OSError, TimeoutError):
                pass  # let _hash_file's own error handling take over below

            if cached and cached["size"] == size and cached["mtime"] == mtime:
                h, err = cached["hash"], None
                seen_file_ids.add(cached["id"])
            else:
                h, err = _hash_file(file_path)
                if h is not None and size is not None:
                    file_id = pigmy_hash_db.upsert_file(conn, folder_id, filename, size, mtime, h)
                    seen_file_ids.add(file_id)

            if h is not None:
                path_to_hash[file_path] = h
            else:
                skipped.append((file_path, err or "unknown error"))
                skipped_paths.add(file_path)
            processed += 1

        pigmy_hash_db.prune_files_not_in(conn, seen_file_ids)
        conn.commit()
    finally:
        conn.close()

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
            scan_entries = _run_with_timeout(
                lambda fp=folder_path: list(os.scandir(fp)), _IO_TIMEOUT
            )
            child_hashes = []
            is_tainted = False
            for entry in scan_entries:
                if entry.name in _SKIP_NAMES or entry.name.startswith(drive_variables.pigmy_hash_file):
                    continue
                if entry.path in skipped_paths or entry.path in tainted_dirs:
                    is_tainted = True
                    break
                if entry.path in path_to_hash:
                    child_hashes.append(path_to_hash[entry.path])
            if is_tainted:
                tainted_dirs.add(folder_path)
                tracer.log(f"Folder tainted (contains unreadable content): {tracer.pid(folder_path)}",
                           trace_level=4)
            else:
                path_to_hash[folder_path] = _compute_folder_hash(child_hashes)
        except (OSError, TimeoutError) as e:
            err = str(e)
            tracer.log_error(f"Cannot hash folder {tracer.pid(folder_path)}: {err}")
            skipped.append((folder_path, err))
            tainted_dirs.add(folder_path)
        processed += 1

    # ── Phase 4: Group by hash, then by bit-by-bit identity ──────────────────
    pigmyhash = _group_by_content(path_to_hash)

    if skipped:
        tracer.log(f"Indexing complete: {len(skipped)} file(s)/dir(s) skipped due to access errors.",
                   trace_level=4)

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


def _group_by_content(path_to_hash):
    """Group paths by hash, then split each hash group by bit-by-bit identity
    (guards against hash collisions). Shared by index_vault (Phase 4) and
    load_pigmy_hash, which both end up with a flat {path: hash} mapping —
    one from a live scan, the other rebuilt from the cache db."""
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
    return pigmyhash


_LEGACY_JSON_FILE = ".pigmy-hash"  # old format, pre-dating .pigmy-hash-db


def save_pigmy_hash(vault_path, pigmyhash):
    """Stamp and return the indexed_at timestamp for this vault.

    Per-file hashes are no longer persisted here — index_vault() already wrote
    every (hit-or-freshly-computed) hash into the cache db incrementally as it
    went. `pigmyhash` is accepted but unused, kept only so every existing call
    site (always `save_pigmy_hash(vault_path, pigmyhash)` right after a
    successful index_vault() call) needs no changes.
    """
    conn = pigmy_hash_db.connect(vault_path)
    try:
        indexed_at = time.time()
        pigmy_hash_db.set_meta(conn, "indexed_at", indexed_at)
        conn.commit()
    finally:
        conn.close()

    # One-time tidiness: drop a leftover pre-.pigmy-hash-db JSON cache if present.
    # Its contents are simply discarded — this vault now has a fresh db cache.
    legacy_path = os.path.join(vault_path, _LEGACY_JSON_FILE)
    if os.path.exists(legacy_path):
        try:
            os.remove(legacy_path)
        except OSError:
            pass
    return indexed_at


def load_pigmy_hash(vault_path):
    """Return (pigmyhash, indexed_at) read entirely from the cache db — no
    filesystem access at all, so opening an already-indexed vault stays instant.

    Folder hashes aren't stored in the db (cheap to recompute from already-known
    file hashes); they're rebuilt bottom-up here from the folder tree.
    """
    conn = pigmy_hash_db.connect(vault_path)
    try:
        indexed_at_str = pigmy_hash_db.get_meta(conn, "indexed_at")
        indexed_at = float(indexed_at_str) if indexed_at_str is not None else None

        folders = list(pigmy_hash_db.all_folders(conn))  # (id, parent_id, name)
        info = {fid: (pid, name) for fid, pid, name in folders}
        children_of = {}
        for fid, pid, _ in folders:
            if pid is not None:
                children_of.setdefault(pid, []).append(fid)

        def folder_path(fid):
            parts = []
            current = fid
            while current is not None:
                pid, name = info[current]
                if name:
                    parts.append(name)
                current = pid
            parts.reverse()
            joined = os.path.join(vault_path, *parts) if parts else vault_path
            return os.path.normpath(joined)

        paths = {fid: folder_path(fid) for fid in info}

        path_to_hash = {}
        files_by_folder = {}
        for folder_id, name, file_hash in pigmy_hash_db.all_files(conn):
            full_path = os.path.normpath(os.path.join(paths[folder_id], name))
            path_to_hash[full_path] = file_hash
            files_by_folder.setdefault(folder_id, []).append(file_hash)

        # Bottom-up (leaves before parents) so a folder's hash always combines
        # already-computed subfolder hashes, mirroring index_vault's Phase 3.
        order = []
        visited = set()

        def visit(fid):
            if fid in visited:
                return
            visited.add(fid)
            for child in children_of.get(fid, []):
                visit(child)
            order.append(fid)

        for fid in info:
            visit(fid)

        folder_hash = {}
        for fid in order:
            child_hashes = list(files_by_folder.get(fid, []))
            child_hashes.extend(folder_hash[c] for c in children_of.get(fid, []))
            folder_hash[fid] = _compute_folder_hash(child_hashes)
            path_to_hash[paths[fid]] = folder_hash[fid]

        # index_vault never includes the vault root itself in pigmyhash.
        path_to_hash.pop(os.path.normpath(vault_path), None)

        return _group_by_content(path_to_hash), indexed_at
    finally:
        conn.close()

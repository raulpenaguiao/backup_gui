import os
import sqlite3
import threading
from tools_library.dbs import PROGRAM_DIR
from tools_library.drive_variables import log_folder

PATHS_DB_FILE = os.path.join(PROGRAM_DIR, log_folder, "paths.db")

_lock = threading.Lock()
_cache = {}  # (parent_id, name) -> id


def _connect():
    os.makedirs(os.path.dirname(PATHS_DB_FILE), exist_ok=True)
    conn = sqlite3.connect(PATHS_DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS paths ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "parent_id INTEGER REFERENCES paths(id), "
        "name TEXT NOT NULL, "
        "UNIQUE(parent_id, name)"
        ")"
    )
    return conn


def _split(full_path):
    """Split a path into (drive_or_root, [segment, segment, ...])."""
    norm = os.path.normpath(full_path)
    drive, rest = os.path.splitdrive(norm)
    rest = rest.strip(os.sep)
    root = drive + os.sep if drive else os.sep
    segments = [s for s in rest.split(os.sep) if s]
    return root, segments


def get_path_id(full_path):
    """Return the integer id for full_path, creating any missing nodes in the chain."""
    root, segments = _split(full_path)
    parts = [root] + segments
    with _lock:
        conn = _connect()
        try:
            parent_id = None
            for part in parts:
                key = (parent_id, part)
                if key in _cache:
                    parent_id = _cache[key]
                    continue
                row = conn.execute(
                    "SELECT id FROM paths WHERE parent_id IS ? AND name = ?",
                    (parent_id, part),
                ).fetchone()
                if row is None:
                    cur = conn.execute(
                        "INSERT INTO paths (parent_id, name) VALUES (?, ?)",
                        (parent_id, part),
                    )
                    conn.commit()
                    parent_id = cur.lastrowid
                else:
                    parent_id = row[0]
                _cache[key] = parent_id
            return parent_id
        finally:
            conn.close()


def resolve_path(path_id):
    """Reconstruct the full path for path_id by walking parent_id up to the root."""
    if path_id is None:
        return None
    with _lock:
        conn = _connect()
        try:
            parts = []
            current = path_id
            while current is not None:
                row = conn.execute(
                    "SELECT parent_id, name FROM paths WHERE id = ?", (current,)
                ).fetchone()
                if row is None:
                    return None
                parent_id, name = row
                parts.append(name)
                current = parent_id
            parts.reverse()
            root = parts[0]
            segments = parts[1:]
            return os.path.join(root, *segments) if segments else root
        finally:
            conn.close()


def clear_cache():
    """Drop the in-memory id cache (mainly useful for tests)."""
    with _lock:
        _cache.clear()

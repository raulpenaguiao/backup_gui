import os
import sqlite3
import time
from tools_library.dbs import PROGRAM_DIR
from tools_library.drive_variables import log_folder
from tools_library import path_db

DELETED_FILES_DB_FILE = os.path.join(PROGRAM_DIR, log_folder, "deleted_files.db")


def _connect():
    os.makedirs(os.path.dirname(DELETED_FILES_DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DELETED_FILES_DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS deleted_files ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "file_hash TEXT, "
        "path_id INTEGER NOT NULL, "
        "copy_path_id INTEGER, "
        "timestamp REAL NOT NULL"
        ")"
    )
    return conn


def record_deletion(file_hash, path, copy_path=None, timestamp=None):
    """Record a deleted file. Paths are stored only as references into path_db — never as raw text."""
    path_id = path_db.get_path_id(path)
    copy_path_id = path_db.get_path_id(copy_path) if copy_path else None
    ts = timestamp if timestamp is not None else time.time()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO deleted_files (file_hash, path_id, copy_path_id, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (file_hash, path_id, copy_path_id, ts),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_deletions(limit=10):
    """Return the most recent deletions, newest first, with paths resolved back to strings."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT file_hash, path_id, copy_path_id, timestamp FROM deleted_files "
            "ORDER BY timestamp DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for file_hash, path_id, copy_path_id, timestamp in rows:
        result.append({
            "file_hash": file_hash,
            "path": path_db.resolve_path(path_id),
            "copy_path": path_db.resolve_path(copy_path_id) if copy_path_id else None,
            "timestamp": timestamp,
        })
    return result

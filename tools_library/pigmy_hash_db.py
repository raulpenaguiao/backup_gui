import os
import sqlite3
import tools_library.drive_variables as drive_variables


def db_path(vault_path):
    return os.path.join(vault_path, drive_variables.pigmy_hash_file)


def connect(vault_path):
    conn = sqlite3.connect(db_path(vault_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS folders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "parent_id INTEGER REFERENCES folders(id), "
        "name TEXT NOT NULL, "
        "UNIQUE(parent_id, name)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS files ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "folder_id INTEGER NOT NULL REFERENCES folders(id), "
        "name TEXT NOT NULL, "
        "size INTEGER NOT NULL, "
        "mtime REAL NOT NULL, "
        "hash TEXT NOT NULL, "
        "UNIQUE(folder_id, name)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    return conn


def _root_folder_id(conn):
    row = conn.execute(
        "SELECT id FROM folders WHERE parent_id IS NULL AND name = ''"
    ).fetchone()
    if row is not None:
        return row[0]
    cur = conn.execute("INSERT INTO folders (parent_id, name) VALUES (NULL, '')")
    return cur.lastrowid


def get_or_create_folder_id(conn, rel_parts):
    """rel_parts: list of folder-name segments relative to the vault root
    (empty list = the vault root itself)."""
    folder_id = _root_folder_id(conn)
    for part in rel_parts:
        row = conn.execute(
            "SELECT id FROM folders WHERE parent_id = ? AND name = ?",
            (folder_id, part),
        ).fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO folders (parent_id, name) VALUES (?, ?)",
                (folder_id, part),
            )
            folder_id = cur.lastrowid
        else:
            folder_id = row[0]
    return folder_id


def resolve_folder_parts(conn, folder_id):
    """Return the list of name segments from the vault root down to folder_id
    (empty list for the root itself)."""
    parts = []
    current = folder_id
    while current is not None:
        row = conn.execute(
            "SELECT parent_id, name FROM folders WHERE id = ?", (current,)
        ).fetchone()
        if row is None:
            break
        parent_id, name = row
        if name:
            parts.append(name)
        current = parent_id
    parts.reverse()
    return parts


def lookup_file(conn, folder_id, name):
    row = conn.execute(
        "SELECT id, size, mtime, hash FROM files WHERE folder_id = ? AND name = ?",
        (folder_id, name),
    ).fetchone()
    if row is None:
        return None
    file_id, size, mtime, file_hash = row
    return {"id": file_id, "size": size, "mtime": mtime, "hash": file_hash}


def upsert_file(conn, folder_id, name, size, mtime, file_hash):
    # Don't rely on cursor.lastrowid here: when ON CONFLICT takes the UPDATE
    # branch (no new row inserted), lastrowid is left stale rather than
    # reflecting the existing row, so look the id up explicitly instead.
    conn.execute(
        "INSERT INTO files (folder_id, name, size, mtime, hash) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(folder_id, name) DO UPDATE SET "
        "size = excluded.size, mtime = excluded.mtime, hash = excluded.hash",
        (folder_id, name, size, mtime, file_hash),
    )
    return lookup_file(conn, folder_id, name)["id"]


def prune_files_not_in(conn, seen_ids):
    seen_ids = list(seen_ids)
    if not seen_ids:
        conn.execute("DELETE FROM files")
        return
    placeholders = ",".join("?" * len(seen_ids))
    conn.execute(f"DELETE FROM files WHERE id NOT IN ({placeholders})", seen_ids)


def all_files(conn):
    """Yield (folder_id, name, hash) for every cached file."""
    for row in conn.execute("SELECT folder_id, name, hash FROM files"):
        yield row


def all_folders(conn):
    """Yield (id, parent_id, name) for every folder, including the root (name='')."""
    for row in conn.execute("SELECT id, parent_id, name FROM folders"):
        yield row


def get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )

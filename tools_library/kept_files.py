import os
import json
import tools_library.tracer as tracer
from tools_library.drive_variables import kept_file as _KEPT_FILE


def _path(vault_path):
    return os.path.join(vault_path, _KEPT_FILE)


def load_kept(vault_path):
    """Return set of (hash, relpath) tuples that must never be deleted."""
    p = _path(vault_path)
    if not os.path.exists(p):
        return set()
    try:
        with open(p) as f:
            data = json.load(f)
        return {(entry[0], entry[1]) for entry in data}
    except Exception as e:
        tracer.log_error(f"Error loading kept files from {tracer.pid(p)}: {e}")
        return set()


def save_kept(vault_path, kept):
    """Persist the kept set to disk."""
    p = _path(vault_path)
    try:
        with open(p, "w") as f:
            json.dump([[h, rp] for h, rp in kept], f, indent=1)
    except Exception as e:
        tracer.log_error(f"Error saving kept files to {tracer.pid(p)}: {e}")


def add_kept(vault_path, file_path, file_hash):
    """Mark a file as always-keep. Returns the updated kept set."""
    rel = os.path.relpath(os.path.normpath(file_path), os.path.normpath(vault_path))
    kept = load_kept(vault_path)
    entry = (file_hash, rel)
    if entry not in kept:
        kept.add(entry)
        save_kept(vault_path, kept)
        tracer.log(f"Always-keep added: {rel!r} (hash prefix: {file_hash[:8]})", trace_level=3)
    return kept


def remove_kept(vault_path, file_hash, relpath):
    """Remove a kept entry. Returns the updated kept set."""
    kept = load_kept(vault_path)
    kept.discard((file_hash, relpath))
    save_kept(vault_path, kept)
    return kept


def is_kept(vault_path, file_path, file_hash):
    """Return True if this file+hash combination is in the keep list."""
    rel = os.path.relpath(os.path.normpath(file_path), os.path.normpath(vault_path))
    kept = load_kept(vault_path)
    return (file_hash, rel) in kept

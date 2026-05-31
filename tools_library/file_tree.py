import os

_SKIP = {".pigmy-hash", ".pigmy"}


def human_size(b):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def build_size_index(vault_path, progress_tracker=None, cancel_token=None):
    """
    Single-pass scandir walk computing recursive sizes and file counts.
    Uses DirEntry.stat() so file sizes come from the cached directory entry
    (no extra syscall per file on NTFS/Windows).
    Returns (sizes, file_counts) where both are dicts path -> int.
      sizes[path]       = total bytes (file: actual; folder: recursive sum)
      file_counts[path] = total contained file count (folders only)
    """
    if progress_tracker:
        progress_tracker.phase = "sizing"

    sizes = {}
    dir_children = {}

    # Top-down pass: collect entries and read file sizes from DirEntry
    stack = [vault_path]
    dir_order = []
    while stack:
        if cancel_token and cancel_token.is_set():
            return {}, {}
        dirpath = stack.pop()
        dir_order.append(dirpath)
        children = []
        try:
            for entry in os.scandir(dirpath):
                if entry.name in _SKIP:
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                if is_dir:
                    stack.append(entry.path)
                else:
                    try:
                        sz = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        sz = 0
                    sizes[entry.path] = sz
                children.append((entry.path, is_dir))
        except (PermissionError, OSError):
            pass
        dir_children[dirpath] = children

    # Bottom-up pass: aggregate directory sizes
    file_counts = {}
    for dirpath in reversed(dir_order):
        dir_bytes = 0
        dir_count = 0
        for child_path, is_dir in dir_children.get(dirpath, []):
            if is_dir:
                dir_bytes += sizes.get(child_path, 0)
                dir_count += file_counts.get(child_path, 0)
            else:
                dir_bytes += sizes.get(child_path, 0)
                dir_count += 1
        sizes[dirpath] = dir_bytes
        file_counts[dirpath] = dir_count

    if progress_tracker:
        progress_tracker.finished = True

    return sizes, file_counts


def build_extension_stats(sizes):
    """Returns list of (ext, count, total_bytes) sorted by total_bytes desc."""
    stats = {}
    for path, sz in sizes.items():
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower() or "(none)"
        entry = stats.setdefault(ext, [0, 0])
        entry[0] += 1
        entry[1] += sz
    return sorted(
        [(ext, v[0], v[1]) for ext, v in stats.items()],
        key=lambda x: x[2],
        reverse=True,
    )


def build_insights(vault_path, sizes, file_counts, pigmyhash):
    """Return dict of insight data."""
    files = [(p, s) for p, s in sizes.items() if os.path.isfile(p)]
    total_files = len(files)
    total_dirs = sum(1 for p in sizes if os.path.isdir(p))
    total_size = sizes.get(vault_path, 0)

    largest_files = sorted(files, key=lambda x: x[1], reverse=True)[:10]

    dup_groups = sum(
        1
        for groups in pigmyhash.values()
        for group in groups
        if len([p for p in group if os.path.isfile(p)]) > 1
    )

    depth_base = vault_path.count(os.sep)
    max_depth = max(
        (p.count(os.sep) - depth_base for p in sizes if p != vault_path),
        default=0,
    )

    return {
        "total_files": total_files,
        "total_dirs": total_dirs,
        "total_size": total_size,
        "largest_files": largest_files,
        "dup_groups": dup_groups,
        "max_depth": max_depth,
    }

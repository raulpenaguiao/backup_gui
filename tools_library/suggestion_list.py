class SuggestionList:
    """De-duplicated collection of EV files suggested for deletion, keyed by path.

    The same EV file can legitimately be matched by more than one detection step
    (e.g. it's both a copy of a main-vault file AND the non-kept half of an
    internal EV duplicate pair), or re-matched after a step is retried. Without
    de-duplication it would be suggested — and later deleted — twice, and the
    second deletion attempt fails since the file is already gone.
    """

    def __init__(self):
        self._items = []
        self._paths = set()

    def add(self, path, size, file_hash, copy_path, reason):
        """Add a suggestion. Returns the new item dict, or None if `path` was
        already suggested (the existing entry is left untouched)."""
        if path in self._paths:
            return None
        item = {"path": path, "size": size, "hash": file_hash,
                "copy_path": copy_path, "reason": reason}
        self._paths.add(path)
        self._items.append(item)
        return item

    def remove_paths(self, paths):
        """Drop every item whose path is in `paths` (e.g. after deletion)."""
        removed = set(paths)
        self._items = [i for i in self._items if i["path"] not in removed]
        self._paths -= removed

    def snapshot(self):
        """Return a de-duplicated-by-path copy of the current items — defensive,
        in case duplicates ever slip in some other way before reaching this list."""
        seen = set()
        out = []
        for item in self._items:
            if item["path"] not in seen:
                seen.add(item["path"])
                out.append(item)
        return out

    def total_size(self):
        return sum(item["size"] for item in self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

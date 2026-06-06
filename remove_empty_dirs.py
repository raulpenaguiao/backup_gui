#!/usr/bin/env python3
"""
Remove every empty directory under a given path, recursively.

A directory is considered empty if it contains no files anywhere in its
subtree — so a folder that only holds other empty folders is also removed.

Usage:
    python3 remove_empty_dirs.py <path>
"""

import os
import sys


def remove_empty_dirs(root):
    removed = 0
    # topdown=False means children are visited before their parents, so by
    # the time we check a parent it already reflects any child removals.
    for dirpath, _, _ in os.walk(root, topdown=False):
        if dirpath == root:
            continue
        if not os.listdir(dirpath):
            os.rmdir(dirpath)
            print(f"Removed: {dirpath}")
            removed += 1
    return removed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 remove_empty_dirs.py <path>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.isdir(path):
        print(f"Error: '{path}' is not a valid directory.")
        sys.exit(1)

    count = remove_empty_dirs(path)
    print(f"\nDone. Removed {count} empty folder(s).")

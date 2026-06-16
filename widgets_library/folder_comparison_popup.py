import os
import tkinter as tk
from tkinter import ttk
import send2trash
import tools_library.tracer as tracer
from widgets_library.tooltip import Tooltip


class FolderComparisonPopup:
    """
    Shows pairs of folders that have exactly identical contents side by side,
    allowing the user to delete one of each pair.
    """

    def __init__(self, root, folder_pairs):
        self._pairs = [list(pair) for pair in folder_pairs]
        self._index = 0

        self.popup = tk.Toplevel(root)
        self.popup.title("Pigmy Backup Application")
        self.popup.geometry("1100x660")
        self.popup.minsize(700, 400)
        self.popup.protocol("WM_DELETE_WINDOW", self._leave)

        tk.Label(self.popup, text="Duplicate Folders",
                 font=("Helvetica", 15, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(6, 0))

        # Header row
        hdr = tk.Frame(self.popup, padx=10, pady=6)
        hdr.pack(fill=tk.X)
        self._nav_label = tk.Label(hdr, font=("Helvetica", 10, "bold"))
        self._nav_label.pack(side=tk.LEFT)

        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Content area — rebuilt for each pair
        self._content = tk.Frame(self.popup)
        self._content.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Button row
        btn_row = tk.Frame(self.popup, padx=10, pady=6)
        btn_row.pack(fill=tk.X)

        btn_del_left = tk.Button(btn_row, text="Delete Left Folder", command=self._delete_left)
        btn_del_left.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_del_left, "Send the left folder and all its contents to the recycle bin.")

        btn_del_right = tk.Button(btn_row, text="Delete Right Folder", command=self._delete_right)
        btn_del_right.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_del_right, "Send the right folder and all its contents to the recycle bin.")

        btn_leave = tk.Button(btn_row, text="Leave", command=self._leave)
        btn_leave.pack(side=tk.LEFT, padx=(0, 16))
        Tooltip(btn_leave, "Close this window without deleting anything.")

        btn_next = tk.Button(btn_row, text="Next >", command=self._next)
        btn_next.pack(side=tk.RIGHT)
        btn_prev = tk.Button(btn_row, text="< Prev", command=self._prev)
        btn_prev.pack(side=tk.RIGHT, padx=(0, 6))

        self._show_pair()
        self.popup.lift()
        self.popup.focus_set()

    def _show_pair(self):
        for w in self._content.winfo_children():
            w.destroy()

        pair = self._pairs[self._index]
        self._nav_label.config(text=f"Duplicate folder pair {self._index + 1} of {len(self._pairs)}")

        left_frame = tk.Frame(self._content, relief=tk.GROOVE, bd=1)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        right_frame = tk.Frame(self._content, relief=tk.GROOVE, bd=1)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        self._build_panel(left_frame, pair[0])
        self._build_panel(right_frame, pair[1])

    def _build_panel(self, parent, folder_path):
        tk.Label(parent, text=folder_path, fg="#0055aa", font=("Helvetica", 9),
                 anchor="w", wraplength=520).pack(fill=tk.X, padx=6, pady=(6, 2))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6)

        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(tree_frame, show="tree", selectmode="none")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._fill_tree(tree, "", folder_path)

    def _fill_tree(self, tree, parent_iid, dir_path):
        try:
            entries = sorted(
                os.scandir(dir_path),
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
            )
        except (PermissionError, OSError):
            return
        for entry in entries:
            iid = tree.insert(parent_iid, "end", text=entry.name)
            if entry.is_dir(follow_symlinks=False):
                self._fill_tree(tree, iid, entry.path)

    def _delete_left(self):
        self._delete_folder(self._pairs[self._index][0])

    def _delete_right(self):
        self._delete_folder(self._pairs[self._index][1])

    def _delete_folder(self, path):
        try:
            send2trash.send2trash(path)
            tracer.log(f"Sent to trash: {tracer.pid(path)}", trace_level=5)
        except Exception as e:
            tracer.log_error(f"Error deleting {path!r}: {e}")
        self._pairs.pop(self._index)
        if not self._pairs:
            self.popup.destroy()
            return
        self._index = min(self._index, len(self._pairs) - 1)
        self._show_pair()

    def _leave(self):
        self.popup.destroy()

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_pair()

    def _next(self):
        if self._index < len(self._pairs) - 1:
            self._index += 1
            self._show_pair()

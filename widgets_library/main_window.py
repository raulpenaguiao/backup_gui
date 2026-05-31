import os
import tkinter as tk
from tkinter import ttk, filedialog
import send2trash
import tools_library.tracer as tracer
from tools_library.file_tree import human_size
from tools_library.vault_operations import delete_empty_folders, get_repetitions, filter_external_vault
from widgets_library.file_selection_popup import FileSelectionPopup
from widgets_library.tooltip import Tooltip

_SKIP = {".pigmy-hash", ".pigmy"}


class MainWindow:
    def __init__(self, root, vault_path, pigmyhash, sizes, file_counts, on_back):
        self.root = root
        self.vault_path = vault_path
        self.pigmyhash = pigmyhash
        self.on_back = on_back
        self._sizes = sizes
        self._file_counts = file_counts
        self._path_map = {}
        self._tree_widget = None
        self._build()
        self._show_stats()
        self._populate_tree()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self.root.title("Vault management")
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(5, weight=1)  # paned window row expands

        # Row 0 — header
        hdr = tk.Frame(self.frame, pady=6, padx=10)
        hdr.grid(row=0, column=0, sticky="ew")
        btn_change = tk.Button(hdr, text="< Change", command=self.on_back, relief=tk.FLAT)
        btn_change.pack(side=tk.LEFT)
        Tooltip(btn_change, "Go back to the vault selection screen.")
        tk.Label(hdr, text="Pigmy Backup",
                 font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Label(hdr, text=self.vault_path,
                 fg="#555", font=("Helvetica", 9)).pack(side=tk.LEFT)
        btn_quit = tk.Button(hdr, text="Quit", command=self.root.destroy, relief=tk.FLAT)
        btn_quit.pack(side=tk.RIGHT)
        Tooltip(btn_quit, "Close the application.")

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky="ew")

        # Row 2 — action buttons
        btn_row = tk.Frame(self.frame, padx=10, pady=6)
        btn_row.grid(row=2, column=0, sticky="ew")
        btn_empty = tk.Button(btn_row, text="Delete Empty Folders",
                              command=self._delete_empty_folders)
        btn_empty.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_empty, "Find and send all empty folders inside the vault to the recycle bin.")
        btn_reps = tk.Button(btn_row, text="Delete Repetitions",
                             command=self._delete_repetitions)
        btn_reps.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_reps, "Find files with identical content and review each duplicate group — keep one copy, delete all, or skip.")
        btn_filter = tk.Button(btn_row, text="Filter External Vault",
                               command=self._filter_external)
        btn_filter.pack(side=tk.LEFT)
        Tooltip(btn_filter, "Pick an external folder and remove any files from it that already exist in this vault.")

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, sticky="ew")

        # Row 4 — stats bar (updated when sizes are ready)
        stats_row = tk.Frame(self.frame, padx=10, pady=4)
        stats_row.grid(row=4, column=0, sticky="ew")
        self._stats_label = tk.Label(stats_row,
                                     text="Computing statistics...",
                                     fg="gray", font=("Helvetica", 9))
        self._stats_label.pack(side=tk.LEFT)

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=5, column=0, sticky="ew")

        # Row 6 — PanedWindow: tree (top) + results (bottom)
        paned = tk.PanedWindow(self.frame, orient=tk.VERTICAL,
                               sashrelief=tk.RAISED, sashwidth=4)
        paned.grid(row=6, column=0, sticky="nsew")
        self.frame.rowconfigure(6, weight=1)

        # Tree pane
        tree_frame = tk.Frame(paned)
        paned.add(tree_frame, stretch="always", minsize=120)
        self._build_tree_area(tree_frame)

        # Results pane
        results_frame = tk.Frame(paned)
        paned.add(results_frame, stretch="never", minsize=60)
        self._build_results_area(results_frame)

    # ── File tree area ────────────────────────────────────────────────────────

    def _build_tree_area(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        cols = ("size", "files", "kind")
        tree = ttk.Treeview(parent, columns=cols,
                            show="tree headings", selectmode="browse")
        tree.heading("#0", text="Name", anchor=tk.W)
        tree.heading("size", text="Size", anchor=tk.E)
        tree.heading("files", text="Files", anchor=tk.E)
        tree.heading("kind", text="Type", anchor=tk.CENTER)
        tree.column("#0", width=380, minwidth=160)
        tree.column("size", width=95, anchor=tk.E, stretch=False)
        tree.column("files", width=75, anchor=tk.E, stretch=False)
        tree.column("kind", width=90, anchor=tk.CENTER, stretch=False)

        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self._tree_widget = tree

    def _populate_tree(self):
        if not self._tree_widget:
            return
        self._insert_dir_children("", self.vault_path)

    def _insert_dir_children(self, parent_iid, dir_path):
        try:
            entries = sorted(
                (e for e in os.scandir(dir_path) if e.name not in _SKIP),
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
            )
        except (PermissionError, OSError):
            return
        for entry in entries:
            path = entry.path
            sz = self._sizes.get(path, 0)
            is_dir = entry.is_dir(follow_symlinks=False)
            if is_dir:
                fc = self._file_counts.get(path, 0)
                iid = self._tree_widget.insert(
                    parent_iid, "end",
                    text=entry.name,
                    values=(human_size(sz), f"{fc:,}", "folder"),
                )
                self._path_map[iid] = path
                try:
                    has_children = any(
                        e.name not in _SKIP for e in os.scandir(path)
                    )
                except (PermissionError, OSError):
                    has_children = False
                if has_children:
                    self._tree_widget.insert(
                        iid, "end", text="", iid=f"_d_{iid}")
            else:
                ext = os.path.splitext(entry.name)[1].lower() or "(none)"
                self._tree_widget.insert(
                    parent_iid, "end",
                    text=entry.name,
                    values=(human_size(sz), "", ext),
                )

    def _on_tree_open(self, _event):
        iid = self._tree_widget.focus()
        dummy = f"_d_{iid}"
        if self._tree_widget.exists(dummy):
            self._tree_widget.delete(dummy)
            dir_path = self._path_map.get(iid)
            if dir_path:
                self._insert_dir_children(iid, dir_path)

    # ── Results area ──────────────────────────────────────────────────────────

    def _build_results_area(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        tk.Label(parent, text="Results", font=("Helvetica", 9, "bold"),
                 anchor=tk.W, padx=6).grid(row=0, column=0, sticky="ew")
        self._results = tk.Text(parent, height=6, state=tk.DISABLED,
                                font=("Courier", 9), wrap=tk.WORD,
                                relief=tk.FLAT, bg="#F5F5F5")
        self._results.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL,
                           command=self._results.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self._results.configure(yscrollcommand=sb.set)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _show_stats(self):
        total_size = self._sizes.get(self.vault_path, 0)
        total_files = self._file_counts.get(self.vault_path, 0)
        dup_groups = sum(1 for gs in self.pigmyhash.values() for g in gs if len(g) > 1)
        depth_base = self.vault_path.count(os.sep)
        max_depth = max(
            (p.count(os.sep) - depth_base for p in self._sizes if p != self.vault_path),
            default=0,
        )
        self._stats_label.config(
            text=(f"{total_files:,} files   {human_size(total_size)}"
                  f"   {dup_groups} duplicate group(s)"
                  f"   max depth {max_depth}"),
            fg="#333",
        )

    # ── Results helpers ───────────────────────────────────────────────────────

    def _log(self, text):
        self._results.config(state=tk.NORMAL)
        self._results.insert(tk.END, text + "\n")
        self._results.see(tk.END)
        self._results.config(state=tk.DISABLED)

    def _clear(self):
        self._results.config(state=tk.NORMAL)
        self._results.delete("1.0", tk.END)
        self._results.config(state=tk.DISABLED)

    # ── Action handlers ───────────────────────────────────────────────────────

    def _delete_empty_folders(self):
        self._clear()
        deleted = delete_empty_folders(self.vault_path)
        if deleted:
            self._log(f"Deleted {len(deleted)} empty folder(s):")
            for d in deleted:
                self._log(f"  {d}")
        else:
            self._log("No empty folders found.")

    def _delete_repetitions(self):
        self._clear()
        reps = get_repetitions(self.pigmyhash)
        if not reps:
            self._log("No duplicate files found in this vault.")
            return
        self._log(f"Found {len(reps)} group(s) of duplicate files. Opening review...")
        self._rep_index = 0
        self._reps = [
            [{"file_path": p, "leave_copies": False} for p in group]
            for group in reps
        ]
        self._show_next_rep()

    def _show_next_rep(self):
        if self._rep_index >= len(self._reps):
            self._log("Done reviewing duplicates.")
            return
        rep = self._reps[self._rep_index]

        def on_close():
            try:
                result = self._popup.result
                if result is None:
                    return
                action = result[0]
                if action == "keep this":
                    keep_path = result[1]
                    for f in rep:
                        if f["file_path"] != keep_path and os.path.exists(f["file_path"]):
                            send2trash.send2trash(f["file_path"])
                            self._log(f"  Deleted: {f['file_path']}")
                elif action == "delete all":
                    for f in rep:
                        if os.path.exists(f["file_path"]):
                            send2trash.send2trash(f["file_path"])
                            self._log(f"  Deleted: {f['file_path']}")
                if action != "leave":
                    self._rep_index += 1
                    self._show_next_rep()
            except Exception as e:
                tracer.log(f"Error in _show_next_rep: {e}")

        self._popup = FileSelectionPopup(
            self.root, rep, self._rep_index, len(self._reps),
            on_close=on_close, drive_full_path=self.vault_path,
        )

    def _filter_external(self):
        path = filedialog.askdirectory(title="Select external vault to filter")
        if not path:
            return
        self._clear()
        self._log(f"Scanning external vault: {path}")
        self.root.update()
        deleted = filter_external_vault(self.pigmyhash, path)
        if deleted:
            self._log(f"Removed {len(deleted)} file(s) from external vault:")
            for d in deleted:
                self._log(f"  {d}")
        else:
            self._log("Nothing to remove - no files in the external vault match this vault.")

    def destroy(self):
        self.frame.destroy()

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tools_library.tracer as tracer
from tools_library.file_tree import human_size

def _read_version():
    try:
        # When frozen by PyInstaller --onefile, bundled data lands in sys._MEIPASS
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "VERSION"), encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return "unknown"
from tools_library.vault_operations import (
    delete_empty_folders, get_repetitions, get_folder_repetitions,
    is_external_inside_vault,
)
from tools_library.drive_variables import kept_file as _KEPT_FILE, rules_file as _RULES_FILE
from widgets_library.duplicates_review_popup import DuplicatesReviewPopup
from widgets_library.filter_external_vault_popup import FilterExternalVaultPopup
from widgets_library.log_viewer import LogViewer
from widgets_library.tooltip import Tooltip

_SKIP = {".pigmy-hash", ".pigmy", _KEPT_FILE, _RULES_FILE}


class MainWindow:
    def __init__(self, root, vault_path, pigmyhash, sizes, file_counts, on_back, on_reindex):
        self.root = root
        self.vault_path = vault_path
        self.pigmyhash = pigmyhash
        self.on_back = on_back
        self.on_reindex = on_reindex
        self._sizes = sizes
        self._file_counts = file_counts
        self._path_map = {}
        self._tree_widget = None
        self._build()
        self._show_stats()
        self._populate_tree()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self.root.title("Pigmy Backup Application")
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(6, weight=1)  # content area row expands
        self.frame.rowconfigure(8, weight=0)  # footer

        # Row 0 — header
        hdr = tk.Frame(self.frame, pady=6, padx=10)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Vault management",
                 font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(hdr, text=self.vault_path,
                 fg="#555", font=("Helvetica", 9)).pack(side=tk.LEFT)
        btn_quit = tk.Button(hdr, text="Quit", command=self.root.destroy, relief=tk.FLAT)
        btn_quit.pack(side=tk.RIGHT)
        Tooltip(btn_quit, "Close the application.")
        btn_logs = tk.Button(hdr, text="Open Logs", relief=tk.FLAT,
                             command=lambda: LogViewer(self.root))
        btn_logs.pack(side=tk.RIGHT, padx=(0, 8))
        Tooltip(btn_logs, "Open the live application log (auto-refreshes every 1.5 s).")
        btn_change = tk.Button(hdr, text="< Change", command=self.on_back, relief=tk.FLAT)
        btn_change.pack(side=tk.RIGHT, padx=(0, 8))
        Tooltip(btn_change, "Go back to the vault selection screen.")

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky="ew")

        # Row 2 — navigation / action buttons
        btn_row = tk.Frame(self.frame, padx=10, pady=6)
        btn_row.grid(row=2, column=0, sticky="ew")

        # View navigation buttons (left group)
        self._btn_tree = tk.Button(btn_row, text="Vault Tree",
                                   command=self._show_tree, relief=tk.SUNKEN)
        self._btn_tree.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self._btn_tree, "Show the vault file tree (the default view).")

        self._btn_dups = tk.Button(btn_row, text="Review Duplicates",
                                   command=self._review_duplicates, relief=tk.FLAT)
        self._btn_dups.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self._btn_dups, "Review all duplicates: identical folder pairs first (largest first), then identical file groups (largest first).")

        self._btn_filter = tk.Button(btn_row, text="Filter External Vault",
                                     command=self._filter_external, relief=tk.FLAT)
        self._btn_filter.pack(side=tk.LEFT, padx=(0, 12))
        Tooltip(self._btn_filter, "Pick an external folder and remove any files from it that already exist in this vault.")

        ttk.Separator(btn_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # Action buttons (right of separator)
        btn_empty = tk.Button(btn_row, text="Delete Empty Folders",
                              command=self._delete_empty_folders)
        btn_empty.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_empty, "Find and send all empty folders inside the vault to the recycle bin.")
        btn_reindex = tk.Button(btn_row, text="Reindex", command=self.on_reindex)
        btn_reindex.pack(side=tk.LEFT)
        Tooltip(btn_reindex, "Rebuild the index database for this vault — re-scans all files and recomputes hashes.")

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, sticky="ew")

        # Row 4 — stats bar
        stats_row = tk.Frame(self.frame, padx=10, pady=4)
        stats_row.grid(row=4, column=0, sticky="ew")
        self._stats_label = tk.Label(stats_row,
                                     text="Computing statistics...",
                                     fg="gray", font=("Helvetica", 9))
        self._stats_label.pack(side=tk.LEFT)

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=5, column=0, sticky="ew")

        # Row 6 — switchable content area
        self._content_area = tk.Frame(self.frame)
        self._content_area.grid(row=6, column=0, sticky="nsew")
        self._content_area.columnconfigure(0, weight=1)
        self._content_area.rowconfigure(0, weight=1)

        # Build the tree panel (default view) inside the content area
        self._tree_pane = tk.PanedWindow(self._content_area, orient=tk.VERTICAL,
                                          sashrelief=tk.RAISED, sashwidth=4)
        self._tree_pane.grid(row=0, column=0, sticky="nsew")

        tree_frame = tk.Frame(self._tree_pane)
        self._tree_pane.add(tree_frame, stretch="always", minsize=120)
        self._build_tree_area(tree_frame)

        results_frame = tk.Frame(self._tree_pane)
        self._tree_pane.add(results_frame, stretch="never", minsize=60)
        self._build_results_area(results_frame)

        self._active_panel = None  # currently shown tool panel (or None = tree)

        # Row 7 — footer separator + version/copyright
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(
            row=7, column=0, sticky="ew")
        version = _read_version()
        footer = tk.Frame(self.frame, padx=10, pady=3)
        footer.grid(row=8, column=0, sticky="ew")
        tk.Label(footer,
                 text=f"Pigmy Backup v{version}   © 2024–2026 Raul Penaguiao   Apache 2.0",
                 fg="#888", font=("Helvetica", 8)).pack(side=tk.RIGHT)

    # ── Panel switching ───────────────────────────────────────────────────────

    def _show_tree(self):
        """Restore the default vault-tree view."""
        if self._active_panel is not None:
            self._active_panel.destroy()
            self._active_panel = None
        self._tree_pane.grid(row=0, column=0, sticky="nsew")
        # Update button relief to show which view is active
        self._btn_tree.config(relief=tk.SUNKEN)
        self._btn_dups.config(relief=tk.FLAT)
        self._btn_filter.config(relief=tk.FLAT)

    def _show_panel(self, builder_fn, active_btn):
        """Replace the content area with an embedded tool panel.

        builder_fn(frame): builds the panel content into the given frame.
        active_btn: the navigation button to mark as active (SUNKEN).
        """
        self._tree_pane.grid_forget()
        if self._active_panel is not None:
            self._active_panel.destroy()
        self._active_panel = tk.Frame(self._content_area)
        self._active_panel.grid(row=0, column=0, sticky="nsew")
        self._active_panel.columnconfigure(0, weight=1)
        self._active_panel.rowconfigure(0, weight=1)
        builder_fn(self._active_panel)
        # Update button relief
        self._btn_tree.config(relief=tk.FLAT)
        self._btn_dups.config(relief=tk.FLAT)
        self._btn_filter.config(relief=tk.FLAT)
        active_btn.config(relief=tk.SUNKEN)

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

    def _review_duplicates(self):
        folder_pairs = get_folder_repetitions(self.pigmyhash)
        file_groups = get_repetitions(self.pigmyhash)
        if not folder_pairs and not file_groups:
            self._show_tree()
            self._clear()
            self._log("No duplicates found.")
            return

        def builder(panel_frame):
            panel_frame.rowconfigure(0, weight=1)
            panel_frame.columnconfigure(0, weight=1)
            inner = tk.Frame(panel_frame)
            inner.grid(row=0, column=0, sticky="nsew")
            DuplicatesReviewPopup(
                inner, self.root,
                folder_pairs, file_groups, self._sizes, self.vault_path,
                pigmyhash=self.pigmyhash,
                on_close=self._show_tree,
            )

        self._show_panel(builder, self._btn_dups)

    def _filter_external(self):
        path = filedialog.askdirectory(title="Select external vault to filter")
        if not path:
            return
        if is_external_inside_vault(self.vault_path, path):
            messagebox.showwarning(
                "Invalid Selection",
                "The selected folder is inside (or is) the current vault.\n\n"
                "Please select a folder that is completely outside the vault "
                "to avoid accidental deletions.",
                parent=self.root,
            )
            tracer.log(f"Rejected: external path {path!r} is inside vault {self.vault_path!r}")
            return

        def builder(panel_frame):
            panel_frame.rowconfigure(0, weight=1)
            panel_frame.columnconfigure(0, weight=1)
            inner = tk.Frame(panel_frame)
            inner.grid(row=0, column=0, sticky="nsew")
            FilterExternalVaultPopup(
                inner, self.root,
                self.pigmyhash, path, self.vault_path,
                on_close=self._show_tree,
            )

        self._show_panel(builder, self._btn_filter)

    def destroy(self):
        self.frame.destroy()

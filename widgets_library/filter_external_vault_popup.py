import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import send2trash
import tools_library.tracer as tracer
from tools_library.file_tree import human_size
from tools_library.vault_operations import scan_external_vault
from widgets_library.tooltip import Tooltip


class FilterExternalVaultPopup:
    """
    Embedded panel for the Filter External Vault workflow:
      1. Scans the external vault in a background thread with a progress bar + cancel.
      2. Shows matches in real-time as EV: <trimmed-path> rows.
      3. After scan, offers folder-grouping (collapse dirs where every file matched).
      4. Before deleting, shows a full pre-action detail view.

    parent: tk.Frame to build into (no Toplevel is created).
    root: root window, used for root.after() and child dialog parents.
    on_close: called when the user clicks Close / finishes.
    """

    def __init__(self, parent, root, pigmyhash, external_path, vault_path, on_close=None):
        self._root = root
        self._on_close_cb = on_close
        self._pigmyhash = pigmyhash
        self._external_path = os.path.normpath(external_path)
        self._vault_path = vault_path

        self._matches = []
        self._all_files = []
        self._stop_event = threading.Event()
        self._queue = queue.Queue()
        self._scan_done = False

        self._win = parent  # container frame, not a Toplevel

        self._build()
        self._start_scan()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Header row
        hdr = tk.Frame(self._win, padx=10, pady=6)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="External vault:", fg="#555").pack(side=tk.LEFT)
        tk.Label(hdr, text=self._external_path,
                 font=("Courier", 9), fg="#333").pack(side=tk.LEFT, padx=(4, 0))

        ttk.Separator(self._win, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Progress row
        prog_frame = tk.Frame(self._win, padx=10, pady=6)
        prog_frame.pack(fill=tk.X)

        self._status_label = tk.Label(prog_frame, text="Preparing scan…",
                                       anchor=tk.W, width=55)
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._cancel_btn = tk.Button(prog_frame, text="Cancel Scan",
                                      command=self._cancel)
        self._cancel_btn.pack(side=tk.RIGHT)
        Tooltip(self._cancel_btn,
                "Stop the scan. Files already found can still be confirmed for deletion.")

        self._progress = ttk.Progressbar(self._win, mode="determinate", maximum=100)
        self._progress.pack(fill=tk.X, padx=10, pady=(0, 4))

        ttk.Separator(self._win, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Controls row
        ctrl = tk.Frame(self._win, padx=10, pady=4)
        ctrl.pack(fill=tk.X)

        tk.Button(ctrl, text="Select All",
                  command=self._select_all).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(ctrl, text="Deselect All",
                  command=self._deselect_all).pack(side=tk.LEFT, padx=(0, 4))

        self._group_btn = tk.Button(ctrl, text="Group by Folder",
                                     command=self._rebuild_grouped,
                                     state=tk.DISABLED)
        self._group_btn.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(self._group_btn,
                "After the scan finishes: collapse directories where every file is a duplicate "
                "into a single folder entry so you can delete them in one click.")

        self._match_label = tk.Label(ctrl, text="0 matches", fg="#555")
        self._match_label.pack(side=tk.LEFT)

        self._delete_btn = tk.Button(ctrl, text="Delete Selected",
                                      command=self._confirm_delete,
                                      state=tk.DISABLED)
        self._delete_btn.pack(side=tk.RIGHT)
        Tooltip(self._delete_btn,
                "Review then confirm deletion of the selected items (moved to system trash).")

        # Results treeview
        tv_frame = tk.Frame(self._win, padx=10, pady=2)
        tv_frame.pack(fill=tk.BOTH, expand=True)
        tv_frame.rowconfigure(0, weight=1)
        tv_frame.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(tv_frame, columns=("size",),
                                   show="tree headings",
                                   selectmode="extended")
        self._tree.heading("#0", text="Path  (EV: = external vault root)", anchor=tk.W)
        self._tree.heading("size", text="Size", anchor=tk.E)
        self._tree.column("#0", width=700, minwidth=200)
        self._tree.column("size", width=100, anchor=tk.E, stretch=False)
        self._tree.tag_configure("folder", background="#e8f4fd",
                                  font=("Helvetica", 9, "bold"))
        self._tree.tag_configure("file", font=("Helvetica", 9))

        vsb = ttk.Scrollbar(tv_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Footer
        foot = tk.Frame(self._win, padx=10, pady=6)
        foot.pack(fill=tk.X)
        tk.Button(foot, text="← Back to Vault Tree",
                  command=self._on_close).pack(side=tk.RIGHT)

    # ── Scan ──────────────────────────────────────────────────────────────────

    def _start_scan(self):
        threading.Thread(target=self._scan_worker, daemon=True).start()
        self._root.after(80, self._poll_queue)

    def _scan_worker(self):
        def on_progress(current, total):
            self._queue.put(("progress", current, total))

        def on_match(file_path):
            try:
                size = os.path.getsize(file_path)
            except OSError:
                size = 0
            self._queue.put(("match", file_path, size))

        all_files, matched = scan_external_vault(
            self._pigmyhash,
            self._external_path,
            stop_event=self._stop_event,
            progress_callback=on_progress,
            match_callback=on_match,
        )
        self._queue.put(("done", all_files, matched))

    def _poll_queue(self):
        try:
            while True:
                self._handle_msg(self._queue.get_nowait())
        except queue.Empty:
            pass
        if not self._scan_done:
            self._root.after(80, self._poll_queue)

    def _handle_msg(self, msg):
        kind = msg[0]
        if kind == "progress":
            _, current, total = msg
            if total > 0:
                pct = int(100 * current / total)
                self._progress["value"] = pct
                self._status_label.config(
                    text=f"Scanning: {current:,}/{total:,} files ({pct}%)")
        elif kind == "match":
            _, file_path, size = msg
            self._matches.append(file_path)
            self._add_file_row(file_path, size)
            self._update_match_label()
            self._delete_btn.config(state=tk.NORMAL)
        elif kind == "done":
            _, all_files, matched = msg
            self._all_files = all_files
            self._matches = matched
            self._scan_done = True
            cancelled = self._stop_event.is_set()
            label = "Scan cancelled." if cancelled else "Scan complete."
            self._status_label.config(
                text=f"{label}  {len(matched):,} match(es) in {len(all_files):,} file(s) scanned.")
            self._progress["value"] = 100
            self._cancel_btn.config(state=tk.DISABLED)
            if matched:
                self._group_btn.config(state=tk.NORMAL)
            self._update_match_label()

    def _add_file_row(self, file_path, size):
        rel = os.path.relpath(file_path, self._external_path)
        self._tree.insert("", tk.END, iid=file_path,
                           text=f"EV: {rel}",
                           values=(human_size(size),), tags=("file",))

    def _update_match_label(self):
        n = len(self._matches)
        self._match_label.config(text=f"{n:,} match{'es' if n != 1 else ''}")

    # ── Folder grouping ───────────────────────────────────────────────────────

    def _rebuild_grouped(self):
        """
        Collapse directories where every file (in that immediate dir) matched.
        Individual files in partially-matched dirs stay as separate rows.
        Everything is sorted largest-first.
        """
        dir_total: dict = {}
        for f in self._all_files:
            d = os.path.dirname(f)
            dir_total[d] = dir_total.get(d, 0) + 1

        dir_matched: dict = {}
        for f in self._matches:
            d = os.path.dirname(f)
            dir_matched[d] = dir_matched.get(d, 0) + 1

        full_dirs = {d for d, cnt in dir_matched.items()
                     if dir_total.get(d, 0) == cnt}

        files_in_full_dirs = {f for f in self._matches
                              if os.path.dirname(f) in full_dirs}
        individual = [f for f in self._matches if f not in files_in_full_dirs]

        def safe_size(p):
            try:
                return os.path.getsize(p)
            except OSError:
                return 0

        def dir_total_size(d):
            return sum(safe_size(f) for f in self._matches
                       if os.path.dirname(f) == d)

        sorted_dirs = sorted(full_dirs, key=dir_total_size, reverse=True)
        sorted_files = sorted(individual, key=safe_size, reverse=True)

        self._tree.delete(*self._tree.get_children())

        for d in sorted_dirs:
            dir_files = [f for f in self._matches if os.path.dirname(f) == d]
            total_sz = sum(safe_size(f) for f in dir_files)
            rel_dir = os.path.relpath(d, self._external_path)
            iid = f"__dir__{d}"
            self._tree.insert("", tk.END, iid=iid,
                               text=f"EV: {rel_dir}/  ({len(dir_files)} files)",
                               values=(human_size(total_sz),),
                               tags=("folder",), open=False)
            for f in sorted(dir_files, key=safe_size, reverse=True):
                rel = os.path.relpath(f, self._external_path)
                self._tree.insert(iid, tk.END, iid=f,
                                   text=f"  EV: {rel}",
                                   values=(human_size(safe_size(f)),),
                                   tags=("file",))

        for f in sorted_files:
            rel = os.path.relpath(f, self._external_path)
            self._tree.insert("", tk.END, iid=f,
                               text=f"EV: {rel}",
                               values=(human_size(safe_size(f)),),
                               tags=("file",))

        self._group_btn.config(state=tk.DISABLED, text="Grouped ✓")

    # ── Selection ─────────────────────────────────────────────────────────────

    def _select_all(self):
        def _recurse(parent=""):
            for child in self._tree.get_children(parent):
                self._tree.selection_add(child)
                _recurse(child)
        _recurse()

    def _deselect_all(self):
        self._tree.selection_remove(*self._tree.selection())

    # ── Deletion ──────────────────────────────────────────────────────────────

    def _get_selected_files(self):
        """Expand folder entries to their child file paths; skip already-gone files."""
        seen = set()
        files = []
        for iid in self._tree.selection():
            if iid.startswith("__dir__"):
                for child in self._tree.get_children(iid):
                    if child not in seen:
                        seen.add(child)
                        files.append(child)
            else:
                if iid not in seen:
                    seen.add(iid)
                    files.append(iid)
        return files

    def _confirm_delete(self):
        files = self._get_selected_files()
        if not files:
            messagebox.showinfo("Nothing selected",
                                "Select one or more items to delete.",
                                parent=self._root)
            return

        def safe_size(p):
            try:
                return os.path.getsize(p)
            except OSError:
                return 0

        total_size = sum(safe_size(f) for f in files)

        # Pre-action detail window
        detail = tk.Toplevel(self._root)
        detail.title("Confirm Deletion — Pre-action Detail")
        detail.geometry("720x460")
        detail.transient(self._root)
        detail.grab_set()
        detail.resizable(True, True)

        tk.Label(detail,
                 text=(f"The following {len(files):,} file(s)  "
                       f"({human_size(total_size)})  will be moved to trash:"),
                 padx=10, pady=8, anchor=tk.W,
                 font=("Helvetica", 10)).pack(fill=tk.X)

        txt_frame = tk.Frame(detail, padx=10)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        txt_frame.rowconfigure(0, weight=1)
        txt_frame.columnconfigure(0, weight=1)

        txt = tk.Text(txt_frame, font=("Courier", 8), wrap=tk.NONE,
                      state=tk.NORMAL, relief=tk.FLAT, bg="#f8f8f8")
        vsb2 = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=txt.yview)
        hsb2 = ttk.Scrollbar(txt_frame, orient=tk.HORIZONTAL, command=txt.xview)
        txt.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)
        txt.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        hsb2.grid(row=1, column=0, sticky="ew")

        for f in sorted(files):
            rel = os.path.relpath(f, self._external_path)
            txt.insert(tk.END, f"EV: {rel}  [{human_size(safe_size(f))}]\n")
        txt.config(state=tk.DISABLED)

        btn_row = tk.Frame(detail, padx=10, pady=6)
        btn_row.pack(fill=tk.X)
        tk.Button(btn_row, text="Cancel",
                  command=detail.destroy).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(btn_row, text="Confirm — Move to Trash",
                  bg="#c0392b", fg="white",
                  command=lambda: self._do_delete(files, detail)).pack(side=tk.RIGHT)

    def _do_delete(self, files, detail_win):
        detail_win.destroy()
        deleted = []
        errors = []
        for f in files:
            try:
                send2trash.send2trash(os.path.normpath(f))
                deleted.append(f)
                tracer.log(f"Deleted from external vault: {f!r}")
                if self._tree.exists(f):
                    self._tree.delete(f)
            except Exception as e:
                errors.append(f)
                tracer.log(f"Error deleting {f!r}: {e}")

        # Remove now-empty folder entries
        for iid in list(self._tree.get_children()):
            if iid.startswith("__dir__") and not self._tree.get_children(iid):
                self._tree.delete(iid)

        deleted_set = set(deleted)
        self._matches = [m for m in self._matches if m not in deleted_set]
        self._update_match_label()

        msg = f"Moved {len(deleted):,} file(s) to trash."
        if errors:
            msg += f"\n{len(errors)} error(s) — check log for details."
        tracer.log(f"Filter external vault: {len(deleted)} deleted, {len(errors)} errors.")
        messagebox.showinfo("Done", msg, parent=self._root)

        if not self._matches:
            self._delete_btn.config(state=tk.DISABLED)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _cancel(self):
        self._stop_event.set()
        self._cancel_btn.config(state=tk.DISABLED)
        self._status_label.config(text="Cancelling scan…")

    def _on_close(self):
        self._stop_event.set()
        if self._on_close_cb:
            self._on_close_cb()

import os
import re
import time
import tkinter as tk
from tkinter import ttk
from tools_library.tracer import log_folder_path, current_log_path
from tools_library import path_db
from tools_library import deleted_files_db

_LINE_RE = re.compile(r"^(\d{15})\s+(?:L(\d)\s+)?(.+?)>([^ ]+)\s+(.*?)\s*$")
_PID_RE = re.compile(r"#(\d+)")


def _resolve_pids(text):
    def _sub(m):
        resolved = path_db.resolve_path(int(m.group(1)))
        return resolved if resolved else m.group(0)
    return _PID_RE.sub(_sub, text)


class LogViewer:
    """Log viewer: plain-text tracer/error logs (with min-level filter and path-id
    resolution) plus a Deleted Files tab backed by the deleted-files SQLite DB."""

    def __init__(self, root):
        self._root = root
        self._win = tk.Toplevel(root)
        self._win.title("Application Log")
        self._win.geometry("900x500")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self._win.destroy)
        self._build()
        self._refresh()

    def _logs_by_prefix(self, prefix):
        try:
            return sorted(
                [e.name for e in os.scandir(log_folder_path)
                 if e.is_file() and e.name.startswith(prefix) and e.name.endswith(".log")],
                reverse=True,
            )
        except FileNotFoundError:
            return []

    def _build(self):
        notebook = ttk.Notebook(self._win)
        notebook.pack(fill=tk.BOTH, expand=True)

        text_tab = tk.Frame(notebook)
        deleted_tab = tk.Frame(notebook)
        notebook.add(text_tab, text="Text logs")
        notebook.add(deleted_tab, text="Deleted files")

        self._build_text_tab(text_tab)
        self._build_deleted_tab(deleted_tab)

    # ── Text logs tab ─────────────────────────────────────────────────────────

    def _build_text_tab(self, parent):
        ctrl = tk.Frame(parent, padx=8, pady=6)
        ctrl.pack(fill=tk.X)

        tk.Label(ctrl, text="Info:", fg="#555").pack(side=tk.LEFT)
        self._info_var = tk.StringVar()
        self._info_combo = ttk.Combobox(ctrl, textvariable=self._info_var,
                                         state="readonly", width=22)
        self._info_combo.pack(side=tk.LEFT, padx=(4, 8))
        self._info_combo.bind("<<ComboboxSelected>>",
                               lambda _: self._load_file(self._info_var.get()))

        tk.Label(ctrl, text="Errors:", fg="#555").pack(side=tk.LEFT)
        self._error_var = tk.StringVar()
        self._error_combo = ttk.Combobox(ctrl, textvariable=self._error_var,
                                          state="readonly", width=22)
        self._error_combo.pack(side=tk.LEFT, padx=(4, 8))
        self._error_combo.bind("<<ComboboxSelected>>",
                                lambda _: self._load_file(self._error_var.get()))

        tk.Label(ctrl, text="Min level:", fg="#555").pack(side=tk.LEFT, padx=(8, 0))
        self._level_var = tk.StringVar(value="1")
        level_combo = ttk.Combobox(ctrl, textvariable=self._level_var,
                                    state="readonly", width=3,
                                    values=["1", "2", "3", "4", "5"])
        level_combo.pack(side=tk.LEFT, padx=(4, 8))
        level_combo.bind("<<ComboboxSelected>>", lambda _: self._rerender())

        tk.Button(ctrl, text="Refresh",
                  command=self._refresh).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X)

        txt_frame = tk.Frame(parent)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        txt_frame.rowconfigure(0, weight=1)
        txt_frame.columnconfigure(0, weight=1)

        self._txt = tk.Text(txt_frame, font=("Courier", 8), wrap=tk.NONE,
                             state=tk.DISABLED, relief=tk.FLAT, bg="#1e1e1e",
                             fg="#d4d4d4", insertbackground="white")
        vsb = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self._txt.yview)
        hsb = ttk.Scrollbar(txt_frame, orient=tk.HORIZONTAL, command=self._txt.xview)
        self._txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._raw_lines = []

    def _refresh(self):
        info_files = self._logs_by_prefix("tracer_")
        error_files = self._logs_by_prefix("error_")

        self._info_combo["values"] = info_files
        self._error_combo["values"] = error_files

        # Default selection: keep current if still valid, else newest
        current_info = os.path.basename(current_log_path())
        if self._info_var.get() not in info_files:
            self._info_var.set(current_info if current_info in info_files
                               else (info_files[0] if info_files else ""))
        if self._error_var.get() not in error_files:
            self._error_var.set(error_files[0] if error_files else "")

        # Open the info log by default
        self._load_file(self._info_var.get())
        self._refresh_deleted()

    def _load_file(self, name):
        if not name:
            self._raw_lines = ["(no log files found)"]
        else:
            try:
                with open(os.path.join(log_folder_path, name),
                          encoding='utf-8', errors="replace") as f:
                    self._raw_lines = f.readlines()
            except FileNotFoundError:
                self._raw_lines = ["(log file not found)"]
            except Exception as e:
                self._raw_lines = [f"(error reading log: {e})"]
        self._rerender()

    def _rerender(self):
        try:
            min_level = int(self._level_var.get())
        except ValueError:
            min_level = 1

        rendered = []
        last_second = None
        last_caller = None

        for raw in self._raw_lines:
            line = raw.rstrip("\n").rstrip()
            m = _LINE_RE.match(line)
            if m:
                ts, level, caller_file, caller_name, message = m.groups()
                if level is not None and int(level) < min_level:
                    continue

                second = ts[:12]  # YYMMDDHHMMSS, drop ms
                caller = f"{os.path.basename(caller_file)}>{caller_name}"
                message = _resolve_pids(message)

                new_second = second != last_second
                new_caller = caller != last_caller

                if new_second:
                    if rendered:
                        rendered.append("\n")
                    rendered.append(f"{second}\n")
                    last_second = second

                if new_caller or new_second:
                    if new_caller and not new_second and last_caller is not None:
                        rendered.append("\n")
                    rendered.append(f"  {caller}\n")
                    last_caller = caller

                rendered.append(f"    {message}\n")
            else:
                rendered.append(_resolve_pids(line) + "\n")

        self._txt.config(state=tk.NORMAL)
        self._txt.delete("1.0", tk.END)
        self._txt.insert(tk.END, "".join(rendered))
        self._txt.see(tk.END)
        self._txt.config(state=tk.DISABLED)

    # ── Deleted files tab ────────────────────────────────────────────────────

    def _build_deleted_tab(self, parent):
        ctrl = tk.Frame(parent, padx=8, pady=6)
        ctrl.pack(fill=tk.X)
        tk.Label(ctrl, text="Most recent deletions (last 10):", fg="#555").pack(side=tk.LEFT)
        tk.Button(ctrl, text="Refresh",
                  command=self._refresh_deleted).pack(side=tk.RIGHT)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X)

        cols = ("path", "copy_path", "hash", "timestamp")
        self._deleted_tree = ttk.Treeview(parent, columns=cols, show="headings")
        self._deleted_tree.heading("path", text="Deleted path")
        self._deleted_tree.heading("copy_path", text="Surviving copy")
        self._deleted_tree.heading("hash", text="Hash")
        self._deleted_tree.heading("timestamp", text="When")
        self._deleted_tree.column("path", width=320)
        self._deleted_tree.column("copy_path", width=320)
        self._deleted_tree.column("hash", width=120, anchor=tk.CENTER)
        self._deleted_tree.column("timestamp", width=120, anchor=tk.CENTER)
        self._deleted_tree.pack(fill=tk.BOTH, expand=True)

    def _refresh_deleted(self):
        self._deleted_tree.delete(*self._deleted_tree.get_children())
        for row in deleted_files_db.get_recent_deletions(limit=10):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["timestamp"]))
            self._deleted_tree.insert(
                "", tk.END,
                values=(row["path"] or "?", row["copy_path"] or "",
                        (row["file_hash"] or "")[:12], ts),
            )

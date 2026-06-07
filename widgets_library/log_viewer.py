import os
import tkinter as tk
from tkinter import ttk
from tools_library.tracer import log_folder_path, current_log_path


class LogViewer:
    """Manual-refresh log viewer with per-minute file selector."""

    def __init__(self, root):
        self._root = root
        self._win = tk.Toplevel(root)
        self._win.title("Application Log")
        self._win.geometry("900x500")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self._win.destroy)
        self._build()
        self._refresh()

    def _available_logs(self):
        try:
            names = sorted(
                [e.name for e in os.scandir(log_folder_path)
                 if e.is_file() and e.name.startswith("tracer_") and e.name.endswith(".log")],
                reverse=True,
            )
        except FileNotFoundError:
            names = []
        return names

    def _build(self):
        ctrl = tk.Frame(self._win, padx=8, pady=6)
        ctrl.pack(fill=tk.X)

        tk.Label(ctrl, text="File:", fg="#555").pack(side=tk.LEFT)
        self._file_var = tk.StringVar()
        self._combo = ttk.Combobox(ctrl, textvariable=self._file_var,
                                    state="readonly", width=22)
        self._combo.pack(side=tk.LEFT, padx=(4, 8))
        self._combo.bind("<<ComboboxSelected>>", lambda _: self._load_selected())

        tk.Label(ctrl, text=log_folder_path, fg="#888",
                 font=("Courier", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(ctrl, text="Refresh",
                  command=self._refresh).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Separator(self._win, orient=tk.HORIZONTAL).pack(fill=tk.X)

        txt_frame = tk.Frame(self._win)
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

    def _refresh(self):
        files = self._available_logs()
        self._combo["values"] = files
        current = os.path.basename(current_log_path())
        if self._file_var.get() not in files:
            self._file_var.set(current if current in files else (files[0] if files else ""))
        self._load_selected()

    def _load_selected(self):
        name = self._file_var.get()
        if not name:
            content = "(no log files found)"
        else:
            try:
                with open(os.path.join(log_folder_path, name),
                          encoding='utf-8', errors="replace") as f:
                    content = f.read()
            except FileNotFoundError:
                content = "(log file not found)"
            except Exception as e:
                content = f"(error reading log: {e})"

        self._txt.config(state=tk.NORMAL)
        self._txt.delete("1.0", tk.END)
        self._txt.insert(tk.END, content)
        self._txt.see(tk.END)
        self._txt.config(state=tk.DISABLED)

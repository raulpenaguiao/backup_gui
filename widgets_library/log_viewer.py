import tkinter as tk
from tkinter import ttk
from tools_library.tracer import log_file_path


class LogViewer:
    """Simple auto-refreshing log viewer Toplevel."""

    _REFRESH_MS = 1500

    def __init__(self, root):
        self._root = root
        self._win = tk.Toplevel(root)
        self._win.title("Application Log")
        self._win.geometry("900x500")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self._refresh()

    def _build(self):
        ctrl = tk.Frame(self._win, padx=8, pady=6)
        ctrl.pack(fill=tk.X)
        tk.Label(ctrl, text=log_file_path, fg="#555",
                 font=("Courier", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(ctrl, text="Refresh now",
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
        try:
            with open(log_file_path, "r", errors="replace") as f:
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

        if self._win.winfo_exists():
            self._after_id = self._win.after(self._REFRESH_MS, self._refresh)

    def _on_close(self):
        try:
            self._win.after_cancel(self._after_id)
        except AttributeError:
            pass
        self._win.destroy()

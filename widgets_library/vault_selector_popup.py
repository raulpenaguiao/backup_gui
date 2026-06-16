import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tools_library.drive_variables as drive_variables
import tools_library.dbs as dbs
from widgets_library.tooltip import Tooltip


class VaultSelectorPopup:
    """Blocking vault-selector dialog: a saved-vaults list (browse/remove) plus
    Back/Confirm buttons. Used for both "Select main vault" and "Select external
    vault (EV)" steps of the Prepare External Vault flow.

    on_confirm(path): called after the popup closes with a valid selected path.
    on_back(): called after the popup closes if the user clicked Back instead.
    """

    def __init__(self, root, title, on_confirm, on_back=None, subtitle=None):
        self._root = root
        self._on_confirm = on_confirm
        self._on_back = on_back

        self.win = tk.Toplevel(root)
        self.win.title(title)
        self.win.geometry("520x420")
        self.win.transient(root)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build(title, subtitle)

    def _build(self, title, subtitle):
        frame = ttk.Frame(self.win, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=title, font=("Helvetica", 14, "bold")).pack(pady=(0, 4))
        if subtitle:
            ttk.Label(frame, text=subtitle, font=("Helvetica", 9),
                      foreground="gray").pack(pady=(0, 12))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._listbox = tk.Listbox(
            list_frame, font=("Segoe UI", 10),
            selectmode=tk.SINGLE, yscrollcommand=sb.set,
            activestyle="none", selectbackground="#0078D7", selectforeground="white"
        )
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self._listbox.yview)
        self._listbox.bind("<Double-Button-1>", lambda _: self._confirm())

        self._refresh_list()

        action_row = ttk.Frame(frame)
        action_row.pack(fill=tk.X, pady=(0, 16))
        btn_browse = ttk.Button(action_row, text="+", command=self._browse, width=3)
        btn_browse.pack(side=tk.LEFT, padx=(0, 4))
        Tooltip(btn_browse, "Open a folder picker to add a new vault to the list.")
        btn_remove = ttk.Button(action_row, text="−", command=self._remove, width=3)
        btn_remove.pack(side=tk.LEFT)
        Tooltip(btn_remove, "Remove the selected vault from the list. Does not delete any files on disk.")

        bottom_row = ttk.Frame(frame)
        bottom_row.pack(fill=tk.X)
        ttk.Button(bottom_row, text="< Back", command=self._cancel).pack(side=tk.LEFT)
        btn_confirm = ttk.Button(bottom_row, text="Confirm", command=self._confirm)
        btn_confirm.pack(side=tk.RIGHT, ipadx=18, ipady=6)

    def _refresh_list(self):
        self._listbox.delete(0, tk.END)
        for v in drive_variables.vaults:
            self._listbox.insert(tk.END, v)
        if self._listbox.size() > 0:
            self._listbox.selection_set(0)
            self._listbox.activate(0)

    def _browse(self):
        path = filedialog.askdirectory(title="Select vault folder", parent=self.win)
        if not path:
            return
        path = os.path.normpath(path)
        if path not in drive_variables.vaults:
            drive_variables.vaults.append(path)
            dbs.update_vaults_list(drive_variables.vaults)
        self._refresh_list()
        try:
            idx = drive_variables.vaults.index(path)
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(idx)
            self._listbox.see(idx)
        except ValueError:
            pass

    def _remove(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        path = self._listbox.get(sel[0])
        drive_variables.vaults = [v for v in drive_variables.vaults if v != path]
        dbs.update_vaults_list(drive_variables.vaults)
        self._refresh_list()

    def _confirm(self):
        sel = self._listbox.curselection()
        if not sel:
            messagebox.showinfo("No vault selected", "Please select or browse for a vault first.",
                                parent=self.win)
            return
        path = os.path.normpath(self._listbox.get(sel[0]))
        if not os.path.isdir(path):
            messagebox.showwarning("Vault not found", f"The folder no longer exists:\n{path}",
                                   parent=self.win)
            return
        self.win.destroy()
        self._on_confirm(path)

    def _cancel(self):
        self.win.destroy()
        if self._on_back:
            self._on_back()

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tools_library.drive_variables as drive_variables
import tools_library.dbs as dbs
import tools_library.tracer as tracer
from widgets_library.tooltip import Tooltip


class VaultPicker:
    def __init__(self, root, on_vault_open):
        self.root = root
        self.on_vault_open = on_vault_open
        self._build()

    def _build(self):
        self.root.title("Pigmy Backup Application")
        self.frame = ttk.Frame(self.root, padding=40)
        self.frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            self.frame, text="Pigmy Backup Application", font=("Helvetica", 20, "bold")
        ).pack(pady=(0, 4))
        ttk.Label(
            self.frame, text="Select a vault to open", font=("Helvetica", 10), foreground="gray"
        ).pack(pady=(0, 24))

        # Vault list
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill=tk.X, pady=(0, 8))

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._listbox = tk.Listbox(
            list_frame, height=7, font=("Segoe UI", 10),
            selectmode=tk.SINGLE, yscrollcommand=sb.set,
            activestyle="none", selectbackground="#0078D7", selectforeground="white"
        )
        self._listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sb.config(command=self._listbox.yview)
        self._listbox.bind("<Double-Button-1>", lambda _: self._open())

        self._refresh_list()

        # Action buttons row
        btn_row = ttk.Frame(self.frame)
        btn_row.pack(fill=tk.X, pady=(0, 24))
        btn_browse = ttk.Button(btn_row, text="+", command=self._browse, width=3)
        btn_browse.pack(side=tk.LEFT, padx=(0, 4))
        Tooltip(btn_browse, "Open a folder picker to add a new vault to the list.")
        btn_remove = ttk.Button(btn_row, text="−", command=self._remove, width=3)
        btn_remove.pack(side=tk.LEFT)
        Tooltip(btn_remove, "Remove the selected vault from the list. Does not delete any files on disk.")

        bottom_row = ttk.Frame(self.frame)
        bottom_row.pack(fill=tk.X)
        btn_open = ttk.Button(bottom_row, text="Open Vault", command=self._open)
        btn_open.pack(side=tk.LEFT, ipadx=24, ipady=10)
        Tooltip(btn_open, "Open the selected vault. If no index exists yet, one will be created automatically.")

    def _refresh_list(self):
        self._listbox.delete(0, tk.END)
        for v in drive_variables.vaults:
            self._listbox.insert(tk.END, v)
        if self._listbox.size() > 0:
            self._listbox.selection_set(0)
            self._listbox.activate(0)

    def _browse(self):
        path = filedialog.askdirectory(title="Select vault folder")
        if not path:
            return
        path = os.path.normpath(path)
        if path not in drive_variables.vaults:
            drive_variables.vaults.append(path)
            dbs.update_vaults_list(drive_variables.vaults)
        self._refresh_list()
        # Select the new entry
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

    def _open(self):
        sel = self._listbox.curselection()
        if not sel:
            messagebox.showinfo("No vault selected", "Please select or browse for a vault first.")
            return
        path = os.path.normpath(self._listbox.get(sel[0]))
        if not os.path.isdir(path):
            if messagebox.askyesno(
                "Vault not found",
                f"The folder no longer exists:\n{path}\n\nRemove it from the list?",
            ):
                drive_variables.vaults = [v for v in drive_variables.vaults if v != path]
                dbs.update_vaults_list(drive_variables.vaults)
                self._refresh_list()
            return
        self.on_vault_open(path)

    def destroy(self):
        self.frame.destroy()

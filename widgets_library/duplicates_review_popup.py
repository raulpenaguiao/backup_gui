import os
import tkinter as tk
from tkinter import ttk, messagebox
import send2trash
import tools_library.tracer as tracer
from widgets_library.tooltip import Tooltip
from PIL import Image, ImageTk

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".mp4", ".m4v"}


def _human_size(b):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _open_file(path):
    try:
        os.startfile(path)
    except AttributeError:
        import subprocess
        subprocess.Popen(["xdg-open", path])
    except Exception as e:
        tracer.log(f"Error opening {path}: {e}")


class DuplicatesReviewPopup:
    """
    Unified popup that reviews duplicate folder pairs first (sorted by size desc),
    then duplicate file groups (sorted by size desc).

    Deletions are QUEUED — nothing is sent to the recycle bin until the user
    confirms via the Report window or the Leave confirmation dialog.
    """

    def __init__(self, root, folder_pairs, file_groups, sizes, vault_path=""):
        folder_items = sorted(
            [{"type": "folder", "paths": list(p)} for p in folder_pairs],
            key=lambda x: sizes.get(x["paths"][0], 0),
            reverse=True,
        )
        file_items = sorted(
            [{"type": "file", "paths": list(g)} for g in file_groups],
            key=lambda x: sizes.get(x["paths"][0], 0),
            reverse=True,
        )
        self._items = folder_items + file_items
        self._index = 0
        self._sizes = sizes
        self._vault_path = vault_path.rstrip(os.sep)
        # Each entry: {"label": str, "deleted": [paths], "original_item": dict}
        self._pending = []

        if not self._items:
            return

        self.popup = tk.Toplevel(root)
        self.popup.title("Pigmy Backup Application")
        self.popup.geometry("1200x720")
        self.popup.minsize(800, 520)
        self.popup.protocol("WM_DELETE_WINDOW", self._leave)

        tk.Label(self.popup, text="Review Duplicates",
                 font=("Helvetica", 15, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(6, 0))

        # ── Info banner — dismissible ─────────────────────────────────────────
        self._info_sep = ttk.Separator(self.popup, orient=tk.HORIZONTAL)
        self._info_frame = tk.Frame(self.popup, bg="#fff3cd", pady=5)
        self._info_frame.pack(fill=tk.X)
        tk.Label(self._info_frame,
                 text="ℹ  Clicking Keep or Delete only stages the action — nothing is sent to the"
                      " recycle bin until you click  Execute  in the Report.",
                 bg="#fff3cd", fg="#6b4c00", font=("Helvetica", 9),
                 anchor="w", justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)
        tk.Button(self._info_frame, text="✕", command=self._dismiss_banner,
                  bg="#fff3cd", fg="#6b4c00", relief=tk.FLAT, font=("Helvetica", 9),
                  cursor="hand2", bd=0).pack(side=tk.RIGHT, padx=6)
        self._info_sep.pack(fill=tk.X)

        # ── Navigation bar (persistent) ───────────────────────────────────────
        nav_bar = tk.Frame(self.popup, padx=10, pady=4)
        nav_bar.pack(fill=tk.X)
        self._nav_label = tk.Label(nav_bar, font=("Helvetica", 10, "bold"))
        self._nav_label.pack(side=tk.LEFT)
        btn_next = tk.Button(nav_bar, text="Next >", command=self._next, relief=tk.FLAT)
        btn_next.pack(side=tk.RIGHT)
        btn_prev = tk.Button(nav_bar, text="< Prev", command=self._prev, relief=tk.FLAT)
        btn_prev.pack(side=tk.RIGHT, padx=(0, 4))
        btn_leave = tk.Button(nav_bar, text="Leave", command=self._leave, relief=tk.FLAT)
        btn_leave.pack(side=tk.RIGHT, padx=(0, 12))
        Tooltip(btn_leave, "Stop reviewing. If there are staged deletions you will be asked to confirm before anything is deleted.")

        # ── Staging bar: pending count / undo / report (persistent) ──────────
        self._staging_bar = tk.Frame(self.popup, bg="#f0f0f0", pady=4)
        self._staging_bar.pack(fill=tk.X)
        self._pending_label = tk.Label(self._staging_bar,
                                       text="Staging area — nothing staged yet",
                                       fg="#888", font=("Helvetica", 9),
                                       bg="#f0f0f0", anchor="w")
        self._pending_label.pack(side=tk.LEFT, padx=(10, 12))
        btn_undo = tk.Button(self._staging_bar, text="↩ Undo last",
                             command=self._undo, relief=tk.FLAT, bg="#f0f0f0")
        btn_undo.pack(side=tk.LEFT, padx=(0, 4))
        Tooltip(btn_undo, "Undo the last staged action and put the item back into the review list.")
        btn_report = tk.Button(self._staging_bar, text="Report / Execute",
                               command=lambda: self._show_report(for_execution=True), relief=tk.FLAT, bg="#f0f0f0")
        btn_report.pack(side=tk.LEFT)
        Tooltip(btn_report, "Review the full list of staged deletions and execute them.")

        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── Action button row (rebuilt per item type) ─────────────────────────
        self._btn_row = tk.Frame(self.popup, padx=10, pady=4)
        self._btn_row.pack(fill=tk.X)

        ttk.Separator(self.popup, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── Content area (rebuilt per item) ───────────────────────────────────
        self._content = tk.Frame(self.popup)
        self._content.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self._show_item()
        self.popup.lift()
        self.popup.focus_set()

    def _dismiss_banner(self):
        self._info_frame.pack_forget()
        self._info_sep.pack_forget()

    # ── Item dispatcher ───────────────────────────────────────────────────────

    def _show_item(self):
        for w in self._content.winfo_children():
            w.destroy()
        for w in self._btn_row.winfo_children():
            w.destroy()

        item = self._items[self._index]
        size = self._sizes.get(item["paths"][0], 0)
        kind = "Folder pair" if item["type"] == "folder" else "File group"
        self._nav_label.config(
            text=f"{kind}  {self._index + 1} / {len(self._items)}  —  {_human_size(size)}"
        )

        if item["type"] == "folder":
            self._build_folder_view(item["paths"])
            self._build_folder_buttons()
        else:
            self._build_file_view(item["paths"])
            self._build_file_buttons()

    def _rel(self, path):
        if self._vault_path and path.startswith(self._vault_path):
            rel = path[len(self._vault_path):].lstrip(os.sep)
            return rel or os.path.basename(path)
        return path

    # ── Folder view ───────────────────────────────────────────────────────────

    def _build_folder_view(self, paths):
        self._folder_paths = paths

        # Listbox docked at the top so full paths are immediately visible
        list_frame = tk.Frame(self._content, relief=tk.GROOVE, bd=1)
        list_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        list_frame.columnconfigure(0, weight=1)

        tk.Label(list_frame, text=f"{len(paths)} folders with identical contents:",
                 font=("Helvetica", 9, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

        self._folder_lb = tk.Listbox(list_frame, font=("Segoe UI", 9),
                                     height=min(len(paths), 5),
                                     selectmode=tk.EXTENDED,
                                     selectbackground="#0078D7", selectforeground="white")
        hsb = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self._folder_lb.xview)
        self._folder_lb.configure(xscrollcommand=hsb.set)
        self._folder_lb.grid(row=1, column=0, sticky="ew")
        hsb.grid(row=2, column=0, sticky="ew")

        for path in paths:
            self._folder_lb.insert(tk.END, self._rel(path))
        self._folder_lb.selection_set(0)

        # Tree fills the remaining space below
        self._folder_tree_frame = tk.Frame(self._content, relief=tk.GROOVE, bd=1)
        self._folder_tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._folder_lb.bind("<<ListboxSelect>>", self._on_folder_select)
        self._on_folder_select()

    def _on_folder_select(self, _event=None):
        sel = self._folder_lb.curselection()
        if not sel:
            return
        path = self._folder_paths[sel[-1]]
        for w in self._folder_tree_frame.winfo_children():
            w.destroy()
        tk.Label(self._folder_tree_frame, text=self._rel(path), fg="#0055aa",
                 font=("Helvetica", 9), anchor="w", wraplength=600).pack(
            fill=tk.X, padx=6, pady=(6, 2))
        ttk.Separator(self._folder_tree_frame).pack(fill=tk.X, padx=6)
        tf = tk.Frame(self._folder_tree_frame)
        tf.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        tree = ttk.Treeview(tf, show="tree", selectmode="none")
        vsb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(tf, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self._fill_tree(tree, "", path)

    def _fill_tree(self, tree, parent_iid, dir_path):
        try:
            entries = sorted(os.scandir(dir_path),
                             key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        except (PermissionError, OSError):
            return
        for entry in entries:
            iid = tree.insert(parent_iid, "end", text=entry.name)
            if entry.is_dir(follow_symlinks=False):
                self._fill_tree(tree, iid, entry.path)

    def _build_folder_buttons(self):
        b1 = tk.Button(self._btn_row, text="Stage: Keep Selected (delete others)",
                       command=self._queue_keep_folder)
        b1.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(b1, "Keep the highlighted folder(s) and stage the rest for deletion. Ctrl/Shift-click to select multiple. Nothing deleted yet.")
        b2 = tk.Button(self._btn_row, text="Stage: Delete All",
                       command=self._queue_delete_all_folders)
        b2.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(b2, "Stage every folder in this group for deletion. Nothing deleted yet.")
        b3 = tk.Button(self._btn_row, text="Keep All (skip)",
                       command=self._skip_item)
        b3.pack(side=tk.LEFT)
        Tooltip(b3, "Keep all copies and move on without staging any deletion.")

    def _queue_keep_folder(self):
        sel = self._folder_lb.curselection()
        keep = {self._folder_paths[i] for i in sel}
        item = self._items[self._index]
        deleted = [p for p in item["paths"] if p not in keep]
        if not deleted:
            self._skip_item()
            return
        label = f"FOLDER — keep {len(keep)}, delete {len(deleted)} other(s)"
        self._pending.append({"label": label, "deleted": deleted, "original_item": dict(item)})
        self._update_pending_label()
        self._items.pop(self._index)
        self._purge_subpath_items(deleted)
        if not self._items:
            self._leave()
            return
        self._index = min(self._index, len(self._items) - 1)
        self._show_item()

    def _queue_delete_all_folders(self):
        item = self._items[self._index]
        deleted = list(item["paths"])
        label = f"FOLDER — delete all {len(deleted)} copies"
        self._pending.append({"label": label, "deleted": deleted, "original_item": dict(item)})
        self._update_pending_label()
        self._items.pop(self._index)
        self._purge_subpath_items(deleted)
        if not self._items:
            self._leave()
            return
        self._index = min(self._index, len(self._items) - 1)
        self._show_item()

    # ── File view ─────────────────────────────────────────────────────────────

    def _build_file_view(self, paths):
        list_frame = tk.Frame(self._content, relief=tk.GROOVE, bd=1)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        tk.Label(list_frame, text="Files with identical content:",
                 font=("Helvetica", 9, "bold"), anchor="w").pack(fill=tk.X, padx=6, pady=(6, 2))

        lf = tk.Frame(list_frame)
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        self._file_lb = tk.Listbox(lf, font=("Segoe UI", 9), selectmode=tk.EXTENDED,
                                   selectbackground="#0078D7", selectforeground="white")
        vsb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self._file_lb.yview)
        hsb = ttk.Scrollbar(lf, orient=tk.HORIZONTAL, command=self._file_lb.xview)
        self._file_lb.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._file_lb.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._file_paths = paths
        for path in paths:
            self._file_lb.insert(tk.END, self._rel(path))
        self._file_lb.selection_set(0)

        self._preview_panel = tk.Frame(self._content, width=260, relief=tk.GROOVE, bd=1)
        self._preview_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
        self._preview_panel.pack_propagate(False)

        self._file_lb.bind("<<ListboxSelect>>", self._on_file_select)
        self._on_file_select()

    def _on_file_select(self, _event=None):
        sel = self._file_lb.curselection()
        if sel:
            self._update_preview(self._file_paths[sel[-1]])

    def _update_preview(self, file_path):
        for w in self._preview_panel.winfo_children():
            w.destroy()
        tk.Label(self._preview_panel, text=os.path.basename(file_path),
                 font=("Helvetica", 8, "bold"), anchor="w", wraplength=245).pack(
            fill=tk.X, padx=4, pady=(6, 2))
        ext = os.path.splitext(file_path)[1].lower()
        if ext in _IMAGE_EXTS:
            try:
                img = Image.open(file_path)
                img.thumbnail((245, 260))
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(self._preview_panel, image=photo)
                lbl.image = photo
                lbl.pack(padx=4, pady=4)
            except Exception as e:
                tk.Label(self._preview_panel, text=f"(image error)\n{e}",
                         wraplength=245, anchor="w").pack(padx=4)
        if ext in _AUDIO_EXTS:
            tk.Label(self._preview_panel, text="Audio file", fg="#555",
                     font=("Helvetica", 9)).pack(padx=4, pady=(8, 2))
            tk.Button(self._preview_panel, text="▶  Play",
                      command=lambda: _open_file(file_path)).pack(padx=4, pady=4)
        tk.Label(self._preview_panel, text="First 100 chars:",
                 font=("Helvetica", 8, "bold"), anchor="w").pack(fill=tk.X, padx=4, pady=(8, 0))
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                preview = f.read(100)
        except Exception:
            preview = "(cannot read file)"
        tk.Label(self._preview_panel, text=preview or "(empty file)",
                 wraplength=245, anchor="nw", justify="left",
                 font=("Courier", 8)).pack(fill=tk.X, padx=4)

    def _build_file_buttons(self):
        b1 = tk.Button(self._btn_row, text="Stage: Keep Selected (delete others)",
                       command=self._queue_keep_file)
        b1.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(b1, "Keep the highlighted file(s) and stage the rest for deletion. Ctrl/Shift-click to select multiple. Nothing deleted yet.")
        b2 = tk.Button(self._btn_row, text="Stage: Delete All",
                       command=self._queue_delete_all_files)
        b2.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(b2, "Stage every file in this group for deletion. Nothing deleted yet.")
        b3 = tk.Button(self._btn_row, text="Keep All (skip)",
                       command=self._skip_item)
        b3.pack(side=tk.LEFT)
        Tooltip(b3, "Keep all copies and move on without staging any deletion.")

    def _queue_keep_file(self):
        sel = self._file_lb.curselection()
        keep = {self._file_paths[i] for i in sel}
        item = self._items[self._index]
        deleted = [p for p in item["paths"] if p not in keep and os.path.exists(p)]
        if not deleted:
            self._skip_item()
            return
        label = f"FILE  — keep {len(keep)}, delete {len(deleted)} other(s)"
        self._pending.append({"label": label, "deleted": deleted, "original_item": dict(item)})
        self._update_pending_label()
        self._advance()

    def _queue_delete_all_files(self):
        item = self._items[self._index]
        deleted = [p for p in item["paths"] if os.path.exists(p)]
        label = f"FILE  — delete all {len(deleted)} copies"
        self._pending.append({"label": label, "deleted": deleted, "original_item": dict(item)})
        self._update_pending_label()
        self._advance()

    def _skip_item(self):
        """Advance without staging anything — user chose to keep all copies."""
        self._advance()

    def _purge_subpath_items(self, deleted_paths):
        """Remove items whose every path lives inside a folder staged for deletion.

        Called after self._items.pop(self._index) so self._index already points
        at the next item; we adjust it downward for any items removed before it.
        """
        if not deleted_paths:
            return
        sep = os.sep
        normed = [os.path.normpath(dp) + sep for dp in deleted_paths]

        def all_covered(item):
            return all(
                any(os.path.normpath(p).startswith(nd) for nd in normed)
                for p in item["paths"]
            )

        new_items = []
        removed_before = 0
        for i, item in enumerate(self._items):
            if all_covered(item):
                if i < self._index:
                    removed_before += 1
            else:
                new_items.append(item)
        self._items = new_items
        self._index = max(0, self._index - removed_before)

    # ── Pending queue helpers ─────────────────────────────────────────────────

    def _update_pending_label(self):
        n = sum(len(a["deleted"]) for a in self._pending)
        groups = len(self._pending)
        if n == 0:
            bg = "#f0f0f0"
            self._pending_label.config(
                text="Staging area — nothing staged yet",
                fg="#888", bg=bg, font=("Helvetica", 9))
        else:
            bg = "#ffe8d6"
            self._pending_label.config(
                text=f"⏳  {groups} action{'s' if groups != 1 else ''} staged"
                     f" ({n} item{'s' if n != 1 else ''} to delete) — click  Report / Execute  to proceed",
                fg="#7a2e00", bg=bg, font=("Helvetica", 9, "bold"))
        self._staging_bar.config(bg=bg)
        for child in self._staging_bar.winfo_children():
            try:
                child.config(bg=bg)
            except tk.TclError:
                pass

    def _undo(self):
        if not self._pending:
            return
        last = self._pending.pop()
        self._items.insert(self._index, last["original_item"])
        self._update_pending_label()
        self._show_item()

    def _show_report(self, for_execution=False):
        win = tk.Toplevel(self.popup)
        win.title("Pigmy Backup Application")
        win.geometry("700x500")
        win.grab_set()

        tk.Label(win, text="Deletion Report",
                 font=("Helvetica", 15, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Separator(win, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(6, 4))

        if not self._pending:
            tk.Label(win, text="Nothing queued — no deletions to execute.",
                     fg="#555", font=("Helvetica", 10)).pack(padx=10, pady=20)
        else:
            txt_frame = tk.Frame(win)
            txt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
            txt_frame.rowconfigure(0, weight=1)
            txt_frame.columnconfigure(0, weight=1)
            txt = tk.Text(txt_frame, wrap=tk.NONE, font=("Courier", 9),
                          state=tk.NORMAL, relief=tk.FLAT, bg="#f8f8f8")
            vsb = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=txt.yview)
            hsb = ttk.Scrollbar(txt_frame, orient=tk.HORIZONTAL, command=txt.xview)
            txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            txt.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")

            for i, action in enumerate(self._pending, 1):
                txt.insert(tk.END, f"[{i}] {action['label']}\n")
                for path in action["deleted"]:
                    txt.insert(tk.END, f"     ✗  {path}\n")
                txt.insert(tk.END, "\n")
            txt.config(state=tk.DISABLED)

        btn_row = tk.Frame(win, padx=10, pady=8)
        btn_row.pack(fill=tk.X)

        if for_execution and self._pending:
            n = sum(len(a["deleted"]) for a in self._pending)

            def execute():
                self._execute_pending()
                win.destroy()
                self.popup.destroy()

            tk.Button(btn_row, text=f"Execute — send {n} item(s) to recycle bin",
                      command=execute, fg="white", bg="#cc4400",
                      activebackground="#aa3300").pack(side=tk.LEFT, padx=(0, 8))
            tk.Button(btn_row, text="Cancel — keep reviewing",
                      command=win.destroy).pack(side=tk.LEFT)
        else:
            tk.Button(btn_row, text="Close", command=win.destroy).pack(side=tk.LEFT)

    def _execute_pending(self):
        errors = []
        for action in self._pending:
            for path in action["deleted"]:
                normed = os.path.normpath(path)
                if not os.path.exists(normed):
                    tracer.log(f"Already gone, skipping: {path}")
                    continue
                try:
                    send2trash.send2trash(normed)
                    tracer.log(f"Sent to trash: {path}")
                except Exception as e:
                    tracer.log(f"Error deleting {path}: {e}")
                    errors.append(f"{os.path.basename(path)}: {e}")
        self._pending.clear()
        self._update_pending_label()
        if errors:
            messagebox.showwarning(
                "Some deletions failed",
                "The following items could not be moved to the recycle bin:\n\n"
                + "\n".join(errors),
                parent=self.popup,
            )

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_item()

    def _next(self):
        if self._index < len(self._items) - 1:
            self._index += 1
            self._show_item()

    def _advance(self):
        self._items.pop(self._index)
        if not self._items:
            self._leave()
            return
        self._index = min(self._index, len(self._items) - 1)
        self._show_item()

    def _leave(self):
        if self._pending:
            n = sum(len(a["deleted"]) for a in self._pending)
            confirmed = messagebox.askyesno(
                "Leave without executing?",
                f"You have {len(self._pending)} staged action(s) ({n} item(s) to delete) "
                f"that have not been executed.\n\nLeave without sending anything to the recycle bin?",
                icon="warning",
                parent=self.popup,
            )
            if confirmed:
                self.popup.destroy()
        else:
            self.popup.destroy()

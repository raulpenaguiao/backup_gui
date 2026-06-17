import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import send2trash
import tools_library.tracer as tracer
from tools_library import kept_files
from tools_library import deleted_files_db
from tools_library.duplicate_rules import load_rules, apply_rules, net_action
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
        subprocess.Popen(["xdg-open", path])
    except Exception as e:
        tracer.log_error(f"Error opening {tracer.pid(path)}: {e}")


def _open_in_explorer(path, is_dir=False):
    """Open the system file explorer at the given path.
    For files, selects the file in its parent folder.
    For directories, opens the directory itself.
    """
    try:
        sys_platform = platform.system()
        norm = os.path.normpath(path)
        if sys_platform == "Windows":
            if is_dir:
                subprocess.Popen(["explorer", norm])
            else:
                subprocess.Popen(["explorer", "/select,", norm])
        elif sys_platform == "Darwin":
            subprocess.Popen(["open", "-R", norm])
        else:
            target = norm if is_dir else os.path.dirname(norm)
            subprocess.Popen(["xdg-open", target])
    except Exception as e:
        tracer.log_error(f"Error opening explorer for {tracer.pid(path)}: {e}")


class DuplicatesReviewPopup:
    """
    Embedded panel that reviews duplicate folder pairs first (sorted by size desc),
    then duplicate file groups (sorted by size desc).

    Deletions are QUEUED — nothing is sent to the recycle bin until the user
    confirms via the Report window or the Leave confirmation dialog.

    parent: tk.Frame to build into (no Toplevel is created).
    root: root window, used for child dialogs and messagebox parents.
    on_close: called when the user clicks Leave / finishes reviewing.
    """

    def __init__(self, parent, root, folder_pairs, file_groups, sizes,
                 vault_path="", pigmyhash=None, on_close=None):
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
        self._root = root
        self._on_close_cb = on_close
        # Each entry: {"label": str, "deleted": [paths], "original_item": dict}
        self._pending = []
        # Build reverse map path -> hash from pigmyhash for "always keep" lookups
        self._path_to_hash = {}
        if pigmyhash:
            for h, groups in pigmyhash.items():
                for group in groups:
                    for p in group:
                        self._path_to_hash[os.path.normpath(p)] = h
        # Load persisted keep list for this vault
        self._kept = kept_files.load_kept(self._vault_path) if self._vault_path else set()
        # Load per-vault duplicate rules
        self._rules = load_rules(self._vault_path) if self._vault_path else []

        self.popup = parent  # the container frame (not a Toplevel)

        if not self._items:
            tk.Label(self.popup, text="No duplicates found.",
                     font=("Helvetica", 11), fg="#555").pack(padx=20, pady=40)
            tk.Button(self.popup, text="← Back to Vault Tree",
                      command=self._call_on_close).pack()
            return

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
        Tooltip(btn_next, "Go to the next duplicate group.")

        btn_prev = tk.Button(nav_bar, text="< Prev", command=self._prev, relief=tk.FLAT)
        btn_prev.pack(side=tk.RIGHT, padx=(0, 4))
        Tooltip(btn_prev, "Go to the previous duplicate group.")

        btn_leave = tk.Button(nav_bar, text="← Back to Vault Tree",
                              command=self._leave, relief=tk.FLAT)
        btn_leave.pack(side=tk.RIGHT, padx=(0, 12))
        Tooltip(btn_leave, "Stop reviewing and return to the vault tree. "
                           "Staged deletions will NOT be executed unless you click "
                           "Report / Execute first.")

        btn_rules = tk.Button(nav_bar, text="Manage Rules",
                              command=self._open_rules_manager, relief=tk.FLAT)
        btn_rules.pack(side=tk.RIGHT, padx=(0, 4))
        Tooltip(btn_rules, "Open the rules editor for this vault. Rules let you automatically "
                           "pre-select or protect files based on their path, folder, or extension.")

        self._btn_auto = tk.Button(nav_bar, text="Auto-apply Rules",
                                   command=self._auto_apply_rules, relief=tk.FLAT,
                                   state=tk.NORMAL if self._rules else tk.DISABLED)
        self._btn_auto.pack(side=tk.RIGHT, padx=(0, 4))
        Tooltip(self._btn_auto,
                "Automatically stage all duplicate groups where rules give an "
                "unambiguous verdict (no delete/keep conflict). Items with conflicts "
                "or no matching rules are left for manual review.")

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

    # ── Kept-files helpers ────────────────────────────────────────────────────

    def _is_file_kept(self, path):
        if not self._vault_path or not self._path_to_hash:
            return False
        norm = os.path.normpath(path)
        h = self._path_to_hash.get(norm)
        if not h:
            return False
        rel = os.path.relpath(norm, self._vault_path)
        return (h, rel) in self._kept

    def _refresh_file_lb(self):
        """Rebuild the file listbox, marking always-kept items and rule verdicts."""
        sel = list(self._file_lb.curselection())
        self._file_lb.delete(0, tk.END)
        verdicts = getattr(self, "_rule_verdicts", {})
        for i, path in enumerate(self._file_paths):
            label = self._rel(path)
            verdict = verdicts.get(path)
            if self._is_file_kept(path):
                label += "  [kept]"
                self._file_lb.insert(tk.END, label)
                self._file_lb.itemconfig(i, bg="#e8f5e9", fg="#1b5e20")
            elif verdict == "delete":
                label += "  [rule: delete]"
                self._file_lb.insert(tk.END, label)
                self._file_lb.itemconfig(i, bg="#fdecea", fg="#7a2e00")
            elif verdict == "keep":
                label += "  [rule: keep]"
                self._file_lb.insert(tk.END, label)
                self._file_lb.itemconfig(i, bg="#e8f5e9", fg="#1b5e20")
            elif verdict == "conflict":
                label += "  [rule: conflict — review manually]"
                self._file_lb.insert(tk.END, label)
                self._file_lb.itemconfig(i, bg="#fff3cd", fg="#6b4c00")
            else:
                self._file_lb.insert(tk.END, label)
        for i in sel:
            if i < len(self._file_paths):
                self._file_lb.selection_set(i)

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
        self._folder_lb.bind("<Control-Button-1>", self._on_ctrl_click_folder)
        Tooltip(self._folder_lb, "Ctrl+click to open in file explorer")
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

    def _on_ctrl_click_folder(self, event):
        index = self._folder_lb.nearest(event.y)
        if 0 <= index < len(self._folder_paths):
            _open_in_explorer(self._folder_paths[index], is_dir=True)

    def _on_ctrl_click_file(self, event):
        index = self._file_lb.nearest(event.y)
        if 0 <= index < len(self._file_paths):
            _open_in_explorer(self._file_paths[index], is_dir=False)

    def _always_keep_selected(self):
        sel = self._file_lb.curselection()
        if not sel:
            return
        for i in sel:
            path = self._file_paths[i]
            norm = os.path.normpath(path)
            h = self._path_to_hash.get(norm)
            if not h:
                tracer.log(f"Always-keep: no hash found for {tracer.pid(path)}, skipping",
                           trace_level=2)
                continue
            rel = os.path.relpath(norm, self._vault_path)
            self._kept.add((h, rel))
            tracer.log(f"Always-keep marked: {rel!r}", trace_level=3)
        kept_files.save_kept(self._vault_path, self._kept)
        self._refresh_file_lb()

    # ── Rules integration ─────────────────────────────────────────────────────

    def _open_rules_manager(self):
        from widgets_library.rules_manager import RulesManager
        mgr = RulesManager(self._root, self._vault_path)
        self._root.wait_window(mgr._win)
        # Reload rules after the manager closes (user may have added/removed rules)
        self._rules = load_rules(self._vault_path) if self._vault_path else []
        self._btn_auto.config(state=tk.NORMAL if self._rules else tk.DISABLED)
        # Refresh current item to reflect new rules
        self._show_item()

    def _auto_apply_rules(self):
        """Stage all items where rules give an unambiguous verdict, skip the rest."""
        if not self._rules:
            return
        auto_staged = 0
        i = 0
        while i < len(self._items):
            item = self._items[i]
            if item["type"] != "file":
                i += 1
                continue
            paths = item["paths"]
            raw = apply_rules(self._rules, paths, self._vault_path)
            verdicts = {p: net_action(matches) for p, matches in raw.items()}

            # Gather delete/keep sets, respecting always-keep
            keep = {p for p in paths
                    if self._is_file_kept(p) or verdicts.get(p) == "keep"}
            to_delete = [p for p in paths
                         if verdicts.get(p) == "delete" and p not in keep
                         and os.path.exists(p)]
            has_conflict = any(v == "conflict" for v in verdicts.values())
            no_verdict = all(v is None for v in verdicts.values())

            if has_conflict or no_verdict or not to_delete:
                i += 1
                continue

            label = f"FILE (auto-rule) — delete {len(to_delete)}, keep {len(keep)}"
            self._pending.append({"label": label,
                                  "deleted": to_delete,
                                  "original_item": dict(item)})
            self._items.pop(i)
            auto_staged += 1
            # don't increment i — next item shifts into position i

        self._update_pending_label()
        if auto_staged:
            tracer.log(f"Auto-apply rules: staged {auto_staged} item(s)", trace_level=3)
            if not self._items:
                self._leave()
                return
            self._index = min(self._index, len(self._items) - 1)
            self._show_item()
        else:
            from tkinter import messagebox
            messagebox.showinfo(
                "Auto-apply rules",
                "No file groups had an unambiguous rule verdict.\n"
                "All remaining items need manual review.",
                parent=self._root,
            )

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

        # Compute rule verdicts for this group
        self._rule_verdicts = {}
        if self._rules and self._vault_path:
            raw = apply_rules(self._rules, paths, self._vault_path)
            self._rule_verdicts = {p: net_action(matches) for p, matches in raw.items()}

        # Rule banner — show when any file has a rule verdict
        verdicts = set(self._rule_verdicts.values()) - {None}
        if verdicts:
            _BANNER_COLORS = {
                "delete":   ("#fdecea", "#7a2e00"),
                "keep":     ("#e8f5e9", "#1b5e20"),
                "conflict": ("#fff3cd", "#6b4c00"),
            }
            dominant = ("conflict" if "conflict" in verdicts
                        else "delete" if "delete" in verdicts else "keep")
            bg, fg = _BANNER_COLORS[dominant]
            n_del = sum(1 for v in self._rule_verdicts.values() if v == "delete")
            n_keep = sum(1 for v in self._rule_verdicts.values() if v == "keep")
            n_conf = sum(1 for v in self._rule_verdicts.values() if v == "conflict")
            parts = []
            if n_del:
                parts.append(f"{n_del} pre-selected for deletion")
            if n_keep:
                parts.append(f"{n_keep} protected (keep)")
            if n_conf:
                parts.append(f"{n_conf} conflict (manual review needed)")
            banner = tk.Frame(list_frame, bg=bg, pady=3)
            banner.pack(fill=tk.X, padx=6)
            tk.Label(banner, text="⚙ Rule: " + ",  ".join(parts),
                     bg=bg, fg=fg, font=("Helvetica", 8), anchor="w").pack(
                fill=tk.X, padx=6)

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
        self._refresh_file_lb()

        # Pre-select files that have an unambiguous "delete" verdict from rules
        for i, p in enumerate(self._file_paths):
            if self._rule_verdicts.get(p) == "delete" and not self._is_file_kept(p):
                self._file_lb.selection_set(i)
        if not self._file_lb.curselection():
            self._file_lb.selection_set(0)

        self._preview_panel = tk.Frame(self._content, width=260, relief=tk.GROOVE, bd=1)
        self._preview_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
        self._preview_panel.pack_propagate(False)

        self._file_lb.bind("<<ListboxSelect>>", self._on_file_select)
        self._file_lb.bind("<Control-Button-1>", self._on_ctrl_click_file)
        Tooltip(self._file_lb, "Ctrl+click to open in file explorer")
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
        if self._vault_path and self._path_to_hash:
            b4 = tk.Button(self._btn_row, text="Always Keep This",
                           command=self._always_keep_selected)
            b4.pack(side=tk.LEFT, padx=(6, 0))
            Tooltip(b4, "Mark selected file(s) as always-keep: they will never be"
                        " suggested for deletion in future sessions, even after reindexing.")

    def _queue_keep_file(self):
        sel = self._file_lb.curselection()
        keep = {self._file_paths[i] for i in sel}
        item = self._items[self._index]
        # Always-kept files and rule-"keep" files are protected regardless of selection
        verdicts = getattr(self, "_rule_verdicts", {})
        keep.update(p for p in item["paths"]
                    if self._is_file_kept(p) or verdicts.get(p) == "keep")
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
        win = tk.Toplevel(self._root)
        win.title("Deletion Report")
        win.geometry("700x500")
        win.transient(self._root)
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
                self._call_on_close()

            tk.Button(btn_row, text=f"Execute — send {n} item(s) to recycle bin",
                      command=execute, fg="white", bg="#cc4400",
                      activebackground="#aa3300").pack(side=tk.LEFT, padx=(0, 8))
            tk.Button(btn_row, text="Cancel — keep reviewing",
                      command=win.destroy).pack(side=tk.LEFT)
        else:
            tk.Button(btn_row, text="Close", command=win.destroy).pack(side=tk.LEFT)

    def _execute_pending(self):
        self._root.config(cursor="watch")
        self._root.update()
        errors = []
        try:
            for action in self._pending:
                group_paths = action.get("original_item", {}).get("paths", [])
                kept_in_group = [p for p in group_paths if p not in action["deleted"]]
                copy_path = kept_in_group[0] if kept_in_group else None
                for path in action["deleted"]:
                    normed = os.path.normpath(path)
                    if not os.path.exists(normed):
                        tracer.log(f"Already gone, skipping: {tracer.pid(path)}", trace_level=2)
                        continue
                    try:
                        send2trash.send2trash(normed)
                        file_hash = self._path_to_hash.get(normed)
                        deleted_files_db.record_deletion(file_hash, path, copy_path)
                        tracer.log(f"Sent to trash: {tracer.pid(path)}", trace_level=5)
                    except Exception as e:
                        tracer.log_error(f"Error deleting {path!r}: {e}")
                        errors.append(f"{os.path.basename(path)}: {e}")
        finally:
            self._root.config(cursor="")
        self._pending.clear()
        self._update_pending_label()
        if errors:
            messagebox.showwarning(
                "Some deletions failed",
                "The following items could not be moved to the recycle bin:\n\n"
                + "\n".join(errors),
                parent=self._root,
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

    def _call_on_close(self):
        if self._on_close_cb:
            self._on_close_cb()

    def _leave(self):
        if self._pending:
            n = sum(len(a["deleted"]) for a in self._pending)
            confirmed = messagebox.askyesno(
                "Leave without executing?",
                f"You have {len(self._pending)} staged action(s) ({n} item(s) to delete) "
                f"that have not been executed.\n\nLeave without sending anything to the recycle bin?",
                icon="warning",
                parent=self._root,
            )
            if confirmed:
                self._call_on_close()
        else:
            self._call_on_close()

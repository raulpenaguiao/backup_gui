import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import tools_library.tracer as tracer
import tools_library.dbs as dbs
from tools_library.pipeline_state import PipelineState, PENDING, IN_PROGRESS, DONE, ERROR
from tools_library.suggestion_list import SuggestionList
from tools_library.progress_tracker import ProgressTracker
from tools_library.pigmy_hash import index_vault, save_pigmy_hash
from tools_library.file_tree import build_size_index, human_size
from tools_library.vault_operations import (
    find_copies_in_external, find_internal_duplicates,
    delete_marked_files, delete_empty_folders,
)
from tools_library.ntfy import send_ntfy
from widgets_library.tooltip import Tooltip

_POLL_MS = 80


def _overall_pct(pt):
    """Same phase-weighted estimate used by LoadingPopup, embedded inline here
    since it's only a few lines and this widget needs no popup-specific state."""
    if pt.phase == "bfs":
        return pt.bfs_progress * 30.0
    if pt.loaded and pt.total_value > 0:
        return 30.0 + (pt.current_value / pt.total_value) * 65.0
    return 30.0


class PrepareEVWindow:
    """Full-window standalone pipeline for preparing an external vault:
    index both vaults, detect copies/duplicates in the EV, then delete what was
    suggested and clean up empty folders — sequentially, with optional
    auto-continue chaining between steps and ntfy progress notifications.
    """

    def __init__(self, root, main_vault, ev_vault, on_back):
        self.root = root
        self.main_vault = main_vault
        self.ev_vault = ev_vault
        self.on_back = on_back

        self._state = PipelineState()
        self._main_pigmyhash = None
        self._ev_pigmyhash = None
        self._suggestions = SuggestionList()
        self._current_cancel_token = None
        self._auto_vars = {}

        settings = dbs.load_prepare_ev_settings()
        self._use_trash = tk.BooleanVar(value=settings.get("use_trash", True))
        self._ntfy_channel = tk.StringVar(value=settings.get("ntfy_channel", ""))

        self._handlers = {
            "Main vault indexing": self._run_index_main,
            "External vault indexing": self._run_index_ev,
            "Copies in EV detection": self._run_copies_detection,
            "Double files in EV": self._run_internal_dupes,
            "Delete suggested files in EV": self._run_delete_suggested,
            "Delete empty folders in EV": self._run_delete_empty,
        }

        self._build()
        self._render_steps()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self.root.title("Pigmy Backup Application — Prepare External Vault")
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)

        hdr = tk.Frame(self.frame, pady=6, padx=10)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        title_col = tk.Frame(hdr)
        title_col.grid(row=0, column=0, sticky="w")
        tk.Label(title_col, text="Prepare External Vault",
                 font=("Helvetica", 13, "bold")).pack(anchor="w")
        self._main_stats_label = tk.Label(title_col, text=f"Main vault: {self.main_vault}",
                                          fg="#555", font=("Helvetica", 9))
        self._main_stats_label.pack(anchor="w")
        self._ev_stats_label = tk.Label(title_col, text=f"External vault: {self.ev_vault}",
                                        fg="#555", font=("Helvetica", 9))
        self._ev_stats_label.pack(anchor="w")

        btn_close = tk.Button(hdr, text="Close", command=self._on_close, relief=tk.FLAT)
        btn_close.grid(row=0, column=1, sticky="e")

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(row=1, column=0, sticky="ew")

        body = tk.PanedWindow(self.frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        body.grid(row=2, column=0, sticky="nsew")

        left = tk.Frame(body, padx=10, pady=10)
        body.add(left, minsize=300, width=340)
        self._build_process_panel(left)

        right = tk.Frame(body, padx=10, pady=10)
        body.add(right, stretch="always")
        self._content_frame = right

    def _build_process_panel(self, parent):
        tk.Label(parent, text="Process", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self._steps_frame = tk.Frame(parent)
        self._steps_frame.pack(fill=tk.X, pady=(6, 10))

        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=(0, 10))
        self._proceed_btn = tk.Button(btn_row, text="Proceed", command=self._on_proceed,
                                      font=("Helvetica", 10, "bold"), padx=12, pady=6)
        self._cancel_btn = tk.Button(btn_row, text="Cancel", command=self._on_cancel,
                                     bg="#dddddd", padx=12, pady=6)
        self._retry_btn = tk.Button(btn_row, text="Retry", command=self._on_retry,
                                    bg="#c0392b", fg="white", font=("Helvetica", 10, "bold"),
                                    padx=12, pady=6)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))

        self._trash_check = tk.Checkbutton(
            parent, text="Send deletions to trash (uncheck = delete permanently)",
            variable=self._use_trash, wraplength=280, justify=tk.LEFT)
        self._trash_check.pack(anchor="w", pady=(0, 10))

        tk.Label(parent, text="ntfy channel:", anchor="w").pack(anchor="w")
        ntfy_row = tk.Frame(parent)
        ntfy_row.pack(fill=tk.X, pady=(2, 4))
        entry = tk.Entry(ntfy_row, textvariable=self._ntfy_channel)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<FocusOut>", lambda _e: self._save_settings())
        tk.Button(ntfy_row, text="⎘", command=self._copy_ntfy_channel).pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(ntfy_row, text="TEST", command=self._test_ntfy).pack(side=tk.LEFT, padx=(4, 0))

        self._ntfy_status_label = tk.Label(parent, text="", fg="#555", font=("Helvetica", 8),
                                           wraplength=280, justify=tk.LEFT, anchor="w")
        self._ntfy_status_label.pack(fill=tk.X)

    # ── Step rendering ───────────────────────────────────────────────────────

    def _render_steps(self):
        for child in self._steps_frame.winfo_children():
            child.destroy()

        head = self._state.head()
        running = any(s.status == IN_PROGRESS for s in self._state.steps)

        for step in self._state.steps:
            row = tk.Frame(self._steps_frame)
            row.pack(fill=tk.X, pady=2)
            if step.status == DONE:
                tk.Label(row, text="✓", fg="#1b5e20", width=2,
                        font=("Helvetica", 11, "bold")).pack(side=tk.LEFT)
            elif step.status == IN_PROGRESS:
                tk.Label(row, text="⏳", width=2).pack(side=tk.LEFT)
            elif step.status == ERROR:
                tk.Label(row, text="❌", width=2).pack(side=tk.LEFT)
            elif step is head:
                tk.Label(row, text="→", width=2, font=("Helvetica", 11, "bold")).pack(side=tk.LEFT)
            else:
                var = self._auto_vars.get(step.name)
                if var is None:
                    var = tk.BooleanVar(value=step.auto_continue)
                    self._auto_vars[step.name] = var
                else:
                    var.set(step.auto_continue)
                cb = tk.Checkbutton(
                    row, text=step.name, variable=var, anchor="w",
                    command=lambda s=step, v=var: self._state.set_auto_continue(s, v.get()))
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
                Tooltip(cb, "Automatically start this step as soon as the previous one finishes.")
                continue
            tk.Label(row, text=step.name, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._cancel_btn.pack_forget()
        self._proceed_btn.pack_forget()
        self._retry_btn.pack_forget()
        if running:
            self._cancel_btn.pack(side=tk.RIGHT)
        elif head is not None and head.status == ERROR:
            self._retry_btn.config(text=f"Retry: {head.name}")
            self._retry_btn.pack(side=tk.RIGHT)
        elif head is not None:
            self._proceed_btn.config(text=f"Proceed: {head.name}", state=tk.NORMAL)
            self._proceed_btn.pack(side=tk.RIGHT)
        else:
            self._proceed_btn.config(text="All steps complete", state=tk.DISABLED)
            self._proceed_btn.pack(side=tk.RIGHT)

    # ── Pipeline driver ──────────────────────────────────────────────────────

    def _on_proceed(self):
        step = self._state.head()
        if step is None:
            return
        self._start_step(step)

    def _on_cancel(self):
        if self._current_cancel_token is not None:
            self._current_cancel_token.set()

    def _on_retry(self):
        step = self._state.head()
        if step is None or step.status != ERROR:
            return
        self._state.retry_error(step)
        self._start_step(step)

    def _start_step(self, step):
        self._state.start(step)
        self._render_steps()
        self._notify_ntfy(f"Prepare External Vault: starting '{step.name}'")
        self._handlers[step.name](step)

    def _on_step_finished(self, step):
        self._current_cancel_token = None
        nxt = self._state.mark_done(step)
        self._render_steps()
        self._notify_ntfy(f"Prepare External Vault: finished '{step.name}'")
        if nxt is not None:
            self._start_step(nxt)

    def _on_step_cancelled(self, step):
        self._current_cancel_token = None
        self._state.mark_cancelled(step)
        self._render_steps()

    def _on_step_error(self, step, error):
        self._current_cancel_token = None
        self._state.mark_error(step)
        self._render_steps()
        self._show_error_panel(step.name, error)
        self._notify_ntfy(f"Prepare External Vault: ERROR in '{step.name}': {error}")
        messagebox.showerror("Step failed", f"{step.name} failed:\n\n{error}\n\n"
                             f"The pipeline has stopped. Click Retry once you've fixed the issue.",
                             parent=self.root)

    def _show_error_panel(self, step_name, error):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text=f"❌ {step_name} failed",
                font=("Helvetica", 11, "bold"), fg="#c0392b").pack(anchor="w")
        tk.Label(self._content_frame, text=str(error), fg="#c0392b",
                wraplength=480, justify=tk.LEFT, anchor="w").pack(anchor="w", pady=(8, 0))

    def _poll_queue(self, q, on_message):
        try:
            while True:
                msg = q.get_nowait()
                if on_message(msg) is False:
                    return
        except queue.Empty:
            pass
        self.root.after(_POLL_MS, lambda: self._poll_queue(q, on_message))

    # ── Step 1/2: indexing ───────────────────────────────────────────────────

    def _show_progress_panel(self, title):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text=title, font=("Helvetica", 11, "bold")).pack(anchor="w")
        bar = ttk.Progressbar(self._content_frame, mode="determinate", maximum=100)
        bar.pack(fill=tk.X, pady=(8, 4))
        status = tk.Label(self._content_frame, text="Starting…", anchor="w")
        status.pack(fill=tk.X)
        file_label = tk.Label(self._content_frame, text="", anchor="w", fg="gray",
                              font=("Helvetica", 8))
        file_label.pack(fill=tk.X)
        return bar, status, file_label

    def _show_index_done_panel(self, title, total_files, total_size):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text=f"{title} — done",
                font=("Helvetica", 11, "bold")).pack(anchor="w")
        tk.Label(self._content_frame,
                text=f"{total_files:,} file(s), {human_size(total_size)}",
                fg="#1b5e20", font=("Helvetica", 10)).pack(anchor="w", pady=(8, 0))

    def _poll_index_progress(self, pt, bar, status, file_label, last_pct, cancel):
        if pt.finished or cancel.is_set() or self._current_cancel_token is not cancel:
            return
        pct = max(_overall_pct(pt), last_pct[0])
        last_pct[0] = pct
        bar["value"] = pct
        fname = os.path.basename(getattr(pt, "current_file", "") or "")
        if pt.phase == "bfs":
            found = getattr(pt, "_scan_found", 0)
            status.config(text=f"Scanning: {found:,} found")
        elif pt.loaded and pt.total_value > 0:
            status.config(text=f"Hashing: {pt.current_value:,} / {pt.total_value:,}")
        file_label.config(text=fname)
        self.root.after(_POLL_MS, lambda: self._poll_index_progress(
            pt, bar, status, file_label, last_pct, cancel))

    def _run_index_main(self, step):
        self._run_indexing(step, self.main_vault, "Indexing main vault…", is_main=True)

    def _run_index_ev(self, step):
        self._run_indexing(step, self.ev_vault, "Indexing external vault…", is_main=False)

    def _run_indexing(self, step, vault_path, title, is_main):
        pt = ProgressTracker(name=title, unit="entries")
        cancel = threading.Event()
        self._current_cancel_token = cancel
        bar, status, file_label = self._show_progress_panel(title)
        self._poll_index_progress(pt, bar, status, file_label, [0.0], cancel)

        def worker():
            try:
                pigmyhash, skipped = index_vault(vault_path, pt, cancel)
                if pigmyhash is None:
                    self.root.after(0, lambda: self._on_step_cancelled(step))
                    return
                save_pigmy_hash(vault_path, pigmyhash)
                sizes, file_counts = build_size_index(vault_path)
                total_size = sizes.get(vault_path, 0)
                total_files = file_counts.get(vault_path, 0)

                def finish():
                    if is_main:
                        self._main_pigmyhash = pigmyhash
                        self._main_stats_label.config(
                            text=f"Main vault: {vault_path}   "
                                 f"({total_files:,} files, {human_size(total_size)})")
                    else:
                        self._ev_pigmyhash = pigmyhash
                        self._ev_stats_label.config(
                            text=f"External vault: {vault_path}   "
                                 f"({total_files:,} files, {human_size(total_size)})")
                    self._show_index_done_panel(title, total_files, total_size)
                    self._on_step_finished(step)
                self.root.after(0, finish)
            except Exception as e:
                tracer.log_error(f"{title} failed: {e}")
                self.root.after(0, lambda: self._on_step_error(step, e))

        threading.Thread(target=worker, daemon=True).start()

    # ── Step 3/4: detection ──────────────────────────────────────────────────

    def _show_suggestion_panel(self, title):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text=title, font=("Helvetica", 11, "bold")).pack(anchor="w")
        self._total_size_label = tk.Label(self._content_frame, text=self._suggestions_summary(),
                                          fg="#555")
        self._total_size_label.pack(anchor="w", pady=(2, 6))
        bar = ttk.Progressbar(self._content_frame, mode="determinate", maximum=100)
        bar.pack(fill=tk.X, pady=(0, 6))

        tv_frame = tk.Frame(self._content_frame)
        tv_frame.pack(fill=tk.BOTH, expand=True)
        tv_frame.rowconfigure(0, weight=1)
        tv_frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(tv_frame, columns=("size", "source"), show="tree headings")
        tree.heading("#0", text="Suggested for deletion (EV)")
        tree.heading("size", text="Size")
        tree.heading("source", text="Reason")
        tree.column("size", width=90, anchor=tk.E, stretch=False)
        tree.column("source", width=160, stretch=False)
        vsb = ttk.Scrollbar(tv_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._suggestion_tree = tree
        for item in self._suggestions:
            self._add_suggestion_row(item)
        return bar

    def _suggestions_summary(self):
        return (f"{len(self._suggestions):,} file(s) marked for deletion — "
                f"{human_size(self._suggestions.total_size())}")

    def _add_suggestion_row(self, item):
        rel = os.path.relpath(item["path"], self.ev_vault)
        self._suggestion_tree.insert("", tk.END, text=f"EV/{rel}",
                                     values=(human_size(item["size"]), item["reason"]))

    def _run_copies_detection(self, step):
        self._run_detection(
            step, "Detecting copies of main vault files in EV…", "copy of main vault file",
            lambda cancel, on_progress, on_match: find_copies_in_external(
                self._main_pigmyhash, self._ev_pigmyhash,
                stop_event=cancel, progress_callback=on_progress, match_callback=on_match))

    def _run_internal_dupes(self, step):
        self._run_detection(
            step, "Finding duplicate files within the EV…", "duplicate within EV",
            lambda cancel, on_progress, on_match: find_internal_duplicates(
                self._ev_pigmyhash,
                stop_event=cancel, progress_callback=on_progress, match_callback=on_match))

    def _run_detection(self, step, title, reason, call_fn):
        cancel = threading.Event()
        self._current_cancel_token = cancel
        bar = self._show_suggestion_panel(title)
        q = queue.Queue()

        def worker():
            def on_progress(current, total):
                q.put(("progress", current, total))

            def on_match(path, size, file_hash, copy_path):
                q.put(("match", path, size, file_hash, copy_path))

            try:
                call_fn(cancel, on_progress, on_match)
                q.put(("done",))
            except Exception as e:
                tracer.log_error(f"{title} failed: {e}")
                q.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()

        def on_message(msg):
            kind = msg[0]
            if kind == "progress":
                _, current, total = msg
                if total > 0:
                    bar["value"] = int(100 * current / total)
            elif kind == "match":
                _, path, size, file_hash, copy_path = msg
                item = self._suggestions.add(path, size, file_hash, copy_path, reason)
                if item is None:
                    return True  # already suggested by an earlier step/retry
                self._add_suggestion_row(item)
                self._total_size_label.config(text=self._suggestions_summary())
            elif kind == "error":
                self._on_step_error(step, msg[1])
                return False
            elif kind == "done":
                bar["value"] = 100
                if cancel.is_set():
                    self._on_step_cancelled(step)
                else:
                    self._on_step_finished(step)
                return False
            return True

        self._poll_queue(q, on_message)

    # ── Step 5/6: deletion ───────────────────────────────────────────────────

    def _show_status_panel(self, title):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text=title, font=("Helvetica", 11, "bold")).pack(anchor="w")
        bar = ttk.Progressbar(self._content_frame, mode="determinate", maximum=100)
        bar.pack(fill=tk.X, pady=(8, 4))
        status = tk.Label(self._content_frame, text="", anchor="w")
        status.pack(fill=tk.X)
        return bar, status

    def _show_delete_done_panel(self, deleted_count, error_count, use_trash):
        for child in self._content_frame.winfo_children():
            child.destroy()
        tk.Label(self._content_frame, text="Deletion complete",
                font=("Helvetica", 11, "bold")).pack(anchor="w")
        where = "trash" if use_trash else "permanently"
        tk.Label(self._content_frame,
                text=f"Deleted {deleted_count:,} file(s) ({where}).",
                fg="#1b5e20", font=("Helvetica", 10)).pack(anchor="w", pady=(8, 0))
        if error_count:
            tk.Label(self._content_frame, text=f"{error_count:,} error(s) — see the error log.",
                    fg="#c0392b").pack(anchor="w", pady=(4, 0))

    def _run_delete_suggested(self, step):
        cancel = threading.Event()
        self._current_cancel_token = cancel
        snapshot = self._suggestions.snapshot()
        bar, status = self._show_status_panel(
            f"Deleting {len(snapshot):,} suggested file(s) from the EV…")
        self._save_settings()
        q = queue.Queue()

        def worker():
            def on_progress(current, total):
                q.put(("progress", current, total))

            try:
                deleted, errors = delete_marked_files(
                    snapshot, use_trash=self._use_trash.get(),
                    progress_callback=on_progress, stop_event=cancel)
                q.put(("done", deleted, errors))
            except Exception as e:
                tracer.log_error(f"Delete suggested files failed: {e}")
                q.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()

        def on_message(msg):
            kind = msg[0]
            if kind == "progress":
                _, current, total = msg
                if total > 0:
                    pct = int(100 * current / total)
                    bar["value"] = pct
                    status.config(text=f"{current:,} / {total:,}")
            elif kind == "error":
                self._on_step_error(step, msg[1])
                return False
            elif kind == "done":
                _, deleted, errors = msg
                self._suggestions.remove_paths(deleted)
                self._show_delete_done_panel(len(deleted), len(errors), self._use_trash.get())
                if errors:
                    messagebox.showwarning(
                        "Some deletions failed",
                        f"{len(errors)} file(s) could not be deleted — see the error log for details.",
                        parent=self.root)
                if cancel.is_set():
                    self._on_step_cancelled(step)
                else:
                    self._on_step_finished(step)
                return False
            return True

        self._poll_queue(q, on_message)

    def _run_delete_empty(self, step):
        cancel = threading.Event()
        self._current_cancel_token = cancel
        bar, status = self._show_status_panel("Deleting empty folders in the EV…")
        bar.config(mode="indeterminate")
        bar.start(25)
        q = queue.Queue()

        def worker():
            def cb(phase, n_deleted, current_path):
                q.put(("progress", phase, n_deleted, current_path))
            try:
                result = delete_empty_folders(self.ev_vault, progress_callback=cb, stop_event=cancel)
                q.put(("done", result))
            except Exception as e:
                tracer.log_error(f"Delete empty folders failed: {e}")
                q.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()

        def on_message(msg):
            kind = msg[0]
            if kind == "progress":
                _, phase, n_deleted, current_path = msg
                if phase == "scan":
                    status.config(text="Scanning for empty folders…")
                else:
                    status.config(text=f"Deleted {n_deleted} folder(s) so far…")
            elif kind == "error":
                bar.stop()
                self._on_step_error(step, msg[1])
                return False
            elif kind == "done":
                _, deleted = msg
                bar.stop()
                bar.config(mode="determinate")
                bar["value"] = 100
                status.config(text=f"Removed {len(deleted)} empty folder(s).")
                if cancel.is_set():
                    self._on_step_cancelled(step)
                else:
                    self._on_step_finished(step)
                return False
            return True

        self._poll_queue(q, on_message)

    # ── ntfy ──────────────────────────────────────────────────────────────────

    def _notify_ntfy(self, message):
        channel = self._ntfy_channel.get().strip()
        if not channel:
            return

        def worker():
            ok, err = send_ntfy(channel, message)
            if not ok:
                self.root.after(0, lambda: self._ntfy_status_label.config(
                    text=f"ntfy error: {err}", fg="#c0392b"))

        threading.Thread(target=worker, daemon=True).start()

    def _copy_ntfy_channel(self):
        channel = self._ntfy_channel.get().strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(channel)

    def _test_ntfy(self):
        channel = self._ntfy_channel.get().strip()
        self._save_settings()
        self._ntfy_status_label.config(text="Sending test notification…", fg="#555")

        def worker():
            ok, err = send_ntfy(channel, "Pigmy Backup: test notification from Prepare External Vault.")
            self.root.after(0, lambda: self._on_ntfy_test_result(ok, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ntfy_test_result(self, ok, err):
        if ok:
            self._ntfy_status_label.config(text="Test notification sent.", fg="#1b5e20")
        else:
            self._ntfy_status_label.config(text=f"ntfy error: {err}", fg="#c0392b")

    def _save_settings(self):
        dbs.save_prepare_ev_settings({
            "ntfy_channel": self._ntfy_channel.get().strip(),
            "use_trash": self._use_trash.get(),
        })

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._save_settings()
        if self._current_cancel_token is not None:
            self._current_cancel_token.set()
        self.on_back()

    def destroy(self):
        self.frame.destroy()

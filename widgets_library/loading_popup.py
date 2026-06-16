import os
import time
import tkinter as tk
from tkinter import ttk
import tools_library.tracer as tracer
from tools_library.progress_tracker import ProgressTracker

_POLL_MS = 150


def _fmt_time(seconds):
    s = int(seconds)
    if s < 60:
        return f"0:{s:02d}"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _overall_pct(pt):
    if pt.phase == "sizing":
        return 95.0
    if pt.phase == "bfs":
        return pt.bfs_progress * 30.0
    if pt.loaded and pt.total_value > 0:
        return 30.0 + (pt.current_value / pt.total_value) * 65.0
    return 30.0


class LoadingPopup:
    def __init__(self, parent, progress_tracker, cancel_token=None, title="Indexing vault..."):
        if not isinstance(progress_tracker, ProgressTracker):
            raise ValueError("progress_tracker must be a ProgressTracker instance")
        self.progress_tracker = progress_tracker
        self.cancel_token = cancel_token
        self._start_time = time.time()
        self._phase2_start = None
        self._last_pct = 0.0

        self.popup = tk.Toplevel(parent)
        self.popup.title("Pigmy Backup Application")
        self.popup.geometry("600x200")
        self.popup.resizable(False, False)
        self.popup.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.popup.update_idletasks()
        sw, sh = self.popup.winfo_screenwidth(), self.popup.winfo_screenheight()
        self.popup.geometry(f"+{(sw - 600) // 2}+{(sh - 200) // 2}")

        self._frame = tk.Frame(self.popup, padx=18, pady=12)
        self._frame.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(self._frame)
        top_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(top_row, text=title, font=("Helvetica", 15, "bold")).pack(side=tk.LEFT)
        if cancel_token is not None:
            tk.Button(top_row, text="Cancel", command=self._on_cancel,
                      relief=tk.FLAT, bg="#dddddd").pack(side=tk.RIGHT)

        self._bar = ttk.Progressbar(self._frame, length=564, mode="determinate", maximum=100)
        self._bar.pack(pady=(0, 4))

        self._count_label = tk.Label(self._frame, text="Scanning...", anchor=tk.W)
        self._count_label.pack(fill=tk.X)

        self._file_label = tk.Label(self._frame, text="", anchor=tk.W, fg="gray",
                                    font=("Helvetica", 8))
        self._file_label.pack(fill=tk.X)

        self._time_label = tk.Label(self._frame, text="Elapsed: 0:00", anchor=tk.W, fg="#555")
        self._time_label.pack(fill=tk.X, pady=(2, 0))

        self._poll_id = None
        self._poll()

    def _on_cancel(self):
        if self.cancel_token is not None:
            self.cancel_token.set()
        # Destroy immediately — background thread will clean up via _on_cancelled
        self.destroy()

    def _poll(self):
        try:
            if not self.popup.winfo_exists():
                return
            pt = self.progress_tracker

            # Progress bar
            pct = max(_overall_pct(pt), self._last_pct)
            self._last_pct = pct
            self._bar["value"] = pct

            # Count label
            fname = os.path.basename(getattr(pt, "current_file", "") or "")
            if pt.phase == "sizing":
                self._count_label.config(text="Computing sizes...")
                self._file_label.config(text="")
            elif pt.phase == "bfs":
                found = getattr(pt, "_scan_found", 0)
                est = getattr(pt, "_scan_estimate", 0)
                self._count_label.config(
                    text=f"Scanning: {found:,} found (~{est:,} estimated)"
                )
                self._file_label.config(text=fname)
            elif pt.loaded and pt.total_value > 0:
                self._count_label.config(
                    text=f"Processing: {pt.current_value:,} / {pt.total_value:,} entries"
                )
                self._file_label.config(text=fname)

            # Elapsed + ETA
            elapsed = time.time() - self._start_time
            if pt.phase == "hashing" and pt.loaded and pt.current_value > 0:
                if self._phase2_start is None:
                    self._phase2_start = time.time()
                elapsed_p2 = time.time() - self._phase2_start
                rate = pt.current_value / max(elapsed_p2, 0.001)
                remaining = (pt.total_value - pt.current_value) / max(rate, 0.001)
                self._time_label.config(
                    text=f"Elapsed: {_fmt_time(elapsed)}   ETA: ~{_fmt_time(remaining)}"
                )
            else:
                self._time_label.config(text=f"Elapsed: {_fmt_time(elapsed)}")

            if not pt.finished:
                self._poll_id = self.popup.after(_POLL_MS, self._poll)
            # When finished: wait for show_done() to be called from main thread

        except Exception as e:
            tracer.log_error(f"LoadingPopup poll error: {e}")

    def show_done(self, on_open):
        """Called from main thread after indexing completes. Shows stats + View Panel button."""
        try:
            if not self.popup.winfo_exists():
                return
            pt = self.progress_tracker
            elapsed = time.time() - self._start_time
            self._bar["value"] = 100
            self._count_label.config(
                text=f"Done  {pt.total_value:,} entries indexed"
            )
            self._file_label.config(text="")
            self._time_label.config(text=f"Total time: {_fmt_time(elapsed)}")

            self.popup.geometry("600x220")
            btn_row = tk.Frame(self._frame, pady=6)
            btn_row.pack(fill=tk.X)
            tk.Button(btn_row, text="Open Vault",
                      command=on_open,
                      font=("Helvetica", 10),
                      padx=16, pady=6).pack(side=tk.RIGHT)
        except Exception as e:
            tracer.log_error(f"LoadingPopup show_done error: {e}")

    def destroy(self):
        if self._poll_id is not None:
            try:
                self.popup.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        try:
            self.popup.destroy()
        except Exception:
            pass

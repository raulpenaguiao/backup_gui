import os
import tkinter as tk
from tkinter import messagebox
import threading
import tools_library.drive_variables as drive_variables
from tools_library.dbs import initialize_vaults, get_saved_vaults
from tools_library.pigmy_hash import index_vault, save_pigmy_hash, load_pigmy_hash
from tools_library.file_tree import build_size_index
from tools_library.progress_tracker import ProgressTracker
from tools_library.app_icon import setup_icon
from widgets_library.vault_picker import VaultPicker
from widgets_library.main_window import MainWindow
from widgets_library.loading_popup import LoadingPopup
import tools_library.tracer as tracer


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Pigmy Backup Application")
        self.root.geometry("960x620")
        self.root.minsize(700, 460)
        self._view = None
        self._show_vault_picker()

    def _show_vault_picker(self):
        if self._view:
            self._view.destroy()
        self._view = VaultPicker(self.root, on_vault_open=self._open_vault)

    def _open_vault(self, vault_path):
        pigmy_hash_path = os.path.join(vault_path, drive_variables.pigmy_hash_file)
        has_hash = os.path.exists(pigmy_hash_path)
        progress_tracker = ProgressTracker(name="Loading vault", unit="files")
        if has_hash:
            progress_tracker.phase = "sizing"
        cancel_token = threading.Event()
        title = "Loading vault" if has_hash else "Loading index"
        loading = LoadingPopup(self.root, progress_tracker, cancel_token=cancel_token, title=title)

        def run():
            try:
                skipped = []
                if has_hash:
                    pigmyhash = load_pigmy_hash(vault_path)
                else:
                    pigmyhash, skipped = index_vault(vault_path, progress_tracker, cancel_token)
                    if pigmyhash is None:
                        self.root.after(0, lambda: self._on_cancelled(loading))
                        return
                    save_pigmy_hash(vault_path, pigmyhash)
                sizes, file_counts = build_size_index(vault_path, progress_tracker, cancel_token)
                if cancel_token.is_set():
                    self.root.after(0, lambda: self._on_cancelled(loading))
                    return
                self.root.after(0, lambda: self._on_ready(
                    loading, vault_path, pigmyhash, sizes, file_counts, skipped))
            except Exception as e:
                tracer.log(f"Error opening vault: {e}")
                self.root.after(0, loading.destroy)

        threading.Thread(target=run, daemon=True).start()

    def _reindex_vault(self, vault_path):
        progress_tracker = ProgressTracker(name="Indexing vault", unit="entries")
        cancel_token = threading.Event()
        loading = LoadingPopup(self.root, progress_tracker, cancel_token=cancel_token, title="Loading index")

        def run():
            try:
                pigmyhash, skipped = index_vault(vault_path, progress_tracker, cancel_token)
                if pigmyhash is None:
                    self.root.after(0, lambda: self._on_cancelled(loading))
                    return
                save_pigmy_hash(vault_path, pigmyhash)
                sizes, file_counts = build_size_index(vault_path, progress_tracker, cancel_token)
                if cancel_token.is_set():
                    self.root.after(0, lambda: self._on_cancelled(loading))
                    return
                self.root.after(0, lambda: self._on_ready(
                    loading, vault_path, pigmyhash, sizes, file_counts, skipped))
            except Exception as e:
                tracer.log(f"Error reindexing vault: {e}")
                self.root.after(0, loading.destroy)

        threading.Thread(target=run, daemon=True).start()

    def _on_cancelled(self, loading):
        loading.destroy()
        self._show_vault_picker()

    def _on_ready(self, loading, vault_path, pigmyhash, sizes, file_counts, skipped=None):
        loading.destroy()
        if self._view:
            self._view.destroy()
        self._view = MainWindow(
            self.root, vault_path, pigmyhash, sizes, file_counts,
            on_back=self._show_vault_picker,
            on_reindex=lambda: self._reindex_vault(vault_path),
        )
        if skipped:
            self._show_skipped_warning(skipped)

    def _show_skipped_warning(self, skipped):
        n = len(skipped)
        MAX_SHOWN = 20
        lines = []
        for path, err in skipped[:MAX_SHOWN]:
            lines.append(f"  {path}\n    → {err}")
        if n > MAX_SHOWN:
            lines.append(f"  … and {n - MAX_SHOWN} more (see log for full list)")

        msg = (
            f"{n} file(s) or folder(s) could not be read during indexing "
            f"and were skipped.\n\n"
            f"These items will NOT appear in duplicate comparisons, and their "
            f"parent folders are protected from deletion suggestions.\n\n"
            f"Skipped items:\n" + "\n".join(lines) +
            f"\n\nCheck the log (Open Logs button) for full details."
        )
        messagebox.showwarning("Indexing incomplete — some files skipped", msg,
                               parent=self.root)


def _check_log_size(root):
    from tools_library.tracer import log_folder_size, log_folder_path
    size = log_folder_size()
    limit = 100 * 1024 * 1024  # 100 MB
    if size < limit:
        return
    try:
        files = sorted(
            [e for e in os.scandir(log_folder_path)
             if e.is_file() and e.name.startswith("tracer_") and e.name.endswith(".log")],
            key=lambda e: e.name,
        )
    except FileNotFoundError:
        return
    n = len(files)
    if n < 2:
        return
    half = n // 2
    size_mb = size / (1024 * 1024)
    if messagebox.askyesno(
        "Log folder too large",
        f"The log folder is {size_mb:.0f} MB ({n} files).\n\n"
        f"Delete the {half} oldest log file(s) to free up space?",
        parent=root,
    ):
        for entry in files[:half]:
            try:
                os.remove(entry.path)
            except Exception:
                pass


def create_gui():
    drive_variables.vaults = get_saved_vaults()
    initialize_vaults()
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    setup_icon(root)
    App(root)
    root.after(500, lambda: _check_log_size(root))
    root.mainloop()


if __name__ == "__main__":
    create_gui()

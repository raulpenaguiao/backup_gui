import tools_library.tracer as tracer

class ProgressTracker:
    def __init__(self, name="Progress Tracker", unit="progress"):
        tracer.log(name + " - " + unit, trace_level=2)
        self.name = name
        self.unit = unit
        self.callbacks = {}
        self.loaded = False
        self.finished = False
        self.current_file = ""
        # BFS phase (before hashing starts)
        self.phase = "bfs"       # "bfs" | "hashing"
        self.bfs_progress = 0.0  # 0.0 -> 1.0 during BFS phase

    def start_progress_tracker(self, total_value):
        self.total_value = total_value
        self.current_value = 0
        self.current_file = ""
        self.loaded = True
        self._notify_subscribers()

    def set_current_value(self, current_value, current_file=None):
        self.current_value = current_value
        if current_file is not None:
            self.current_file = current_file
        if self.current_value >= self.total_value:
            self.finished = True
        self._notify_subscribers()

    def subscribe(self, callback, id):
        """Subscribe a callback function to be notified of progress changes."""
        if id not in self.callbacks:
            self.callbacks[id] = callback

    def unsubscribe(self, id):
        """Unsubscribe a callback function."""
        if id in self.callbacks:
            del self.callbacks[id]

    def _notify_subscribers(self):
        """Notify all subscribed callbacks."""
        if not self.loaded:
            return
        for callback in self.callbacks.values():
            callback()
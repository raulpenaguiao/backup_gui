import tools_library.tracer as tracer

class ProgressTracker:
    def __init__(self, name="Progress Tracker", unit="progress"):
        tracer.log(name + " - " + unit)
        self.name = name
        self.unit = unit
        self.callbacks = {} # List of callback functions
        self.loaded = False
        self.finished = False

    def start_progress_tracker(self, total_value):
        self.total_value = total_value
        self.current_value = 0
        self.loaded = True
        self._notify_subscribers()

    def set_current_value(self, current_value):
        self.current_value = current_value
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
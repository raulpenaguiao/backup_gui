PENDING = "PENDING"
IN_PROGRESS = "IN_PROGRESS"
DONE = "DONE"
ERROR = "ERROR"

#: Names of the six steps, in execution order.
STEP_NAMES = [
    "Main vault indexing",
    "External vault indexing",
    "Copies in EV detection",
    "Double files in EV",
    "Delete suggested files in EV",
    "Delete empty folders in EV",
]


class PipelineStep:
    def __init__(self, name, auto_continue=False):
        self.name = name
        self.status = PENDING
        self.auto_continue = auto_continue


class PipelineState:
    """Tracks the status of each step in the Prepare External Vault pipeline.

    Render rule for the UI: DONE -> checkmark (non-interactive), IN_PROGRESS ->
    hourglass + Cancel button, ERROR -> cross (non-interactive, pipeline halted —
    a Retry button must be used before Proceed becomes available again), head()
    -> arrow (no checkbox, Proceed runs it), every other PENDING step -> an
    interactive checkbox bound to auto_continue.
    """

    def __init__(self, step_names=None):
        self.steps = [PipelineStep(name) for name in (step_names or STEP_NAMES)]

    def head(self):
        """First step that is not DONE — the one Proceed acts on, or the one running."""
        for step in self.steps:
            if step.status != DONE:
                return step
        return None

    def get(self, name):
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def is_finished(self):
        return all(step.status == DONE for step in self.steps)

    def start(self, step):
        step.status = IN_PROGRESS

    def mark_done(self, step):
        """Mark step DONE and return the next step if it should auto-start, else None."""
        step.status = DONE
        nxt = self.head()
        if nxt is not None and nxt.auto_continue:
            return nxt
        return None

    def mark_cancelled(self, step):
        """Revert step to PENDING; it becomes head() again. The chain never auto-resumes."""
        step.status = PENDING

    def mark_error(self, step):
        """Mark step ERROR. It stays head() (so the UI can show exactly where things
        stopped) but the pipeline halts here — no auto-continue, Proceed is replaced
        by Retry until the user explicitly clears the error."""
        step.status = ERROR

    def retry_error(self, step):
        """Clear an ERROR status back to PENDING so the step can be attempted again."""
        if step.status == ERROR:
            step.status = PENDING

    def set_auto_continue(self, step, value):
        step.auto_continue = value

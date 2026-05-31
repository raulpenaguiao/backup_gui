import tkinter as tk

_DELAY_MS = 600
_PAD = 6


class Tooltip:
    """Show a small floating label when the mouse hovers over a widget."""

    def __init__(self, widget, text):
        self._widget = widget
        self._text = text
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event):
        self._cancel()
        self._after_id = self._widget.after(_DELAY_MS, self._show)

    def _on_leave(self, _event):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tip:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            self._tip, text=self._text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("Helvetica", 9), wraplength=280, padx=_PAD, pady=_PAD,
        )
        lbl.pack()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None

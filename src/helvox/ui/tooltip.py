from __future__ import annotations

import tkinter as tk


def add_tooltip(widget: tk.Misc, text: str, delay_ms: int = 450) -> None:
    """Show a small tooltip on hover. Works with any Tk widget (including Canvas)."""
    tip: list[tk.Toplevel | None] = [None]
    after_id: list[str | None] = [None]

    def destroy_tip() -> None:
        if after_id[0] is not None:
            try:
                widget.after_cancel(after_id[0])
            except tk.TclError:
                pass
            after_id[0] = None
        if tip[0] is not None:
            try:
                tip[0].destroy()
            except tk.TclError:
                pass
            tip[0] = None

    def show_tip() -> None:
        after_id[0] = None
        if not text.strip():
            return
        try:
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 4
        except tk.TclError:
            return
        tw = tk.Toplevel(widget)
        tip[0] = tw
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        label = tk.Label(
            tw,
            text=text,
            justify="left",
            background="#ffffe0",
            foreground="#222",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9),
            padx=6,
            pady=4,
        )
        label.pack()
        tw.update_idletasks()
        try:
            sw = tw.winfo_screenwidth()
            sh = tw.winfo_screenheight()
            w = tw.winfo_width()
            h = tw.winfo_height()
            if x + w > sw - 8:
                x = max(0, sw - w - 8)
            if y + h > sh - 8:
                y = widget.winfo_rooty() - h - 4
        except tk.TclError:
            pass
        tw.geometry(f"+{x}+{y}")

    def on_enter(_event: object) -> None:
        destroy_tip()
        after_id[0] = widget.after(delay_ms, show_tip)

    def on_leave(_event: object) -> None:
        destroy_tip()

    widget.bind("<Enter>", on_enter, add="+")
    widget.bind("<Leave>", on_leave, add="+")

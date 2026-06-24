import tkinter as tk
from typing import Optional


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text="",
        command=None,
        bg_color="#000000",
        fg_color="#FFFFFF",
        width=150,
        height=50,
        corner_radius=20,
        dot=False,
        font=None,
        image: Optional[tk.PhotoImage] = None,
    ):
        tk.Canvas.__init__(
            self,
            parent,
            width=width,
            height=height,
            bg="#f0f0f0",
            highlightthickness=0,
        )

        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.corner_radius = corner_radius
        self.text = text
        self.dot = dot
        self.state = "normal"
        self.label_font = (
            font if font is not None else ("Arial", 10, "bold")
        )
        self._photo_image: Optional[tk.PhotoImage] = image

        # Draw the button
        self.draw_button()

        # Bind click event
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def draw_button(self, hover=False):
        self.delete("all")

        # Slightly lighter color on hover
        if self.state == "disabled":
            current_bg = "#C7C7C7"
            current_fg = "#7A7A7A"
        else:
            current_bg = self._adjust_color(self.bg_color, 30) if hover else self.bg_color
            current_fg = self.fg_color

        # Draw rounded rectangle
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        radius = self.corner_radius

        # Create rounded rectangle using polygon
        points = [
            radius,
            0,
            width - radius,
            0,
            width,
            0,
            width,
            radius,
            width,
            height - radius,
            width,
            height,
            width - radius,
            height,
            radius,
            height,
            0,
            height,
            0,
            height - radius,
            0,
            radius,
            0,
            0,
        ]

        self.create_polygon(points, fill=current_bg, smooth=True, outline=current_bg)

        # Draw red dot
        if self.dot:
            dot_x = width // 2 - 20
            dot_y = height // 2
            self.create_oval(
                dot_x - 5,
                dot_y - 5,
                dot_x + 5,
                dot_y + 5,
                fill="#8B0000",
                outline="#8B0000",
            )

        # Icon (centered); keep a reference so Tk does not GC the PhotoImage
        if self._photo_image is not None:
            self.create_image(
                width // 2,
                height // 2,
                image=self._photo_image,
            )
        elif self.text:
            text_x = width // 2 + 5 if self.dot else width // 2
            self.create_text(
                text_x,
                height // 2,
                text=self.text,
                fill=current_fg,
                font=self.label_font,
            )

    def _adjust_color(self, color, amount):
        """Lighten a hex color by amount"""
        color = color.lstrip("#")
        rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, c + amount) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _on_click(self, event):
        if self.state == "disabled":
            return
        if self.command:
            self.command()

    def _on_enter(self, event):
        if self.state == "disabled":
            return
        self.draw_button(hover=True)

    def _on_leave(self, event):
        self.draw_button(hover=False)

    def update_button(self, **kwargs):
        """Update button properties and redraw"""
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "bg_color" in kwargs:
            self.bg_color = kwargs["bg_color"]
        if "fg_color" in kwargs:
            self.fg_color = kwargs["fg_color"]
        if "dot" in kwargs:
            self.dot = kwargs["dot"]
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "font" in kwargs:
            self.label_font = kwargs["font"]
        if "image" in kwargs:
            self._photo_image = kwargs["image"]

        # Redraw the button with new settings
        self.draw_button()

    def set_state(self, state: str) -> None:
        self.update_button(state=state)

    config = update_button
    configure = update_button

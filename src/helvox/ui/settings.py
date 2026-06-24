import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from helvox.ui.tooltip import add_tooltip
from helvox.utils.config_paths import portable_config_file, user_config_file
from helvox.utils.data import validate_samples_for_dialect
from helvox.utils.platform import app_font, recordings_dir
from helvox.utils.recorder import Recorder


class SettingsDialog:
    def __init__(self, parent: tk.Tk, recorder: Recorder) -> None:
        self.recorder = recorder
        self.result = None

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("650x580")
        self.dialog.minsize(650, 580)
        self.dialog.resizable(True, True)

        self.dialog.transient(parent)

        # Set app icon
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app.png"
        if icon_path.exists():
            icon = tk.PhotoImage(file=icon_path)
            self.dialog.iconphoto(False, icon)

        # Configure style
        self.setup_styles()
        self.setup_ui()

        # Center after content exists; grab only once the window is viewable
        self.center_dialog(parent)
        self.dialog.update_idletasks()
        self.dialog.wait_visibility()
        self.dialog.grab_set()

        # Handle window close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Bind Enter and Escape keys
        self.dialog.bind("<Return>", lambda e: self.on_ok())
        self.dialog.bind("<Escape>", lambda e: self.on_cancel())

    def center_dialog(self, parent: tk.Tk) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        x = (
            parent.winfo_x()
            + (parent.winfo_width() // 2)
            - (self.dialog.winfo_width() // 2)
        )
        y = (
            parent.winfo_y()
            + (parent.winfo_height() // 2)
            - (self.dialog.winfo_height() // 2)
        )
        self.dialog.geometry(f"+{x}+{y}")

    def setup_styles(self) -> None:
        """Configure custom styles for better appearance."""
        style = ttk.Style()

        # Custom styles
        style.configure("Title.TLabel", font=app_font(8))
        style.configure("Info.TLabel", font=app_font(9), foreground="#666")
        style.configure("TLabelframe.Label", font=app_font(9, bold=True))
        style.configure("TLabelframe", padding=15)

        # Button styles
        style.configure("Accent.TButton", font=app_font(9, bold=True))

    def setup_ui(self) -> None:
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights for responsiveness
        self.dialog.rowconfigure(0, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Allow spacing before buttons
        main_frame.columnconfigure(0, weight=1)

        # Tabs
        tab_control = ttk.Notebook(main_frame)
        tab_speaker = ttk.Frame(tab_control)
        tab_data = ttk.Frame(tab_control)
        tab_audio = ttk.Frame(tab_control)

        tab_control.add(tab_speaker, text="Speaker")
        tab_control.add(tab_data, text="Data")
        tab_control.add(tab_audio, text="Audio")

        tab_control.grid(row=0, column=0, sticky="ew")

        # Speaker Settings
        speaker_frame = ttk.LabelFrame(
            tab_speaker, text="Speaker Configuration", padding="15"
        )
        speaker_frame.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        speaker_frame.columnconfigure(1, weight=1)

        # Speaker ID
        ttk.Label(speaker_frame, text="Speaker ID:", style="Title.TLabel").grid(
            column=0, row=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.speaker_var = tk.StringVar(value=self.recorder.speaker_id)
        self.speaker_input = ttk.Entry(
            speaker_frame, textvariable=self.speaker_var, font=app_font(9)
        )
        self.speaker_input.grid(row=1, column=0, padx=(0, 5), pady=8, sticky="ew")

        # Dialect
        ttk.Label(speaker_frame, text="Dialect:", style="Title.TLabel").grid(
            column=1, row=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.dialect_var = tk.StringVar(value=self.recorder.speaker_dialect)
        self.speaker_dialect = ttk.Combobox(
            speaker_frame,
            textvariable=self.dialect_var,
            state="readonly",
            font=app_font(9),
            width=30,
        )
        self.speaker_dialect["values"] = (
            "AG",
            "BE",
            "BS",
            "GR",
            "LU",
            "SG",
            "VS",
            "ZH",
        )
        self.speaker_dialect.grid(row=1, column=1, padx=(0, 5), pady=8, sticky="w")

        # Input File Selection
        file_frame = ttk.LabelFrame(tab_data, text="Input File", padding="15")
        file_frame.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        file_frame.columnconfigure(0, weight=1)

        # Folder path display
        file_display_frame = ttk.Frame(file_frame)
        file_display_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        file_display_frame.columnconfigure(0, weight=1)

        self.file_var = tk.StringVar(value=str(self.recorder.input_file))
        self.file_input = ttk.Entry(
            file_display_frame,
            textvariable=self.file_var,
            font=app_font(9),
            width=60,
        )
        self.file_input.grid(row=0, column=0, sticky="ew")

        # Browse button
        self.browse_file_btn = ttk.Button(
            file_frame, text="Browse...", command=self.select_file, width=12
        )
        self.browse_file_btn.grid(row=0, column=1, pady=(0, 0), sticky="e")

        # Info label
        info_label = ttk.Label(
            file_frame,
            text="Select the file where the text data is stored (JSON)",
            style="Info.TLabel",
        )
        info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Output / recordings folder — only shown/editable in non-portable mode
        rec_frame = ttk.LabelFrame(tab_data, text="Output folder (recordings)", padding="15")
        rec_frame.grid(row=1, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        rec_frame.columnconfigure(0, weight=1)

        self.folder_var = tk.StringVar(value=str(self.recorder.output_folder))
        self.folder_input = ttk.Entry(
            rec_frame,
            textvariable=self.folder_var,
            font=app_font(9),
            width=60,
        )
        self.folder_input.grid(row=0, column=0, sticky="ew")

        self.browse_out_btn = ttk.Button(
            rec_frame, text="Browse...", command=self.select_output_folder, width=12
        )
        self.browse_out_btn.grid(row=0, column=1, pady=(0, 0), sticky="e")

        self.folder_info_label = ttk.Label(
            rec_frame,
            text="",
            style="Info.TLabel",
            wraplength=560,
        )
        self.folder_info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Portable mode
        settings_store_frame = ttk.LabelFrame(
            tab_data, text="Portable mode", padding="15"
        )
        settings_store_frame.grid(row=2, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        settings_store_frame.columnconfigure(0, weight=1)

        self.config_portable_var = tk.BooleanVar(value=self.recorder.config_portable)
        portable_check = ttk.Checkbutton(
            settings_store_frame,
            text="Portable — store config and recordings in helvox/ next to the app",
            variable=self.config_portable_var,
            command=self.on_config_portable_toggle,
        )
        portable_check.grid(row=0, column=0, sticky="w")

        self.config_path_label = ttk.Label(
            settings_store_frame, text="", style="Info.TLabel", wraplength=560
        )
        self.config_path_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        options_frame = ttk.LabelFrame(tab_data, text="Options", padding="15")
        options_frame.grid(row=3, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        options_frame.columnconfigure(0, weight=1)

        self.enable_skip_var = tk.BooleanVar(value=self.recorder.enable_skip)
        enable_skip_check = ttk.Checkbutton(
            options_frame,
            text="Enable Skip button",
            variable=self.enable_skip_var,
        )
        enable_skip_check.grid(row=0, column=0, sticky="w")

        # Audio Device Selection
        device_frame = ttk.LabelFrame(
            tab_audio, text="Audio Input Device", padding="15"
        )
        device_frame.grid(row=2, column=0, sticky="ew", padx=(10, 10), pady=(10, 0))
        device_frame.columnconfigure(0, weight=1)

        # Device selection row
        device_row = ttk.Frame(device_frame)
        device_row.grid(row=0, column=0, sticky="ew")
        device_row.columnconfigure(0, weight=1)

        self.device_var = tk.StringVar(value=self.recorder.selected_device or "")
        self.device_combo = ttk.Combobox(
            device_row,
            textvariable=self.device_var,
            state="readonly",
            font=app_font(9),
        )
        self.device_combo.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")

        refresh_btn = ttk.Button(
            device_row, text="Refresh", command=self.refresh_devices, width=12
        )
        refresh_btn.grid(row=0, column=1, pady=5)

        # Info label
        info_label = ttk.Label(
            device_frame,
            text="Select the microphone or audio input device to use for recording",
            style="Info.TLabel",
        )
        info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Populate devices
        self.refresh_devices()

        # Spacer
        ttk.Frame(main_frame).grid(row=3, column=0, sticky="nsew")

        # Button frame with separator
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=4, column=0, sticky="ew", pady=(0, 15)
        )

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, pady=(0, 0))

        # Buttons with improved styling
        cancel_btn = ttk.Button(
            button_frame, text="Cancel", command=self.on_cancel, width=15
        )
        cancel_btn.grid(row=0, column=0, padx=5)

        ok_btn = ttk.Button(
            button_frame,
            text="OK",
            command=self.on_ok,
            style="Accent.TButton",
            width=15,
        )
        ok_btn.grid(row=0, column=1, padx=5)

        # Set focus to OK button
        ok_btn.focus_set()

        add_tooltip(
            self.speaker_input,
            "Your speaker ID (e.g. name, short name, nickname, or whatever).",
        )
        add_tooltip(
            self.speaker_dialect,
            "Your spoken dialect.",
        )
        add_tooltip(
            self.file_input,
            "Input JSON with the lines to record.",
        )
        add_tooltip(self.browse_file_btn, "Choose the input JSON file.")
        add_tooltip(
            self.folder_input,
            "Where FLAC and output.json are stored (default: helvox next to the app).",
        )
        add_tooltip(self.browse_out_btn, "Choose output folder.")
        add_tooltip(
            portable_check,
            "Checked: config in helvox next to the exe, with portable input/output paths when possible. Unchecked: OS user config directory.",
        )
        add_tooltip(
            enable_skip_check,
            "Show the Skip button in the main window.",
        )
        add_tooltip(
            self.device_combo,
            "Audio input used for recording.",
        )
        add_tooltip(refresh_btn, "Reload audio devices.")
        add_tooltip(cancel_btn, "Close without saving changes.")
        add_tooltip(ok_btn, "Save and apply these settings.")

        self.on_config_portable_toggle()

    def on_config_portable_toggle(self) -> None:
        is_portable = self.config_portable_var.get()

        if is_portable:
            # Lock output folder to helvox/ next to the app.
            base = recordings_dir()
            self.folder_var.set(str(base))
            self.folder_input.configure(state="disabled")
            self.browse_out_btn.configure(state="disabled")
            self.folder_info_label.configure(
                text=f"Locked to: {base}  (recordings go in <speaker>/ inside)"
            )
            self.config_path_label.configure(
                text=f"Config:  {portable_config_file()}\n"
                     f"Recordings:  {base / '<speaker_id>'}"
            )
        else:
            self.folder_input.configure(state="normal")
            self.browse_out_btn.configure(state="normal")
            self.folder_info_label.configure(text="")
            self.config_path_label.configure(
                text=f"Config will be saved to: {user_config_file()}"
            )

        self.file_input.configure(state="normal")
        self.browse_file_btn.configure(state="normal")

    def select_output_folder(self) -> None:
        raw = self.folder_var.get().strip() or str(recordings_dir())
        initial = Path(raw)
        base = initial if initial.is_dir() else initial.parent
        while not base.exists() and base != base.parent:
            base = base.parent
        initialdir = str(base if base.exists() else Path.home())
        folder = filedialog.askdirectory(
            title="Select Output Folder", initialdir=initialdir
        )
        if folder:
            self.folder_var.set(str(Path(folder)))

    def select_file(self) -> None:
        current = Path(self.file_var.get().strip())
        if current.is_file():
            initialdir = str(current.parent)
        elif current.is_dir():
            initialdir = str(current)
        else:
            initialdir = str(Path.home())

        file = filedialog.askopenfilename(
            title="Select Input File",
            initialdir=initialdir,
            filetypes=[("JSON files", "*.json")],
        )

        if file:
            self.file_var.set(str(Path(file)))

    def refresh_devices(self) -> None:
        """Refresh available audio devices."""
        self.recorder.refresh_audio_devices()
        device_names = list(self.recorder.device_map.keys())
        self.device_combo["values"] = device_names

        # Set default device if none selected
        if device_names:
            current = self.device_var.get()
            if not current or current not in device_names:
                self.device_var.set(device_names[0])
        else:
            self.device_var.set("")

    def validate_inputs(self) -> bool:
        """Validate user inputs before saving."""
        speaker_id = self.speaker_var.get().strip()
        if not speaker_id:
            messagebox.showwarning(
                "Invalid Input", "Please enter a Speaker ID.", parent=self.dialog
            )
            self.speaker_input.focus_set()
            return False

        out = Path(self.folder_var.get().strip() or str(recordings_dir()))
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showwarning(
                "Output folder",
                f"Cannot create or use this folder:\n{e}",
                parent=self.dialog,
            )
            return False

        if not self.device_var.get():
            messagebox.showwarning(
                "No Device Selected",
                "Please select an audio input device.",
                parent=self.dialog,
            )
            self.device_combo.focus_set()
            return False

        input_path = Path(self.file_var.get())
        if not input_path.exists():
            messagebox.showwarning(
                "Invalid Input File",
                "The selected input JSON file does not exist.",
                parent=self.dialog,
            )
            return False

        try:
            with open(input_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showwarning(
                "Invalid Input File",
                f"Could not read JSON: {e}",
                parent=self.dialog,
            )
            return False

        if not isinstance(data, list):
            messagebox.showwarning(
                "Invalid Input File",
                "The input file must be a JSON array of objects.",
                parent=self.dialog,
            )
            return False

        dialect = self.dialect_var.get()
        err = validate_samples_for_dialect(data, dialect)
        if err:
            messagebox.showwarning("Invalid Input File", err, parent=self.dialog)
            return False

        return True

    def on_ok(self) -> None:
        """Handle OK button click."""
        if not self.validate_inputs():
            return

        is_portable = self.config_portable_var.get()
        # In portable mode the output folder is always recordings_dir() — locked.
        out_folder = (
            str(recordings_dir())
            if is_portable
            else self.folder_var.get().strip() or str(recordings_dir())
        )
        self.result = {
            "speaker_id": self.speaker_var.get().strip(),
            "speaker_dialect": self.dialect_var.get(),
            "output_folder": out_folder,
            "config_portable": is_portable,
            "device": self.device_var.get(),
            "enable_skip": self.enable_skip_var.get(),
            "input_file": self.file_var.get(),
        }
        self.dialog.destroy()

    def on_cancel(self) -> None:
        """Handle Cancel button click."""
        self.result = None
        self.dialog.destroy()

    def show(self) -> dict | None:
        """Show dialog and return result."""
        self.dialog.wait_window()
        return self.result

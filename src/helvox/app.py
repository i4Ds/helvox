import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from helvox.ui.auto_resize_text import AutoResizingText
from helvox.ui.button import RoundedButton
from helvox.ui.rounded_canvas import RoundedCanvas
from helvox.ui.settings import SettingsDialog
from helvox.ui.tooltip import add_tooltip
from helvox.utils.config_paths import (
    has_any_config_file,
    portable_config_file,
    prune_other_config,
    resolve_startup_settings_path,
    user_config_file,
)
from helvox.utils.platform import app_font, recordings_dir
from helvox.utils.recorder import Recorder


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        self.recorder = Recorder(
            output_folder=recordings_dir(), sample_rate=48000, channels=1
        )

        self.settings_path, default_portable = resolve_startup_settings_path()
        self.recorder.load_settings(
            self.settings_path,
            default_config_portable=default_portable,
        )

        self.setup_window()
        self.setup_ui()
        self.current_id: str | None = None

        if self._has_saved_config():
            self._refresh_ui_after_session_change()
        else:
            self.show_settings()

    def setup_window(self) -> None:
        self.root.title("Helvox")
        self.root.geometry("800x600")

        # Set minimum window size
        self.root.minsize(900, 700)

        # Set app icon
        icon_path = Path(__file__).parent / "resources" / "icons" / "app.png"
        if icon_path.exists():
            icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(False, icon)

        # Bind configure event
        self.root.bind("<Configure>", self.configure_handler)

    @staticmethod
    def _bind_label_wrap(label: ttk.Label, padding: int = 10) -> None:
        label.bind(
            "<Configure>",
            lambda e: e.widget.configure(wraplength=e.width - padding),
        )

    def _recorder_identity(self) -> tuple[str, str, str, str]:
        return (
            str(self.recorder.output_folder),
            self.recorder.speaker_id,
            self.recorder.input_file,
            self.recorder.speaker_dialect,
        )

    def setup_ui(self) -> None:
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nswe")

        # Configure grid weights for responsiveness
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Allow spacing before buttons
        main_frame.columnconfigure(0, weight=1)

        # Settings button at the top
        settings_frame = ttk.Frame(main_frame)
        settings_frame.grid(row=0, column=0, sticky="we", pady=(0, 10))
        settings_frame.columnconfigure(0, weight=1)

        settings_btn = RoundedButton(
            settings_frame,
            text="Settings",
            command=self.show_settings,
            bg_color="#E6E6E6",
            fg_color="#363636",
            width=120,
            height=40,
            corner_radius=20,
            dot=False,
        )
        settings_btn.grid(row=0, column=0, padx=5, sticky="e")
        add_tooltip(settings_btn, "Open app settings.")

        # Text frame
        text_frame = ttk.LabelFrame(main_frame, text="Text", padding="5")
        text_frame.grid(row=1, column=0, sticky="we", pady=5, padx=5)
        text_frame.columnconfigure(0, weight=1)

        de_text_frame = ttk.Frame(text_frame)
        de_text_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        de_text_frame.columnconfigure(0, weight=1)

        ttk.Label(de_text_frame, text="DE:").grid(row=0, column=0, sticky=tk.W, padx=0)

        self.de_text_var = tk.StringVar(value="")
        de_text_label = ttk.Label(
            de_text_frame,
            textvariable=self.de_text_var,
            relief="sunken",
            background="white",
            foreground="#8A8A8A",
            font=app_font(12),
            padding=5,
            anchor="w",
        )
        de_text_label.grid(row=1, column=0, sticky="ew")
        self._bind_label_wrap(de_text_label)

        # CH
        ch_text_frame = ttk.Frame(text_frame)
        ch_text_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ch_text_frame.columnconfigure(0, weight=1)

        ttk.Label(ch_text_frame, text="CH (Suggestion):").grid(
            row=0, column=0, sticky=tk.W, padx=0
        )

        self.ch_text_var = tk.StringVar(value="")
        ch_text_label = ttk.Label(
            ch_text_frame,
            textvariable=self.ch_text_var,
            relief="sunken",
            background="white",
            foreground="#8A8A8A",
            font=app_font(12),
            padding=5,
            anchor="w",
        )
        ch_text_label.grid(row=1, column=0, sticky="ew")
        self._bind_label_wrap(ch_text_label)

        # CH (Editable)
        ch_text_edit_frame = ttk.Frame(text_frame)
        ch_text_edit_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ch_text_edit_frame.columnconfigure(0, weight=1)

        ttk.Label(ch_text_edit_frame, text="CH (Edit):").grid(
            row=0, column=0, sticky=tk.W, padx=0
        )

        self.ch_text_edit_var = tk.StringVar(value="")
        self.speaker_input = AutoResizingText(
            ch_text_edit_frame,
            textvariable=self.ch_text_edit_var,
            font=app_font(12),
            background="white",
            foreground="#000000",
            wrap="word",
            padx=5,
            pady=5,
            min_height=2,
            max_height=8,
        )
        self.speaker_input.grid(row=1, column=0, padx=(0, 0), pady=8, sticky="ew")

        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=2, column=0, sticky="we", pady=(0, 5), padx=5)
        progress_frame.columnconfigure(0, weight=1)

        self.progress_text = tk.StringVar(value="Progress: 0 / 0")
        ttk.Label(progress_frame, textvariable=self.progress_text).grid(
            row=0, column=0, sticky=tk.W
        )

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate"
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        # Recording frame
        recording_frame = ttk.LabelFrame(main_frame, text="Recording", padding="5")
        recording_frame.grid(row=3, column=0, sticky="we", pady=5, padx=5)

        # Configure recording frame columns - column 2 expands
        recording_frame.columnconfigure(2, weight=1)

        self.level_canvas = tk.Canvas(recording_frame, width=40, height=160, bg="black")
        self.level_canvas.grid(row=0, rowspan=4, column=0, sticky="ns", padx=5, pady=5)

        self.level_text = tk.StringVar(value="Level: 0 dB")
        ttk.Label(recording_frame, textvariable=self.level_text).grid(
            row=4, column=0, sticky=tk.W, padx=5
        )

        self.waveform_canvas_full = RoundedCanvas(
            recording_frame, height=50, bg="black", corner_radius=20
        )
        self.waveform_canvas_full.grid(row=0, column=2, sticky="we", padx=5, pady=5)

        self.play_btn_full = RoundedButton(
            recording_frame,
            text="Preview",
            command=self.recorder.play_audio_data_full_audio,
            bg_color="#10A560",
            fg_color="#FFFFFF",
            width=120,
            height=50,
            corner_radius=20,
        )
        self.play_btn_full.grid(row=0, column=3, padx=5)
        add_tooltip(self.play_btn_full, "Play the full take.")

        self.duration_text_full = tk.StringVar(value="Full | Duration: 0.0 seconds")
        ttk.Label(recording_frame, textvariable=self.duration_text_full).grid(
            row=1, column=2, sticky=tk.W, padx=5
        )

        self.waveform_canvas_trimmed = RoundedCanvas(
            recording_frame, height=50, bg="black", corner_radius=20
        )
        self.waveform_canvas_trimmed.grid(row=2, column=2, sticky="we", padx=5, pady=5)

        self.play_btn_trimmed = RoundedButton(
            recording_frame,
            text="Preview",
            command=self.recorder.play_audio_data_trimmed_audio,
            bg_color="#10A560",
            fg_color="#FFFFFF",
            width=120,
            height=50,
            corner_radius=20,
        )
        self.play_btn_trimmed.grid(row=2, column=3, padx=5)
        add_tooltip(self.play_btn_trimmed, "Play the trimmed take.")

        self.duration_text_trimmed = tk.StringVar(
            value="Trimmed | Duration: 0.0 seconds"
        )
        ttk.Label(recording_frame, textvariable=self.duration_text_trimmed).grid(
            row=3, column=2, sticky=tk.W, padx=5
        )

        # Thumbs + REC: PNG icons (_w = inactive, _b = active); only one active at a time
        record_controls = ttk.Frame(recording_frame)
        record_controls.grid(row=4, column=1, columnspan=3, sticky="e", padx=5, pady=5)
        self._load_thumb_icon_photos()

        self.thumb_up_btn = RoundedButton(
            record_controls,
            text="",
            command=self._select_thumb_up,
            bg_color="#2E7D4A",
            fg_color="#FFFFFF",
            width=self._thumb_btn_w,
            height=self._thumb_btn_h,
            corner_radius=20,
            dot=False,
            image=self._thumb_photo_up_b,
        )
        self.thumb_up_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.thumb_down_btn = RoundedButton(
            record_controls,
            text="",
            command=self._select_thumb_down,
            bg_color="#E6E6E6",
            fg_color="#363636",
            width=self._thumb_btn_w,
            height=self._thumb_btn_h,
            corner_radius=20,
            dot=False,
            image=self._thumb_photo_down_w,
        )
        self.thumb_down_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.record_btn = RoundedButton(
            record_controls,
            text="REC",
            command=self.toggle_recording,
            bg_color="#000000",
            fg_color="#FFFFFF",
            width=120,
            height=40,
            corner_radius=20,
            dot=True,
        )
        self.record_btn.pack(side=tk.LEFT)

        self._thumb_choice = "up"
        add_tooltip(
            self.thumb_up_btn,
            "Recording and text are OK.",
        )
        add_tooltip(
            self.thumb_down_btn,
            "Recording or text is wrong.",
        )
        add_tooltip(self.record_btn, "Start or stop recording.")

        # Spacer
        ttk.Frame(main_frame).grid(row=4, column=0, sticky="nsew")

        # Button frame with separator
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=5, column=0, columnspan=1, sticky="ew", pady=(0, 15)
        )

        # Controls: duration (left) | Previous, [Skip], Save & Next (right)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=6, column=0, sticky="we", pady=(0, 0))
        control_frame.columnconfigure(0, weight=1)

        self.duration_text = tk.StringVar(value="Total Duration: 0s")
        ttk.Label(control_frame, textvariable=self.duration_text).grid(
            row=0, column=0, sticky=tk.W, padx=5
        )

        nav_btn_frame = ttk.Frame(control_frame)
        nav_btn_frame.grid(row=0, column=1, sticky="e")

        self.prev_btn = RoundedButton(
            nav_btn_frame,
            text="Previous",
            command=self.go_previous,
            bg_color="#E6E6E6",
            fg_color="#363636",
            width=120,
            height=40,
            corner_radius=20,
            dot=False,
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.skip_btn = RoundedButton(
            nav_btn_frame,
            text="Skip",
            command=self.skip,
            bg_color="#E6E6E6",
            fg_color="#363636",
            width=120,
            height=40,
            corner_radius=20,
            dot=False,
        )
        if self.recorder.enable_skip:
            self.skip_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = RoundedButton(
            nav_btn_frame,
            text="Save & Next",
            command=self.save,
            bg_color="#3B32B3",
            fg_color="#F5F5F5",
            width=120,
            height=40,
            corner_radius=20,
            dot=False,
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        add_tooltip(
            self.prev_btn,
            "Go to the previous line.",
        )
        add_tooltip(
            self.skip_btn,
            "Skip this line.",
        )
        add_tooltip(
            self.save_btn,
            "Save and go to the next line.",
        )

    @staticmethod
    def _fit_photo(
        path: Path,
        *,
        max_width: int | None = None,
        max_height: int | None = 40,
    ) -> tk.PhotoImage:
        """Scale down a PNG to fit within the requested bounds."""
        photo = tk.PhotoImage(file=str(path))
        width = photo.width()
        height = photo.height()

        step_x = 1
        step_y = 1
        if max_width is not None and width > max_width:
            step_x = max(2, (width + max_width - 1) // max_width)
        if max_height is not None and height > max_height:
            step_y = max(2, (height + max_height - 1) // max_height)

        if step_x == 1 and step_y == 1:
            return photo
        return photo.subsample(step_x, step_y)

    def _load_thumb_icon_photos(self) -> None:
        icon_dir = Path(__file__).resolve().parent / "resources" / "icons"
        self._thumb_photo_up_w = self._fit_photo(
            icon_dir / "thumbs_up_w.png", max_width=20, max_height=20
        )
        self._thumb_photo_up_b = self._fit_photo(
            icon_dir / "thumbs_up_b.png", max_width=20, max_height=20
        )
        self._thumb_photo_down_w = self._fit_photo(
            icon_dir / "thumbs_down_w.png", max_width=20, max_height=20
        )
        self._thumb_photo_down_b = self._fit_photo(
            icon_dir / "thumbs_down_b.png", max_width=20, max_height=20
        )
        self._thumb_btn_w = 40
        self._thumb_btn_h = 40

    def _persist_settings(self) -> None:
        self.settings_path = (
            portable_config_file()
            if self.recorder.config_portable
            else user_config_file()
        ).resolve()
        self.recorder.save_settings(self.settings_path)
        prune_other_config(self.settings_path)

    def _apply_settings_result(self, result: dict) -> None:
        before = self._recorder_identity()

        self.recorder.config_portable = result["config_portable"]
        self.recorder.update_output_folder(result["output_folder"])
        self.settings_path = (
            portable_config_file()
            if self.recorder.config_portable
            else user_config_file()
        )

        self.recorder.update_selected_device(result["device"])
        self.recorder.speaker_id = result["speaker_id"]
        self.recorder.speaker_dialect = result["speaker_dialect"]
        self.recorder.enable_skip = result.get("enable_skip", False)
        self.recorder.input_file = result["input_file"]

        speaker_dir = Path(result["output_folder"]) / result["speaker_id"]
        self.recorder.output_file = speaker_dir / "output.json"
        self.recorder.skipped_file = speaker_dir / "skipped.txt"

        if before != self._recorder_identity():
            self.recorder.load_data()
            self.current_id = None
            self.recorder.current_track = None

    def show_settings(self) -> None:
        dialog = SettingsDialog(self.root, self.recorder)
        result = dialog.show()

        if result:
            self._apply_settings_result(result)
            try:
                self._persist_settings()
            except OSError as exc:
                messagebox.showerror(
                    "Could not save settings",
                    f"Failed to write config file:\n{exc}\n\n"
                    "On macOS, try moving the app out of the DMG to a local folder first.",
                    parent=self.root,
                )

        self._refresh_ui_after_session_change()

    def _has_saved_config(self) -> bool:
        return has_any_config_file()

    def _refresh_ui_after_session_change(self) -> None:
        self.recorder.refresh_audio_devices()
        restored = False
        if self.recorder.current_track:
            tid = str(self.recorder.current_track)
            if tid in self.recorder.input_index:
                self.current_id = tid
                self.recorder.set_current_track_queue(tid)
                self._sync_ui_for_current_sample()
                restored = True
            else:
                self.recorder.current_track = None
        if not restored and self.current_id is None:
            self.load_next_sample()
        elif not restored:
            self.update_navigation_controls()

        self.recorder.stop_monitoring()
        self.start_monitoring()
        self.update_duration()

    def update_duration(self) -> None:
        total_seconds = self.recorder.total_duration
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - int(total_seconds)) * 100)

        self.duration_text.set(
            f"Total Duration: {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        )

    def update_level_meter(self) -> None:
        level = self.recorder.get_current_level()

        # Update level text
        self.level_text.set(f"Level: {level:.1f} dB")

        # Get canvas dimensions
        width = self.level_canvas.winfo_width()
        height = self.level_canvas.winfo_height()

        if height > 1:  # Only draw if canvas is visible
            # Clear canvas
            self.level_canvas.delete("all")

            # Convert dB to normalized value (0-1)
            db_min = -60
            db_max = 0
            normalized = max(0, min(1, (level - db_min) / (db_max - db_min)))

            # Number of segments
            num_segments = 20
            segment_height = height / num_segments
            segment_spacing = 2  # Pixels between segments

            # Draw segments from bottom to top
            for i in range(num_segments):
                segment_normalized = i / num_segments
                segment_y = height - (i + 1) * segment_height

                # Determine if segment should be lit
                is_lit = normalized >= segment_normalized

                # Determine color based on position
                if i >= int(num_segments * 0.9):  # Top 10% red
                    color = "red" if is_lit else "darkred"
                elif i >= int(num_segments * 0.7):  # Next 20% yellow
                    color = "yellow" if is_lit else "darkgoldenrod4"
                else:  # Bottom 70% green
                    color = "green2" if is_lit else "darkgreen"

                # Draw segment
                self.level_canvas.create_rectangle(
                    2,  # Left margin
                    segment_y + segment_spacing / 2,
                    width - 2,  # Right margin
                    segment_y + segment_height - segment_spacing / 2,
                    fill=color,
                    outline="",
                )

            # Draw tick marks and dB labels every 10 dB
            for i in range(0, 7):
                db_value = db_min + (i * 10)
                y_pos = height * (1 - (db_value - db_min) / (db_max - db_min))
                # Tick mark
                self.level_canvas.create_line(0, y_pos, 5, y_pos, fill="gray", width=1)
                # dB label
                self.level_canvas.create_text(
                    width + 15,
                    y_pos,
                    text=f"{db_value}",
                    fill="white",
                    anchor="w",
                    font=("Arial", 7),
                )

        # Schedule next update
        self.root.after(50, self.update_level_meter)

    def start_monitoring(self) -> None:
        if self.recorder.selected_device:
            self.recorder.start_monitoring()
            self.update_level_meter()

    def toggle_recording(self) -> None:
        if not self.recorder.recording:
            self.recorder.start_recording()
            self.clear_waveform_canvas()
            self.record_btn.config(
                text="Stop Recording", bg_color="#8B0000", dot=False
            )  # Dark red
        else:
            self.recorder.stop_recording()
            self.record_btn.config(text="REC", bg_color="#000000", dot=True)  # Black
            self.update_waveform()

    def clear_waveform_canvas(self) -> None:
        self.waveform_canvas_full.delete("all")
        self.waveform_canvas_trimmed.delete("all")

        self.waveform_canvas_full.draw_canvas()
        self.waveform_canvas_trimmed.draw_canvas()

    def _set_thumb_choice(self, choice: str) -> None:
        self._thumb_choice = choice
        self._sync_thumb_buttons()

    def _select_thumb_up(self) -> None:
        self._set_thumb_choice("up")

    def _select_thumb_down(self) -> None:
        self._set_thumb_choice("down")

    def _sync_thumb_buttons(self) -> None:
        """One thumb active (_b icon + highlight); the other inactive (_w)."""
        if self._thumb_choice == "up":
            self.thumb_up_btn.config(
                image=self._thumb_photo_up_b,
                bg_color="#2E7D4A",
                fg_color="#FFFFFF",
            )
            self.thumb_down_btn.config(
                image=self._thumb_photo_down_w,
                bg_color="#E6E6E6",
                fg_color="#363636",
            )
        else:
            self.thumb_up_btn.config(
                image=self._thumb_photo_up_w,
                bg_color="#E6E6E6",
                fg_color="#363636",
            )
            self.thumb_down_btn.config(
                image=self._thumb_photo_down_b,
                bg_color="#B00020",
                fg_color="#FFFFFF",
            )

    def _get_sample_ch_text(self, sample: dict) -> str:
        if "ch" in sample:
            return sample["ch"]
        return sample[f"ch_{self.recorder.speaker_dialect.lower()}"]

    def _reload_saved_audio_into_buffers(self) -> None:
        """Reload FLAC for current_id after save() cleared in-memory audio (needed for waveform + next save)."""
        if not self.current_id:
            return
        id_str = str(self.current_id)
        self.recorder.load_saved_clip_for_sample(id_str)
        if self.recorder.full_audio is None:
            self.clear_waveform_canvas()
        else:
            self.update_waveform()

    def _sync_ui_for_current_sample(self) -> None:
        """Load DE/CH text, thumbs, saved clip, waveforms, progress, and nav for current_id (e.g. after navigation)."""
        if not self.current_id:
            return

        self.recorder.current_track = str(self.current_id)

        sample = self.recorder.get_sample_by_id(self.current_id)
        text_de = sample["de"]
        text_ch = self._get_sample_ch_text(sample)

        self.de_text_var.set(text_de)
        self.ch_text_var.set(text_ch)
        self.ch_text_edit_var.set(text_ch)

        id_str = str(self.current_id)
        if id_str in self.recorder.output_index:
            self._thumb_choice = self.recorder.output_index[id_str].get("thumb", "up")
        else:
            self._thumb_choice = "up"
        self._sync_thumb_buttons()

        self._reload_saved_audio_into_buffers()
        self.update_progress()
        self.update_navigation_controls()

    def load_next_sample(self) -> None:
        self.current_id = self.recorder.get_next_id()
        if self.current_id is None:
            self._handle_no_next_sample()
            return

        self._sync_ui_for_current_sample()
        self._persist_settings()

    def _handle_no_next_sample(self) -> None:
        """No pending lines left: show the last dataset line for review (not blank UI)."""
        if self.recorder.input_data:
            last_id = str(self.recorder.input_data[-1]["id"])
            self.current_id = last_id
            self.recorder.set_current_track_queue(last_id)
            self._sync_ui_for_current_sample()
        else:
            self.show_done_state()
        self._persist_settings()

    def show_done_state(self) -> None:
        self.current_id = None
        self.recorder.current_track = None
        self.de_text_var.set("")
        self.ch_text_var.set("")
        self.ch_text_edit_var.set("")
        self.clear_waveform_canvas()
        self._thumb_choice = "up"
        self._sync_thumb_buttons()
        self.update_progress()
        self.update_navigation_controls()

    def _current_input_line_index(self) -> int | None:
        """0-based index of current_id in input_data order, or None if unknown."""
        if not self.current_id:
            return None
        cid = str(self.current_id)
        for i, s in enumerate(self.recorder.input_data):
            if str(s["id"]) == cid:
                return i
        return None

    def update_progress(self) -> None:
        total_count = len(self.recorder.input_data)
        if total_count == 0:
            self.progress_text.set("Progress: 0 / 0")
            self.progress_bar["maximum"] = 1
            self.progress_bar["value"] = 0
            return

        if self.current_id is not None:
            ids_ordered = [str(s["id"]) for s in self.recorder.input_data]
            try:
                line_no = ids_ordered.index(str(self.current_id)) + 1
            except ValueError:
                line_no = 0
            self.progress_text.set(f"Progress: {line_no} / {total_count}")
            self.progress_bar["maximum"] = total_count
            self.progress_bar["value"] = line_no
        else:
            done_count = len(self.recorder.output_data) + len(self.recorder.skipped_ids)
            done_count = min(done_count, total_count)
            self.progress_text.set(f"Progress: {done_count} / {total_count}")
            self.progress_bar["maximum"] = max(total_count, 1)
            self.progress_bar["value"] = done_count

    def update_navigation_controls(self) -> None:
        has_current = self.current_id is not None
        self.save_btn.set_state("normal" if has_current else "disabled")
        self.record_btn.set_state("normal" if has_current else "disabled")

        idx = self._current_input_line_index()
        can_prev = has_current and idx is not None and idx > 0
        self.prev_btn.set_state("normal" if can_prev else "disabled")

        thumb_state = "normal" if has_current else "disabled"
        self.thumb_up_btn.set_state(thumb_state)
        self.thumb_down_btn.set_state(thumb_state)

        if self.recorder.enable_skip:
            if self.skip_btn.winfo_manager() == "":
                self.skip_btn.pack(side=tk.LEFT, padx=5, before=self.save_btn)
            self.skip_btn.set_state("normal" if has_current else "disabled")
        else:
            if self.skip_btn.winfo_manager() != "":
                self.skip_btn.pack_forget()

    def _draw_waveform_bars(
        self,
        canvas: RoundedCanvas,
        waveform: list[float],
        width: int,
        height: int,
    ) -> None:
        center_y = height // 2
        bar_width = max(1, width // len(waveform) // 2)
        for i, value in enumerate(waveform):
            x = int((i / len(waveform)) * width)
            bar_height = int(value * (height / 2))
            if bar_height == 0:
                continue
            canvas.create_line(
                x,
                center_y - bar_height,
                x,
                center_y + bar_height,
                fill="orange red",
                width=bar_width,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

    def update_waveform(self) -> None:
        if self.recorder.full_audio is None or self.recorder.trimmed_audio is None:
            return

        # Update duration text
        duration_full = self.recorder.get_duration_full_audio()
        self.duration_text_full.set(f"Full | Duration: {duration_full:.1f} seconds")

        duration_trimmed = self.recorder.get_duration_trimmed_audio()
        self.duration_text_trimmed.set(
            f"Trimmed | Duration: {duration_trimmed:.1f} seconds"
        )

        # Get waveform data
        waveform_full = self.recorder.get_waveform_full_audio()
        waveform_trimmed = self.recorder.get_waveform_trimmed_audio()

        # Get canvas dimensions
        width = self.waveform_canvas_full.winfo_width()
        height = self.waveform_canvas_full.winfo_height()
        # Clear canvas
        self.clear_waveform_canvas()

        self._draw_waveform_bars(
            self.waveform_canvas_full, waveform_full, width, height
        )
        self._draw_waveform_bars(
            self.waveform_canvas_trimmed, waveform_trimmed, width, height
        )

    def configure_handler(self, event):
        self.update_waveform()

    def save(self) -> None:
        if self.current_id is None or self.recorder.trimmed_audio is None:
            return

        duration_s = self.recorder.save_audio(self.current_id)
        self.recorder.add_sample(
            id=self.current_id,
            text_de=self.de_text_var.get(),
            text_ch=self.ch_text_edit_var.get(),
            dialect=self.recorder.speaker_dialect,
            audio_path=f"{self.current_id}.flac",
            duration_s=duration_s,
            thumb=self._thumb_choice,
        )

        self.recorder.audio_data = []
        self.recorder.full_audio = None
        self.recorder.trimmed_audio = None

        self.clear_waveform_canvas()

        self.update_duration()
        if self.recorder.open_ids:
            self.load_next_sample()
        else:
            # current_id unchanged; save() cleared buffers — reload clip so Save works and Previous stays usable
            self._reload_saved_audio_into_buffers()
            self.update_progress()
            self.update_navigation_controls()
        self._persist_settings()

    def go_previous(self) -> None:
        if self.current_id is None:
            return
        idx = self._current_input_line_index()
        if idx is None or idx == 0:
            return
        if self.recorder.recording:
            self.toggle_recording()

        self.recorder.open_ids.insert(0, str(self.current_id))
        prev_id = str(self.recorder.input_data[idx - 1]["id"])
        if prev_id in self.recorder.skipped_ids:
            self.recorder.remove_skip(prev_id)

        self.current_id = prev_id
        self._sync_ui_for_current_sample()
        self._persist_settings()

    def skip(self):
        if self.current_id is None or not self.recorder.enable_skip:
            return

        self.recorder.add_skip(self.current_id)
        self.load_next_sample()

    def on_closing(self) -> None:
        self._persist_settings()
        self.recorder.stop_monitoring()
        if self.recorder.recording:
            self.recorder.stop_recording()
        self.root.destroy()

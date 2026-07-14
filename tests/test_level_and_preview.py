"""Tests for level meter formatting and preview play/stop toggle."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from helvox.utils.recorder import Recorder


@pytest.fixture
def recorder(tmp_path: Path) -> Recorder:
    return Recorder(tmp_path)


def _level_label(level: float) -> str:
    """Mirror App.update_level_meter formatting."""
    level = round(float(level), 1)
    return f"Level: {level:5.1f} dB"


class TestLevelMeterFormatting:
    def test_silence_is_minus_sixty(self, recorder: Recorder) -> None:
        assert recorder.calculate_rms_db(np.zeros(100)) == -60.0

    def test_empty_audio_is_minus_sixty(self, recorder: Recorder) -> None:
        assert recorder.calculate_rms_db(np.array([])) == -60.0

    def test_result_has_at_most_one_decimal(self, recorder: Recorder) -> None:
        for amplitude in (0.001, 0.01, 0.05, 0.1, 0.5, 1.0):
            db = recorder.calculate_rms_db(np.full(500, amplitude))
            assert round(db, 1) == db
            # String form never has two digits after the decimal point
            text = f"{db:.10f}".rstrip("0")
            if "." in text:
                assert len(text.split(".")[1]) <= 1

    def test_label_always_one_decimal_place(self) -> None:
        for level in (-60.0, -9.5, -12.34, -1.0, 0.0, -0.05):
            label = _level_label(level)
            number = label.removeprefix("Level: ").removesuffix(" dB").strip()
            assert number.count(".") == 1
            assert len(number.split(".")[1]) == 1

    def test_label_width_stays_constant(self) -> None:
        lengths = {
            len(_level_label(level))
            for level in (-60.0, -50.0, -9.9, -1.2, 0.0)
        }
        assert len(lengths) == 1


class TestPreviewToggle:
    def test_play_none_does_nothing(self, recorder: Recorder) -> None:
        assert recorder.play_audio_data(None, "full") is False
        assert recorder.get_playback_source() is None

    def test_second_click_stops_same_source(self, recorder: Recorder) -> None:
        audio = np.zeros((4800, 1), dtype=np.float32)
        stream = SimpleNamespace(active=True)

        with (
            patch("helvox.utils.recorder.sd.play") as play,
            patch("helvox.utils.recorder.sd.stop") as stop,
            patch("helvox.utils.recorder.sd.get_stream", return_value=stream),
        ):
            assert recorder.play_audio_data(audio, "full") is True
            play.assert_called_once()
            assert recorder.get_playback_source() == "full"

            assert recorder.play_audio_data(audio, "full") is False
            stop.assert_called_once()
            assert recorder.get_playback_source() is None

    def test_switching_source_restarts_without_stop_toggle(
        self, recorder: Recorder
    ) -> None:
        audio_a = np.zeros((1000, 1), dtype=np.float32)
        audio_b = np.ones((1000, 1), dtype=np.float32)
        stream = SimpleNamespace(active=True)

        with (
            patch("helvox.utils.recorder.sd.play") as play,
            patch("helvox.utils.recorder.sd.stop") as stop,
            patch("helvox.utils.recorder.sd.get_stream", return_value=stream),
        ):
            assert recorder.play_audio_data(audio_a, "full") is True
            assert recorder.play_audio_data(audio_b, "trimmed") is True
            assert play.call_count == 2
            # Switching sources starts the new clip; stop is only for same-source toggle
            stop.assert_not_called()
            assert recorder.get_playback_source() == "trimmed"

    def test_full_and_trimmed_wrappers_use_buffers(
        self, recorder: Recorder
    ) -> None:
        recorder.full_audio = np.zeros((100, 1), dtype=np.float32)
        recorder.trimmed_audio = np.ones((50, 1), dtype=np.float32)
        stream = SimpleNamespace(active=True)

        with (
            patch("helvox.utils.recorder.sd.play") as play,
            patch("helvox.utils.recorder.sd.get_stream", return_value=stream),
        ):
            assert recorder.play_audio_data_full_audio() is True
            play.assert_called_with(recorder.full_audio, recorder.sample_rate)

            assert recorder.play_audio_data_trimmed_audio() is True
            play.assert_called_with(recorder.trimmed_audio, recorder.sample_rate)

    def test_stop_playback_clears_source(self, recorder: Recorder) -> None:
        recorder._playback_source = "full"
        with patch("helvox.utils.recorder.sd.stop") as stop:
            recorder.stop_playback()
            stop.assert_called_once()
        assert recorder.get_playback_source() is None

    def test_get_playback_source_clears_when_inactive(
        self, recorder: Recorder
    ) -> None:
        recorder._playback_source = "full"
        stream = SimpleNamespace(active=False)
        with patch("helvox.utils.recorder.sd.get_stream", return_value=stream):
            assert recorder.get_playback_source() is None
        assert recorder._playback_source is None

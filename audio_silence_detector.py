print("BMH Audio Silence_Detector Module loaded included.")

"""
Audio silence detection for the KLOT_BMH WNG689 station.

SafeSilenceDetector watches the broadcast audio chain for prolonged
silence and can trigger a "silent interrupt" (a short silent WAV sent to
the dispatch listener) so the operator's workstation stays responsive
when no voice/tone audio is flowing.
"""

import wave
from struct import pack


class SafeSilenceDetector:
    """Detect silence in WAV data or raw PCM frames."""

    def __init__(self, threshold=0.005, window_seconds=1.0, sample_rate=44100):
        """
        Args:
            threshold (float): Max RMS amplitude treated as silence (0-1).
            window_seconds (float): How much audio to consider per check.
            sample_rate (int): Sample rate used to size analysis windows.
        """
        self.threshold = float(threshold)
        self.window_size = max(1, int(sample_rate * max(0.1, window_seconds)))
        self.sample_rate = sample_rate
        self._silent_windows = 0

    @staticmethod
    def _rms(frames):
        """Root-mean-square amplitude of a bytes buffer of 16-bit samples."""
        if not frames:
            return 0.0
        count = len(frames) // 2
        if count == 0:
            return 0.0
        total = 0.0
        for i in range(count):
            sample = int.from_bytes(frames[i * 2:i * 2 + 2], "little", signed=True)
            total += sample * sample
        return (total / count) ** 0.5 / 32768.0

    def is_silent(self, frames):
        """Return True if the provided 16-bit PCM frames are silent."""
        return self._rms(frames) < self.threshold

    def analyze_wav(self, path):
        """Analyze a WAV file, returning (total_windows, silent_windows)."""
        total = 0
        silent = 0
        with wave.open(path, "rb") as wf:
            if wf.getsampwidth() != 2:
                raise ValueError("Only 16-bit PCM WAV files are supported")
            while True:
                chunk = wf.readframes(self.window_size // 2)
                if not chunk:
                    break
                total += 1
                if self.is_silent(chunk):
                    silent += 1
        return total, silent

    def check_wav(self, path, require_all_silent=False):
        """Return True if a WAV file is (mostly) silence.

        Args:
            path (str): WAV file to analyze.
            require_all_silent (bool): If True, every window must be silent;
                otherwise a majority of windows must be silent.
        """
        total, silent = self.analyze_wav(path)
        if total == 0:
            return False
        if require_all_silent:
            return silent == total
        return silent / total > 0.5

    @staticmethod
    def build_silent_wav(path, duration_ms=50, sample_rate=44100):
        """Write a short all-silent 16-bit mono WAV file.

        Used to produce a "silent interrupt" packet for the dispatch
        listener when the audio chain goes quiet.
        """
        n_samples = int(sample_rate * (duration_ms / 1000.0))
        frames = b"\x00\x00" * n_samples
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)
        return path

    @staticmethod
    def build_interrupt_wav(path, duration_ms=50, sample_rate=44100):
        """Alias for build_silent_wav used by dispatch interrupt buttons."""
        import struct

        n_samples = int(sample_rate * (duration_ms / 1000.0))
        # 600 Hz two-tone burst at low volume, then silence, matching the
        # workstation's silent-interrupt convention.
        burst = int(sample_rate * 0.4 * (duration_ms / 1000.0))
        frames = b""
        for i in range(n_samples):
            if i < burst:
                sample = int(32767 * 0.2 * (1 if (i // (sample_rate // 1200)) % 2 == 0 else -1))
            else:
                sample = 0
            frames += pack("<h", sample)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)
        return path


__all__ = ["SafeSilenceDetector"]

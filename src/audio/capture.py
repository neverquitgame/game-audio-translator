import sys
import logging
import threading
from typing import Callable, Optional

import numpy as np

from src.config import Config

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import pyaudiowpatch as pyaudio
        logger.info("Using pyaudiowpatch for WASAPI loopback capture")
    except ImportError:
        import pyaudio
        logger.warning("pyaudiowpatch not found, falling back to standard pyaudio on Windows")
else:
    import pyaudio
    logger.info("Non-Windows platform detected, using standard pyaudio (mic input)")


class AudioCapture:
    def __init__(self):
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._thread = None
        self._running = False
        self._stop_lock = threading.Lock()

    def list_audio_devices(self) -> list[dict]:
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if IS_WINDOWS:
                # On Windows with pyaudiowpatch, loopback devices have isLoopbackDevice flag
                if info.get("isLoopbackDevice", False):
                    devices.append({"index": i, "name": info["name"], "channels": info["maxInputChannels"]})
            else:
                # On macOS/Linux, list input devices (microphones)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append({"index": i, "name": info["name"], "channels": info["maxInputChannels"]})
        return devices

    def get_default_device_index(self) -> Optional[int]:
        if IS_WINDOWS:
            try:
                # Find the default output device's corresponding loopback device
                default_output = self._pa.get_default_wasapi_loopback()
                return default_output["index"]
            except Exception as e:
                logger.warning(f"Could not get default WASAPI loopback device: {e}")
                devices = self.list_audio_devices()
                return devices[0]["index"] if devices else None
        else:
            try:
                info = self._pa.get_default_input_device_info()
                return info["index"]
            except Exception as e:
                logger.warning(f"Could not get default input device: {e}")
                return None

    def start_capture(self, device_index: Optional[int] = None, callback: Optional[Callable] = None) -> bool:
        if self._running:
            logger.warning("Capture already running")
            return False

        if device_index is None:
            device_index = self.get_default_device_index()

        if device_index is None:
            logger.error("No suitable audio device found")
            return False

        try:
            device_info = self._pa.get_device_info_by_index(device_index)
            channels = min(int(device_info.get("maxInputChannels", 1)), 2)
            chunk_size = int(Config.SAMPLE_RATE * Config.CHUNK_DURATION_MS / 1000)

            # Use blocking mode (no stream_callback) to avoid PortAudio's AUHAL
            # callback path which double-frees on macOS with virtual audio devices.
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=Config.SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=chunk_size,
            )
            self._running = True

            def _read_loop():
                while self._running:
                    try:
                        data = self._stream.read(chunk_size, exception_on_overflow=False)
                        # Downmix stereo → mono so webrtcvad always receives mono PCM
                        if channels > 1 and data:
                            pcm = np.frombuffer(data, dtype=np.int16)
                            data = pcm.reshape(-1, channels).mean(axis=1).astype(np.int16).tobytes()
                        if callback and data:
                            callback(data)
                    except Exception as e:
                        if self._running:
                            logger.error(f"Audio read error: {e}")
                        break

            self._thread = threading.Thread(
                target=_read_loop, daemon=True, name="audio-reader"
            )
            self._thread.start()
            logger.info(f"Audio capture started on device: {device_info['name']} (index {device_index})")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self._stream = None
            return False

    def stop_capture(self):
        with self._stop_lock:
            if not self._running and self._stream is None:
                return
            self._running = False
            # Atomically grab references and clear them so no other thread can close them
            stream, self._stream = self._stream, None
            thread, self._thread = self._thread, None

        # Do blocking operations outside the lock to avoid holding lock during join/close
        if thread and thread.is_alive():
            thread.join(timeout=2)
        if stream:
            try:
                stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
            logger.info("Audio capture stopped")

    def close(self):
        """Explicit teardown — call this before the process exits to avoid double-free in pa.terminate()."""
        self.stop_capture()
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            finally:
                self._pa = None

    def __del__(self):
        # Only stop the stream — do NOT call pa.terminate() here.
        # pa.terminate() during Python GC causes a double-free in PortAudio's
        # CoreAudio AUHAL backend on macOS. Call close() explicitly instead.
        self.stop_capture()

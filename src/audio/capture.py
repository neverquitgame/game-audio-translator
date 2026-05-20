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
        self._capture_rate = Config.SAMPLE_RATE
        self._resample = False

    def list_audio_devices(self) -> list[dict]:
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            sample_rate = int(info.get("defaultSampleRate", 0))
            if IS_WINDOWS:
                # On Windows with pyaudiowpatch, loopback devices have isLoopbackDevice flag
                if info.get("isLoopbackDevice", False):
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "default_sample_rate": sample_rate,
                    })
            else:
                # On macOS/Linux, list input devices (microphones)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "default_sample_rate": sample_rate,
                    })
        return devices

    def _device_default_rate(self, device_index: int) -> int:
        try:
            info = self._pa.get_device_info_by_index(device_index)
            return int(info.get("defaultSampleRate", Config.SAMPLE_RATE))
        except Exception:
            return Config.SAMPLE_RATE

    def _resample_int16(self, samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate or len(samples) == 0:
            return samples
        out_len = int(round(len(samples) * dst_rate / src_rate))
        if out_len <= 0:
            return np.empty((0,), dtype=np.int16)
        positions = np.linspace(0, len(samples) - 1, out_len)
        resampled = np.interp(positions, np.arange(len(samples)), samples.astype(np.float64))
        return np.clip(np.round(resampled), -32768, 32767).astype(np.int16)

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
            device_rate = self._device_default_rate(device_index)
            stream_rate = Config.SAMPLE_RATE
            chunk_size = int(stream_rate * Config.CHUNK_DURATION_MS / 1000)
            stream_exception = None

            # Attempt to open the requested sample rate first; if the device does not
            # support it, fall back to the device's default sample rate and resample.
            try:
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=stream_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=chunk_size,
                )
            except Exception as e:
                stream_exception = e
                if device_rate != stream_rate:
                    logger.warning(
                        "Device does not support configured sample rate %s Hz; falling back to device default %s Hz",
                        stream_rate,
                        device_rate,
                    )
                    stream_rate = device_rate
                    chunk_size = int(stream_rate * Config.CHUNK_DURATION_MS / 1000)
                    self._stream = self._pa.open(
                        format=pyaudio.paInt16,
                        channels=channels,
                        rate=stream_rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=chunk_size,
                    )
                else:
                    raise

            self._capture_rate = stream_rate
            self._resample = self._capture_rate != Config.SAMPLE_RATE
            self._running = True

            def _read_loop():
                while self._running:
                    try:
                        data = self._stream.read(chunk_size, exception_on_overflow=False)
                        if not data:
                            continue

                        pcm = np.frombuffer(data, dtype=np.int16)
                        if channels > 1:
                            pcm = pcm.reshape(-1, channels).mean(axis=1).astype(np.int16)

                        if self._resample:
                            pcm = self._resample_int16(pcm, self._capture_rate, Config.SAMPLE_RATE)

                        data = pcm.tobytes()
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
        if stream:
            try:
                stream.stop_stream()
            except Exception:
                pass
        if thread and thread.is_alive():
            thread.join(timeout=3)
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

import logging
import numpy as np
import soundfile as sf
import sounddevice as sd

from PyQt6 import QtCore

logger = logging.getLogger("Ambient Player Client")

class AmbientPlayer(QtCore.QThread):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, file_path, device_index=None):
        super().__init__()
        self.file_path = file_path
        self.device_index = device_index
        self.data = None
        self.samplerate = None
        self.volume = 0.2
    
    def run(self):
        try:
            sd.default.device = self.device_index

            data, samplerate = sf.read(self.file_path)
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0

            peak = np.max(np.abs(data))
            if peak > 0:
                data /= peak

            data *= self.volume

            self.data = data
            self.samplerate = samplerate

            sd.play(self.data, self.samplerate, device=self.device_index, loop=True)

        except Exception as e:
            self.error.emit(f"Loading file error: {e}")

        self.finished.emit()

    def set_device(self, index):
        self.device_index = index

    def stop_audio(self):
        sd.stop()
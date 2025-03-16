import cv2
import pyaudio
import wave
import speech_recognition as sr
import pyttsx3
import logging
import time
from typing import Optional

class DeviceManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.camera: Optional[cv2.VideoCapture] = None
        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.tts_engine = pyttsx3.init()

        # Audio recording parameters
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.record_seconds = 5

        # Device IDs - adjust these for your Raspberry Pi setup
        self.camera_id = 0  # Usually 0 for USB camera
        self.microphone_id = None  # Will be detected automatically
        self.speaker_id = None  # Will be detected automatically

        # Retry parameters
        self.last_error_time = 0
        self.retry_delay = 1  # Start with 1 second delay
        self.max_retry_delay = 30  # Maximum delay between retries
        self.last_error_message = None

    def detect_devices(self):
        """Detect and configure available audio devices"""
        # Find microphone
        try:
            mic_list = sr.Microphone.list_microphone_names()
            self.logger.info(f"Available microphones: {mic_list}")
            if mic_list:
                # Use the first available microphone
                self.microphone_id = mic_list.index(mic_list[0])
        except Exception as e:
            self.logger.warning(f"Microphone detection error: {str(e)}")

        # Find speaker
        try:
            info = self.audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            for i in range(num_devices):
                if self.audio.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels') > 0:
                    self.speaker_id = i
                    break
        except Exception as e:
            self.logger.warning(f"Speaker detection error: {str(e)}")

    def initialize_devices(self):
        """Initialize all USB devices"""
        try:
            # Detect available devices
            self.detect_devices()

            # Initialize camera
            self.camera = cv2.VideoCapture(self.camera_id)
            if not self.camera.isOpened():
                self.logger.warning("Failed to open camera, will retry on Raspberry Pi")
            else:
                self.logger.info("Camera initialized successfully")

            # Test audio input
            try:
                with sr.Microphone(device_index=self.microphone_id) as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    self.logger.info("Microphone initialized successfully")
            except Exception as e:
                self.logger.warning(f"Microphone initialization warning (will retry on Raspberry Pi): {str(e)}")

            # Configure text-to-speech
            if self.speaker_id is not None:
                try:
                    self.tts_engine.setProperty('voice', self.tts_engine.getProperty('voices')[0].id)
                    self.tts_engine.say("System initialized")
                    self.tts_engine.runAndWait()
                    self.logger.info("Text-to-speech initialized successfully")
                except Exception as e:
                    self.logger.warning(f"Text-to-speech warning (will retry on Raspberry Pi): {str(e)}")

            self.logger.info("Device initialization completed - some devices may need to be configured on Raspberry Pi")
            return True

        except Exception as e:
            self.logger.error(f"Device initialization error: {str(e)}")
            return False

    def _should_retry(self, error_msg: str) -> bool:
        """Determine if we should retry based on error and timing"""
        current_time = time.time()

        # If this is a new error message, log it
        if error_msg != self.last_error_message:
            self.last_error_message = error_msg
            self.logger.error(f"Audio capture error: {error_msg}")
            self.retry_delay = 1  # Reset delay for new error type
            return True

        # Check if enough time has passed since last attempt
        if current_time - self.last_error_time < self.retry_delay:
            return False

        # Update timing and increase delay
        self.last_error_time = current_time
        self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
        return True

    def capture_audio(self) -> str:
        """Capture audio from microphone and convert to text"""
        try:
            with sr.Microphone(device_index=self.microphone_id) as source:
                self.logger.info("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                self.logger.info("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                self.logger.info(f"Recognized text: {text}")

                # Reset retry parameters on success
                self.retry_delay = 1
                self.last_error_message = None
                return text

        except sr.WaitTimeoutError:
            if self._should_retry("No speech detected"):
                self.logger.warning("No speech detected")
            return ""
        except sr.UnknownValueError:
            if self._should_retry("Could not understand audio"):
                self.logger.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            if self._should_retry(str(e)):
                self.logger.error(f"Speech recognition error: {str(e)}")
            return ""
        except Exception as e:
            if self._should_retry(str(e)):
                self.logger.error(f"Unexpected audio capture error: {str(e)}")
            return ""

    def speak_text(self, text: str):
        """Convert text to speech and play through speakers"""
        try:
            self.logger.info(f"Speaking: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            if self._should_retry(str(e)):
                self.logger.error(f"Text-to-speech error: {str(e)}")

    def capture_image(self):
        """Capture image from camera"""
        if self.camera is None or not self.camera.isOpened():
            if self._should_retry("Camera is not initialized"):
                self.logger.error("Camera is not initialized")
            return None

        ret, frame = self.camera.read()
        if ret:
            return frame
        else:
            if self._should_retry("Failed to capture image"):
                self.logger.error("Failed to capture image")
            return None

    def cleanup(self):
        """Clean up and release all devices"""
        try:
            if self.camera is not None:
                self.camera.release()
            self.audio.terminate()
            self.tts_engine.stop()
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")
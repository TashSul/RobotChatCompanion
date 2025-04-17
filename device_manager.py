import subprocess
import os
import tempfile
import wave
import speech_recognition as sr
import logging
import time
import base64
import openai
from typing import Optional

# Import cv2 with error handling for environments without it
try:
    import cv2
except ImportError:
    cv2 = None
    print("WARNING: OpenCV (cv2) module not available - camera functions will be limited")

class DeviceManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.camera = None  # Will hold the camera object if available
        self.recognizer = sr.Recognizer()
        
        # Simulation mode flag - default is enabled for development environments
        self.simulation_enabled = True
        
        # For tracking simulation state
        self.last_simulated_text = ""

        # Audio recording parameters
        self.record_seconds = 5
        
        # ALSA device names for Raspberry Pi USB audio - based on hardware detection
        self.microphone_device = "plughw:3,0"  # USB PnP Sound Device (microphone)
        self.speaker_device = "plughw:2,0"     # iStore Audio (speaker)
        
        # Camera ID - video0 for USB camera
        self.camera_id = 0  # /dev/usb_cam -> video0

        # Temporary file for audio recording
        self.temp_wav_file = os.path.join(tempfile.gettempdir(), "robot_audio.wav")
        
        # Retry parameters
        self.last_error_time = 0
        self.retry_delay = 1  # Start with 1 second delay
        self.max_retry_delay = 30  # Maximum delay between retries
        self.last_error_message = None

    def detect_devices(self):
        """Check audio devices using aplay and arecord"""
        try:
            # Check speaker using aplay
            self.logger.info(f"Testing speaker device: {self.speaker_device}")
            result = subprocess.run(
                f"speaker-test -D {self.speaker_device} -c 1 -t sine -f 440 -l 1", 
                shell=True, 
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                self.logger.warning(f"Speaker test warning: {result.stderr.decode()}")
                
            # No direct way to test microphone without recording, so we'll just log the device
            self.logger.info(f"Using microphone device: {self.microphone_device}")
            
        except Exception as e:
            self.logger.warning(f"Device detection error: {str(e)}")

    def initialize_devices(self):
        """Initialize all USB devices"""
        try:
            # Print device configuration
            self.logger.info(f"Using microphone device: {self.microphone_device}")
            self.logger.info(f"Using speaker device: {self.speaker_device}")
            
            # Test devices
            self.detect_devices()

            # Initialize camera if cv2 is available
            if cv2 is not None:
                try:
                    # First check if camera device exists
                    import subprocess
                    
                    # Try multiple methods to detect camera devices
                    self.logger.info("Checking for camera devices...")
                    
                    # Method 1: Check for video devices in /dev
                    camera_check = subprocess.run("ls -l /dev/video* 2>/dev/null", 
                                                  shell=True, capture_output=True)
                    
                    if camera_check.returncode == 0:
                        camera_devices = camera_check.stdout.decode().strip()
                        self.logger.info(f"Found video devices in /dev: {camera_devices}")
                    else:
                        self.logger.warning("No camera devices found in /dev/video*")
                        
                        # Method 2: Check for video4linux devices in sysfs
                        camera_check = subprocess.run("ls -l /sys/class/video4linux/ 2>/dev/null", 
                                                      shell=True, capture_output=True)
                        if camera_check.returncode == 0:
                            camera_devices = camera_check.stdout.decode().strip()
                            self.logger.info(f"Found video devices in sysfs: {camera_devices}")
                        else:
                            self.logger.warning("No video4linux devices found in sysfs")
                            
                            # Method 3: Check for USB cameras
                            camera_check = subprocess.run(
                                "find /sys/bus/usb/devices -type l -exec cat {}/manufacturer {}/product 2>/dev/null \\; 2>/dev/null | grep -i camera", 
                                shell=True, capture_output=True)
                            if camera_check.returncode == 0:
                                camera_info = camera_check.stdout.decode().strip()
                                self.logger.info(f"Found USB camera info: {camera_info}")
                            else:
                                self.logger.warning("No USB camera devices detected")
                        
                    # Try specific camera devices if default fails
                    camera_paths = [self.camera_id, "/dev/video0", "/dev/usb_cam", 0, 1, 2]
                    
                    # Try each possible camera device
                    for cam_id in camera_paths:
                        try:
                            self.logger.info(f"Trying camera device: {cam_id}")
                            self.camera = cv2.VideoCapture(cam_id)
                            if self.camera.isOpened():
                                self.logger.info(f"Camera initialized successfully with device {cam_id}")
                                break
                        except Exception as e:
                            self.logger.warning(f"Failed to open camera {cam_id}: {str(e)}")
                    
                    # Check if we found a working camera
                    if self.camera is None or not self.camera.isOpened():
                        if not self.simulation_enabled:
                            self.logger.error("Failed to open camera - hardware required but not available")
                        else:
                            self.logger.warning("Failed to open camera, will use simulation")
                            
                except Exception as e:
                    self.logger.warning(f"Camera initialization error: {str(e)}")
                    if not self.simulation_enabled:
                        self.logger.error("Camera is required but unavailable - please check USB connections")
            else:
                self.logger.warning("OpenCV (cv2) not available - camera functions disabled")
                if not self.simulation_enabled:
                    self.logger.error("OpenCV required for camera functions but not installed")

            # Welcome message
            self.speak_text("System initialized")
            
            self.logger.info("Device initialization completed")
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

    def check_audio_hardware(self) -> bool:
        """Check if audio hardware is available"""
        try:
            # Check if any audio devices are available
            result = subprocess.run("arecord -l", shell=True, capture_output=True)
            if "no soundcards found" in result.stderr.decode():
                return False
            return True
        except:
            return False

    def capture_audio(self) -> str:
        """Capture audio from microphone using arecord and convert to text"""
        try:
            self.logger.info("Listening...")
            
            # Check if we're running in a development environment without audio hardware
            # and simulation is enabled
            if not self.check_audio_hardware() and self.simulation_enabled:
                self.logger.warning("No audio hardware detected - using simulated input")
                
                # Check if we have a simulated input file from the test script
                temp_sim_file = os.path.join(tempfile.gettempdir(), "robot_sim_input.txt")
                if os.path.exists(temp_sim_file):
                    try:
                        with open(temp_sim_file, "r") as f:
                            text = f.read().strip()
                        # Remove the file after reading
                        os.remove(temp_sim_file)
                        self.logger.info(f"Using simulated input from file: {text}")
                        # Save the last simulated text for training simulation purposes
                        self.last_simulated_text = text
                        return text
                    except Exception as e:
                        self.logger.warning(f"Error reading simulated input file: {e}")
                        # Fall back to random simulation
                
                # Simulate some input for testing
                import time
                import random
                
                # Simulate processing time
                time.sleep(2)
                
                # Return simulated input based on the current time
                simulated_phrases = [
                    # Standard conversation phrases
                    "Hello robot how are you today",
                    "What time is it",
                    "Tell me about the weather",
                    "What can you do",
                    "Tell me a joke",
                    
                    # Camera/object recognition phrases
                    "What do you see in front of you",
                    "Can you identify this object",
                    "What am I holding",
                    "Look at this and tell me what it is",
                    
                    # Robot movement commands (for ROS testing)
                    "Wave",
                    "Wave your hand",
                    "Move 3 steps forward",
                    "Move 2 steps backward",
                    "Stop moving",
                    "Track the object",
                    "Kick the ball",
                    "Stop",
                    
                    # Object picking commands (for ROS testing)
                    "Pick up that object",
                    "Grab the object in front of you",
                    "Can you pick up this object",
                    "Take that object",
                    "Get that object for me",
                    
                    # Wake word related commands
                    "Beta",
                    "Beta wave your hand",
                    "Beta pick up that object",
                    "Beta what do you see",
                    "Beta disable wake word",
                    "Wake word on",
                    "Wake word off",
                    "Enable wake word",
                    "Disable wake word",
                    
                    # Haptic feedback calibration commands
                    "Beta calibrate grip",
                    "Beta calibrate hand",
                    "Beta adjust grip sensitivity",
                    "Beta haptic feedback calibration",
                    "Calibrate haptic feedback",
                    
                    # Object training commands
                    "Train object coffee mug",
                    "Train object rubber duck",
                    "Train object keyboard",
                    "Train object remote control",
                    "What do you see",
                    "What is this",
                    "Another angle",
                    "Different angle",
                    "More angles",
                    "Finished training",
                    "Cancel training"
                ]
                text = random.choice(simulated_phrases)
                self.logger.info(f"Simulated text input: {text}")
                # Save the last simulated text for training simulation purposes
                self.last_simulated_text = text
                return text
            
            # If simulation is disabled but no hardware is available, return empty to wait for hardware
            if not self.check_audio_hardware() and not self.simulation_enabled:
                self.logger.error("Audio hardware required but not available - simulation disabled")
                return ""
            
            # If hardware is available, use it
            # Record audio using arecord command
            self.logger.info(f"Recording from device: {self.microphone_device}")
            subprocess.run(
                f"arecord -D {self.microphone_device} -d {self.record_seconds} -f cd {self.temp_wav_file}",
                shell=True,
                check=True
            )
            
            self.logger.info("Processing speech...")
            
            # Convert audio to text using SpeechRecognition
            with sr.AudioFile(self.temp_wav_file) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                self.logger.info(f"Recognized text: {text}")
                
            # Reset retry parameters on success
            self.retry_delay = 1
            self.last_error_message = None
            return text

        except subprocess.CalledProcessError as e:
            if self._should_retry(f"Error recording audio: {e}"):
                self.logger.warning(f"Recording error: {e}")
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
        """Convert text to speech using espeak and aplay"""
        try:
            self.logger.info(f"Speaking: {text}")
            
            # Check if we're running in a development environment without audio hardware
            # and simulation is enabled
            if not self.check_audio_hardware() and self.simulation_enabled:
                self.logger.warning("No audio hardware detected - speech output simulated")
                # In a real environment with hardware, the text would be spoken aloud
                # Just log the output for development
                print(f"🔊 ROBOT SAYS: \"{text}\"")
                return
            
            # If simulation is disabled but no hardware is available, log error
            if not self.check_audio_hardware() and not self.simulation_enabled:
                self.logger.error("Audio hardware required for speech but not available - simulation disabled")
                return
            
            # Create a temporary file for the text
            text_file = os.path.join(tempfile.gettempdir(), "robot_speech.txt")
            with open(text_file, "w") as f:
                f.write(text)
            
            # Use espeak to convert text to speech and pipe to aplay
            self.logger.info(f"Playing speech through device: {self.speaker_device}")
            subprocess.run(
                f"espeak -f {text_file} --stdout | aplay -D {self.speaker_device}",
                shell=True,
                check=True
            )
            
        except Exception as e:
            if self._should_retry(str(e)):
                self.logger.error(f"Text-to-speech error: {str(e)}")

    def capture_image(self):
        """Capture image from camera"""
        # Check if cv2 is available
        if cv2 is None:
            if self._should_retry("OpenCV not available"):
                self.logger.error("Camera functionality unavailable - OpenCV not installed")
            return None
            
        # Check if camera is initialized
        if self.camera is None or not self.camera.isOpened():
            if self._should_retry("Camera is not initialized"):
                self.logger.error("Camera is not initialized")
            return None

        try:
            ret, frame = self.camera.read()
            if ret:
                return frame
            else:
                if self._should_retry("Failed to capture image"):
                    self.logger.error("Failed to capture image")
                return None
        except Exception as e:
            if self._should_retry(f"Camera error: {str(e)}"):
                self.logger.error(f"Error capturing image: {str(e)}")
            return None

    def identify_object(self) -> str:
        """Capture an image and use OpenAI to identify objects in it"""
        self.logger.info("Attempting to identify objects in camera view...")
        
        # First, capture an image from the camera
        frame = self.capture_image()
        
        # Check if we're running in a development environment without camera hardware
        # and simulation is enabled
        if frame is None and self.simulation_enabled:
            self.logger.warning("No camera or frame detected - using simulated image recognition")
            
            # In training mode, try to match the simulated response to the object being trained
            # We'll infer the training state from the current simulated command
            try:
                # Look for a commonly used training object pattern in recent simulated text
                # This is a hack for simulation purposes - in a real system, we'd have proper state management
                import re
                training_object = None
                
                # Check if we recently simulated a Train object command
                if "train object" in self.last_simulated_text.lower():
                    match = re.search(r'train\s+object\s+([a-zA-Z0-9_\s]+)', self.last_simulated_text.lower())
                    if match:
                        training_object = match.group(1).strip()
                        self.logger.info(f"Detected training mode for object: {training_object} from simulated input")
                        self.logger.info(f"Simulating recognition for training object: {training_object}")
                        
                        # Create custom responses for the specific object being trained
                        result = ""
                        if training_object and ("coffee" in training_object or "mug" in training_object):
                            result = "I can see a ceramic coffee mug with a handle. It appears to be on a flat surface."
                        elif training_object and ("duck" in training_object or "rubber" in training_object):
                            result = "There's a small yellow rubber duck toy. It has an orange beak and appears to be made of plastic."
                        elif training_object and ("remote" in training_object or "control" in training_object):
                            result = "I can see what appears to be a black remote control with multiple buttons. It's likely for a TV or entertainment system."
                        elif training_object and "keyboard" in training_object:
                            result = "There's a computer keyboard with black keys. It appears to be a standard QWERTY layout."
                        else:
                            result = f"I can see what looks like a {training_object} in the image."
                        
                        self.logger.info(f"Simulated training image recognition: {result}")
                        return result
            except:
                # If there's any error in the above, fall back to standard responses
                self.logger.warning("Error in custom training response, using standard simulation")
                pass
            
            # Standard simulated responses
            simulated_responses = [
                "I can see what appears to be a coffee mug on a desk.",
                "There seems to be a smartphone in the image.",
                "I can see a book or notebook on a surface.",
                "It looks like a houseplant, possibly a small succulent.",
                "I can see what appears to be a pair of headphones."
            ]
            import random
            result = random.choice(simulated_responses)
            self.logger.info(f"Simulated image recognition: {result}")
            return result
            
        # If simulation is disabled but no camera is available, return error message
        if frame is None and not self.simulation_enabled:
            self.logger.error("Camera hardware required but not available - simulation disabled")
            return "I'm unable to see anything right now. My camera appears to be unavailable."
        
        try:
            # Convert the OpenCV frame to a format that can be sent to OpenAI
            # First save the image to a temporary file
            temp_img_path = os.path.join(tempfile.gettempdir(), "robot_vision.jpg")
            cv2.imwrite(temp_img_path, frame)
            
            # Read the image file and encode it as base64
            with open(temp_img_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create OpenAI client
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Ensure OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.error("OpenAI API key is not available")
                return "I'm unable to analyze the image. My vision system requires setup."
            
            # Send the image to OpenAI's Vision model for analysis
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a vision assistant helping a robot identify objects through its camera. Describe what you see clearly and concisely. Focus on the main objects in view, their approximate positions, and any notable characteristics."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "What objects do you see in this image? Please describe them clearly but concisely, as if you're telling a person what they're holding or what's in front of them."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ],
                    max_tokens=300
                )
            except openai.OpenAIError as e:
                self.logger.error(f"OpenAI API error during image analysis: {str(e)}")
                return "I encountered an issue with my vision system. I can't identify what's in the image right now."
            
            # Extract the result
            result = response.choices[0].message.content
            self.logger.info(f"Object identification result: {result}")
            
            # Clean up the temporary file
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error during object identification: {str(e)}")
            return f"I'm having trouble identifying objects right now. Error: {str(e)}"

    def cleanup(self):
        """Clean up and release all devices"""
        try:
            # Release the camera if cv2 is available
            if cv2 is not None and self.camera is not None:
                try:
                    self.camera.release()
                except Exception as e:
                    self.logger.warning(f"Error releasing camera: {str(e)}")
                
            # Remove temporary files
            if os.path.exists(self.temp_wav_file):
                os.remove(self.temp_wav_file)
                
            # Stop any ongoing audio processes
            try:
                subprocess.run("pkill -f aplay", shell=True, stderr=subprocess.DEVNULL)
                subprocess.run("pkill -f arecord", shell=True, stderr=subprocess.DEVNULL)
            except Exception as e:
                self.logger.warning(f"Error stopping audio processes: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")
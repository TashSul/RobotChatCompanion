# Robot Voice Interface

A Python-powered intelligent voice interface for a humanoid robot, optimized for precise USB device management and seamless hardware integration on a Raspberry Pi 5.

## Overview

This project creates a voice-based conversational interface for a Hiwonder Ainex humanoid robot running on Raspberry Pi 5 with Ubuntu. The system utilizes:

- OpenAI GPT-4o for natural language processing and conversation
- OpenAI Vision API for object recognition and scene understanding
- USB camera for visual perception and object identification
- USB microphone and speaker for audio interactions
- Direct hardware access via ALSA commands for reliable device management

## Key Features

- Seamless voice interaction with ChatGPT API integration
- Natural voice output using OpenAI TTS API with multiple voice options
- Object recognition and visual perception powered by OpenAI Vision
- Trigger phrases for activating camera-based object identification
- Voice commands for changing voice type and speech speed
- Hardware-optimized audio capture and playback
- Automatic USB device detection and configuration
- Error-resilient operation with exponential backoff
- Comprehensive logging for troubleshooting
- Simulation mode for development environments
- Modular design for easy component updates

## Hardware Requirements

- **Raspberry Pi 5** running Ubuntu (or compatible Linux distro)
- **USB Camera**: Any standard USB webcam
- **USB Microphone**: USB PnP Sound Device (detected as card 3)
- **USB Speaker**: iStore Audio (detected as card 2)
- **Internet connection** for API access

## Software Requirements

- Python 3.x
- OpenAI API key
- Required system packages:
  - ALSA utilities
  - espeak (text-to-speech fallback)
  - OpenCV libraries
  - ffmpeg (for OpenAI TTS audio playback)
  - mplayer (alternative audio player)
  - FLAC (for audio conversion)
  - PyAudio (for microphone input)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/robot-voice-interface.git
cd robot-voice-interface
```

### 2. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y python3-pip python3-opencv
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y espeak
sudo apt install -y ffmpeg mplayer
sudo apt install -y flac

# Install ALSA utilities for audio device management
sudo apt install -y alsa-utils
```

### 3. Install Python Packages

```bash
# Install required Python packages
pip3 install openai opencv-python pyaudio pyttsx3 speechrecognition
```

### 4. Configure OpenAI API Key

```bash
# Add your OpenAI API key to environment variables
echo "export OPENAI_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc
```

## Audio Device Configuration

The system is configured with separate devices for microphone input and speaker output:

- **Microphone Device**: `plughw:3,0` (USB PnP Sound Device)
- **Speaker Device**: `plughw:2,0` (iStore Audio)

You can verify your audio hardware configuration with:

```bash
# List recording devices
arecord -l

# List playback devices
aplay -l
```

If your devices are different, modify the settings in `device_manager.py`.

## Running the Interface

```bash
# Run the main interface (with simulation fallback for development)
python3 robot_voice_interface.py

# Run in hardware-only mode (disable simulation fallbacks)
python3 robot_voice_interface.py --no-sim

# Stop a running instance
python3 robot_voice_interface.py --stop
```

### Command-Line Options

- **Default Mode**: When run without options, the system will use simulation mode as a fallback when hardware is not available.
- **`--no-sim`**: Disables simulation mode, requiring actual hardware to be present. Use this on the Raspberry Pi with real devices.
- **`--stop`**: Stops any running instance of the robot voice interface.

### Expected Behavior

When running correctly, you should see:
1. "Robot voice interface initialized" message in the console
2. "Hello, I'm ready to talk" spoken through the speaker
3. The system will listen for your voice input through the microphone
4. When you speak, it will process your words through ChatGPT and respond verbally

### Using Object Recognition

The robot can identify objects through its camera. To activate this feature:
1. Use trigger phrases like "What do you see?", "What is this?", or "Identify this object"
2. The robot will respond with "Looking at what's in front of me..."
3. It will then take a photo with the camera and analyze the image using OpenAI Vision API
4. The robot will then verbally describe what it sees

This feature works best with good lighting and the object clearly visible to the camera.

### Voice Control Features

The robot now uses OpenAI's Text-to-Speech API to produce natural-sounding voices. You can control the voice using these commands:

#### Voice Selection
- **List available voices**: Say "list voices" or "show voices" to see all available options
- **Change voice**: Say "use voice [name]" or "change voice to [name]" to switch voices
  
Available voices include:
- **Nova**: Natural female voice (default)
- **Alloy**: Neutral voice
- **Echo**: Male voice
- **Fable**: Expressive male voice
- **Onyx**: Deep male voice
- **Shimmer**: Energetic female voice

#### Voice Speed Control
- **Speed up**: Say "speak faster" to increase speaking speed
- **Slow down**: Say "speak slower" to decrease speaking speed
- **Reset speed**: Say "reset voice speed" to return to normal speed

The system automatically falls back to espeak for text-to-speech if the OpenAI API is unavailable, ensuring the robot can always communicate.

## Testing Tools

We provide several testing scripts to verify your hardware setup:

### Voice Input and OpenAI Test

This simple test focuses only on the voice and OpenAI components:

```bash
python3 test_voice_openai.py
```

You can also test with simulated voice input:

```bash
# Create a simulated voice input
echo "Tell me a joke" > /tmp/test_sim_input.txt

# Run the test
python3 test_voice_openai.py
```

### Basic Command Test

```bash
python3 test_audio_commands.py
```

### Simple Audio Device Test

```bash
python3 audio_device_test.py
```

You can also list available devices:

```bash
python3 audio_device_test.py --list
```

### Comprehensive Robot Audio Test

```bash
python3 robot_audio_test.py
```

### Object Recognition Test

To test the camera and object recognition capabilities:

```bash
# Test with real camera
python3 test_object_recognition.py

# Test in simulation mode (no camera required)
python3 test_object_recognition.py --simulate
```

### Camera Diagnostics Tool

For comprehensive camera troubleshooting:

```bash
# Run full camera diagnostics
python3 test_camera_diagnostics.py
```

This tool will check:
- USB device connections
- Video device nodes
- Kernel driver status
- OpenCV camera compatibility
- Raspberry Pi camera module
- And provide troubleshooting tips

## Troubleshooting

### General Issues

1. **Stop a running instance**:
   If the application is stuck or you need to restart it:
   ```bash
   # Stop any running instances
   python3 robot_voice_interface.py --stop
   
   # Or kill processes manually
   pkill -f robot_voice_interface.py
   ```

2. **Force hardware-only mode**:
   If you want to ensure the application only uses real hardware:
   ```bash
   python3 robot_voice_interface.py --no-sim
   ```

### Audio Issues

1. **Check device availability**:
   ```bash
   aplay -l
   arecord -l
   ```

2. **Test direct recording and playback**:
   ```bash
   # Record 5 seconds of audio with USB PnP Sound Device
   arecord -D plughw:3,0 -d 5 -f cd test.wav
   
   # Play back the recording through iStore Audio
   aplay -D plughw:2,0 test.wav
   ```

3. **Check for busy devices**:
   ```bash
   # Kill any processes using audio devices
   pkill -f aplay
   pkill -f arecord
   ```

### Camera Issues

1. **Check if camera is detected**:
   ```bash
   ls -l /dev/video*
   ```

2. **View camera details**:
   ```bash
   v4l2-ctl --list-devices
   ```
   
3. **Verify USB camera connection**:
   ```bash
   lsusb
   ```
   Look for entries containing "camera" or "webcam" in the output.

4. **Check kernel driver**:
   ```bash
   dmesg | grep -i camera
   dmesg | grep -i video
   ```
   
5. **Try direct device access**:
   If your camera isn't appearing as /dev/video0, try other device paths:
   ```bash
   # For Raspberry Pi camera module:
   raspistill -o test.jpg
   
   # For USB webcams on different device nodes:
   python3 -c "import cv2; cap = cv2.VideoCapture(1); ret, frame = cap.read(); print(f'Camera 1 capture success: {ret}'); cap.release()"
   python3 -c "import cv2; cap = cv2.VideoCapture(2); ret, frame = cap.read(); print(f'Camera 2 capture success: {ret}'); cap.release()"
   ```
   
6. **Restart USB subsystem** (if camera was disconnected/reconnected):
   ```bash
   sudo modprobe -r uvcvideo
   sudo modprobe uvcvideo
   ```

### Object Recognition Issues

1. **Verify OpenAI API key is set**:
   ```bash
   echo $OPENAI_API_KEY
   ```
   If it's not set or incorrect, update it according to the installation instructions.

2. **Check camera functionality**:
   Use a simple camera test to ensure the camera is working properly:
   ```bash
   python3 -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); print(f'Camera capture success: {ret}'); cv2.imwrite('camera_test.jpg', frame) if ret else print('Camera capture failed'); cap.release()"
   ```

3. **Test OpenAI Vision API manually**:
   ```bash
   python3 -c "import os, openai, base64; client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY')); print('API key loaded'); print('If this fails, check your OpenAI API key')"
   ```

## Project Structure

- `robot_voice_interface.py` - Main application entry point with voice and vision interaction
- `device_manager.py` - Handles device initialization, hardware interfaces, and object recognition
- `ai_processor.py` - Manages OpenAI API interactions and conversation context
- `logger_config.py` - Configures logging system
- `*.md` - Documentation files including hardware setup instructions
- Various test scripts for hardware, audio, and API verification

## Log Files

Log files are automatically generated in the project directory with timestamps, e.g., `robot_logs_20250415_054915.log`.

## Development Mode

When running in environments without hardware (like development machines), the system will automatically detect the absence of audio devices and use simulated input/output for testing. 

### Simulation Mode

The system has built-in simulation capabilities for development and testing:

1. **Default Mode**: Automatically falls back to simulation when hardware is not detected
2. **Disable Simulation**: Use `--no-sim` flag to run in hardware-only mode
3. **Stop Running Instances**: Use `--stop` flag to terminate any running instances

Simulation mode provides:
- Randomized text inputs to simulate speech recognition
- Console output to simulate speech synthesis
- Simulated camera image recognition
- Fallback responses for all hardware interactions

## Git Repository Management

### Setting Up GitHub Repository

1. Create a new GitHub repository at https://github.com/new
2. Connect your local repository to GitHub:

```bash
# Add the GitHub repository as remote
git remote add origin https://github.com/your-username/robot-voice-interface.git

# Push your code to GitHub
git push -u origin main
```

### Important Git Practices

When managing this project with Git, make sure to:

1. Keep sensitive information out of the repository:
   - Never commit API keys or credentials
   - Use environment variables on the deployment system
   - The `.gitignore` file is already set up to exclude logs and sensitive files

2. Document dependencies:
   - All Python package requirements are listed in `requirements.txt`
   - System dependencies are documented in this README

3. When making changes:
   - Test thoroughly before committing
   - Use descriptive commit messages
   - Consider creating feature branches for major changes

### Updating the Repository

```bash
# Get latest changes
git pull origin main

# Make your changes to the files

# Add changed files
git add .

# Commit with a descriptive message
git commit -m "Description of your changes"

# Push to GitHub
git push origin main
```

## License

[MIT License](LICENSE)

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
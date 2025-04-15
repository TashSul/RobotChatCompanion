# Robot Voice Interface

A Python-powered intelligent voice interface for a humanoid robot, optimized for precise USB device management and seamless hardware integration on a Raspberry Pi 5.

## Overview

This project creates a voice-based conversational interface for a Hiwonder Ainex humanoid robot running on Raspberry Pi 5 with Ubuntu. The system utilizes:

- OpenAI GPT-4 for natural language processing and conversation
- USB camera for vision capabilities
- USB microphone and speaker for audio interactions
- Direct hardware access via ALSA commands for reliable device management

## Key Features

- Seamless voice interaction with ChatGPT API integration
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
  - espeak (text-to-speech)
  - OpenCV libraries

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
# Run the main interface
python3 robot_voice_interface.py
```

### Expected Behavior

When running correctly, you should see:
1. "Robot voice interface initialized" message in the console
2. "Hello, I'm ready to talk" spoken through the speaker
3. The system will listen for your voice input through the microphone
4. When you speak, it will process your words through ChatGPT and respond verbally

## Testing Tools

We provide several testing scripts to verify your hardware setup:

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

## Troubleshooting

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

## Project Structure

- `robot_voice_interface.py` - Main application entry point
- `device_manager.py` - Handles device initialization and hardware interfaces
- `ai_processor.py` - Manages OpenAI API interactions
- `logger_config.py` - Configures logging system
- `*.md` - Documentation files
- Various test scripts for hardware verification

## Log Files

Log files are automatically generated in the project directory with timestamps, e.g., `robot_logs_20250415_054915.log`.

## Development Mode

When running in environments without hardware (like development machines), the system will automatically detect the absence of audio devices and use simulated input/output for testing.

## Git Repository Management

When deploying to Git, make sure to:

1. Set up a `.gitignore` file to exclude logs and sensitive files:
   ```
   # .gitignore
   robot_logs_*.log
   .env
   __pycache__/
   *.py[cod]
   *$py.class
   ```

2. Use environment variables for the API key instead of hardcoding it
3. Ensure all Python requirements are documented in `requirements.txt`

To create a requirements file:
```bash
pip freeze > requirements.txt
```

## License

[MIT License](LICENSE)

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
# Raspberry Pi Setup Instructions for Robot Voice Interface

## 1. Initial Setup
1. Connect your USB devices to the Raspberry Pi:
   - USB Camera
   - USB Microphone
   - USB Speaker

## 2. Install Required System Packages
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

## 3. Install Python Packages
```bash
# Install required Python packages
pip3 install openai opencv-python pyaudio pyttsx3 speechrecognition
```

## 4. Copy Project Files
1. Copy all these Python files to your Raspberry Pi:
   - `robot_voice_interface.py`
   - `device_manager.py`
   - `ai_processor.py`
   - `logger_config.py`

## 5. Set Up OpenAI API Key
```bash
# Add your OpenAI API key to environment
echo "export OPENAI_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc
```

## 6. Verify Audio Devices
```bash
# List all audio devices
arecord -l  # Lists recording devices (microphones)
aplay -l    # Lists playback devices (speakers)
```

## 7. Run the Robot Interface
```bash
# Navigate to your project directory
cd /path/to/your/project

# Run the interface
python3 robot_voice_interface.py
```

## Troubleshooting

### If microphone isn't detected:
1. Check USB connection
2. Verify device with: `lsusb`
3. Test microphone: `arecord -d 5 test.wav`
4. Play back test: `aplay test.wav`

### If camera isn't detected:
1. Check USB connection
2. Verify with: `ls /dev/video*`
3. Test with: `v4l2-ctl --list-devices`

### If speaker isn't working:
1. Check USB connection
2. Set default device: `alsamixer`
3. Test with: `speaker-test -t wav`

## Expected Behavior
When running correctly, you should see:
1. "Robot voice interface initialized" message
2. "Hello, I'm ready to talk" spoken through speakers
3. The system will then listen for your voice input
4. When you speak, it will process your words through ChatGPT and respond

## Notes
- The system automatically detects USB devices
- If a device isn't found, check the device IDs in `device_manager.py`
- Log files are created in the same directory for debugging

# Raspberry Pi Setup Guide for Robot Voice Interface

This guide provides step-by-step instructions for setting up your Raspberry Pi 5 to work with the Robot Voice Interface system.

## Hardware Requirements

- Raspberry Pi 5 (recommended) or Raspberry Pi 4 (2GB+ RAM)
- USB Camera (compatible with V4L2)
- USB Microphone (or USB audio interface with mic input)
- Speaker (3.5mm or USB)
- MicroSD card (16GB+ recommended)
- Power supply appropriate for your Raspberry Pi model

## Software Setup

1. **Operating System Installation**
   - Install Ubuntu Server 22.04 LTS or Raspberry Pi OS (64-bit recommended)
   - Make sure to enable SSH during installation for remote access

2. **Initial Configuration**
   - Update your system:
     ```bash
     sudo apt update
     sudo apt upgrade -y
     ```
   - Set up timezone and locale:
     ```bash
     sudo dpkg-reconfigure tzdata
     sudo dpkg-reconfigure locales
     ```

3. **Camera Configuration**
   - For Raspberry Pi Camera Module:
     ```bash
     # Edit the config file
     sudo nano /boot/firmware/config.txt  # Ubuntu
     # OR
     sudo nano /boot/config.txt  # Raspberry Pi OS
     
     # Add these lines:
     start_x=1
     gpu_mem=128
     ```
   - For USB cameras, no additional configuration is needed

4. **Install Required Packages**
   - Install Python and development tools:
     ```bash
     sudo apt install -y python3-pip python3-dev python3-venv
     sudo apt install -y v4l-utils fswebcam
     sudo apt install -y portaudio19-dev python3-pyaudio
     sudo apt install -y espeak alsa-utils
     sudo apt install -y git cmake build-essential
     ```

5. **Audio Configuration**
   - Check audio devices:
     ```bash
     arecord -l  # List recording devices
     aplay -l    # List playback devices
     ```
   - Test speaker:
     ```bash
     speaker-test -D plughw:2,0 -c 2 -t wav
     ```
   - Test microphone:
     ```bash
     arecord -D plughw:3,0 -d 5 -f cd test.wav && aplay test.wav
     ```
   - Add your user to the audio group:
     ```bash
     sudo usermod -a -G audio $USER
     ```

## Installing the Robot Voice Interface

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-organization/robot-voice-interface.git
   cd robot-voice-interface
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure OpenAI API Key**
   ```bash
   # Create a .env file
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

## Running the Software

1. **Basic Test Run**
   ```bash
   python3 robot_voice_interface.py
   ```

2. **Running with Real Hardware**
   ```bash
   python3 robot_voice_interface.py --no-sim
   ```

3. **Creating a Service (for auto-start)**
   ```bash
   sudo nano /etc/systemd/system/robot-voice.service
   ```
   
   Add the following content:
   ```
   [Unit]
   Description=Robot Voice Interface
   After=network.target

   [Service]
   Type=simple
   User=pi  # Change to your username
   WorkingDirectory=/home/pi/robot-voice-interface  # Change to your path
   ExecStart=/home/pi/robot-voice-interface/venv/bin/python3 robot_voice_interface.py --no-sim
   Restart=on-failure
   Environment="OPENAI_API_KEY=your-api-key-here"

   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start the service:
   ```bash
   sudo systemctl enable robot-voice.service
   sudo systemctl start robot-voice.service
   ```

## Troubleshooting

### Camera Issues

If you're experiencing camera problems:

1. **Run the camera diagnostic script**:
   ```bash
   python3 test_camera_diagnostics.py
   ```

2. **Fix common camera issues**:
   ```bash
   sudo ./raspberry_pi_camera_fix.sh
   ```

3. **Check if the camera is detected**:
   ```bash
   ls -l /dev/video*
   v4l2-ctl --list-devices
   ```

4. **Test camera capture**:
   ```bash
   fswebcam -d /dev/video0 -r 640x480 test.jpg
   ```

### Audio Issues

If you're experiencing audio problems:

1. **Check audio devices again**:
   ```bash
   arecord -l
   aplay -l
   ```

2. **Test recording manually**:
   ```bash
   arecord -D plughw:3,0 -f S16_LE -c 1 -r 44100 -d 5 test.wav
   aplay test.wav
   ```

3. **Run the audio test script**:
   ```bash
   python3 robot_audio_test.py
   ```

4. **Kill any stuck audio processes**:
   ```bash
   sudo killall arecord
   ```

5. **Check for permission issues**:
   ```bash
   sudo chmod a+rw /dev/snd/*
   ```

### OpenAI API Key Issues

If you're having problems with the OpenAI API:

1. **Verify your API key is valid**
2. **Check your .env file or environment variable**:
   ```bash
   echo $OPENAI_API_KEY  # Should display your key
   ```
3. **Try setting the key directly**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

## Advanced Configuration

For detailed configuration options and integration with ROS (Robot Operating System):

1. **Install ROS 2 Humble** (for Ubuntu 22.04):
   Follow the installation guide at https://docs.ros.org/en/humble/Installation.html

2. **Enable ROS Integration**:
   ```bash
   python3 robot_voice_interface.py --no-sim
   ```

3. **Customize Wake Word**:
   The default wake word is "Beta". To customize or disable it, use:
   ```
   # In conversation:
   "Beta disable wake word"  # Disable wake word
   "Wake word on"            # Enable wake word
   ```

## Performance Tips

- If you're experiencing slow responses or high CPU usage:
  1. Lower camera resolution in device_manager.py
  2. Reduce microphone sample rate
  3. Enable GPU acceleration for OpenCV if available
  4. Close other applications running on the Pi

- For better speech recognition:
  1. Position the microphone close to the speaker
  2. Reduce background noise
  3. Speak clearly and at a moderate pace

## Updating the Software

To update to the latest version:

```bash
cd robot-voice-interface
git pull
pip install -r requirements.txt
```

## Security Considerations

- **API Key Safety**: Never share your OpenAI API key
- **Network Security**: If exposing to the internet, use proper firewall rules
- **Data Privacy**: Be aware that audio data is sent to OpenAI for processing
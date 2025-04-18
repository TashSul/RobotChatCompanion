#!/bin/bash
# Install Dependencies Script for Robot Voice Interface
# This script installs all required system packages for the robot voice interface

echo "===== Installing Robot Voice Interface Dependencies ====="
echo "This script will install all required packages for the robot voice interface"
echo "You may be prompted for your password for sudo commands"
echo ""

echo "Updating package lists..."
sudo apt update

echo ""
echo "Installing audio utilities and libraries..."
sudo apt install -y alsa-utils pulseaudio
sudo apt install -y flac # Required for SpeechRecognition FLAC conversion
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y espeak

echo ""
echo "Installing video utilities and libraries..."
sudo apt install -y v4l-utils # Video4Linux utilities for diagnostics
sudo apt install -y libopencv-dev python3-opencv # OpenCV libraries

echo ""
echo "Setting up permissions for audio and video devices..."
sudo usermod -a -G audio $USER
sudo usermod -a -G video $USER

echo ""
echo "Fixing video device permissions..."
if ls /dev/video* 1>/dev/null 2>&1; then
    sudo chmod 666 /dev/video*
    echo "Set permissions for video devices:"
    ls -l /dev/video*
else
    echo "No video devices found at /dev/video*"
fi

echo ""
echo "Installation complete!"
echo "You may need to log out and log back in for group permission changes to take effect."
echo "Try running the robot voice interface with: python3 robot_voice_interface.py"
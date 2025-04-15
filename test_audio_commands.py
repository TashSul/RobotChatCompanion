#!/usr/bin/env python3
"""
Test Script for ALSA Audio Commands

This script tests the basic audio commands (arecord and aplay) 
to ensure they are installed and working properly.

Usage:
    python3 test_audio_commands.py
"""

import subprocess
import os
import tempfile
import sys

def test_command_existence():
    """Test if the required commands are installed"""
    print("Testing for required commands...")
    commands = ["arecord", "aplay", "espeak", "speaker-test"]
    missing = []
    
    for cmd in commands:
        try:
            result = subprocess.run(f"which {cmd}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                print(f"✓ {cmd} found at: {path}")
            else:
                print(f"✗ {cmd} not found!")
                missing.append(cmd)
        except Exception as e:
            print(f"✗ Error checking for {cmd}: {str(e)}")
            missing.append(cmd)
    
    if missing:
        print("\nMissing commands: " + ", ".join(missing))
        print("\nTo install these commands on Ubuntu/Raspberry Pi, run:")
        print("sudo apt-get install alsa-utils espeak")
        print("\nOn Replit, install system dependencies:")
        print("Use the packager_tool with 'alsa-utils' and 'espeak'")
        return False
    else:
        print("\nAll required commands are available!")
        return True

def test_audio_listing():
    """Test listing audio devices"""
    print("\nListing audio devices...")
    try:
        print("\n=== Recording devices (arecord -l) ===")
        subprocess.run("arecord -l", shell=True)
        
        print("\n=== Playback devices (aplay -l) ===")
        subprocess.run("aplay -l", shell=True)
        
        return True
    except Exception as e:
        print(f"Error listing audio devices: {str(e)}")
        return False

def test_audio_capabilities():
    """Test basic audio functionality"""
    if not test_command_existence():
        return False
    
    if not test_audio_listing():
        return False
    
    # Create a test file
    test_file = os.path.join(tempfile.gettempdir(), "test_message.txt")
    with open(test_file, "w") as f:
        f.write("This is a test of the audio system.")
    
    # Define test devices based on hardware detection
    mic_device = "plughw:3,0"   # USB PnP Sound Device (microphone)
    speaker_device = "plughw:2,0"  # iStore Audio (speaker)
    
    # Test text-to-speech with aplay
    print(f"\nTesting text-to-speech with espeak and aplay on {speaker_device}...")
    try:
        # Using espeak to generate speech to play through aplay
        wav_file = os.path.join(tempfile.gettempdir(), "test_speech.wav")
        
        # First, generate wav file with espeak
        subprocess.run(f"espeak -f {test_file} -w {wav_file}", shell=True, check=True)
        
        # Then play with aplay
        print("Playing audio... (you should hear speech)")
        subprocess.run(f"aplay -D {speaker_device} {wav_file}", shell=True, check=True)
        print("✓ Speech playback successful!")
    except Exception as e:
        print(f"✗ Error during speech playback: {str(e)}")
        return False
    
    # Test recording with arecord
    print(f"\nTesting recording with arecord on {mic_device}...")
    try:
        record_file = os.path.join(tempfile.gettempdir(), "test_recording.wav")
        print("Recording 3 seconds of audio... (please speak now)")
        subprocess.run(f"arecord -D {mic_device} -d 3 -f cd {record_file}", shell=True, check=True)
        
        print("Playing back recording...")
        subprocess.run(f"aplay -D {speaker_device} {record_file}", shell=True, check=True)
        print("✓ Recording and playback successful!")
    except Exception as e:
        print(f"✗ Error during recording test: {str(e)}")
        return False
    
    print("\nAll audio tests completed successfully!")
    return True

if __name__ == "__main__":
    print("=== ALSA Audio Command Test ===\n")
    
    success = test_audio_capabilities()
    
    if success:
        print("\nAll tests PASSED! Your audio commands and devices are working properly.")
        sys.exit(0)
    else:
        print("\nSome tests FAILED. Please check the error messages above.")
        sys.exit(1)
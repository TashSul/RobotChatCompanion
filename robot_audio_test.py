#!/usr/bin/env python3
"""
Robot Audio Test Script for Raspberry Pi

This script tests the audio functionality of the robot, using arecord and aplay
directly to ensure compatibility with the USB audio devices.

Usage:
    python3 robot_audio_test.py
"""

import os
import subprocess
import time
import tempfile
import argparse

# Default device settings based on hardware detection
DEFAULT_MIC = "plughw:3,0"  # USB PnP Sound Device (microphone)
DEFAULT_SPEAKER = "plughw:2,0"  # iStore Audio (speaker)
TEMP_DIR = tempfile.gettempdir()

def test_speaker(speaker_device):
    """Test the speaker with a simple tone"""
    print(f"\n=== Testing Speaker [{speaker_device}] ===")
    try:
        # Test with a simple tone
        print("Playing a test tone... (you should hear a beep)")
        result = subprocess.run(
            f"speaker-test -D {speaker_device} -c 1 -t sine -f 440 -l 1",
            shell=True,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            print(f"WARNING: Speaker test failed with error: {result.stderr.decode()}")
            return False
            
        # Test with espeak
        print("\nTesting text-to-speech... (you should hear a voice)")
        message = "Hello, this is a test of the robot voice system"
        
        # Create temporary file for the message
        text_file = os.path.join(TEMP_DIR, "test_speech.txt")
        with open(text_file, "w") as f:
            f.write(message)
            
        # Use espeak to generate speech
        subprocess.run(
            f"espeak -f {text_file} --stdout | aplay -D {speaker_device}",
            shell=True
        )
        
        print("Speaker test completed.")
        return True
        
    except Exception as e:
        print(f"ERROR testing speaker: {str(e)}")
        return False

def test_microphone(mic_device, speaker_device):
    """Test the microphone by recording and playing back"""
    print(f"\n=== Testing Microphone [{mic_device}] ===")
    
    try:
        # Record audio
        wav_file = os.path.join(TEMP_DIR, "test_recording.wav")
        print("Recording 5 seconds of audio... (please speak now)")
        
        subprocess.run(
            f"arecord -D {mic_device} -d 5 -f cd {wav_file}",
            shell=True,
            check=True
        )
        
        print("\nPlaying back the recording...")
        subprocess.run(
            f"aplay -D {speaker_device} {wav_file}",
            shell=True,
            check=True
        )
        
        print("Microphone test completed.")
        return True
        
    except Exception as e:
        print(f"ERROR testing microphone: {str(e)}")
        return False

def run_comprehensive_test(mic_device, speaker_device):
    """Run a comprehensive test of all audio functionality"""
    print("\n===== STARTING COMPREHENSIVE AUDIO TEST =====")
    print(f"Microphone device: {mic_device}")
    print(f"Speaker device: {speaker_device}")
    
    # Test 1: Basic device check
    print("\n--- Test 1: Checking audio devices ---")
    try:
        # List recording devices
        print("Available recording devices:")
        subprocess.run("arecord -l", shell=True)
        
        # List playback devices
        print("\nAvailable playback devices:")
        subprocess.run("aplay -l", shell=True)
    except Exception as e:
        print(f"Error listing devices: {str(e)}")
    
    # Test 2: Speaker test
    print("\n--- Test 2: Speaker Test ---")
    speaker_ok = test_speaker(speaker_device)
    
    # Test 3: Microphone test
    print("\n--- Test 3: Microphone Test ---")
    mic_ok = test_microphone(mic_device, speaker_device)
    
    # Results
    print("\n===== TEST RESULTS =====")
    print(f"Speaker test: {'PASSED' if speaker_ok else 'FAILED'}")
    print(f"Microphone test: {'PASSED' if mic_ok else 'FAILED'}")
    
    if speaker_ok and mic_ok:
        print("\nAll tests PASSED! Your audio devices are working correctly.")
    else:
        print("\nSome tests FAILED. Please check your audio devices and connections.")
    
    print("\nTest completed.")

if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Test robot audio devices")
    parser.add_argument("--mic", default=DEFAULT_MIC, help=f"Microphone device (default: {DEFAULT_MIC})")
    parser.add_argument("--speaker", default=DEFAULT_SPEAKER, help=f"Speaker device (default: {DEFAULT_SPEAKER})")
    
    args = parser.parse_args()
    
    # Run the test
    run_comprehensive_test(args.mic, args.speaker)
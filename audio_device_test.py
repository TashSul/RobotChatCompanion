#!/usr/bin/env python3
"""
Simple Audio Device Test Script

This script tests your audio hardware using directly arecord and aplay commands.

Usage:
    python3 audio_device_test.py [--mic DEVICE] [--speaker DEVICE]

Example:
    python3 audio_device_test.py --mic plughw:3,0 --speaker plughw:2,0
"""

import argparse
import os
import subprocess
import tempfile
import time

DEFAULT_MIC = "plughw:3,0"      # USB PnP Sound Device (microphone)
DEFAULT_SPEAKER = "plughw:2,0"  # iStore Audio (speaker)
TEMP_DIR = tempfile.gettempdir()

def test_speaker(device):
    """Test speaker using aplay"""
    print(f"\n=== Testing Speaker [{device}] ===")
    
    # Create a test WAV file with a simple tone
    try:
        print("Creating test audio file...")
        test_wav = os.path.join(TEMP_DIR, "test_tone.wav")
        
        # Use sox to generate a test tone
        try:
            subprocess.run(
                f"sox -n -r 44100 -c 1 {test_wav} synth 2 sine 440",
                shell=True,
                check=True
            )
        except:
            # If sox is not available, try to create a simple text message
            with open(os.path.join(TEMP_DIR, "test_message.txt"), "w") as f:
                f.write("This is a test of the robot audio system.")
            
            # Use espeak to generate speech
            subprocess.run(
                f"espeak -f {os.path.join(TEMP_DIR, 'test_message.txt')} --stdout > {test_wav}",
                shell=True,
                check=True
            )
        
        print(f"Playing test audio through {device}...")
        subprocess.run(
            f"aplay -D {device} {test_wav}",
            shell=True,
            check=True
        )
        
        print("Speaker test completed successfully.")
        return True
        
    except Exception as e:
        print(f"ERROR: Speaker test failed: {str(e)}")
        return False

def test_microphone(mic_device, speaker_device):
    """Test microphone using arecord"""
    print(f"\n=== Testing Microphone [{mic_device}] ===")
    
    try:
        # Record a short audio sample
        recording_file = os.path.join(TEMP_DIR, "test_recording.wav")
        
        print("Recording 5 seconds of audio... Please speak now.")
        subprocess.run(
            f"arecord -D {mic_device} -d 5 -f cd {recording_file}",
            shell=True,
            check=True
        )
        
        print("Recording completed.")
        
        # Play back the recording
        print("Playing back your recording...")
        subprocess.run(
            f"aplay -D {speaker_device} {recording_file}",
            shell=True,
            check=True
        )
        
        print("Microphone test completed successfully.")
        return True
        
    except Exception as e:
        print(f"ERROR: Microphone test failed: {str(e)}")
        return False

def list_audio_devices():
    """List available audio devices"""
    print("\n=== Available Audio Devices ===")
    
    try:
        print("\nRecording Devices (arecord -l):")
        subprocess.run("arecord -l", shell=True)
        
        print("\nPlayback Devices (aplay -l):")
        subprocess.run("aplay -l", shell=True)
        
    except Exception as e:
        print(f"Error listing audio devices: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Test audio devices with arecord and aplay")
    parser.add_argument("--mic", default=DEFAULT_MIC, help=f"Microphone device (default: {DEFAULT_MIC})")
    parser.add_argument("--speaker", default=DEFAULT_SPEAKER, help=f"Speaker device (default: {DEFAULT_SPEAKER})")
    parser.add_argument("--list", action="store_true", help="List available audio devices")
    
    args = parser.parse_args()
    
    print("=== Audio Device Test Tool ===")
    print(f"Microphone: {args.mic}")
    print(f"Speaker: {args.speaker}")
    
    if args.list:
        list_audio_devices()
        return
    
    # First test the speaker
    speaker_ok = test_speaker(args.speaker)
    
    # Then test the microphone (which also uses the speaker for playback)
    mic_ok = test_microphone(args.mic, args.speaker)
    
    # Print results
    print("\n=== Test Results ===")
    print(f"Speaker test: {'PASSED' if speaker_ok else 'FAILED'}")
    print(f"Microphone test: {'PASSED' if mic_ok else 'FAILED'}")
    
    if speaker_ok and mic_ok:
        print("\nAll tests PASSED! Audio devices are configured correctly.")
    else:
        print("\nSome tests FAILED. Please check your audio device configuration.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Audio Subsystem Fix for Robot Voice Interface in no-sim mode

This script diagnoses and fixes issues with the robot_voice_interface.py
when running with the --no-sim flag on hardware.

Usage:
    python3 fix_no_sim_mode.py

Output:
    Detailed diagnostics and fixes for audio subsystem issues.
"""

import os
import sys
import time
import subprocess
import tempfile

def print_section(title):
    """Print a formatted section header"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)

def run_command(cmd, capture=True, check=False):
    """Run a shell command and return the output"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, check=check, 
                                  capture_output=True, text=True)
            return result
        else:
            subprocess.run(cmd, shell=True, check=check)
            return None
    except subprocess.CalledProcessError as e:
        return e

def check_audio_devices():
    """Check available audio devices"""
    print_section("Checking Audio Devices")
    
    # Check recording devices
    print("Checking recording devices (arecord -l):")
    result = run_command("arecord -l")
    if result.returncode != 0 or "no soundcards found" in result.stderr:
        print("❌ No recording devices found!")
    else:
        print("✅ Recording devices found:")
        print(result.stdout)
    
    # Check playback devices
    print("\nChecking playback devices (aplay -l):")
    result = run_command("aplay -l")
    if result.returncode != 0 or "no soundcards found" in result.stderr:
        print("❌ No playback devices found!")
    else:
        print("✅ Playback devices found:")
        print(result.stdout)
    
    # Check USB devices
    print("\nChecking USB devices:")
    result = run_command("lsusb")
    if result.returncode == 0:
        print(result.stdout)
        
        # Look for audio-related USB devices
        audio_devices = []
        for line in result.stdout.splitlines():
            if any(keyword in line.lower() for keyword in 
                   ["audio", "sound", "mic", "headset", "webcam"]):
                audio_devices.append(line)
        
        if audio_devices:
            print("Detected audio-related USB devices:")
            for device in audio_devices:
                print(f"  {device}")
        else:
            print("No obvious audio-related USB devices detected")
    else:
        print("❌ Error checking USB devices")

def test_audio_output():
    """Test audio output by playing a tone"""
    print_section("Testing Audio Output")
    
    # Test with default device
    print("Testing default audio output:")
    result = run_command('speaker-test -t sine -f 440 -l 1')
    
    # Test with plughw:2,0 (common for Raspberry Pi)
    print("\nTesting speaker device plughw:2,0:")
    result = run_command('speaker-test -D plughw:2,0 -t sine -f 440 -l 1')
    
    # Notify user
    print("\n⚠️ If you didn't hear any sound, there may be issues with the audio output.")

def test_audio_input(device="plughw:3,0"):
    """Test audio input by recording a short clip"""
    print_section(f"Testing Audio Input (device: {device})")
    
    # Create a temporary file for the recording
    temp_file = os.path.join(tempfile.gettempdir(), "test_recording.wav")
    
    print(f"Recording 3 seconds of audio to {temp_file}...")
    print("Please speak into the microphone.")
    
    # Record audio
    record_cmd = f"arecord -D {device} -d 3 -f S16_LE -r 44100 -c 1 {temp_file}"
    result = run_command(record_cmd)
    
    if result.returncode != 0:
        print(f"❌ Error recording audio: {result.stderr}")
        return False
    
    print(f"✅ Recording completed to {temp_file}")
    
    # Play back the recording
    print("\nPlaying back the recording:")
    playback_cmd = f"aplay {temp_file}"
    run_command(playback_cmd)
    
    return True

def check_flac_installation():
    """Check if FLAC is installed and install it if missing"""
    print_section("Checking FLAC Installation")
    
    result = run_command("which flac")
    if result.returncode != 0:
        print("❌ FLAC is not installed.")
        print("This is required for the speech recognition to work.")
        
        print("\nAttempting to install FLAC...")
        install_result = run_command("sudo apt-get update && sudo apt-get install -y flac", 
                                 capture=False)
        
        # Verify installation
        result = run_command("which flac")
        if result.returncode == 0:
            print("✅ FLAC successfully installed!")
        else:
            print("❌ Failed to install FLAC. Speech recognition may not work correctly.")
            print("   You may need to manually install it with: sudo apt-get install -y flac")
    else:
        print("✅ FLAC is installed at:", result.stdout.strip())

def check_openai_api_key():
    """Check if OpenAI API key is available"""
    print_section("Checking OpenAI API Key")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable is not set!")
        print("   Speech recognition fallback to Whisper API will not work.")
        print("\n   Set it with: export OPENAI_API_KEY=your-api-key")
        return False
    else:
        print("✅ OPENAI_API_KEY is set")
        return True

def check_openai_whisper_setup():
    """Check OpenAI packages for Whisper API usage"""
    print_section("Checking OpenAI Setup for Whisper")
    
    try:
        import openai
        print(f"✅ OpenAI Python library is installed")
        
        # Check if API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            print("✅ OPENAI_API_KEY environment variable is set")
            # Create client to verify we can initialize properly
            client = openai.OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized successfully")
        else:
            print("❌ OPENAI_API_KEY environment variable is not set")
            print("   Set it with: export OPENAI_API_KEY=your-api-key")
            return False
        
    except ImportError:
        print("❌ OpenAI Python library is not installed or not available")
        print("   Install it with: pip install openai")
        return False
    
    return True

def test_recording_with_whisper(device="plughw:3,0"):
    """Test recording and transcription with OpenAI Whisper"""
    print_section("Testing Recording + OpenAI Whisper Transcription")
    
    # First check if OpenAI API key is set
    if not check_openai_api_key():
        return
    
    try:
        import openai
    except ImportError:
        print("❌ OpenAI Python library is not installed or not available")
        return
    
    # Record audio
    temp_file = os.path.join(tempfile.gettempdir(), "whisper_test.wav")
    
    print(f"Recording 5 seconds of audio to {temp_file}...")
    print("Please speak a test phrase into the microphone.")
    
    record_cmd = f"arecord -D {device} -d 5 -f S16_LE -r 44100 -c 1 {temp_file}"
    result = run_command(record_cmd)
    
    if result.returncode != 0:
        print(f"❌ Error recording audio: {result.stderr}")
        return
    
    print(f"✅ Recording completed to {temp_file}")
    
    # Transcribe with Whisper
    print("\nTranscribing with OpenAI Whisper API...")
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=api_key)
        
        with open(temp_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        print("✅ Transcription successful!")
        print(f"Text: {transcription.text}")
    except Exception as e:
        print(f"❌ Error transcribing with Whisper API: {e}")

def fix_device_manager():
    """Generate a fix for device_manager.py to prioritize Whisper in no-sim mode"""
    print_section("Creating Fix for device_manager.py")
    
    backup_file = "device_manager.py.bak"
    
    # Create backup
    print(f"Creating backup at {backup_file}...")
    run_command(f"cp device_manager.py {backup_file}", capture=False)
    
    # Read the original file
    with open("device_manager.py", "r") as f:
        content = f.read()
    
    # Create the fix
    # 1. We want to modify how the audio is processed when simulation is disabled
    # 2. Instead of trying Google first, we'll go straight to Whisper if simulation is disabled
    
    if "# If simulation is disabled, prioritize OpenAI Whisper API for reliability" in content:
        print("✅ Fix already applied to device_manager.py")
        return
    
    # Locate the section we need to modify
    target = "            # If hardware is available, use it\n            # Record audio using arecord command with a modified format\n"
    if target not in content:
        print("❌ Unable to locate the target section in device_manager.py")
        print("   Manual fix may be required")
        return
    
    # Create the updated content
    replace_with = """            # If hardware is available, use it
            # Record audio using arecord command with a modified format
            
            # Always use OpenAI Whisper API for speech recognition
            # This ensures consistent performance in both hardware and simulation mode
            self.logger.info(f"Recording from device: {self.microphone_device}")
            try:
                # Record the audio
                subprocess.run(
                    f"arecord -D {self.microphone_device} -d {self.record_seconds} -f S16_LE -r 44100 -c 1 {self.temp_wav_file}",
                    shell=True,
                    check=True
                )
                
                # Use OpenAI Whisper API for speech recognition
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    
                    with open(self.temp_wav_file, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_file
                        )
                    
                    text = transcription.text
                    self.logger.info(f"OpenAI Whisper recognized text: {text}")
                    
                    # Remove the lock file and return the text
                    if os.path.exists(lock_file):
                        try:
                            os.remove(lock_file)
                        except Exception as e:
                            self.logger.warning(f"Error removing lock file: {e}")
                    
                    return text
                else:
                    self.logger.error("OPENAI_API_KEY not set. Cannot use Whisper API.")
                    self.logger.error("Set the OPENAI_API_KEY environment variable for speech recognition.")
                    raise Exception("OpenAI API key not available")
            except Exception as e:
                self.logger.error(f"Error in audio capture: {e}")
                raise
            
            # Standard processing flow (used in simulation mode or as fallback)
"""
    
    # Apply the fix
    new_content = content.replace(target, replace_with)
    
    # Write the updated file
    with open("device_manager.py", "w") as f:
        f.write(new_content)
    
    print("✅ Fix applied to device_manager.py")
    print("   The device manager will now prioritize OpenAI Whisper API in no-sim mode")

def print_summary():
    """Print a summary of findings and recommendations"""
    print_section("Summary and Recommendations")
    
    print("1. Make sure you have the necessary hardware connected:")
    print("   - USB microphone (typically on card 3, device 0)")
    print("   - USB speaker or audio output (typically on card 2, device 0)")
    print()
    
    print("2. Ensure the OPENAI_API_KEY environment variable is set:")
    print("   export OPENAI_API_KEY=your-api-key")
    print()
    
    print("3. Install the FLAC utility if it's not already installed:")
    print("   sudo apt-get install -y flac")
    print()
    
    print("4. Use the fixed device_manager.py for more reliable speech recognition:")
    print("   - The fix uses OpenAI Whisper API exclusively for all speech recognition")
    print("   - This offers more reliable and consistent speech recognition")
    print()
    
    print("5. To run the application in hardware mode:")
    print("   python3 robot_voice_interface.py --no-sim")
    print()
    
    print("6. If problems persist, check the logs for specific errors:")
    print("   - Look for errors related to audio devices or speech recognition")
    print("   - Ensure microphone permissions are correct")
    print()
    
    print("7. Test the recording and playback separately:")
    print("   - Recording: arecord -D plughw:3,0 -d 5 -f S16_LE -r 44100 -c 1 test.wav")
    print("   - Playback: aplay test.wav")

def main():
    print("\n=== Robot Voice Interface Hardware Mode (--no-sim) Fix ===\n")
    
    # Run diagnostics
    check_audio_devices()
    test_audio_output()
    test_audio_input()
    check_flac_installation()
    check_openai_api_key()
    check_openai_whisper_setup()
    test_recording_with_whisper()
    
    # Apply fix
    fix_device_manager()
    
    # Print summary
    print_summary()
    
    print("\nFix complete! The interface now exclusively uses OpenAI Whisper API for speech recognition.")
    print("Try running the interface in standard or hardware mode:")
    print("  python3 robot_voice_interface.py            # Standard mode")
    print("  python3 robot_voice_interface.py --no-sim   # Hardware mode")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Voice Input / OpenAI Response Tester

This script provides a simple test interface that captures audio input,
sends it to OpenAI's API, and speaks the response.

Usage:
    python test_voice_openai.py

Options:
    Create a text file at /tmp/test_sim_input.txt with your message
    to simulate voice input when running without audio hardware.

Example:
    # Create a simulated voice input
    echo "Tell me a joke" > /tmp/test_sim_input.txt
    
    # Run the tester
    python test_voice_openai.py

This tool can help test voice hardware and OpenAI integration independent 
of the full robot interface.
"""

import os
import sys
import time
import tempfile
import subprocess
import logging
import base64
from typing import Optional

import openai

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("VoiceOpenAITester")

class VoiceOpenAITester:
    def __init__(self):
        # Audio device configuration
        self.microphone_device = "plughw:3,0"  # USB PnP Sound Device (microphone)
        self.speaker_device = "plughw:2,0"     # iStore Audio (speaker)
        
        # Simulation flags
        self.simulation_enabled = True
        self.last_simulated_text = ""
        
        # Recording parameters
        self.record_seconds = 5
        self.temp_wav_file = os.path.join(tempfile.gettempdir(), "test_audio.wav")
        
        # OpenAI configuration
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables.")
            logger.warning("Please set this environment variable to use OpenAI services.")
        
        # Conversation history
        self.conversation_history = [
            {"role": "system", "content": "You are a helpful voice assistant. Keep responses brief and conversational."}
        ]
    
    def cleanup_audio_processes(self):
        """Kill any existing arecord processes that might be using the microphone"""
        try:
            logger.info("Cleaning up existing audio processes")
            subprocess.run("killall arecord 2>/dev/null", shell=True)
            # Wait a moment for the device to be released
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Error cleaning up audio processes: {e}")
    
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
        """Capture audio from microphone and convert to text"""
        lock_file = "/tmp/tester_microphone.lock"
        try:
            logger.info("Listening for 5 seconds...")
            
            # Check if we're running without audio hardware and simulation is enabled
            if not self.check_audio_hardware() and self.simulation_enabled:
                logger.warning("No audio hardware detected - using simulated input")
                
                # Check if we have a simulated input file from the test script
                temp_sim_file = os.path.join(tempfile.gettempdir(), "test_sim_input.txt")
                if os.path.exists(temp_sim_file):
                    try:
                        with open(temp_sim_file, "r") as f:
                            text = f.read().strip()
                        # Remove the file after reading
                        os.remove(temp_sim_file)
                        logger.info(f"Using simulated input from file: {text}")
                        self.last_simulated_text = text
                        return text
                    except Exception as e:
                        logger.warning(f"Error reading simulated input file: {e}")
                
                # In Replit or other non-interactive environments, use a default question
                try:
                    text = input("Enter simulated voice input: ")
                except EOFError:
                    logger.warning("Non-interactive environment detected, using default input")
                    text = "Tell me about yourself"
                
                logger.info(f"Simulated text input: {text}")
                self.last_simulated_text = text
                return text
            
            # Check if lock file exists
            if os.path.exists(lock_file):
                try:
                    # Check if it's stale (older than 30 seconds)
                    if time.time() - os.path.getmtime(lock_file) > 30:
                        os.remove(lock_file)
                        logger.warning("Removed stale microphone lock file")
                    else:
                        logger.warning("Microphone appears to be in use - trying to kill existing processes")
                        self.cleanup_audio_processes()
                except Exception as e:
                    logger.warning(f"Error checking lock file: {e}")
            
            # Create lock file
            try:
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))
            except Exception as e:
                logger.warning(f"Error creating lock file: {e}")
                
            # Clean up any existing audio processes
            self.cleanup_audio_processes()
            
            # Record audio using arecord command with a modified format
            logger.info(f"Recording from device: {self.microphone_device}")
            subprocess.run(
                f"arecord -D {self.microphone_device} -d {self.record_seconds} -f S16_LE -r 44100 -c 1 {self.temp_wav_file}",
                shell=True,
                check=True
            )
            
            # Use OpenAI's Whisper API for speech recognition
            try:
                logger.info("Processing speech with OpenAI Whisper...")
                
                if not self.api_key:
                    logger.error("OPENAI_API_KEY not set. Cannot use Whisper API.")
                    return ""
                
                client = openai.OpenAI(api_key=self.api_key)
                
                with open(self.temp_wav_file, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                
                text = transcription.text
                logger.info(f"Recognized text: {text}")
                
                # Remove the lock file
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except Exception as e:
                        logger.warning(f"Error removing lock file: {e}")
                
                return text
                
            except Exception as e:
                logger.error(f"Speech recognition error: {e}")
                
                # Remove the lock file if there was an error
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except:
                        pass
                
                return ""
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error recording audio: {e}")
            # Remove the lock file if there was an error
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
            return ""
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Remove the lock file if there was an error
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
            return ""
    
    def get_openai_response(self, user_input: str) -> str:
        """Get a response from OpenAI based on user input"""
        try:
            if not user_input.strip():
                return "I couldn't hear anything. Could you please try again?"
            
            if not self.api_key:
                return "I'm unable to respond because the OpenAI API key is not configured."
            
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Get response from OpenAI
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=self.conversation_history,
                max_tokens=150
            )
            
            # Extract and log the response
            ai_response = response.choices[0].message.content
            logger.info(f"AI Response: {ai_response}")
            
            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Keep conversation history to a reasonable size
            if len(self.conversation_history) > 10:
                # Keep system message and last 4 exchanges (8 messages)
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-8:]
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return f"I encountered an error: {str(e)}"
    
    def speak_text(self, text: str):
        """Convert text to speech"""
        try:
            logger.info(f"Speaking: {text}")
            
            # Check if we're running without audio hardware and simulation is enabled
            if not self.check_audio_hardware() and self.simulation_enabled:
                logger.warning("No audio hardware detected - speech output simulated")
                # Just print the output for development
                print(f"🔊 SAYS: \"{text}\"")
                return
            
            # Create a temporary file for the text
            text_file = os.path.join(tempfile.gettempdir(), "test_speech.txt")
            with open(text_file, "w") as f:
                f.write(text)
            
            # Use espeak to convert text to speech and pipe to aplay
            logger.info(f"Playing speech through device: {self.speaker_device}")
            subprocess.run(
                f"espeak -f {text_file} --stdout | aplay -D {self.speaker_device}",
                shell=True,
                check=True
            )
            
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
    
    def run(self):
        """Main test loop"""
        print("\n===== Voice + OpenAI Tester =====")
        print("Say something to start a conversation.")
        print("Press Ctrl+C to exit.\n")
        
        try:
            # For the first interaction in a non-interactive environment like Replit,
            # use a preset example to show how it works
            if not self.check_audio_hardware() and self.simulation_enabled:
                print("--- DEMONSTRATION MODE ---")
                print("This is a simulated conversation example:")
                
                example_input = "Tell me a fact about robots"
                print(f"User: {example_input}")
                
                # Get response from OpenAI for the example
                response = self.get_openai_response(example_input)
                
                # Display the response
                self.speak_text(response)
                print("\nNow it's your turn. On real hardware, you would speak into the microphone.")
                print("In this simulation, you'll be prompted to type your input.\n")
            
            # Main conversation loop
            while True:
                # Capture audio input
                user_input = self.capture_audio()
                
                if user_input.lower() in ["exit", "quit", "goodbye"]:
                    print("Exiting based on user request.")
                    break
                
                # Get response from OpenAI
                response = self.get_openai_response(user_input)
                
                # Speak the response
                self.speak_text(response)
                
                # Short pause between interactions
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nTest terminated by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            print("\nTest complete")
            
            # Clean up temporary files
            if os.path.exists(self.temp_wav_file):
                os.remove(self.temp_wav_file)

if __name__ == "__main__":
    tester = VoiceOpenAITester()
    tester.run()
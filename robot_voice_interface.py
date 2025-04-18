#!/usr/bin/env python3
"""
Robot Voice Interface

This script provides a voice-controlled interface for robot interaction
using speech recognition, ChatGPT, and ROS integration for Ainex humanoid robot.

Usage:
    python3 robot_voice_interface.py [--no-sim] [--stop] [--no-ros]

Options:
    --no-sim    Disable simulation mode (requires real hardware)
    --stop      Stop all running instances of the application
    --no-ros    Disable ROS integration (no physical movement)

Example:
    python3 robot_voice_interface.py
    python3 robot_voice_interface.py --no-sim
    python3 robot_voice_interface.py --stop
    python3 robot_voice_interface.py --no-ros
"""

import time
import signal
import sys
import argparse
from logger_config import setup_logger
from device_manager import DeviceManager
from ai_processor import AIProcessor
from ros_controller import RosController
from error_translator import ErrorTranslator, ErrorContext

class RobotVoiceInterface:
    def __init__(self, ros_enabled=True):
        self.logger = setup_logger()
        self.device_manager = DeviceManager(self.logger)
        self.ai_processor = AIProcessor(self.logger)
        self.error_translator = ErrorTranslator(self.logger)
        self.running = True
        self.ros_enabled = ros_enabled
        
        # Wake word configuration
        self.wake_word = "beta"
        self.wake_word_enabled = True
        self.wake_word_active = False
        self.wake_word_timeout = 30  # seconds
        self.last_wake_time = 0
        
        # Initialize ROS controller if enabled
        if self.ros_enabled:
            self.ros_controller = RosController(self.logger)
        else:
            self.ros_controller = None
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Shutdown signal received")
        self.running = False

    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            self.device_manager.initialize_devices()
            self.logger.info("Robot voice interface initialized - ready for operation on Raspberry Pi")
            return True
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Initialization error: {error_msg}")
            
            # Determine the appropriate error context based on the error message
            error_context = ErrorContext.GENERAL
            if "camera" in error_msg.lower() or "cv2" in error_msg.lower() or "video" in error_msg.lower():
                error_context = ErrorContext.CAMERA
            elif "microphone" in error_msg.lower() or "audio input" in error_msg.lower() or "arecord" in error_msg.lower():
                error_context = ErrorContext.MICROPHONE
            elif "speaker" in error_msg.lower() or "audio output" in error_msg.lower() or "aplay" in error_msg.lower():
                error_context = ErrorContext.SPEAKER
            elif "device" in error_msg.lower() or "hardware" in error_msg.lower() or "usb" in error_msg.lower():
                error_context = ErrorContext.HARDWARE
                
            # Translate the error message to user-friendly language
            friendly_error = self.error_translator.translate_error(error_msg, error_context)
            self.logger.info(f"User-friendly explanation: {friendly_error}")
            
            return False

    def run(self):
        """Main operation loop"""
        if not self.initialize():
            error_msg = "Initialization incomplete - some features may not work until running on Raspberry Pi"
            self.logger.warning(error_msg)

        try:
            self.device_manager.speak_text("Hello, I'm ready to talk")
        except Exception as e:
            error_msg = str(e)
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.SPEAKER)
            self.logger.warning(f"Initial greeting failed: {error_msg}")
            self.logger.info(f"User-friendly explanation: {friendly_error}")

        while self.running:
            try:
                # Capture audio input
                user_input = self.device_manager.capture_audio()

                if user_input:
                    # Check for wake word if enabled
                    if self.wake_word_enabled:
                        user_input_lower = user_input.lower()
                        
                        # Check if this is just the wake word by itself
                        if user_input_lower == self.wake_word:
                            self.wake_word_active = True
                            self.last_wake_time = time.time()
                            self.logger.info(f"Wake word '{self.wake_word}' detected")
                            self.device_manager.speak_text(f"Yes, I'm listening.")
                            continue
                        
                        # If wake word at beginning of command, process without requiring separate activation
                        if user_input_lower.startswith(f"{self.wake_word} "):
                            self.wake_word_active = True
                            self.last_wake_time = time.time()
                            # Remove wake word from the beginning of the command
                            user_input = user_input[len(self.wake_word):].strip()
                            self.logger.info(f"Wake word with command detected: {user_input}")
                        
                        # If wake word isn't active and not in the input, ignore the command
                        elif not self.wake_word_active:
                            self.logger.info(f"Ignoring command - wake word not active: {user_input}")
                            continue
                        
                        # Check for timeout on wake word
                        elif self.wake_word_active and (time.time() - self.last_wake_time > self.wake_word_timeout):
                            self.wake_word_active = False
                            self.logger.info("Wake word timed out")
                            self.device_manager.speak_text("I'm going back to sleep. Say Beta to wake me up.")
                            continue
                        else:
                            # Update the last wake time since we're processing a command
                            self.last_wake_time = time.time()
                    
                    # Check if this is an object identification request
                    if any(phrase in user_input.lower() for phrase in [
                        "what do you see", 
                        "what is this", 
                        "identify this", 
                        "what object", 
                        "recognize this",
                        "look at this",
                        "what's in front of you",
                        "can you see",
                        "what am i holding"
                    ]):
                        # This is an object identification request
                        self.logger.info("Object identification request detected")
                        self.device_manager.speak_text("Looking at what's in front of me...")
                        
                        # Use the camera to identify objects
                        identification_result = self.device_manager.identify_object()
                        
                        # Check if this is a trained object
                        trained_object = self.ai_processor.is_trained_object(identification_result)
                        if trained_object:
                            response = f"I recognize this as your trained object: {trained_object}"
                            self.device_manager.speak_text(response)
                        else:
                            # Respond with the standard identification result
                            self.device_manager.speak_text(identification_result)
                        
                        # Also update the AI with this context
                        if trained_object:
                            context_update = f"User asked to identify an object. I recognized it as the trained object '{trained_object}'"
                        else:
                            context_update = f"User asked to identify an object. I responded: {identification_result}"
                        self.ai_processor.process_input(context_update)
                    
                    # Check for wake word control commands
                    elif user_input.lower() in ["wake word on", "enable wake word"]:
                        self.wake_word_enabled = True
                        self.logger.info("Wake word requirement enabled")
                        self.device_manager.speak_text(f"Wake word '{self.wake_word}' is now required. Say '{self.wake_word}' to activate me.")
                        continue
                    elif user_input.lower() in ["wake word off", "disable wake word"]:
                        self.wake_word_enabled = False
                        self.wake_word_active = True  # Always active when disabled
                        self.logger.info("Wake word requirement disabled")
                        self.device_manager.speak_text("Wake word is now disabled. I'll listen to all commands.")
                        continue
                        
                    # Handle object training mode commands
                    elif "train" in user_input.lower() and "object" in user_input.lower():
                        # Extract the object name (everything after "train object")
                        import re
                        match = re.search(r'train\s+object\s+([a-zA-Z0-9_\s]+)', user_input.lower())
                        if match:
                            object_name = match.group(1).strip()
                            response = self.ai_processor.start_object_training_mode(object_name)
                            self.device_manager.speak_text(response)
                            continue
                        else:
                            self.device_manager.speak_text("Please specify an object name, like 'train object coffee mug'.")
                            continue
                            
                    elif self.ai_processor.training_mode_active and "finish" in user_input.lower() and "training" in user_input.lower():
                        response = self.ai_processor.finish_training()
                        self.device_manager.speak_text(response)
                        continue
                        
                    elif self.ai_processor.training_mode_active and "cancel" in user_input.lower() and "training" in user_input.lower():
                        response = self.ai_processor.cancel_training()
                        self.device_manager.speak_text(response)
                        continue
                        
                    # If in training mode and this is an object identification request, use it as a training sample
                    elif self.ai_processor.training_mode_active and any(phrase in user_input.lower() for phrase in [
                        "what do you see", 
                        "what is this", 
                        "identify this", 
                        "what object", 
                        "recognize this",
                        "look at this",
                        "what's in front of you",
                        "can you see",
                        "what am i holding",
                        "another angle",
                        "different angle",
                        "more angles"
                    ]):
                        self.device_manager.speak_text("Looking at this training sample...")
                        # Capture the object identification result
                        identification_result = self.device_manager.identify_object()
                        # Add it as a training sample
                        training_response = self.ai_processor.add_training_sample(identification_result)
                        self.device_manager.speak_text(training_response)
                        continue
                        
                    # Voice control commands
                    elif any(phrase in user_input.lower() for phrase in ["change voice", "change your voice", "use voice", "switch voice"]):
                        # Extract the voice name - everything after the command phrase
                        voice_name = None
                        for phrase in ["change voice", "change your voice", "use voice", "switch voice"]:
                            if phrase in user_input.lower():
                                parts = user_input.lower().split(phrase)
                                if len(parts) > 1:
                                    voice_name = parts[1].strip()
                                break
                                
                        if voice_name:
                            response = self.ai_processor.change_voice(self.device_manager, voice_name)
                            self.device_manager.speak_text(response)
                            continue
                        else:
                            # No voice specified, list available voices
                            response = self.ai_processor.change_voice(self.device_manager)
                            self.device_manager.speak_text(response)
                            continue
                    
                    # Is this a voice speed adjustment command?
                    elif any(phrase in user_input.lower() for phrase in ["speak faster", "talk faster", "speed up", 
                                                                         "speak slower", "talk slower", "slow down"]):
                        if any(phrase in user_input.lower() for phrase in ["faster", "speed up"]):
                            # Increase speed by 25%
                            current_speed = self.device_manager.voice_settings["speed"]
                            new_speed = min(1.5, current_speed + 0.25)
                            response = self.ai_processor.adjust_voice_speed(self.device_manager, new_speed)
                        else:
                            # Decrease speed by 25%
                            current_speed = self.device_manager.voice_settings["speed"]
                            new_speed = max(0.5, current_speed - 0.25)
                            response = self.ai_processor.adjust_voice_speed(self.device_manager, new_speed)
                            
                        self.device_manager.speak_text(response)
                        continue
                        
                    # Is this a voice list command?
                    elif any(phrase in user_input.lower() for phrase in ["list voices", "what voices", 
                                                                         "available voices", "show voices"]):
                        response = self.ai_processor.change_voice(self.device_manager)
                        self.device_manager.speak_text(response)
                        continue
                    
                    # Check if this is a ROS movement/action command
                    elif self.ros_enabled and self.ros_controller:
                        # Try to execute the command with the ROS controller
                        ros_response = self.ros_controller.execute_command(user_input)
                        
                        if ros_response:
                            # This was a valid robot movement command
                            self.logger.info(f"Executed robot command: {user_input}")
                            self.device_manager.speak_text(ros_response)
                            
                            # Update AI with the action taken
                            context_update = f"User asked the robot to perform an action. Command: {user_input}. Response: {ros_response}"
                            self.ai_processor.process_input(context_update)
                        else:
                            # Not a movement command, process through AI
                            ai_response = self.ai_processor.process_input(user_input)
                            
                            if ai_response:
                                # Convert response to speech
                                self.device_manager.speak_text(ai_response)
                            else:
                                self.device_manager.speak_text("I'm sorry, I couldn't process that request")
                    else:
                        # Process through AI for normal conversation (no ROS or not a movement command)
                        ai_response = self.ai_processor.process_input(user_input)

                        if ai_response:
                            # Convert response to speech
                            self.device_manager.speak_text(ai_response)
                        else:
                            self.device_manager.speak_text("I'm sorry, I couldn't process that request")
                    
                # Check for ROS action timeouts if ROS is enabled
                if self.ros_enabled and self.ros_controller:
                    self.ros_controller.check_timeouts()

                time.sleep(0.1)  # Small delay to prevent CPU overuse

            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error in main loop: {error_msg}")
                
                # Determine the appropriate error context based on the error message
                error_context = ErrorContext.GENERAL
                if "camera" in error_msg.lower() or "cv2" in error_msg.lower() or "video" in error_msg.lower():
                    error_context = ErrorContext.CAMERA
                elif "microphone" in error_msg.lower() or "audio input" in error_msg.lower() or "arecord" in error_msg.lower():
                    error_context = ErrorContext.MICROPHONE
                elif "speaker" in error_msg.lower() or "audio output" in error_msg.lower() or "aplay" in error_msg.lower():
                    error_context = ErrorContext.SPEAKER
                elif "openai" in error_msg.lower() or "api key" in error_msg.lower() or "api call" in error_msg.lower():
                    error_context = ErrorContext.API
                elif "network" in error_msg.lower() or "http" in error_msg.lower() or "connection" in error_msg.lower():
                    error_context = ErrorContext.NETWORK
                elif "move" in error_msg.lower() or "motor" in error_msg.lower() or "servo" in error_msg.lower():
                    error_context = ErrorContext.MOVEMENT
                
                # Translate the error message to user-friendly language
                friendly_error = self.error_translator.translate_error(error_msg, error_context)
                self.logger.info(f"User-friendly explanation: {friendly_error}")
                
                try:
                    self.device_manager.speak_text(friendly_error)
                except Exception as speak_error:
                    self.logger.error(f"Could not provide error feedback through speech: {str(speak_error)}")

    def cleanup(self):
        """Clean up resources"""
        try:
            # Clean up device manager resources
            self.device_manager.cleanup()
            
            # Clean up ROS controller resources if enabled
            if self.ros_enabled and self.ros_controller:
                self.ros_controller.cleanup()
                
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Robot Voice Interface')
    parser.add_argument('--no-sim', action='store_true', 
                        help='Disable simulation mode (for use on actual hardware)')
    parser.add_argument('--stop', action='store_true',
                        help='Stop the running voice interface')
    parser.add_argument('--no-ros', action='store_true',
                        help='Disable ROS integration (no physical movements)')
    args = parser.parse_args()
    
    # Handle stop command
    if args.stop:
        print("Sending stop signal to any running robot voice interface...")
        try:
            # Try to kill any existing process
            import subprocess
            subprocess.run("pkill -f robot_voice_interface.py", shell=True)
            print("Stop signal sent successfully.")
            return
        except Exception as e:
            print(f"Error sending stop signal: {str(e)}")
            return

    # Create and run the interface with ROS flag
    ros_enabled = not args.no_ros
    robot_interface = RobotVoiceInterface(ros_enabled=ros_enabled)
    
    # Log ROS status
    if args.no_ros:
        print("ROS integration disabled - no physical movements will be performed")
    
    # Set simulation flag if requested
    if args.no_sim:
        # Pass flag to device manager to disable simulation
        robot_interface.device_manager.simulation_enabled = False
        print("Simulation mode disabled - running in hardware mode only")
        
        # Also pass to ROS controller if enabled
        if ros_enabled and robot_interface.ros_controller:
            robot_interface.ros_controller.simulation_enabled = False
    
    try:
        robot_interface.run()
    except Exception as e:
        print(f"Critical error: {str(e)}")
    finally:
        robot_interface.cleanup()

if __name__ == "__main__":
    main()
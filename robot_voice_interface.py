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

class RobotVoiceInterface:
    def __init__(self, ros_enabled=True):
        self.logger = setup_logger()
        self.device_manager = DeviceManager(self.logger)
        self.ai_processor = AIProcessor(self.logger)
        self.running = True
        self.ros_enabled = ros_enabled
        
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
            self.logger.error(f"Initialization error: {str(e)}")
            return False

    def run(self):
        """Main operation loop"""
        if not self.initialize():
            self.logger.warning("Initialization incomplete - some features may not work until running on Raspberry Pi")

        try:
            self.device_manager.speak_text("Hello, I'm ready to talk")
        except Exception as e:
            self.logger.warning(f"Initial greeting failed (will work on Raspberry Pi): {str(e)}")

        while self.running:
            try:
                # Capture audio input
                user_input = self.device_manager.capture_audio()

                if user_input:
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
                        
                        # Respond with the identification result
                        self.device_manager.speak_text(identification_result)
                        
                        # Also update the AI with this context
                        context_update = f"User asked to identify an object. I responded: {identification_result}"
                        self.ai_processor.process_input(context_update)
                    
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
                self.logger.error(f"Error in main loop: {str(e)}")
                try:
                    self.device_manager.speak_text("I encountered an error. Please try again")
                except:
                    self.logger.error("Could not provide error feedback through speech")

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
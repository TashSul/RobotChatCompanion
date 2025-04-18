#!/usr/bin/env python3
"""
Error Simulation Script

This script simulates various error scenarios to test the error translation functionality
of the robot voice interface.

Usage:
    python3 simulate_errors.py [--error-type TYPE]

Options:
    --error-type     Type of error to simulate (camera, microphone, speaker, api, network, movement)
                     Default is to cycle through all error types.
"""

import os
import time
import argparse
import logging
from logger_config import setup_logger
from error_translator import ErrorTranslator, ErrorContext

class ErrorSimulator:
    """Simulates various error scenarios"""
    
    def __init__(self):
        """Initialize the error simulator"""
        self.logger = setup_logger()
        self.error_translator = ErrorTranslator(self.logger)
        
    def simulate_camera_error(self):
        """Simulate camera-related errors"""
        try:
            self.logger.info("Simulating camera error...")
            # Attempt to open a non-existent camera
            import cv2
            cap = cv2.VideoCapture(99)  # Non-existent camera index
            if not cap.isOpened():
                raise RuntimeError("Failed to open camera at index 99")
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Camera error: {error_msg}")
            
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.CAMERA)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def simulate_microphone_error(self):
        """Simulate microphone-related errors"""
        try:
            self.logger.info("Simulating microphone error...")
            # Try to use a non-existent audio device
            import subprocess
            result = subprocess.run(
                ["arecord", "-d", "1", "-D", "plughw:99,0", "/tmp/test.wav"],
                capture_output=True,
                text=True,
                check=True
            )
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Microphone error: {error_msg}")
            
            # Extract the actual error message from subprocess error
            if hasattr(e, "stderr"):
                error_msg = e.stderr
                
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.MICROPHONE)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def simulate_speaker_error(self):
        """Simulate speaker-related errors"""
        try:
            self.logger.info("Simulating speaker error...")
            # Try to use a non-existent audio output device
            import subprocess
            # Create a text file for espeak
            with open("/tmp/speak_test.txt", "w") as f:
                f.write("This is a test")
                
            result = subprocess.run(
                ["aplay", "-D", "plughw:99,0", "/non_existent_file.wav"],
                capture_output=True,
                text=True,
                check=True
            )
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Speaker error: {error_msg}")
            
            # Extract the actual error message from subprocess error
            if hasattr(e, "stderr"):
                error_msg = e.stderr
                
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.SPEAKER)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def simulate_api_error(self):
        """Simulate API-related errors"""
        try:
            self.logger.info("Simulating API error...")
            # Try to use the OpenAI API with an invalid key
            import openai
            client = openai.OpenAI(api_key="invalid_key_for_testing")
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test"}]
            )
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"API error: {error_msg}")
            
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.API)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def simulate_network_error(self):
        """Simulate network-related errors"""
        try:
            self.logger.info("Simulating network error...")
            # Try to connect to a non-existent host
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("non-existent-host-name.invalid", 80))
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Network error: {error_msg}")
            
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.NETWORK)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def simulate_movement_error(self):
        """Simulate movement-related errors"""
        try:
            self.logger.info("Simulating movement error...")
            # Mock a movement error
            raise RuntimeError("Motor controller error: Servo angle exceeded maximum rotation at joint 2")
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Movement error: {error_msg}")
            
            # Translate the error
            friendly_error = self.error_translator.translate_error(error_msg, ErrorContext.MOVEMENT)
            print(f"\nOriginal error: {error_msg}")
            print(f"User-friendly explanation: {friendly_error}")
            
    def run_all_simulations(self):
        """Run all error simulations"""
        self.simulate_camera_error()
        time.sleep(1)  # Add delay to prevent rate limiting of API calls
        
        self.simulate_microphone_error()
        time.sleep(1)
        
        self.simulate_speaker_error()
        time.sleep(1)
        
        self.simulate_api_error()
        time.sleep(1)
        
        self.simulate_network_error()
        time.sleep(1)
        
        self.simulate_movement_error()
        
def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Error simulation for testing error translation")
    parser.add_argument("--error-type", type=str, 
                        choices=["camera", "microphone", "speaker", "api", "network", "movement", "all"],
                        default="all", help="Type of error to simulate")
    
    args = parser.parse_args()
    
    simulator = ErrorSimulator()
    
    if args.error_type == "all":
        simulator.run_all_simulations()
    elif args.error_type == "camera":
        simulator.simulate_camera_error()
    elif args.error_type == "microphone":
        simulator.simulate_microphone_error()
    elif args.error_type == "speaker":
        simulator.simulate_speaker_error()
    elif args.error_type == "api":
        simulator.simulate_api_error()
    elif args.error_type == "network":
        simulator.simulate_network_error()
    elif args.error_type == "movement":
        simulator.simulate_movement_error()
    
if __name__ == "__main__":
    main()
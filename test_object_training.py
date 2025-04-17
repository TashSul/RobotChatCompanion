#!/usr/bin/env python3
"""
Test Script for Object Training Functionality

This script tests the object training and recognition capabilities
by simulating a sequence of voice commands.

Usage:
    python3 test_object_training.py
"""

import os
import time
import subprocess
import tempfile

def simulate_user_input(text, delay=3.0):
    """Generate a file with the given text to simulate user input"""
    print(f"Simulating user input: {text}")
    
    # Create a temporary file that will be picked up by the voice interface
    temp_dir = tempfile.gettempdir()
    sim_file = os.path.join(temp_dir, "robot_sim_input.txt")
    
    # Write the simulated input to the file
    with open(sim_file, "w") as f:
        f.write(text)
    
    # Sleep to allow the main application to process the command
    time.sleep(delay)

def run_test_sequence():
    """Run a complete test sequence for object training"""
    # First use wake word directly with training command
    simulate_user_input("Beta train object coffee mug")
    time.sleep(4)  # Allow time for response
    
    # Add first training sample - with Beta since wake word still enabled
    simulate_user_input("Beta what do you see")
    time.sleep(4)  # Allow time for image processing
    
    # Now disable wake word to make subsequent commands simpler
    simulate_user_input("Beta disable wake word")
    time.sleep(4)  # Allow time to process
    
    # Add second training sample from different angle (no Beta needed now)
    simulate_user_input("Another angle")
    time.sleep(4)  # Allow time for image processing
    
    # Complete training after 2 samples
    simulate_user_input("Finished training")
    time.sleep(4)  # Allow time for response
    
    # Test recognition of the trained object
    simulate_user_input("What is this")
    time.sleep(4)  # Allow time for image processing and recognition
    
    print("Test sequence completed.")

if __name__ == "__main__":
    print("Starting object training test sequence...")
    run_test_sequence()
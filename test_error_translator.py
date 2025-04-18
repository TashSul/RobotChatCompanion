#!/usr/bin/env python3
"""
Test Script for Error Translator

This script tests the error translation functionality by simulating various
types of errors and translating them to user-friendly messages.

Usage:
    python3 test_error_translator.py
"""

import sys
import logging
from error_translator import ErrorTranslator, ErrorContext

# Set up simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ErrorTranslatorTest")

def test_error_translation():
    """Test the error translator with various error messages"""
    print("\n=== Error Translator Test ===\n")
    
    # Create translator instance
    translator = ErrorTranslator(logger)
    
    # Define test cases - (error_message, context)
    test_cases = [
        ("Cannot open camera at index 0", ErrorContext.CAMERA),
        ("Camera index out of range", ErrorContext.CAMERA),
        ("Device or resource busy: '/dev/video0'", ErrorContext.CAMERA),
        ("ALSA lib pcm.c:8526:(snd_pcm_recover) underrun occurred", ErrorContext.MICROPHONE),
        ("arecord: main:830: audio open error: Device or resource busy", ErrorContext.MICROPHONE),
        ("FLAC conversion utility not found - consider installing flac", ErrorContext.MICROPHONE),
        ("aplay: main:830: audio open error: No such file or directory", ErrorContext.SPEAKER),
        ("Text-to-speech engine failed to initialize", ErrorContext.SPEAKER),
        ("OpenAI API key invalid or expired", ErrorContext.API),
        ("Rate limit exceeded on API calls - try again later", ErrorContext.API),
        ("Network connection timed out after 30 seconds", ErrorContext.NETWORK),
        ("Could not resolve host: api.openai.com", ErrorContext.NETWORK),
        ("Motor controller returned error code 0x7A: torque limit exceeded", ErrorContext.MOVEMENT),
        ("Collision detected, stopping movement", ErrorContext.MOVEMENT),
        ("Out of memory: Killed process", ErrorContext.GENERAL),
        ("Bus error at address 0x00000000", ErrorContext.GENERAL),
        ("USB device disconnected unexpectedly", ErrorContext.HARDWARE),
        ("Temperature warning: CPU at 85°C", ErrorContext.HARDWARE)
    ]
    
    # Test each case and print results
    for i, (error_msg, context) in enumerate(test_cases):
        print(f"[Test {i+1}] Context: {context.value}")
        print(f"Original: {error_msg}")
        
        # Time the translation
        import time
        start_time = time.time()
        translation = translator.translate_error(error_msg, context)
        elapsed = time.time() - start_time
        
        print(f"Translation: {translation}")
        print(f"Time taken: {elapsed:.4f} seconds")
        print("-" * 60)

def test_error_detection():
    """Test the error detection logic from the robot_voice_interface.py file"""
    print("\n=== Error Context Detection Test ===\n")
    
    # Simulate the detection logic from robot_voice_interface.py
    def detect_error_context(error_msg):
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
        return error_context
    
    # Test cases for context detection
    detection_tests = [
        "Failed to open camera device at index 0",
        "cv2.error: OpenCV(4.5.1) error",
        "Error initializing microphone: Device busy",
        "arecord: Device or resource busy",
        "aplay failed with error code 1",
        "Speaker not found or disconnected",
        "OpenAI API returned error 401: Invalid API key",
        "API call failed: Rate limit exceeded",
        "Network connection timed out",
        "HTTP request failed with status 500",
        "Motor stalled on joint 3",
        "Servo position out of range",
        "Unhandled exception in main loop",
        "Unknown error occurred during operation"
    ]
    
    # Test each case and print results
    for i, error_msg in enumerate(detection_tests):
        detected_context = detect_error_context(error_msg)
        print(f"[Detection {i+1}]")
        print(f"Error: {error_msg}")
        print(f"Detected context: {detected_context.value}")
        print("-" * 60)

def test_ai_translation():
    """Test the AI-based translation (requires API key)"""
    print("\n=== AI Translation Test ===\n")
    
    # Create translator instance
    translator = ErrorTranslator(logger)
    
    # Check if we have an API key
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OpenAI API key not found in environment - skipping AI translation test")
        return
    
    # Test cases for AI translation
    ai_test_cases = [
        ("IndexError: list index out of range in object_detection.py:245", ErrorContext.VISION),
        ("Camera module failed to initialize with error code 0xE2: Cannot allocate memory for buffer", ErrorContext.CAMERA),
        ("Failed to find suitable audio format for device. Expected S16_LE but device reports S24_3LE only.", ErrorContext.MICROPHONE),
        ("JSON parsing error in API response: Unexpected token < in JSON at position 0", ErrorContext.API)
    ]
    
    # Test each case and print results
    for i, (error_msg, context) in enumerate(ai_test_cases):
        print(f"[AI Test {i+1}] Context: {context.value}")
        print(f"Original: {error_msg}")
        
        # Force AI translation by using a made-up error message that won't match any patterns
        translation = translator._translate_with_ai(error_msg, context.value)
        
        if translation:
            print(f"AI Translation: {translation}")
        else:
            print("AI Translation failed or skipped due to rate limiting")
        print("-" * 60)

def main():
    """Main function to run the tests"""
    print("\nTesting Error Translator functionality...\n")
    
    try:
        # Run the tests
        test_error_translation()
        test_error_detection()
        test_ai_translation()
        
        print("\nAll tests completed.\n")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
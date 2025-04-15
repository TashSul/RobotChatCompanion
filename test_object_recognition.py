#!/usr/bin/env python3
"""
Test Script for Object Recognition Functionality

This script tests the object recognition capabilities using OpenAI's Vision API.
It captures an image using the camera and sends it to OpenAI for analysis.

Usage:
    python3 test_object_recognition.py
"""

import os
import sys
import base64
import tempfile
import argparse
import cv2
import openai
from typing import Optional

def setup_openai_client() -> Optional[openai.OpenAI]:
    """Initialize the OpenAI client with the API key from environment variables"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set")
        print("Please set your OpenAI API key with:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return None
        
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)
        return client
    except Exception as e:
        print(f"ERROR: Failed to initialize OpenAI client: {e}")
        return None

def capture_image() -> Optional[str]:
    """Capture an image from the camera and save it to a temporary file"""
    try:
        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("ERROR: Could not open camera")
            return None
            
        # Capture a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("ERROR: Failed to capture image")
            return None
            
        # Save the frame to a temporary file
        temp_img_path = os.path.join(tempfile.gettempdir(), "vision_test.jpg")
        cv2.imwrite(temp_img_path, frame)
        print(f"Image captured and saved to: {temp_img_path}")
        
        # Convert image to base64
        with open(temp_img_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        return base64_image
            
    except Exception as e:
        print(f"ERROR: Failed to capture image: {e}")
        return None

def analyze_image_with_openai(client: openai.OpenAI, base64_image: str) -> Optional[str]:
    """Send the image to OpenAI for analysis"""
    try:
        print("Sending image to OpenAI for analysis...")
        
        # Use OpenAI's GPT-4 Vision model to analyze the image
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {
                    "role": "system",
                    "content": "You are a vision assistant helping a robot identify objects through its camera. Describe what you see clearly and concisely. Focus on the main objects in view, their positions, and any notable characteristics."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What objects do you see in this image? Please describe them clearly but concisely."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        
        result = response.choices[0].message.content
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to analyze image with OpenAI: {e}")
        return None

def simulate_image_analysis() -> str:
    """Provide a simulated response for environments without camera hardware"""
    print("No camera detected - using simulated image recognition")
    return "This is a simulated response: I can see what appears to be a computer keyboard on a desk with some papers beside it."

def main():
    """Main function to run the object recognition test"""
    print("Object Recognition Test")
    print("======================")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test object recognition functionality')
    parser.add_argument('--simulate', action='store_true', help='Use simulation mode instead of actual camera')
    args = parser.parse_args()
    
    # Set up OpenAI client
    client = setup_openai_client()
    if not client and not args.simulate:
        print("Failed to set up OpenAI client")
        return
    
    if args.simulate:
        # Use simulation mode
        result = simulate_image_analysis()
    else:
        # Capture image from camera
        base64_image = capture_image()
        if not base64_image:
            print("Failed to capture image")
            return
            
        # Analyze the image with OpenAI
        result = analyze_image_with_openai(client, base64_image)
        if not result:
            print("Failed to analyze image")
            return
    
    # Display the result
    print("\nObject Recognition Result:")
    print("-----------------------")
    print(result)
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
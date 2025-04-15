#!/usr/bin/env python3
"""
Camera Diagnostics Tool for Raspberry Pi

This script performs comprehensive testing of camera hardware 
and helps troubleshoot connection issues.

Usage:
    python3 test_camera_diagnostics.py
"""

import os
import subprocess
import sys
import time

# Try to import OpenCV
try:
    import cv2
    has_cv2 = True
except ImportError:
    has_cv2 = False
    print("WARNING: OpenCV (cv2) module not available")

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def run_command(command):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

def check_usb_devices():
    """Check USB devices using multiple methods"""
    print_section("USB Devices")
    
    # Try different commands to find USB devices
    print("Method 1: Using /sys/bus/usb/devices")
    print(run_command("ls -l /sys/bus/usb/devices/"))
    
    print("\nMethod 2: Using /proc/bus/usb")
    print(run_command("ls -l /proc/bus/usb/ 2>/dev/null || echo 'Not available'"))
    
    print("\nMethod 3: Using sysfs attributes")
    print(run_command("find /sys/bus/usb/devices -maxdepth 1 -type l -exec cat {}/manufacturer {}/product 2>/dev/null \\; 2>/dev/null || echo 'Not available'"))
    
    print("\nMethod 4: Checking USB character devices")
    print(run_command("grep -l USB /sys/class/video4linux/*/name 2>/dev/null || echo 'No USB video devices found'"))

def check_video_devices():
    """Check video devices"""
    print_section("Video Devices")
    
    # Check for video device nodes
    print("Video device nodes:")
    print(run_command("ls -l /dev/video* 2>/dev/null || echo 'No video devices found in /dev/'"))
    
    # Check if V4L2 is available
    print("\nV4L2 Devices (if available):")
    print(run_command("v4l2-ctl --list-devices 2>/dev/null || echo 'v4l2-ctl command not available'"))
    
    # Alternative checks for video devices
    print("\nChecking alternative video device locations:")
    print(run_command("ls -l /sys/class/video4linux/ 2>/dev/null || echo 'No video4linux devices found'"))
    
    # If available, read device info from sysfs
    print("\nVideo device information from sysfs:")
    print(run_command("find /sys/class/video4linux -type d -name 'video*' -exec cat {}/name {}/dev 2>/dev/null \\; 2>/dev/null || echo 'No device information available'"))
    
    # Check loaded camera modules
    print("\nLoaded camera kernel modules:")
    print(run_command("lsmod | grep -E 'uvc|camera|video' 2>/dev/null || echo 'No camera modules found'"))

def check_kernel_logs():
    """Check kernel logs for camera/video related messages"""
    print_section("Kernel Logs (Camera/Video)")
    
    # Try to check for kernel modules instead of dmesg which may require privileges
    print("Camera/Video kernel modules:")
    print(run_command("lsmod | grep -E 'video|camera|webcam|uvc' 2>/dev/null || echo 'No camera modules found or lsmod not available'"))
    
    # Check for camera in sysfs
    print("\nCamera hardware information from sysfs:")
    print(run_command("find /sys/devices/ -name '*camera*' 2>/dev/null || echo 'No camera devices found in sysfs'"))
    
    # Look for loaded USB camera drivers
    print("\nUSB video class drivers:")
    print(run_command("find /sys/bus/usb/drivers -name '*video*' 2>/dev/null || echo 'No USB video drivers found'"))
    
    # Try to get basic hardware info without dmesg privileges
    print("\nBasic hardware info:")
    print(run_command("cat /proc/cpuinfo | grep 'model name' | head -1 2>/dev/null || echo 'CPU info not available'"))
    print(run_command("cat /proc/version 2>/dev/null || echo 'Kernel version not available'"))

def test_opencv_capture():
    """Test OpenCV camera capture"""
    print_section("OpenCV Camera Test")
    
    if not has_cv2:
        print("OpenCV is not installed. Cannot test camera with cv2.")
        return False
    
    # Test multiple camera indices
    for camera_idx in range(4):  # Try indices 0, 1, 2, 3
        print(f"\nTesting camera index {camera_idx}...")
        try:
            cap = cv2.VideoCapture(camera_idx)
            if not cap.isOpened():
                print(f"  Failed to open camera at index {camera_idx}")
                continue
                
            # Read a frame
            ret, frame = cap.read()
            if not ret:
                print(f"  Failed to capture frame from camera {camera_idx}")
                cap.release()
                continue
                
            # Save the image
            test_img_path = f"camera_test_{camera_idx}.jpg"
            cv2.imwrite(test_img_path, frame)
            
            # Report success
            print(f"  SUCCESS: Captured image from camera {camera_idx}")
            print(f"  Image saved to {test_img_path}")
            cap.release()
            
        except Exception as e:
            print(f"  Error testing camera {camera_idx}: {str(e)}")
            continue
            
    print("\nCamera test completed")

def test_rpi_camera():
    """Test Raspberry Pi camera module"""
    print_section("Raspberry Pi Camera Module Test")
    
    # Check if raspistill is available
    if os.system("which raspistill >/dev/null 2>&1") != 0:
        print("raspistill not found - not a Raspberry Pi or camera module not enabled")
        return
        
    try:
        print("Testing Raspberry Pi camera module...")
        print(run_command("raspistill -o rpi_camera_test.jpg -t 1000"))
        print("If no errors above, check for rpi_camera_test.jpg file")
    except Exception as e:
        print(f"Error: {str(e)}")

def print_troubleshooting_tips():
    """Print troubleshooting tips"""
    print_section("Troubleshooting Tips")
    
    print("1. If no camera is detected:")
    print("   - Verify that the camera is properly connected")
    print("   - Try a different USB port")
    print("   - Check the camera with another computer if possible")
    
    print("\n2. If camera is detected but doesn't work with OpenCV:")
    print("   - Install v4l-utils: sudo apt install v4l-utils")
    print("   - Check support for your camera format:")
    print("     v4l2-ctl --list-formats-ext")
    
    print("\n3. If the camera worked before but stopped working:")
    print("   - Restart the USB subsystem:")
    print("     sudo rmmod uvcvideo")
    print("     sudo modprobe uvcvideo")
    
    print("\n4. For Raspberry Pi camera module issues:")
    print("   - Ensure camera is enabled: sudo raspi-config")
    print("   - Check ribbon cable connection")
    print("   - Try legacy camera stack: sudo raspi-config -> Interface Options -> Legacy Camera")

def main():
    """Main function"""
    print_section("Camera Diagnostics Tool")
    print("This tool will test your camera hardware and configuration")
    
    # Run diagnostics
    check_usb_devices()
    check_video_devices()
    check_kernel_logs()
    test_opencv_capture()
    test_rpi_camera()
    print_troubleshooting_tips()
    
    print("\nDiagnostics completed. Check the output above for camera status.")

if __name__ == "__main__":
    main()
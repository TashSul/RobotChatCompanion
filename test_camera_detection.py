#!/usr/bin/env python3
"""
Camera Detection Test Script

This script tests camera detection for the robot vision system,
attempting multiple detection methods to find a working camera.

Usage:
    python3 test_camera_detection.py [--device DEVICE]

Options:
    --device    Specify a particular camera device to test
                (e.g., /dev/video0, 0, /dev/usb_cam)

Example:
    python3 test_camera_detection.py
    python3 test_camera_detection.py --device 1
"""

import argparse
import os
import subprocess
import time
import sys

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_section(title):
    """Print a section header"""
    print("\n" + "-" * 50)
    print(f"  {title}")
    print("-" * 50)

def run_command(cmd):
    """Run a shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result
    except Exception as e:
        print(f"Error executing command: {e}")
        return None

def check_opencv():
    """Check if OpenCV is installed"""
    print_section("Checking OpenCV")
    
    try:
        import cv2
        print(f"✅ OpenCV (version {cv2.__version__}) is installed")
        return True
    except ImportError:
        print("❌ OpenCV is not installed")
        print("   Install it with: pip install opencv-python")
        return False

def detect_cameras():
    """Detect available cameras"""
    print_section("Detecting Cameras")
    
    # Check for video devices in /dev
    print("Checking for video devices in /dev...")
    result = run_command("ls -l /dev/video* 2>/dev/null")
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("No video devices found in /dev/video*")
    
    # Check for USB cameras
    print("\nChecking for USB cameras...")
    result = run_command("lsusb | grep -i camera")
    if result.returncode == 0:
        print(result.stdout)
    else:
        result = run_command("lsusb | grep -i video")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No USB cameras detected with lsusb")
    
    # Check for V4L2 devices if v4l2-ctl is available
    result = run_command("which v4l2-ctl")
    if result.returncode == 0:
        print("\nListing V4L2 devices...")
        result = run_command("v4l2-ctl --list-devices")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Failed to list V4L2 devices")
    else:
        print("\nv4l2-ctl not found (install v4l-utils for more detailed camera info)")

def test_camera(device=None):
    """Test camera with OpenCV"""
    print_section("Testing Camera with OpenCV")
    
    try:
        import cv2
    except ImportError:
        print("❌ Cannot test camera - OpenCV not installed")
        return False
    
    # Define a set of devices to try
    if device:
        devices = [device]
    else:
        devices = [
            "/dev/usb_cam",
            "/dev/video0",
            "/dev/webcam",
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -1
        ]
    
    success = False
    for dev in devices:
        print(f"\nTrying camera device: {dev}")
        try:
            # Set timeout for camera initialization
            start_time = time.time()
            
            # Open camera
            cap = cv2.VideoCapture(dev)
            
            # Check if opened successfully
            if cap.isOpened():
                # Try to read a frame
                ret, frame = cap.read()
                
                if ret:
                    print(f"✅ Successfully captured frame from camera {dev}")
                    print(f"   Frame dimensions: {frame.shape[1]}x{frame.shape[0]}")
                    
                    # Save the frame as a test image
                    test_file = f"camera_test_{dev if not isinstance(dev, int) else f'index_{dev}'}.jpg"
                    cv2.imwrite(test_file, frame)
                    print(f"   Test image saved to: {test_file}")
                    
                    # Show camera properties
                    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    print(f"   Camera properties: {width}x{height} at {fps} FPS")
                    
                    success = True
                else:
                    print(f"❌ Camera {dev} opened but failed to capture frame")
                
                # Release the camera
                cap.release()
            else:
                print(f"❌ Failed to open camera {dev}")
                
            # Check timeout
            if time.time() - start_time > 5:
                print(f"   Camera test for {dev} took more than 5 seconds")
                
        except Exception as e:
            print(f"❌ Error testing camera {dev}: {e}")
    
    return success

def create_usb_cam_symlink():
    """Create a symlink to the first available camera device"""
    print_section("Creating USB Camera Symlink")
    
    result = run_command("ls /dev/video* 2>/dev/null | head -1")
    if result.returncode == 0 and result.stdout.strip():
        device = result.stdout.strip()
        print(f"Found video device: {device}")
        
        # Check if we have permission to create the symlink
        if os.geteuid() == 0:
            # Remove existing symlink if it exists
            if os.path.exists("/dev/usb_cam"):
                run_command("rm -f /dev/usb_cam")
            
            # Create the symlink
            result = run_command(f"ln -sf {device} /dev/usb_cam")
            if result.returncode == 0:
                print(f"✅ Created symlink: /dev/usb_cam -> {device}")
                return True
            else:
                print(f"❌ Failed to create symlink: {result.stderr}")
                return False
        else:
            print("⚠️ Not running as root, cannot create symlink")
            print(f"   Run: sudo ln -sf {device} /dev/usb_cam")
            return False
    else:
        print("❌ No video devices found to create symlink")
        return False

def print_recommendations():
    """Print recommendations for solving camera issues"""
    print_section("Recommendations")
    
    print("""
If your camera isn't being detected:

1. Check hardware connections:
   - Make sure the camera is properly connected
   - Try a different USB port (USB 2.0 ports are sometimes more reliable)
   - For Raspberry Pi camera module, check the ribbon cable connection

2. Check system configuration:
   - For Raspberry Pi camera module: sudo raspi-config > Interface Options > Camera
   - Make sure your user has proper permissions: sudo usermod -a -G video $USER

3. Software solutions:
   - Ensure OpenCV is properly installed: pip install opencv-python
   - Create a symlink to the camera device: sudo ln -sf /dev/video0 /dev/usb_cam
   - Try running the script with sudo to test permissions

4. Run the comprehensive camera fix script:
   - python3 fix_camera_detection.py --reset-permissions --force-symlink

5. For troubleshooting on Raspberry Pi:
   - Check if modules are loaded: lsmod | grep -E '(bcm2835_v4l2|v4l2_common)'
   - Manually load the module: sudo modprobe bcm2835_v4l2
   - Reboot and try again
    """)

def main():
    parser = argparse.ArgumentParser(description="Test camera detection for robot vision")
    parser.add_argument("--device", help="Specific camera device to test (e.g., /dev/video0, 0)")
    args = parser.parse_args()
    
    print_header("Camera Detection Test")
    
    # Check OpenCV
    if not check_opencv():
        print("\nCannot proceed without OpenCV")
        sys.exit(1)
    
    # Detect cameras
    detect_cameras()
    
    # Test camera
    device = None
    if args.device:
        # Convert string numbers to integers for OpenCV
        if args.device.isdigit():
            device = int(args.device)
        else:
            device = args.device
    
    success = test_camera(device)
    
    # Create symlink if no specific device was requested
    if not args.device:
        create_usb_cam_symlink()
    
    # Print recommendations
    print_recommendations()
    
    if not success:
        print("\n❌ Camera detection test failed")
        print("   Run fix_camera_detection.py to diagnose and fix issues")
        return 1
    else:
        print("\n✅ Camera detection test successful")
        print("   The robot should now be able to use the camera")
        return 0

if __name__ == "__main__":
    sys.exit(main())
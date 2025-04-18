#!/usr/bin/env python3
"""
Camera Diagnostics Tool for Robot Vision System

This script provides comprehensive diagnostics for camera issues on the robot.
It checks camera connections, driver status, and captures test images.

Usage:
    python3 test_camera_diagnostics.py [--test-all] [--fix] [--device DEVICE]

Options:
    --test-all   Test all possible camera indices and paths
    --fix        Attempt to fix common camera issues
    --device     Specify a camera device to test (e.g., /dev/video0)
"""

import argparse
import os
import subprocess
import sys
import time
import tempfile
import traceback
import glob
from datetime import datetime

# Check if we're running on the actual robot hardware
try:
    with open("/proc/device-tree/model", "r") as f:
        model = f.read()
    IS_RASPBERRY_PI = "Raspberry Pi" in model
except:
    IS_RASPBERRY_PI = False

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

def print_result(success, message):
    """Print a test result with appropriate formatting"""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    
def run_command(cmd):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result
    except Exception as e:
        print(f"Error executing command: {e}")
        return None

def get_system_info():
    """Get system information"""
    print_section("System Information")
    
    # Get OS information
    os_info = run_command("cat /etc/os-release | grep PRETTY_NAME")
    if os_info and os_info.returncode == 0:
        print(f"OS: {os_info.stdout.strip().split('=')[1].strip('\"')}")
    else:
        print("OS: Unknown")
    
    # Get kernel version
    kernel = run_command("uname -r")
    if kernel and kernel.returncode == 0:
        print(f"Kernel: {kernel.stdout.strip()}")
    
    # Check if we're on a Raspberry Pi
    if IS_RASPBERRY_PI:
        print(f"Hardware: {model.strip()}")
        # Get GPU memory allocation
        vcgencmd = run_command("vcgencmd get_mem gpu")
        if vcgencmd and vcgencmd.returncode == 0:
            print(f"GPU Memory: {vcgencmd.stdout.strip()}")
    else:
        cpu_info = run_command("cat /proc/cpuinfo | grep 'model name' | head -1")
        if cpu_info and cpu_info.returncode == 0:
            print(f"CPU: {cpu_info.stdout.strip().split(':')[1].strip()}")
    
    # Check available memory
    mem_info = run_command("free -h | grep Mem")
    if mem_info and mem_info.returncode == 0:
        print(f"Memory: {mem_info.stdout.strip()}")

def check_camera_driver():
    """Check camera driver status"""
    print_section("Camera Driver Status")
    
    # Check if we're on a Raspberry Pi
    if IS_RASPBERRY_PI:
        # Check if the camera module is loaded
        mod_check = run_command("lsmod | grep -E '(bcm2835_v4l2|v4l2_common)'")
        if mod_check and mod_check.returncode == 0:
            print_result(True, "Camera kernel modules are loaded")
            print(mod_check.stdout)
        else:
            print_result(False, "Camera kernel modules are not loaded")
            # Attempt to load module
            if os.geteuid() == 0:  # Check if we're running as root
                print("Attempting to load camera module...")
                mod_load = run_command("modprobe bcm2835_v4l2")
                if mod_load and mod_load.returncode == 0:
                    print_result(True, "Successfully loaded bcm2835_v4l2 module")
                else:
                    print_result(False, "Failed to load camera module")
            else:
                print("Not running as root, cannot load kernel module")
                print("Run: sudo modprobe bcm2835_v4l2")
        
        # Check camera enabled in config.txt
        if os.path.exists("/boot/config.txt"):
            config_path = "/boot/config.txt"
        elif os.path.exists("/boot/firmware/config.txt"):
            config_path = "/boot/firmware/config.txt"
        else:
            config_path = None
        
        if config_path:
            with open(config_path, "r") as f:
                config = f.read()
            
            if "start_x=1" in config:
                print_result(True, "Camera is enabled in config.txt")
            else:
                print_result(False, "Camera is not enabled in config.txt")
                print("To enable the camera, add 'start_x=1' to /boot/config.txt")
    else:
        # On non-Raspberry Pi systems, check for V4L2 driver
        v4l2_check = run_command("ls -l /dev/video*")
        if v4l2_check and v4l2_check.returncode == 0:
            print_result(True, "V4L2 devices are available")
            print(v4l2_check.stdout)
        else:
            print_result(False, "No V4L2 devices found")
            
        # Check loaded modules
        mod_check = run_command("lsmod | grep -E '(videodev|v4l2|uvcvideo)'")
        if mod_check and mod_check.returncode == 0:
            print_result(True, "Video-related kernel modules are loaded")
            print(mod_check.stdout)
        else:
            print_result(False, "No video-related kernel modules found")
            print("Required modules may not be loaded")

def detect_cameras():
    """Detect available camera devices"""
    print_section("Camera Device Detection")
    
    # Method 1: Check /dev/video* devices
    video_devices = glob.glob("/dev/video*")
    if video_devices:
        print_result(True, f"Found {len(video_devices)} video devices")
        
        # Get detailed information for each device
        for device in video_devices:
            print(f"\nDevice: {device}")
            
            # Check device permissions
            perms = run_command(f"ls -l {device}")
            if perms and perms.returncode == 0:
                print(f"Permissions: {perms.stdout.strip()}")
                # Highlight potential permission issues
                if not ("crw-rw" in perms.stdout or "crw-rw-rw" in perms.stdout):
                    print_result(False, f"Insufficient permissions for {device}")
                    print(f"Fix with: sudo chmod a+rw {device}")
            
            # Check if v4l2-ctl is available
            v4l2_check = run_command("which v4l2-ctl")
            if v4l2_check and v4l2_check.returncode == 0:
                # Get device capabilities
                caps = run_command(f"v4l2-ctl --device={device} --all")
                if caps and caps.returncode == 0:
                    driver = None
                    card = None
                    for line in caps.stdout.split('\n'):
                        if "Driver name" in line:
                            driver = line.split(':')[1].strip()
                        elif "Card type" in line:
                            card = line.split(':')[1].strip()
                    
                    if driver and card:
                        print(f"Driver: {driver}")
                        print(f"Card: {card}")
                    
                    # Check for MJPEG format support (often good for webcams)
                    formats = run_command(f"v4l2-ctl --device={device} --list-formats")
                    if formats and formats.returncode == 0:
                        print("Supported formats:")
                        for line in formats.stdout.split('\n'):
                            if ":" in line and not "[" in line:
                                print(f"  {line.strip()}")
    else:
        print_result(False, "No /dev/video* devices found")
    
    # Method 2: Check USB devices
    usb_cams = run_command("lsusb | grep -i 'cam\\|video'")
    if usb_cams and usb_cams.returncode == 0 and usb_cams.stdout.strip():
        print("\nUSB cameras/video devices:")
        print(usb_cams.stdout)
    else:
        print("\nNo USB cameras detected with lsusb")
    
    # Method 3: Check for device busy status
    busy_check = run_command("lsof /dev/video* 2>/dev/null")
    if busy_check and busy_check.returncode == 0 and busy_check.stdout.strip():
        print_result(False, "Some video devices are in use by other processes")
        print(busy_check.stdout)
    
    return video_devices

def test_camera_with_opencv(device=None, test_all=False):
    """Test camera with OpenCV"""
    print_section("OpenCV Camera Test")
    
    try:
        import cv2
        print_result(True, f"OpenCV is installed (version {cv2.__version__})")
    except ImportError:
        print_result(False, "OpenCV (cv2) is not installed")
        print("Install OpenCV with: pip install opencv-python")
        return False
    
    # Determine which devices to test
    if test_all:
        # Test all common camera indices and paths
        devices = [
            "/dev/video0", 
            "/dev/video1", 
            "/dev/video2", 
            "/dev/usb_cam", 
            "/dev/webcam",
            0, 1, 2, 3, 4, 5, -1
        ]
    elif device:
        # Convert string number to int if it's a digit
        if isinstance(device, str) and device.isdigit():
            devices = [int(device)]
        else:
            devices = [device]
    else:
        # Default to common devices
        devices = [0, "/dev/video0", "/dev/usb_cam"]
    
    success = False
    working_devices = []
    
    # Test each device
    for dev in devices:
        print(f"\nTesting camera device: {dev}")
        try:
            # Set a timeout for camera initialization
            start_time = time.time()
            
            # Attempt to open the camera
            cap = cv2.VideoCapture(dev)
            
            # Check if opened successfully
            if cap.isOpened():
                # Get camera properties
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                print(f"Camera opened successfully: {width}x{height} at {fps} FPS")
                
                # Try to read a frame
                ret, frame = cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    print_result(True, f"Successfully captured frame from {dev}")
                    
                    # Save a test image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if isinstance(dev, int):
                        dev_str = f"index_{dev}"
                    else:
                        dev_str = os.path.basename(str(dev))
                    
                    test_img = f"camera_test_{dev_str}_{timestamp}.jpg"
                    cv2.imwrite(test_img, frame)
                    print(f"Test image saved to: {test_img}")
                    
                    # Store the working device
                    working_devices.append(dev)
                    success = True
                else:
                    print_result(False, f"Camera opened but failed to capture frame from {dev}")
                
                # Close the camera
                cap.release()
            else:
                print_result(False, f"Failed to open camera {dev}")
            
            # Check how long it took
            elapsed = time.time() - start_time
            if elapsed > 3:
                print(f"Warning: Camera initialization took {elapsed:.2f} seconds")
                
        except Exception as e:
            print_result(False, f"Error testing camera {dev}: {str(e)}")
            print(traceback.format_exc())
    
    if working_devices:
        print("\nWorking camera devices:")
        for dev in working_devices:
            print(f"  - {dev}")
    
    return success

def fix_common_issues(video_devices):
    """Attempt to fix common camera issues"""
    print_section("Fixing Common Camera Issues")
    
    fixed_anything = False
    
    # Check user permissions
    if os.geteuid() != 0:
        print_result(False, "Not running as root, limited fixes available")
        print("For full fixes, run: sudo python3 test_camera_diagnostics.py --fix")
    
    # Fix 1: Reset permissions on video devices
    if os.geteuid() == 0 and video_devices:
        print("Fixing video device permissions...")
        for device in video_devices:
            run_command(f"chmod a+rw {device}")
        print_result(True, "Reset permissions on all video devices")
        fixed_anything = True
    
    # Fix 2: Create a symlink to the first video device
    if video_devices:
        if os.path.exists("/dev/usb_cam"):
            print("Removing existing /dev/usb_cam symlink...")
            if os.geteuid() == 0:
                run_command("rm -f /dev/usb_cam")
            else:
                print("Cannot remove symlink without root privileges")
        
        if os.geteuid() == 0:
            print(f"Creating symlink from {video_devices[0]} to /dev/usb_cam...")
            result = run_command(f"ln -sf {video_devices[0]} /dev/usb_cam")
            if result and result.returncode == 0:
                print_result(True, f"Created symlink: /dev/usb_cam -> {video_devices[0]}")
                fixed_anything = True
            else:
                print_result(False, "Failed to create symlink")
        else:
            print(f"To create symlink, run: sudo ln -sf {video_devices[0]} /dev/usb_cam")
    
    # Fix 3: Check for and kill processes using the camera
    busy_check = run_command("lsof /dev/video* 2>/dev/null")
    if busy_check and busy_check.returncode == 0 and busy_check.stdout.strip():
        print("Found processes using the camera:")
        print(busy_check.stdout)
        
        if os.geteuid() == 0:
            print("Attempting to release camera by killing processes...")
            for line in busy_check.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        print(f"Killing process {pid}...")
                        run_command(f"kill -9 {pid}")
            print_result(True, "Killed processes using the camera")
            fixed_anything = True
        else:
            print("Cannot kill processes without root privileges")
    
    # Fix 4: Reload camera modules (Raspberry Pi specific)
    if IS_RASPBERRY_PI and os.geteuid() == 0:
        print("Reloading camera modules...")
        run_command("rmmod bcm2835_v4l2 2>/dev/null; modprobe bcm2835_v4l2")
        print_result(True, "Reloaded camera modules")
        fixed_anything = True
    
    if not fixed_anything:
        print("No fixes were applied - either no issues found or insufficient permissions")
    
    return fixed_anything

def create_diagnostic_report():
    """Create a comprehensive diagnostic report"""
    print_section("Creating Diagnostic Report")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"camera_diagnostic_report_{timestamp}.txt"
    
    print(f"Saving diagnostic report to: {report_file}")
    
    # Redirect stdout to the report file
    original_stdout = sys.stdout
    with open(report_file, 'w') as f:
        sys.stdout = f
        
        print(f"Camera Diagnostic Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"===================================================================\n")
        
        # Run all diagnostics
        get_system_info()
        check_camera_driver()
        video_devices = detect_cameras()
        test_camera_with_opencv(test_all=True)
        
        # Add recommendations
        print_section("Recommendations")
        
        if not video_devices:
            print("1. Check physical camera connections")
            print("2. Ensure camera is enabled in raspi-config (if using Raspberry Pi)")
            print("3. Check for available camera kernel modules:")
            print("   sudo modprobe bcm2835_v4l2")
        else:
            print("1. Ensure camera permissions are correct:")
            for device in video_devices:
                print(f"   sudo chmod a+rw {device}")
            print(f"2. Create a symlink to the camera device:")
            print(f"   sudo ln -sf {video_devices[0]} /dev/usb_cam")
            print("3. Check for other processes using the camera:")
            print("   lsof /dev/video*")
        
    # Restore stdout
    sys.stdout = original_stdout
    
    print(f"Diagnostic report saved to: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description="Camera Diagnostics Tool for Robot Vision System")
    parser.add_argument("--test-all", action="store_true", help="Test all possible camera indices and paths")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common camera issues")
    parser.add_argument("--device", help="Specify a camera device to test (e.g., /dev/video0)")
    parser.add_argument("--report", action="store_true", help="Generate a comprehensive diagnostic report")
    args = parser.parse_args()
    
    print_header("Camera Diagnostics Tool for Robot Vision System")
    
    # Get system information
    get_system_info()
    
    # Check camera driver status
    check_camera_driver()
    
    # Detect available cameras
    video_devices = detect_cameras()
    
    # Test camera with OpenCV
    if args.device:
        success = test_camera_with_opencv(device=args.device)
    elif args.test_all:
        success = test_camera_with_opencv(test_all=True)
    else:
        success = test_camera_with_opencv()
    
    # Fix common issues if requested
    if args.fix:
        fix_common_issues(video_devices)
    
    # Create diagnostic report if requested
    if args.report:
        report_file = create_diagnostic_report()
    
    print_section("Summary")
    
    if success:
        print_result(True, "Camera is working properly")
        print("The robot vision system should be able to use the camera")
    else:
        print_result(False, "Camera test failed")
        print("\nTry the following:")
        print("1. Run with --fix option: python3 test_camera_diagnostics.py --fix")
        print("2. Check physical camera connections")
        print("3. Verify camera drivers are loaded")
        print("4. Check for permission issues")
        print("5. Generate a diagnostic report: python3 test_camera_diagnostics.py --report")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
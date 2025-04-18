#!/usr/bin/env python3
"""
Camera Access Troubleshooter

This script provides a comprehensive diagnostic tool for camera issues on Raspberry Pi.
It will help identify and resolve common camera access problems.

Usage:
    python3 fix_camera_access.py
"""

import os
import sys
import subprocess
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CameraTroubleshooter")

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 50)
    print(f" {title} ")
    print("=" * 50)

def run_command(cmd: str) -> Tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, and return code"""
    try:
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), -1

def check_usb_devices() -> Dict[str, Any]:
    """Check USB devices using multiple methods"""
    print_section("USB Device Check")
    
    results = {}
    
    # Check lsusb output
    stdout, stderr, _ = run_command("lsusb")
    print("USB Devices (lsusb):")
    print(stdout or "No output")
    
    # Look for cameras in lsusb output
    camera_devices = []
    for line in stdout.splitlines():
        if any(keyword in line.lower() for keyword in ["cam", "video", "webcam", "imaging"]):
            camera_devices.append(line)
    
    results["usb_cameras_found"] = bool(camera_devices)
    if camera_devices:
        print("\nPotential camera devices found:")
        for device in camera_devices:
            print(f"  {device}")
    else:
        print("\nNo potential camera devices found in USB list")
    
    # Check if the camera might be on a different bus/device
    print("\nChecking USB devices by type:")
    stdout, _, _ = run_command("cat /proc/bus/input/devices")
    print(stdout or "No input devices found")
    
    return results

def check_video_devices() -> Dict[str, Any]:
    """Check available video devices"""
    print_section("Video Device Check")
    
    results = {}
    
    # Check for video devices
    stdout, stderr, _ = run_command("ls -l /dev/video*")
    if "No such file or directory" in stderr:
        print("No video devices found at /dev/video*")
        results["video_devices_found"] = False
    else:
        print("Video devices:")
        print(stdout)
        results["video_devices_found"] = True
        
        # Get the list of video devices
        devices = []
        for line in stdout.splitlines():
            if "/dev/video" in line:
                device = line.split()[-1]
                devices.append(device)
        results["video_devices"] = devices
    
    # Check v4l2 devices (more detailed)
    stdout, stderr, _ = run_command("v4l2-ctl --list-devices")
    if stdout:
        print("\nV4L2 devices:")
        print(stdout)
    else:
        print("\nNo V4L2 devices found or v4l2-ctl not installed")
    
    return results

def test_opencv_capture() -> Dict[str, Any]:
    """Test OpenCV camera capture on different device indices"""
    print_section("OpenCV Camera Test")
    
    results = {"success": False, "working_index": None}
    
    try:
        import cv2
        print("OpenCV version:", cv2.__version__)
        
        # Try different device indices
        for i in range(10):  # Try indices 0-9
            print(f"\nTesting camera at index {i}...")
            cap = cv2.VideoCapture(i)
            if not cap.isOpened():
                print(f"  Failed to open camera at index {i}")
                continue
            
            # Try to read a frame
            ret, frame = cap.read()
            if not ret:
                print(f"  Camera opened at index {i} but failed to read frame")
                cap.release()
                continue
            
            # If we get here, we successfully read a frame
            print(f"  SUCCESS: Camera working at index {i}")
            print(f"  Frame dimensions: {frame.shape[1]}x{frame.shape[0]}")
            
            # Save a test image
            test_file = f"camera_test_idx{i}.jpg"
            cv2.imwrite(test_file, frame)
            print(f"  Saved test image to {test_file}")
            
            results["success"] = True
            results["working_index"] = i
            
            # Release before trying the next camera
            cap.release()
    
    except ImportError:
        print("OpenCV (cv2) is not installed. Cannot test camera capture.")
    except Exception as e:
        print(f"Error during OpenCV testing: {e}")
    
    return results

def check_kernel_logs() -> Dict[str, Any]:
    """Check kernel logs for camera/video related messages"""
    print_section("Kernel Log Check")
    
    stdout, stderr, _ = run_command("dmesg | grep -i -E 'camera|video|uvc|webcam'")
    print("Camera-related kernel messages:")
    print(stdout or "No camera-related messages found in kernel log")
    
    return {"logs_checked": True}

def fix_video_device_permissions() -> Dict[str, Any]:
    """Fix permissions on video devices"""
    print_section("Fixing Video Device Permissions")
    
    results = {"attempted": True}
    
    # Find video devices
    stdout, stderr, _ = run_command("ls -l /dev/video*")
    if "No such file or directory" in stderr:
        print("No video devices found to fix permissions")
        return {"attempted": False}
    
    # Fix permissions
    print("Setting permissions for video devices...")
    devices = []
    for line in stdout.splitlines():
        if "/dev/video" in line:
            device = line.split()[-1]
            devices.append(device)
            cmd = f"sudo chmod 666 {device}"
            print(f"Running: {cmd}")
            run_command(cmd)
    
    print("\nCurrent permissions:")
    run_command("ls -l /dev/video*")
    
    results["devices_fixed"] = devices
    return results

def fix_camera_modules() -> Dict[str, Any]:
    """Load/reload camera kernel modules"""
    print_section("Fixing Camera Kernel Modules")
    
    results = {"attempted": True}
    
    # Unload and reload the UVC driver
    print("Unloading and reloading UVC driver...")
    run_command("sudo modprobe -r uvcvideo")
    time.sleep(1)
    run_command("sudo modprobe uvcvideo")
    time.sleep(2)
    
    # Check if the module is loaded
    stdout, stderr, _ = run_command("lsmod | grep uvc")
    if "uvcvideo" in stdout:
        print("UVC driver successfully reloaded")
        results["uvc_reloaded"] = True
    else:
        print("Failed to reload UVC driver")
        results["uvc_reloaded"] = False
    
    return results

def check_and_create_symlink() -> Dict[str, Any]:
    """Check if we need to create a symlink to the correct video device"""
    print_section("Checking for Video Device Symlink Needs")
    
    results = {"attempted": True}
    
    # Check if /dev/video0 exists
    stdout, stderr, _ = run_command("ls -l /dev/video0")
    if "No such file or directory" in stderr:
        print("/dev/video0 doesn't exist")
        
        # Find other video devices that might be available
        stdout, stderr, _ = run_command("ls -l /dev/video*")
        if "No such file or directory" not in stderr:
            # Find the first available video device
            for line in stdout.splitlines():
                if "/dev/video" in line:
                    source_device = line.split()[-1]
                    print(f"Found alternative video device: {source_device}")
                    
                    # Create a symlink
                    cmd = f"sudo ln -sf {source_device} /dev/video0"
                    print(f"Creating symlink with: {cmd}")
                    run_command(cmd)
                    
                    # Verify the symlink
                    stdout, stderr, _ = run_command("ls -l /dev/video0")
                    if "No such file or directory" not in stderr:
                        print("Symlink created successfully:")
                        print(stdout)
                        results["symlink_created"] = True
                    else:
                        print("Failed to create symlink")
                        results["symlink_created"] = False
                    
                    break
        else:
            print("No video devices found to create symlink from")
            results["no_devices"] = True
    else:
        print("/dev/video0 already exists:")
        print(stdout)
        results["already_exists"] = True
    
    return results

def update_device_manager_code() -> Dict[str, Any]:
    """Update the device_manager.py code with improved camera detection"""
    print_section("Updating Code for Better Camera Detection")
    
    results = {"attempted": True}
    
    # Get the OpenCV camera detection results
    opencv_results = test_opencv_capture()
    
    if opencv_results["success"]:
        working_index = opencv_results["working_index"]
        print(f"\nFound working camera at index {working_index}")
        
        # Update the device_manager.py file if it exists
        if os.path.exists("device_manager.py"):
            with open("device_manager.py", "r") as f:
                content = f.read()
            
            # Look for camera initialization code
            if "self.camera = cv2.VideoCapture(0)" in content:
                # Replace with the working index
                new_content = content.replace(
                    "self.camera = cv2.VideoCapture(0)", 
                    f"self.camera = cv2.VideoCapture({working_index})"
                )
                
                # Save the updated file
                with open("device_manager.py", "w") as f:
                    f.write(new_content)
                
                print(f"Updated device_manager.py to use camera index {working_index}")
                results["code_updated"] = True
            else:
                print("Could not find the camera initialization line in device_manager.py")
                results["code_updated"] = False
        else:
            print("device_manager.py not found in the current directory")
            results["file_found"] = False
    else:
        print("\nNo working camera found with OpenCV")
        results["working_camera"] = False
    
    return results

def generate_recommendations(all_results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on all test results"""
    recommendations = []
    
    # Check if we found a working camera
    if all_results.get("opencv", {}).get("success", False):
        working_index = all_results["opencv"]["working_index"]
        recommendations.append(f"✓ Working camera found at index {working_index}")
        recommendations.append(f"  Update your code to use: cv2.VideoCapture({working_index})")
    else:
        recommendations.append("✗ No working camera detected with OpenCV")
        
        # Check if USB devices were found
        if not all_results.get("usb_devices", {}).get("usb_cameras_found", False):
            recommendations.append("✗ No camera devices found in USB list")
            recommendations.append("  - Check if the camera is properly connected")
            recommendations.append("  - Try a different USB port")
            recommendations.append("  - Test the camera on another computer")
        
        # Check if video devices were found
        if not all_results.get("video_devices", {}).get("video_devices_found", False):
            recommendations.append("✗ No video devices found in /dev")
            recommendations.append("  - Make sure the camera driver is loaded")
            recommendations.append("  - Try running: sudo modprobe uvcvideo")
    
    # Add general recommendations
    recommendations.append("\nGeneral recommendations:")
    recommendations.append("1. Restart the Raspberry Pi and try again")
    recommendations.append("2. Try removing and reconnecting the camera")
    recommendations.append("3. In device_manager.py, update camera device index")
    recommendations.append("4. Update code to try multiple camera indices (0-9)")
    
    return recommendations

def main():
    print("Camera Access Troubleshooter")
    print("===========================")
    print("This script will help identify and fix camera access issues on Raspberry Pi")
    
    # Run all checks and fixes
    results = {}
    
    # Check USB devices
    results["usb_devices"] = check_usb_devices()
    
    # Check video devices
    results["video_devices"] = check_video_devices()
    
    # Check kernel logs
    results["kernel_logs"] = check_kernel_logs()
    
    # Fix video device permissions
    results["permissions"] = fix_video_device_permissions()
    
    # Fix camera modules
    results["modules"] = fix_camera_modules()
    
    # Check for symlink needs
    results["symlink"] = check_and_create_symlink()
    
    # Test OpenCV capture
    results["opencv"] = test_opencv_capture()
    
    # Update device_manager.py if a working camera was found
    if results["opencv"]["success"]:
        results["code_update"] = update_device_manager_code()
    
    # Generate recommendations
    print_section("Recommendations")
    recommendations = generate_recommendations(results)
    for rec in recommendations:
        print(rec)
    
    print("\nIf the camera still doesn't work after these fixes, try:")
    print("1. Check if the camera is supported on Raspberry Pi")
    print("2. Update Raspberry Pi OS to the latest version")
    print("3. Try a different camera")

if __name__ == "__main__":
    main()
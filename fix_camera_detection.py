#!/usr/bin/env python3
"""
Camera Detection Fix for Robot Vision System

This script provides a comprehensive solution for diagnosing and fixing camera detection
issues on Raspberry Pi systems with USB cameras.

Usage:
    python3 fix_camera_detection.py [--force-symlink] [--reset-permissions]

Options:
    --force-symlink      Create a symbolic link from /dev/usb_cam to detected camera
    --reset-permissions  Reset permissions on all video devices

This script handles common issues with USB cameras on Raspberry Pi:
1. Camera device detection problems
2. Permission issues
3. V4L2 driver compatibility
4. Camera index mapping conflicts
"""

import os
import sys
import subprocess
import argparse
import time

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "-" * 50)
    print(f"  {title}")
    print("-" * 50)

def run_command(cmd, capture=True, check=False):
    """Run a shell command and return the output"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result
        else:
            subprocess.run(cmd, shell=True, check=check)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return None

def check_v4l_utils():
    """Check if v4l-utils is installed and install if needed"""
    print_section("Checking for v4l-utils")
    
    result = run_command("which v4l2-ctl")
    if result.returncode != 0:
        print("v4l-utils not found, attempting to install...")
        if os.geteuid() == 0:  # Check if we're running as root
            install_result = run_command("apt-get update && apt-get install -y v4l-utils", capture=False)
            if install_result and install_result.returncode != 0:
                print("❌ Failed to install v4l-utils. Some diagnostic features will be limited.")
                return False
            else:
                print("✅ v4l-utils installed successfully")
                return True
        else:
            print("⚠️ Not running as root, cannot install v4l-utils.")
            print("   Please run: sudo apt-get update && sudo apt-get install -y v4l-utils")
            return False
    else:
        print("✅ v4l-utils is already installed")
        return True

def list_video_devices():
    """List all video devices"""
    print_section("Detecting Video Devices")
    
    # Check /dev/video*
    print("Checking for video devices in /dev...")
    result = run_command("ls -l /dev/video* 2>/dev/null")
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("No video devices found in /dev/video*")
    
    # Check v4l2 devices if available
    result = run_command("which v4l2-ctl")
    if result.returncode == 0:
        print("\nDetailed V4L2 device information:")
        result = run_command("v4l2-ctl --list-devices")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Failed to list V4L2 devices")
    
    # Check USB devices
    print("\nChecking for USB camera devices...")
    result = run_command("lsusb | grep -i camera")
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("No USB cameras detected with lsusb")
        # Try a more generic search
        result = run_command("lsusb | grep -i video")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No USB video devices detected with lsusb")

    return result.returncode == 0

def test_camera_access(devices=None):
    """Test camera access with OpenCV"""
    print_section("Testing Camera Access with OpenCV")
    
    try:
        import cv2
        print("✅ OpenCV is installed")
    except ImportError:
        print("❌ OpenCV (cv2) is not installed")
        print("   Install with: pip install opencv-python")
        return False
    
    # If no specific devices provided, try common options
    if devices is None:
        devices = ["/dev/video0", "/dev/usb_cam", "/dev/webcam", 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -1]
    
    for device in devices:
        print(f"\nTrying camera device: {device}")
        try:
            cap = cv2.VideoCapture(device)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"✅ Successfully captured frame from camera {device}")
                    # Save a test image
                    test_img_path = f"camera_test_{device}.jpg"
                    # Handle integer device IDs for the filename
                    if isinstance(device, int):
                        test_img_path = f"camera_test_index_{device}.jpg"
                    try:
                        cv2.imwrite(test_img_path, frame)
                        print(f"   Test image saved to {test_img_path}")
                    except Exception as e:
                        print(f"   Failed to save test image: {e}")
                else:
                    print(f"❌ Camera {device} opened but failed to capture frame")
                cap.release()
            else:
                print(f"❌ Failed to open camera {device}")
        except Exception as e:
            print(f"❌ Error accessing camera {device}: {e}")
    
    return True

def fix_camera_permissions():
    """Fix camera device permissions"""
    print_section("Fixing Camera Permissions")
    
    if os.geteuid() != 0:
        print("⚠️ Not running as root, cannot modify permissions.")
        print("   Run with sudo for full functionality.")
        return False
    
    # Fix permissions for all video devices
    result = run_command("chmod a+rw /dev/video* 2>/dev/null")
    if result.returncode == 0:
        print("✅ Permission fixed for video devices")
    else:
        print("No video devices found or permission fix failed")
    
    # Check group membership
    user = os.environ.get("USER", os.environ.get("LOGNAME", "pi"))
    result = run_command(f"groups {user} | grep -q video")
    if result.returncode != 0:
        print(f"\nAdding user {user} to video group...")
        result = run_command(f"usermod -a -G video {user}")
        if result.returncode == 0:
            print(f"✅ Added {user} to video group")
            print("   You may need to log out and back in for changes to take effect")
        else:
            print(f"❌ Failed to add {user} to video group")
    else:
        print(f"✅ User {user} is already in video group")
    
    return True

def create_camera_symlink(force=False):
    """Create symbolic link from /dev/usb_cam to first available camera"""
    print_section("Creating Camera Symlink")
    
    # Check if symlink already exists
    if os.path.exists("/dev/usb_cam") and not force:
        print("Symlink /dev/usb_cam already exists")
        result = run_command("ls -la /dev/usb_cam")
        if result.returncode == 0:
            print(result.stdout)
        print("\nUse --force-symlink to recreate it")
        return True
    
    # Find the first available video device
    result = run_command("ls /dev/video* 2>/dev/null | head -1")
    if result.returncode == 0 and result.stdout.strip():
        video_device = result.stdout.strip()
        print(f"Found video device: {video_device}")
        
        # Remove existing symlink if forced
        if os.path.exists("/dev/usb_cam") and force:
            run_command("rm -f /dev/usb_cam")
        
        # Create the symlink
        result = run_command(f"ln -sf {video_device} /dev/usb_cam")
        if result.returncode == 0:
            print(f"✅ Created symlink: /dev/usb_cam -> {video_device}")
            result = run_command("ls -la /dev/usb_cam")
            if result.returncode == 0:
                print(result.stdout)
            return True
        else:
            print(f"❌ Failed to create symlink to {video_device}")
            return False
    else:
        print("❌ No video devices found to link to")
        return False

def update_device_manager():
    """Update device_manager.py with improved camera code"""
    print_section("Updating Camera Code in device_manager.py")
    
    if not os.path.exists("device_manager.py"):
        print("❌ device_manager.py not found in current directory")
        return False
    
    # Create a backup
    backup_file = "device_manager.py.camera_backup"
    print(f"Creating backup: {backup_file}")
    run_command(f"cp device_manager.py {backup_file}")
    
    # Read the existing file
    with open("device_manager.py", "r") as f:
        content = f.read()
    
    # Check if we've already applied the update
    if "# Enhanced camera detection (added by fix_camera_detection.py)" in content:
        print("✅ Camera detection code has already been updated")
        return True
    
    # Look for the camera initialization section
    camera_init_section = """            # Initialize camera if cv2 is available
            if cv2 is not None:
                try:
                    # First check if camera device exists
                    import subprocess
                    
                    # Try multiple methods to detect camera devices
                    self.logger.info("Checking for camera devices...")"""
    
    if camera_init_section not in content:
        print("❌ Camera initialization section not found in device_manager.py")
        print("Manual update may be required")
        return False
    
    # Create the enhanced camera detection code
    enhanced_camera_code = """            # Initialize camera if cv2 is available
            if cv2 is not None:
                try:
                    # Enhanced camera detection (added by fix_camera_detection.py)
                    # First check if camera device exists
                    import subprocess
                    import glob
                    import platform
                    
                    self.logger.info("Enhanced camera detection starting...")
                    
                    # Get system info
                    system_info = platform.system()
                    self.logger.info(f"Running on: {system_info} {platform.release()}")
                    
                    # Try multiple methods to detect camera devices
                    self.logger.info("Checking for camera devices...")
                    
                    # Get list of all available video devices
                    video_devices = glob.glob("/dev/video*")
                    if video_devices:
                        video_str = ", ".join(video_devices)
                        self.logger.info(f"Found video devices: {video_str}")
                    else:
                        self.logger.warning("No /dev/video* devices found")
                    
                    # Check USB devices with lsusb if available
                    try:
                        usb_check = subprocess.run("lsusb | grep -i cam", 
                                              shell=True, capture_output=True, text=True)
                        if usb_check.returncode == 0:
                            self.logger.info(f"USB camera devices: {usb_check.stdout.strip()}")
                        else:
                            # Try a more generic search for video devices
                            usb_check = subprocess.run("lsusb | grep -i video", 
                                                  shell=True, capture_output=True, text=True)
                            if usb_check.returncode == 0:
                                self.logger.info(f"USB video devices: {usb_check.stdout.strip()}")
                    except Exception as e:
                        self.logger.warning(f"Error checking USB devices: {e}")
                    
                    # Check for V4L2 devices if v4l2-ctl is available
                    try:
                        v4l_check = subprocess.run("which v4l2-ctl", 
                                              shell=True, capture_output=True)
                        if v4l_check.returncode == 0:
                            v4l_list = subprocess.run("v4l2-ctl --list-devices", 
                                                 shell=True, capture_output=True, text=True)
                            if v4l_list.returncode == 0:
                                self.logger.info(f"V4L2 devices:\\n{v4l_list.stdout.strip()}")
                    except Exception as e:
                        self.logger.warning(f"Error checking V4L2 devices: {e}")"""
    
    # Update the content
    new_content = content.replace(camera_init_section, enhanced_camera_code)
    
    # Update camera paths to include more device options
    camera_paths_line = "                    camera_paths = [self.camera_id, \"/dev/video0\", \"/dev/usb_cam\", 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]"
    enhanced_paths = "                    camera_paths = [self.camera_id, \"/dev/video0\", \"/dev/usb_cam\", \"/dev/webcam\", \
\"/dev/v4l/by-id/usb-USB_Camera_USB_Camera-video-index0\", \
\"/dev/v4l/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3:1.0-video-index0\", \
-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15]"
    
    new_content = new_content.replace(camera_paths_line, enhanced_paths)
    
    # Update the attempt to open each camera with more robust error handling
    camera_open_block = """                    # Try each possible camera device
                    for cam_id in camera_paths:
                        try:
                            self.logger.info(f"Trying camera device: {cam_id}")
                            self.camera = cv2.VideoCapture(cam_id)
                            if self.camera.isOpened():
                                self.logger.info(f"Camera initialized successfully with device {cam_id}")
                                break
                        except Exception as e:
                            self.logger.warning(f"Failed to open camera {cam_id}: {str(e)}")"""
    
    enhanced_camera_open = """                    # Try each possible camera device with improved error handling
                    for cam_id in camera_paths:
                        try:
                            self.logger.info(f"Trying camera device: {cam_id}")
                            
                            # Set a timeout for camera initialization to prevent hanging
                            # This is particularly important for Raspberry Pi cameras
                            start_time = time.time()
                            
                            # Attempt to open the camera with the current ID
                            self.camera = cv2.VideoCapture(cam_id)
                            
                            # Check if camera opened successfully
                            if self.camera.isOpened():
                                # Try to read a test frame to verify it's working
                                ret, test_frame = self.camera.read()
                                
                                if ret and test_frame is not None and test_frame.size > 0:
                                    self.logger.info(f"Camera initialized successfully with device {cam_id}")
                                    
                                    # Store the working camera ID
                                    self.working_camera_id = cam_id
                                    
                                    # Set camera properties for better performance
                                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                                    
                                    # Log camera properties
                                    width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                                    height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                                    fps = self.camera.get(cv2.CAP_PROP_FPS)
                                    self.logger.info(f"Camera configured: {width}x{height} at {fps} FPS")
                                    
                                    break
                                else:
                                    self.logger.warning(f"Camera {cam_id} opened but failed to capture test frame")
                                    self.camera.release()
                                    self.camera = None
                            else:
                                self.logger.warning(f"Failed to open camera {cam_id}")
                                
                            # Check if we've spent too long on this camera ID
                            if time.time() - start_time > 2.0:  # 2 second timeout
                                self.logger.warning(f"Timeout while initializing camera {cam_id}")
                                
                        except Exception as e:
                            self.logger.warning(f"Error accessing camera {cam_id}: {str(e)}")"""
    
    new_content = new_content.replace(camera_open_block, enhanced_camera_open)
    
    # Add a working_camera_id attribute to the __init__ method
    init_code = """        # Camera ID - video0 for USB camera
        self.camera_id = 0  # /dev/usb_cam -> video0"""
    
    enhanced_init = """        # Camera ID - video0 for USB camera
        self.camera_id = 0  # /dev/usb_cam -> video0
        self.working_camera_id = None  # Will store the ID of the successfully initialized camera"""
    
    new_content = new_content.replace(init_code, enhanced_init)
    
    # Write the updated content back to the file
    with open("device_manager.py", "w") as f:
        f.write(new_content)
    
    print("✅ Updated device_manager.py with enhanced camera detection")
    print("   Original file backed up to device_manager.py.camera_backup")
    return True

def fix_raspi_camera_config():
    """Check and fix Raspberry Pi camera configuration"""
    print_section("Checking Raspberry Pi Camera Configuration")
    
    # Check if this is a Raspberry Pi
    if not os.path.exists("/proc/device-tree/model"):
        print("This doesn't appear to be a Raspberry Pi")
        return False
    
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read()
        if "Raspberry Pi" not in model:
            print(f"This doesn't appear to be a Raspberry Pi: {model}")
            return False
        
        print(f"Detected: {model}")
    except:
        print("Unable to determine if this is a Raspberry Pi")
        return False
    
    # Check if camera is enabled in config
    print("\nChecking config.txt for camera settings...")
    camera_enabled = False
    camera_legacy = False
    
    if os.path.exists("/boot/config.txt"):
        config_path = "/boot/config.txt"
    elif os.path.exists("/boot/firmware/config.txt"):
        config_path = "/boot/firmware/config.txt"
    else:
        print("Could not find config.txt in /boot or /boot/firmware")
        return False
    
    try:
        with open(config_path, "r") as f:
            config = f.read()
        
        if "start_x=1" in config:
            camera_enabled = True
            print("✅ Camera is enabled (start_x=1)")
        else:
            print("❌ Camera may not be enabled (start_x=1 not found)")
        
        if "camera_auto_detect=1" in config:
            print("✅ Camera auto-detection is enabled")
        
        if "dtoverlay=vc4-kms-v3d" in config:
            print("✅ Using VC4 KMS V3D overlay")
            camera_legacy = False
        
        if "dtoverlay=ov5647" in config or "dtoverlay=imx219" in config:
            print("✅ Camera module overlay detected")
        
    except Exception as e:
        print(f"Error reading config.txt: {e}")
        return False
    
    # Check if this is running on a supported OS
    print("\nChecking OS...")
    result = run_command("cat /etc/os-release")
    if result.returncode == 0:
        print(result.stdout)
    
    # Load camera modules if needed
    print("\nChecking camera modules...")
    result = run_command("lsmod | grep -E 'bcm2835_v4l2|v4l2_common'")
    if result.returncode != 0:
        print("Camera modules not loaded, attempting to load...")
        if camera_legacy:
            result = run_command("sudo modprobe bcm2835_v4l2")
            if result.returncode == 0:
                print("✅ Loaded bcm2835_v4l2 module")
            else:
                print("❌ Failed to load bcm2835_v4l2 module")
        else:
            result = run_command("sudo modprobe v4l2_common")
            if result.returncode == 0:
                print("✅ Loaded v4l2_common module")
            else:
                print("❌ Failed to load v4l2_common module")
    else:
        print("✅ Camera modules are loaded")
    
    return True

def print_recommendations():
    """Print recommendations for solving camera issues"""
    print_section("Recommendations")
    
    print("""
1. If using a USB camera:
   - Make sure the camera is properly connected to a USB port
   - Try a different USB port (preferably USB 2.0 for compatibility)
   - Ensure the camera is not in use by another application

2. If using a Raspberry Pi Camera Module:
   - Verify that the ribbon cable is properly connected to both the camera and the Pi
   - Make sure the camera module is enabled in raspi-config
   - If using bullseye or later, ensure legacy camera support is enabled

3. Check permissions:
   - Ensure your user is in the 'video' group: sudo usermod -a -G video $USER
   - Make sure video devices have the right permissions: sudo chmod a+rw /dev/video*

4. For OpenCV issues:
   - Try different camera indices (0, 1, 2) as device numbering can vary
   - Use the symbolic link (/dev/usb_cam) created by this script

5. If the camera is detected but images are corrupted:
   - Try a powered USB hub if using a USB camera
   - Lower the resolution and frame rate in the code

6. For advanced debugging:
   - Install v4l-utils: sudo apt-get install v4l-utils
   - Check available video devices: v4l2-ctl --list-devices
   - Query camera capabilities: v4l2-ctl --device=/dev/video0 --all
    """)

def main():
    parser = argparse.ArgumentParser(description="Fix camera detection issues for robot vision")
    parser.add_argument("--force-symlink", action="store_true", 
                        help="Force recreation of the /dev/usb_cam symlink")
    parser.add_argument("--reset-permissions", action="store_true",
                        help="Reset permissions on all video devices")
    args = parser.parse_args()
    
    print_header("Camera Detection Fix for Robot Vision System")
    
    # Check v4l-utils
    have_v4l_utils = check_v4l_utils()
    
    # List video devices
    list_video_devices()
    
    # Test camera access
    test_camera_access()
    
    # Fix permissions if requested
    if args.reset_permissions:
        fix_camera_permissions()
    
    # Create symlink if requested
    if args.force_symlink:
        create_camera_symlink(force=True)
    else:
        create_camera_symlink()
    
    # Check Raspberry Pi camera config
    fix_raspi_camera_config()
    
    # Update device_manager.py
    update_device_manager()
    
    # Print recommendations
    print_recommendations()
    
    print("\nCamera detection fix complete!")
    print("Run the robot_voice_interface.py again to see if the camera is now detected.")
    print("If problems persist, try running with sudo for permission fixes:")
    print("  sudo python3 fix_camera_detection.py --reset-permissions --force-symlink")

if __name__ == "__main__":
    main()
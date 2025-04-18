#!/bin/bash
# Raspberry Pi Camera Fix Script
# This script performs a comprehensive fix for camera access issues on Raspberry Pi

echo "=========================================================="
echo "          Raspberry Pi Camera Access Fix Tool             "
echo "=========================================================="
echo "This script will diagnose and fix common camera access issues"
echo "You may be prompted for your sudo password"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "=========================================================="
    echo "  $1"
    echo "=========================================================="
}

# Check if running as root, if not, warn user
if [ "$EUID" -ne 0 ]; then
    echo "Note: This script is not running as root."
    echo "Some operations require sudo privileges and you may be prompted for your password."
    echo ""
fi

# Check for camera hardware
print_section "Checking for camera hardware"
echo "Checking USB devices:"
lsusb | grep -i "cam\|video\|webcam"

if [ $? -ne 0 ]; then
    echo "No USB camera detected with lsusb."
    echo "Checking alternative methods..."
    
    # Try another detection method
    if [ -d "/dev/v4l/by-id" ]; then
        echo "Checking /dev/v4l/by-id:"
        ls -la /dev/v4l/by-id
    else
        echo "No devices found in /dev/v4l/by-id"
    fi
fi

# Check for video devices
print_section "Checking for video devices"
echo "Checking for video devices in /dev:"
ls -l /dev/video* 2>/dev/null

if [ $? -ne 0 ]; then
    echo "No video devices found in /dev."
    echo "This might indicate your camera is not properly connected or recognized."
    echo "Try disconnecting and reconnecting the camera."
else
    echo "Found video devices. Setting permissions..."
    sudo chmod 666 /dev/video* 2>/dev/null
    echo "New permissions:"
    ls -l /dev/video*
fi

# Check v4l2 devices (more detailed)
print_section "Checking V4L2 devices"
if command -v v4l2-ctl &> /dev/null; then
    v4l2-ctl --list-devices
else
    echo "v4l2-ctl not found. Installing v4l-utils..."
    sudo apt-get update
    sudo apt-get install -y v4l-utils
    echo "Checking V4L2 devices:"
    v4l2-ctl --list-devices
fi

# Install necessary packages
print_section "Installing necessary packages"
echo "Installing required packages for camera access:"
sudo apt-get update
sudo apt-get install -y v4l-utils python3-opencv libopencv-dev

# Reload uvcvideo module
print_section "Reloading UVC video module"
echo "Unloading and reloading the UVC video driver..."
sudo modprobe -r uvcvideo
sleep 2
sudo modprobe uvcvideo
sleep 2

# Check if the module loaded correctly
lsmod | grep uvc
if [ $? -eq 0 ]; then
    echo "UVC driver successfully reloaded."
else
    echo "Failed to reload UVC driver. This may indicate an issue with your kernel or camera."
fi

# Create symlinks if needed
print_section "Setting up device symlinks"
if [ ! -e "/dev/video0" ]; then
    echo "/dev/video0 doesn't exist. Looking for alternative video devices..."
    
    # Find first available video device
    for i in $(ls /dev/video* 2>/dev/null); do
        if [ -e "$i" ]; then
            echo "Found alternative video device: $i"
            echo "Creating symlink from $i to /dev/video0..."
            sudo ln -sf "$i" /dev/video0
            if [ -e "/dev/video0" ]; then
                echo "Symlink created successfully."
                echo "New symlink:"
                ls -l /dev/video0
            else
                echo "Failed to create symlink."
            fi
            break
        fi
    done
else
    echo "/dev/video0 already exists:"
    ls -l /dev/video0
fi

# Add user to video group to ensure permissions
print_section "Setting up user permissions"
echo "Adding current user to video group..."
sudo usermod -a -G video $USER
echo "User added to video group. You may need to log out and back in for this to take effect."
echo "Current groups for $USER:"
groups $USER

# Custom fix for Raspberry Pi specific issues
print_section "Raspberry Pi specific fixes"

# Check for and enable the camera interface if using a Raspberry Pi camera module
if [ -f "/boot/config.txt" ]; then
    echo "Checking Raspberry Pi camera configuration..."
    if grep -q "^start_x=1" /boot/config.txt; then
        echo "Camera interface already enabled in /boot/config.txt"
    else
        echo "Enabling camera interface in /boot/config.txt..."
        sudo sed -i 's/^start_x=0/start_x=1/' /boot/config.txt
        if ! grep -q "^start_x=" /boot/config.txt; then
            echo "Adding start_x=1 to /boot/config.txt..."
            echo "start_x=1" | sudo tee -a /boot/config.txt
        fi
        echo "Camera interface enabled. A reboot is required for changes to take effect."
    fi
    
    # Ensure GPU memory is sufficient for camera
    if grep -q "^gpu_mem=" /boot/config.txt; then
        gpu_mem=$(grep "^gpu_mem=" /boot/config.txt | cut -d= -f2)
        if [ "$gpu_mem" -lt 128 ]; then
            echo "Increasing GPU memory from $gpu_mem to 128MB..."
            sudo sed -i 's/^gpu_mem=.*/gpu_mem=128/' /boot/config.txt
            echo "GPU memory increased. A reboot is required for changes to take effect."
        else
            echo "GPU memory already set to $gpu_mem MB, which should be sufficient."
        fi
    else
        echo "Setting GPU memory to 128MB..."
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
        echo "GPU memory set. A reboot is required for changes to take effect."
    fi
    
    reboot_needed=true
fi

# Test camera with Python OpenCV
print_section "Testing camera with OpenCV"
echo "Testing camera access with OpenCV..."
echo "This will try each possible camera index (0-9) to find your camera"

# Create a temporary Python script to test camera access
cat > /tmp/test_camera.py << 'EOF'
import cv2
import sys

def test_camera(index):
    print(f"Testing camera index {index}...")
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"Could not open camera at index {index}")
        return False, None
    
    ret, frame = cap.read()
    if not ret:
        print(f"Camera opened at index {index} but could not read frame")
        cap.release()
        return False, None
    
    print(f"SUCCESS: Camera working at index {index}")
    print(f"Frame dimensions: {frame.shape[1]}x{frame.shape[0]}")
    
    # Save a test image
    test_file = f"camera_test_idx{index}.jpg"
    cv2.imwrite(test_file, frame)
    print(f"Saved test image to {test_file}")
    
    cap.release()
    return True, index

def main():
    working_index = None
    
    # Try indices 0-9
    for i in range(10):
        success, index = test_camera(i)
        if success:
            working_index = index
            break
    
    if working_index is not None:
        print(f"\nCamera found at index {working_index}")
        print("Use this index in your Python code: cv2.VideoCapture({})".format(working_index))
        
        print("\nCreating a helper script to use this camera index...")
        with open("use_camera.py", "w") as f:
            f.write(f"""#!/usr/bin/env python3
# Quick camera test script
import cv2
import time

def main():
    print("Opening camera at index {working_index}...")
    cap = cv2.VideoCapture({working_index})
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print("Camera opened successfully")
    print("Press 'q' to exit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break
        
        cv2.imshow('Camera Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
""")
        print("Created use_camera.py - run with: python3 use_camera.py")
        
        # Update the device_manager.py if it exists
        try:
            if working_index != 0:
                import fileinput
                import re
                
                file_path = "device_manager.py"
                with open(file_path, 'r') as file:
                    content = file.read()
                
                # Update the camera_id
                camera_id_pattern = r'self\.camera_id\s*=\s*\d+'
                if re.search(camera_id_pattern, content):
                    new_content = re.sub(camera_id_pattern, f'self.camera_id = {working_index}', content)
                    with open(file_path, 'w') as file:
                        file.write(new_content)
                    print(f"Updated device_manager.py to use camera index {working_index}")
        except Exception as e:
            print(f"Could not update device_manager.py: {e}")
    else:
        print("\nNo working camera found.")
        print("Make sure the camera is properly connected and try again.")
        print("You may need to reboot after the changes made by this script.")

if __name__ == "__main__":
    main()
EOF

# Run the camera test script
echo "Running camera test script..."
python3 /tmp/test_camera.py

# Final recommendations
print_section "Final recommendations"
echo "If your camera still doesn't work after these fixes, try:"
echo "1. Reboot your Raspberry Pi"
echo "2. Try a different USB port (preferably USB 3.0 if available)"
echo "3. Try a different USB cable"
echo "4. Make sure your camera is compatible with Raspberry Pi"
echo "5. Check the camera manufacturer's website for Linux drivers"

# Add a recommendation for using Whisper API
echo "6. If your camera works but speech recognition still fails:"
echo "   Make sure you've installed the FLAC utility with:"
echo "   sudo apt-get install -y flac"
echo "   Your code will automatically fall back to OpenAI Whisper API if needed"

if [ "$reboot_needed" = true ]; then
    print_section "Reboot Required"
    echo "Some changes require a reboot to take effect."
    echo "Please reboot your Raspberry Pi with: sudo reboot"
fi

echo ""
echo "Camera fix script completed!"
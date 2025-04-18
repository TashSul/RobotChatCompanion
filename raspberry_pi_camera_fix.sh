#!/bin/bash
# Raspberry Pi Camera Fix Script for Robot Vision
# This script fixes common camera issues on Raspberry Pi for the robot vision system
# Run with sudo: sudo ./raspberry_pi_camera_fix.sh

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root: sudo $0${NC}"
  exit 1
fi

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  Raspberry Pi Camera Fix for Robot Vision  ${NC}"
echo -e "${BLUE}=============================================${NC}"

# Function to print section header
print_section() {
  echo -e "\n${YELLOW}$1${NC}"
  echo -e "${YELLOW}----------------------------------------${NC}"
}

# Function to print success message
success() {
  echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error message
error() {
  echo -e "${RED}✗ $1${NC}"
}

# Check if we're running on a Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
  error "This script is designed for Raspberry Pi systems only"
  exit 1
fi

# Get Raspberry Pi model
MODEL=$(cat /proc/device-tree/model | tr -d '\0')
echo -e "Detected: ${BLUE}$MODEL${NC}"

# Check OS
print_section "Checking Operating System"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo "OS: $PRETTY_NAME"
  
  # Check if this is Raspberry Pi OS (Raspbian)
  if [[ "$PRETTY_NAME" == *"Raspberry Pi OS"* ]] || [[ "$PRETTY_NAME" == *"Raspbian"* ]]; then
    success "Running on Raspberry Pi OS"
  elif [[ "$PRETTY_NAME" == *"Ubuntu"* ]]; then
    success "Running on Ubuntu for Raspberry Pi"
  else
    echo "Running on a different OS: $PRETTY_NAME"
    echo "This script is tested on Raspberry Pi OS and Ubuntu, but should work on other Linux distributions"
  fi
else
  error "Could not determine OS"
fi

# Fix 1: Check and update camera configuration
print_section "Checking Camera Configuration"

# Determine config.txt location
if [ -f /boot/config.txt ]; then
  CONFIG_PATH="/boot/config.txt"
elif [ -f /boot/firmware/config.txt ]; then
  CONFIG_PATH="/boot/firmware/config.txt"
else
  error "Could not find config.txt in /boot or /boot/firmware"
  exit 1
fi

echo "Using config file: $CONFIG_PATH"

# Check if camera is enabled
if grep -q "^start_x=1" $CONFIG_PATH; then
  success "Camera is enabled in config.txt"
else
  echo "Camera might not be enabled in config.txt"
  echo "Adding start_x=1 to $CONFIG_PATH"
  
  # Back up config.txt
  cp $CONFIG_PATH ${CONFIG_PATH}.backup
  
  # Add start_x=1 if not present
  if ! grep -q "start_x=" $CONFIG_PATH; then
    echo "start_x=1" >> $CONFIG_PATH
    success "Added start_x=1 to $CONFIG_PATH"
  else
    # Replace start_x=0 with start_x=1
    sed -i 's/start_x=0/start_x=1/g' $CONFIG_PATH
    success "Updated start_x to 1 in $CONFIG_PATH"
  fi
  
  # Add gpu_mem=128 if not present
  if ! grep -q "gpu_mem=" $CONFIG_PATH; then
    echo "gpu_mem=128" >> $CONFIG_PATH
    success "Added gpu_mem=128 to $CONFIG_PATH"
  fi
  
  echo "Original config.txt backed up to ${CONFIG_PATH}.backup"
  echo "You will need to reboot for these changes to take effect"
fi

# Fix 2: Check and load camera modules
print_section "Checking Camera Kernel Modules"

# Check if camera kernel module is loaded
if lsmod | grep -q "bcm2835_v4l2"; then
  success "Camera kernel module 'bcm2835_v4l2' is loaded"
else
  echo "Loading camera module 'bcm2835_v4l2'..."
  modprobe bcm2835_v4l2
  
  if lsmod | grep -q "bcm2835_v4l2"; then
    success "Successfully loaded camera module"
  else
    error "Failed to load camera module"
    echo "Add 'bcm2835_v4l2' to /etc/modules to load at boot time"
  fi
fi

# Fix 3: Set up /dev/usb_cam symlink
print_section "Setting up Camera Symlinks"

# First check for video devices
if ls /dev/video* >/dev/null 2>&1; then
  VIDEO_DEVICES=$(ls /dev/video* | wc -l)
  success "Found $VIDEO_DEVICES video device(s)"
  
  # Create symlink to first video device if it doesn't exist
  if [ -L /dev/usb_cam ]; then
    echo "Symlink /dev/usb_cam already exists, pointing to $(readlink /dev/usb_cam)"
    echo "Removing existing symlink and recreating..."
    rm -f /dev/usb_cam
  fi
  
  FIRST_VIDEO=$(ls /dev/video* | head -1)
  ln -sf $FIRST_VIDEO /dev/usb_cam
  success "Created symlink: /dev/usb_cam -> $FIRST_VIDEO"
else
  error "No video devices found in /dev"
  echo "Camera not detected or driver not loaded"
fi

# Fix 4: Set proper permissions
print_section "Setting Permissions"

# Fix permissions on video devices
echo "Setting permissions on camera devices..."
chmod a+rw /dev/video* 2>/dev/null
success "Updated permissions on camera devices"

# Make sure user is in video group
USER_TO_ADD=${SUDO_USER:-pi}
if ! groups $USER_TO_ADD | grep -q "video"; then
  echo "Adding user $USER_TO_ADD to video group..."
  usermod -a -G video $USER_TO_ADD
  success "Added $USER_TO_ADD to video group"
else
  success "User $USER_TO_ADD is already in video group"
fi

# Fix 5: Kill any processes that might be using the camera
print_section "Checking for Processes Using the Camera"

# Check if any processes are using the camera
if lsof /dev/video* >/dev/null 2>&1; then
  echo "Found processes using the camera:"
  lsof /dev/video*
  
  echo "Killing processes using the camera..."
  fuser -k /dev/video* 2>/dev/null
  success "Terminated processes using camera"
else
  success "No processes are currently using the camera"
fi

# Fix 6: Test camera capture
print_section "Testing Camera Capture"

# Check if v4l-utils is installed
if ! command -v v4l2-ctl >/dev/null; then
  echo "Installing v4l-utils for camera testing..."
  apt-get update && apt-get install -y v4l-utils
  success "Installed v4l-utils"
else
  success "v4l-utils is already installed"
fi

# Check camera capabilities
echo "Camera device capabilities:"
v4l2-ctl --device=/dev/usb_cam --all | grep -E "Driver|Card|Video input|Format"

# Try to capture a test image with v4l2-ctl
echo "Capturing test image with v4l2-ctl..."
TEST_IMG_PATH="/tmp/camera_test_$(date +%Y%m%d%H%M%S).jpg"
v4l2-ctl --device=/dev/usb_cam --set-fmt-video=width=640,height=480,pixelformat=MJPG --stream-mmap --stream-to=$TEST_IMG_PATH --stream-count=1

if [ -f $TEST_IMG_PATH ]; then
  success "Successfully captured test image to $TEST_IMG_PATH"
  echo "You can view this image to confirm camera is working"
else
  error "Failed to capture test image"
fi

# Install fswebcam if not available (simple utility to test camera)
if ! command -v fswebcam >/dev/null; then
  echo "Installing fswebcam for camera testing..."
  apt-get update && apt-get install -y fswebcam
  success "Installed fswebcam"
fi

# Try to capture a test image with fswebcam
echo "Capturing test image with fswebcam..."
FSWEBCAM_IMG_PATH="/tmp/fswebcam_test_$(date +%Y%m%d%H%M%S).jpg"
fswebcam -d /dev/usb_cam -r 640x480 $FSWEBCAM_IMG_PATH

if [ -f $FSWEBCAM_IMG_PATH ]; then
  success "Successfully captured test image with fswebcam to $FSWEBCAM_IMG_PATH"
else
  error "Failed to capture test image with fswebcam"
fi

# Fix 7: Add camera module to load at boot
print_section "Setting Up Automatic Module Loading"

if ! grep -q "bcm2835_v4l2" /etc/modules; then
  echo "Adding camera module to /etc/modules for loading at boot time..."
  echo "bcm2835_v4l2" >> /etc/modules
  success "Added bcm2835_v4l2 to /etc/modules"
else
  success "Camera module already configured to load at boot time"
fi

# Create udev rule for camera
print_section "Setting Up Camera udev Rules"

UDEV_RULE="/etc/udev/rules.d/99-camera.rules"
echo "Creating udev rule for camera..."
cat > $UDEV_RULE << EOF
# Rules for camera devices
KERNEL=="video*", SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
# Create persistent symlink to the first camera
KERNEL=="video0", SUBSYSTEM=="video4linux", SYMLINK+="usb_cam"
EOF

success "Created udev rule: $UDEV_RULE"
echo "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

print_section "Next Steps"

echo -e "${GREEN}Camera setup completed!${NC}"
echo "Here are the next steps:"
echo "1. Reboot your Raspberry Pi: sudo reboot"
echo "2. After reboot, test the camera with: python3 test_camera_diagnostics.py"
echo "3. If issues persist, run: python3 fix_camera_detection.py"
echo
echo -e "${YELLOW}NOTE:${NC} Some changes require a reboot to take effect"
echo "For ongoing issues, check the camera connection or try a different USB port"
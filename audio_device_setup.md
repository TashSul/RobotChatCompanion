# Audio Device Configuration for Robot Voice Interface

This document explains how to configure and test the audio devices for the robot voice interface on a Raspberry Pi.

## Default Configuration

The system is configured with separate devices for microphone input and speaker output:

- **Microphone Device**: `plughw:3,0` (USB PnP Sound Device)
- **Speaker Device**: `plughw:2,0` (iStore Audio)

This configuration is based on hardware detection from your Raspberry Pi:

```
# Capture (Recording) Devices:
card 3: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0

# Playback Devices:
card 2: Audio [iStore Audio], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

## ALSA Configuration

The system uses direct hardware addressing through the `plughw` interface. If you want to set default devices in your ALSA configuration, you can create or modify `/etc/asound.conf` or `~/.asoundrc`:

```
# Example configuration for default playback through iStore Audio (card 2)
pcm.!default {
    type hw
    card 2  # iStore Audio for playback
}
ctl.!default {
    type hw
    card 2
}

# For recording, explicitly specify the USB PnP Sound Device (card 3)
# when using arecord
```

## Testing the Audio Devices

We've provided several test scripts to verify your audio device setup:

### 1. Basic Command Test

This script verifies that the required audio commands are installed and working:

```bash
python test_audio_commands.py
```

### 2. Simple Audio Device Test

This script tests the microphone and speaker functionality with minimal dependencies:

```bash
python audio_device_test.py
```

You can also list available devices:

```bash
python audio_device_test.py --list
```

### 3. Comprehensive Robot Audio Test

This script performs a more thorough test of the robot's audio capabilities:

```bash
python robot_audio_test.py
```

## Customizing Device Settings

If your audio devices are on different cards, you can modify the settings in the following files:

1. `device_manager.py` - Main device settings for the robot interface
2. `audio_device_test.py` - Test script device settings
3. `robot_audio_test.py` - Comprehensive test script settings
4. `test_audio_commands.py` - Command test script settings

## Troubleshooting

If you encounter audio device errors:

1. Check device availability:
   ```bash
   aplay -l
   arecord -l
   ```

2. Test direct recording and playback:
   ```bash
   # Record 5 seconds of audio with USB PnP Sound Device
   arecord -D plughw:3,0 -d 5 -f cd test.wav
   
   # Play back the recording through iStore Audio
   aplay -D plughw:2,0 test.wav
   ```

3. Check if devices are busy:
   ```bash
   # Kill any processes using audio devices
   pkill -f aplay
   pkill -f arecord
   ```

4. Verify ALSA configuration:
   ```bash
   # Check ALSA configuration
   cat /etc/asound.conf
   cat ~/.asoundrc
   ```

5. Try different device addressing formats:
   ```bash
   # Try these alternatives
   aplay -D hw:3,0 test.wav
   aplay -D default:3 test.wav
   ```
#!/usr/bin/env python3
"""
Contextual Error Message Translator

This module translates technical error messages into user-friendly explanations
that are more understandable to non-technical users.

Usage:
    from error_translator import ErrorTranslator
    
    # Initialize translator
    translator = ErrorTranslator(logger)
    
    # Translate an error message
    user_friendly_message = translator.translate_error(error_message, context="camera")
"""

import re
import logging
import os
from typing import Dict, List, Optional, Tuple, Union
import json
import time
import openai
from enum import Enum


class ErrorContext(Enum):
    """Enum defining different contexts for error translation"""
    GENERAL = "general"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    SPEAKER = "speaker"
    NETWORK = "network"
    API = "api"
    MOVEMENT = "movement"
    VISION = "vision"
    SPEECH = "speech"
    DATABASE = "database"
    HARDWARE = "hardware"
    SOFTWARE = "software"


class ErrorTranslator:
    """Translates technical error messages to user-friendly explanations"""
    
    def __init__(self, logger: logging.Logger):
        """Initialize the error translator
        
        Args:
            logger: Logger instance to use for logging
        """
        self.logger = logger
        
        # Cached translations to avoid repeated API calls for the same errors
        self.translation_cache: Dict[str, str] = {}
        
        # Translation rules for common errors
        # Format: {error_pattern: (user_friendly_message, severity_level)}
        self.translation_rules: Dict[str, Dict[str, Tuple[str, str]]] = self._load_translation_rules()
        
        # Rate limiting variables for API-based translation
        self.last_api_call_time = 0
        self.min_api_call_interval = 2.0  # Minimum seconds between API calls

    def _load_translation_rules(self) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """Load translation rules for different contexts
        
        Returns:
            Dict mapping context to rules dictionary
        """
        rules = {}
        
        # General error rules - applicable to all contexts
        rules[ErrorContext.GENERAL.value] = {
            r"permission denied|access denied": (
                "I don't have permission to access a required resource. This might be a file or device that needs different permissions.",
                "error"
            ),
            r"not found|no such file|no such device": (
                "I couldn't find something I need. A required file, device, or resource is missing.",
                "error"
            ),
            r"timed? ?out|timeout": (
                "An operation took too long and was cancelled. This might be due to slow network or a resource that's not responding.",
                "warning"
            ),
            r"memory|out of memory|allocation failed": (
                "I'm running low on memory. I might need more resources or there could be a memory leak.",
                "error"
            ),
            r"disk.*full|no space|insufficient space": (
                "The storage device is full. I need more disk space to continue.",
                "error"
            ),
            r"invalid|illegal|bad argument|invalid parameter": (
                "I received an invalid input or parameter that I can't process correctly.",
                "warning"
            ),
            r"unexpected|unknown error": (
                "An unexpected error occurred. This might be a bug or an edge case that wasn't handled properly.",
                "error"
            ),
            r"unsupported|not supported": (
                "I tried to use a feature or operation that isn't supported on this system.",
                "warning"
            ),
            r"initialization failed|init.*failed": (
                "A component failed to initialize properly. This might be due to missing resources or configuration issues.",
                "error"
            ),
            r"version mismatch|incompatible version": (
                "There's a version compatibility issue. The software versions might not work together.",
                "warning"
            )
        }
        
        # Camera-specific error rules
        rules[ErrorContext.CAMERA.value] = {
            r"camera.*?(not|cannot).*?(found|detected|open)|can't open camera": (
                "I can't access the camera. It may be disconnected, in use by another application, or you might need to check its permissions.",
                "error"
            ),
            r"video device.*?busy|camera.*?use": (
                "The camera is currently being used by another application. Please close other programs that might be using it.",
                "warning"
            ),
            r"insufficient.*?(resolution|frame rate)|low.*?(resolution|frame rate)": (
                "The camera's resolution or frame rate is too low for optimal performance. Consider using a higher quality camera.",
                "warning"
            ),
            r"(no|cannot).*?capture frame|failed to capture": (
                "I can't capture images from the camera. It may be malfunctioning or disconnected.",
                "error"
            ),
            r"index out of range|invalid.*?camera.*?index": (
                "I can't find a camera at the specified device index. The camera might be connected to a different port or not recognized by the system.",
                "error"
            ),
            r"v4l2|video4linux": (
                "There's an issue with the camera driver. This might require updating the driver or using a different camera.",
                "warning"
            ),
            r"camera.*?initialization|init.*?camera": (
                "The camera failed to initialize properly. Try reconnecting it or restarting the system.",
                "error"
            ),
            r"uvc|usb video": (
                "There's an issue with the USB video device. This might be related to the camera's USB connection or driver.",
                "warning"
            ),
            r"webcam|web camera": (
                "There's an issue with the webcam. Make sure it's properly connected and not being used by another application.",
                "warning"
            ),
            r"exposure|brightness|contrast|saturation": (
                "There's an issue with the camera's image settings. The lighting conditions might not be optimal.",
                "info"
            )
        }
        
        # Microphone-specific error rules
        rules[ErrorContext.MICROPHONE.value] = {
            r"microphone.*?(not|cannot).*?(found|detected|open)": (
                "I can't access the microphone. It may be disconnected, in use by another application, or you might need to check its permissions.",
                "error"
            ),
            r"audio device.*?busy|microphone.*?use": (
                "The microphone is currently being used by another application. Please close other programs that might be using it.",
                "warning"
            ),
            r"audio capture|recording failed|failed to record": (
                "I couldn't capture audio from the microphone. It may be malfunctioning or disconnected.",
                "error"
            ),
            r"no .*?input devices|no.*?audio.*?input": (
                "No audio input devices were detected. Make sure a microphone is connected and properly set up.",
                "error"
            ),
            r"alsa|pulse|pulseaudio|audio subsystem": (
                "There's an issue with the audio system. This might require reconfiguring the audio settings or restarting the audio service.",
                "warning"
            ),
            r"sample rate|bit depth|audio format": (
                "There's an issue with the audio settings. The microphone might not support the requested audio format.",
                "warning"
            ),
            r"arecord|recording command": (
                "The audio recording command failed. This might be due to incorrect parameters or missing audio utilities.",
                "error"
            ),
            r"flac conversion|flac.*?not.*?available": (
                "The FLAC audio conversion tool is missing. This is needed for speech recognition.",
                "error"
            ),
            r"speech recognition|transcription": (
                "I had trouble understanding what was said. The speech recognition service might be unavailable or the audio quality was poor.",
                "warning"
            ),
            r"too (quiet|silent)|volume too low|no audio detected": (
                "I couldn't hear anything or the volume was too low. Please speak louder or move closer to the microphone.",
                "info"
            )
        }
        
        # Speaker-specific error rules
        rules[ErrorContext.SPEAKER.value] = {
            r"speaker.*?(not|cannot).*?(found|detected|open)": (
                "I can't access the speaker. It may be disconnected or you might need to check its permissions.",
                "error"
            ),
            r"audio output|playback failed|failed to play": (
                "I couldn't play audio through the speaker. It may be malfunctioning or disconnected.",
                "error"
            ),
            r"no .*?output devices|no.*?audio.*?output": (
                "No audio output devices were detected. Make sure speakers are connected and properly set up.",
                "error"
            ),
            r"text to speech|tts|espeak": (
                "There was an issue with the text-to-speech system. I couldn't convert text to spoken words.",
                "error"
            ),
            r"aplay|playback command": (
                "The audio playback command failed. This might be due to incorrect parameters or missing audio utilities.",
                "error"
            )
        }
        
        # Network-specific error rules
        rules[ErrorContext.NETWORK.value] = {
            r"connection (refused|failed|error|timed? out)": (
                "I couldn't establish a network connection. The server might be down or there might be network issues.",
                "error"
            ),
            r"network (unreachable|unavailable)": (
                "The network is unreachable. Check your internet connection.",
                "error"
            ),
            r"dns|name resolution|resolve host": (
                "I couldn't resolve a domain name. There might be issues with DNS or the domain might not exist.",
                "warning"
            ),
            r"proxy|firewall": (
                "There might be a proxy or firewall blocking the connection. Check your network settings.",
                "warning"
            ),
            r"ssl|certificate|https": (
                "There's an issue with the secure connection. The certificate might be invalid or expired.",
                "warning"
            ),
            r"http.*?4[0-9]{2}": (
                "The server returned a client error. The request might be invalid or unauthorized.",
                "warning"
            ),
            r"http.*?5[0-9]{2}": (
                "The server returned a server error. The service might be experiencing issues.",
                "error"
            )
        }
        
        # API-specific error rules
        rules[ErrorContext.API.value] = {
            r"api key|authentication|unauthorized|auth": (
                "There's an issue with API authentication. The API key might be invalid or expired.",
                "error"
            ),
            r"rate limit|too many requests|429": (
                "I've reached the rate limit for API calls. I need to wait before making more requests.",
                "warning"
            ),
            r"quota exceeded|usage limit": (
                "I've exceeded the usage quota for an API. This might require upgrading the service plan.",
                "error"
            ),
            r"invalid request|bad request|400": (
                "The API request was invalid. There might be an issue with the parameters or format.",
                "warning"
            ),
            r"response format|parse (json|xml)|deserialization": (
                "I couldn't understand the API response. The format might have changed or be invalid.",
                "warning"
            ),
            r"openai|gpt": (
                "There was an issue with the OpenAI service. The API might be experiencing problems or the request was invalid.",
                "warning"
            ),
            r"whisper|transcription api": (
                "There was an issue with the speech transcription service. The audio might be unclear or the service might be unavailable.",
                "warning"
            ),
            r"vision|image analysis": (
                "There was an issue with the image analysis service. The image might be unclear or the service might be unavailable.",
                "warning"
            )
        }
        
        # Movement-specific error rules
        rules[ErrorContext.MOVEMENT.value] = {
            r"obstacle|collision": (
                "I detected an obstacle or potential collision. I've stopped moving for safety.",
                "warning"
            ),
            r"motor|servo|actuator": (
                "There's an issue with a motor or actuator. The hardware might be malfunctioning.",
                "error"
            ),
            r"kinematics|inverse kinematics": (
                "I couldn't calculate the required movement. The requested position might be out of reach.",
                "warning"
            ),
            r"joint limit|range of motion": (
                "A joint has reached its limit. I can't move further in that direction.",
                "warning"
            ),
            r"balance|stability": (
                "I'm having trouble maintaining balance or stability.",
                "warning"
            ),
            r"trajectory|path planning": (
                "I couldn't plan a safe path to the target. There might be obstacles or constraints.",
                "warning"
            ),
            r"gripper|grasping|grip": (
                "There's an issue with the gripper. I might not be able to grasp objects properly.",
                "warning"
            )
        }
        
        # Vision-specific error rules
        rules[ErrorContext.VISION.value] = {
            r"object (detection|recognition)": (
                "I'm having trouble detecting or recognizing objects in the image.",
                "warning"
            ),
            r"lighting|too (dark|bright)": (
                "The lighting conditions are making it difficult to see. It might be too dark or too bright.",
                "info"
            ),
            r"focus|blur": (
                "The image is out of focus or blurry. I can't see clearly.",
                "warning"
            ),
            r"occlusion|obstruction": (
                "Something is blocking my view. I can't see the target clearly.",
                "info"
            ),
            r"feature extraction|keypoints": (
                "I'm having trouble identifying key features in the image.",
                "warning"
            ),
            r"classification|categorization": (
                "I couldn't classify or categorize what I'm seeing.",
                "warning"
            )
        }
        
        # Speech-specific error rules
        rules[ErrorContext.SPEECH.value] = {
            r"speech recognition|transcription": (
                "I'm having trouble understanding speech. The audio might be unclear or there might be background noise.",
                "warning"
            ),
            r"background noise|ambient sound": (
                "There's too much background noise, which is making it difficult to understand speech.",
                "info"
            ),
            r"pronunciation|accent": (
                "I'm having trouble understanding the pronunciation or accent.",
                "info"
            ),
            r"voice detection|speech detection": (
                "I couldn't detect any speech. Please make sure you're speaking clearly and the microphone is working.",
                "warning"
            ),
            r"language model|vocabulary": (
                "I encountered unfamiliar words or phrases that I couldn't understand.",
                "info"
            )
        }
        
        # Hardware-specific error rules
        rules[ErrorContext.HARDWARE.value] = {
            r"usb|device disconnect": (
                "A USB device or hardware component was disconnected or is not responding.",
                "error"
            ),
            r"driver|firmware": (
                "There's an issue with a hardware driver or firmware. It might need to be updated.",
                "warning"
            ),
            r"temperature|overheating": (
                "A hardware component is overheating. I might need to cool down or reduce activity.",
                "warning"
            ),
            r"battery|power": (
                "There's an issue with the power supply or battery. I might shut down soon if not connected to power.",
                "warning"
            ),
            r"sensor|reading": (
                "A sensor is giving unusual readings. It might be malfunctioning or out of calibration.",
                "warning"
            ),
            r"calibration": (
                "A hardware component needs calibration. Its readings or actions might not be accurate.",
                "warning"
            )
        }
        
        # Software-specific error rules
        rules[ErrorContext.SOFTWARE.value] = {
            r"exception|runtime error": (
                "A software error occurred. This might be a bug or unexpected situation.",
                "error"
            ),
            r"dependency|module not found": (
                "A required software component or library is missing.",
                "error"
            ),
            r"configuration|config file": (
                "There's an issue with the configuration. Some settings might be incorrect or missing.",
                "warning"
            ),
            r"stack trace|traceback": (
                "A software error occurred with detailed debugging information available.",
                "error"
            ),
            r"assertion|assert": (
                "A software condition that should be true was found to be false. This indicates a bug.",
                "error"
            ),
            r"deadlock|race condition": (
                "A software threading issue occurred. This might cause the system to freeze or behave unpredictably.",
                "error"
            ),
            r"corrupted|corruption": (
                "Data corruption was detected. Some information might be lost or invalid.",
                "error"
            )
        }
        
        return rules

    def reload_translation_rules(self):
        """Reload translation rules from the database or files
        
        This allows for dynamic updates to the translation rules without restarting
        the application.
        """
        self.translation_rules = self._load_translation_rules()
        self.logger.info("Translation rules reloaded")

    def translate_error(self, error_message: str, context: Union[str, ErrorContext] = ErrorContext.GENERAL) -> str:
        """Translate a technical error message to a user-friendly explanation
        
        Args:
            error_message: The technical error message to translate
            context: The context in which the error occurred (camera, mic, etc.)
                    Can be a string or an ErrorContext enum value
                    
        Returns:
            A user-friendly explanation of the error
        """
        if not error_message:
            return "An unknown error occurred."
        
        # Convert context to string if it's an enum
        if isinstance(context, ErrorContext):
            context_str = context.value
        else:
            context_str = context
        
        # Normalize the message
        normalized_message = self._normalize_message(error_message)
        
        # Check cache first to avoid repeated translations of the same error
        cache_key = f"{context_str}:{normalized_message}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        # Try to match against known patterns for the specified context
        context_rules = self.translation_rules.get(context_str, {})
        for pattern, (translation, severity) in context_rules.items():
            if re.search(pattern, normalized_message, re.IGNORECASE):
                self.logger.info(f"Translated error using rule ({severity}): {pattern}")
                self.translation_cache[cache_key] = translation
                return translation
        
        # If no match in specific context, try general patterns
        if context_str != ErrorContext.GENERAL.value:
            general_rules = self.translation_rules.get(ErrorContext.GENERAL.value, {})
            for pattern, (translation, severity) in general_rules.items():
                if re.search(pattern, normalized_message, re.IGNORECASE):
                    self.logger.info(f"Translated error using general rule ({severity}): {pattern}")
                    self.translation_cache[cache_key] = translation
                    return translation
        
        # If no match found in the rules, use AI to generate a translation
        ai_translation = self._translate_with_ai(error_message, context_str)
        if ai_translation:
            self.translation_cache[cache_key] = ai_translation
            return ai_translation
        
        # Fallback to a generic message if AI translation fails
        fallback = "I encountered a technical issue that prevented me from completing the task."
        self.translation_cache[cache_key] = fallback
        return fallback

    def _normalize_message(self, message: str) -> str:
        """Normalize an error message for better pattern matching
        
        Args:
            message: The error message to normalize
            
        Returns:
            Normalized message with consistent spacing, case, etc.
        """
        # Convert to lowercase
        message = message.lower()
        
        # Replace multiple spaces with a single space
        message = re.sub(r'\s+', ' ', message)
        
        # Remove common prefixes often found in error messages
        message = re.sub(r'^(error|warning|fatal|exception|critical):\s*', '', message)
        
        # Remove timestamps and log IDs
        message = re.sub(r'\[\d{4}-\d{2}-\d{2}.*?\]', '', message)
        message = re.sub(r'\[\w+\]', '', message)
        
        # Remove file paths
        message = re.sub(r'(/\w+)+/\w+\.\w+', 'FILE', message)
        
        # Remove line numbers
        message = re.sub(r'line \d+', 'LINE', message)
        
        # Remove specific error codes
        message = re.sub(r'error code: \w+', 'ERROR_CODE', message)
        
        return message.strip()

    def _translate_with_ai(self, error_message: str, context: str) -> Optional[str]:
        """Use OpenAI to translate technical error messages to user-friendly explanations
        
        Args:
            error_message: The technical error message to translate
            context: The context in which the error occurred
            
        Returns:
            A user-friendly explanation of the error, or None if translation failed
        """
        # Check if OpenAI API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.logger.warning("OpenAI API key not found, skipping AI translation")
            return None
        
        # Apply rate limiting to avoid excessive API calls
        current_time = time.time()
        if current_time - self.last_api_call_time < self.min_api_call_interval:
            self.logger.warning("Skipping AI translation due to rate limiting")
            return None
        
        self.last_api_call_time = current_time
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=api_key)
            
            # Prepare prompt with error message and context
            prompt = f"""
            You are a helpful assistant that translates technical error messages into user-friendly explanations.
            
            Technical error message: "{error_message}"
            Context: {context}
            
            Translate this technical error into a brief, conversational explanation that a non-technical user would understand. 
            Use simple language, avoid technical jargon, and keep it under 200 characters.
            Focus only on explaining what went wrong, not how to fix it.
            """
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            # Extract and return the translated message
            translation = response.choices[0].message.content.strip()
            
            # Remove quotes if present (sometimes the model returns the translation in quotes)
            translation = re.sub(r'^["\'](.*)["\']$', r'\1', translation)
            
            self.logger.info(f"AI translated error: {translation}")
            return translation
            
        except Exception as e:
            self.logger.error(f"Error using OpenAI for translation: {e}")
            return None
            
    def add_custom_rule(self, context: Union[str, ErrorContext], pattern: str, 
                       translation: str, severity: str = "warning") -> bool:
        """Add a custom translation rule
        
        Args:
            context: The context for the rule (camera, mic, etc.)
            pattern: The regex pattern to match in error messages
            translation: The user-friendly translation to use
            severity: The severity level (info, warning, error)
            
        Returns:
            True if the rule was added successfully, False otherwise
        """
        try:
            # Convert context to string if it's an enum
            if isinstance(context, ErrorContext):
                context_str = context.value
            else:
                context_str = context
                
            # Validate the pattern by testing it
            re.compile(pattern)
            
            # Add the rule
            if context_str not in self.translation_rules:
                self.translation_rules[context_str] = {}
                
            self.translation_rules[context_str][pattern] = (translation, severity)
            
            # Clear cache to ensure the new rule takes effect
            self.translation_cache = {}
            
            self.logger.info(f"Added custom translation rule for context '{context_str}': {pattern}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding custom rule: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("ErrorTranslatorTest")
    
    # Create translator instance
    translator = ErrorTranslator(logger)
    
    # Test some translations
    test_errors = [
        ("Camera index out of range", ErrorContext.CAMERA),
        ("Permission denied: /dev/video0", ErrorContext.CAMERA),
        ("ALSA lib pcm.c:8526:(snd_pcm_recover) underrun occurred", ErrorContext.MICROPHONE),
        ("Network connection timed out after 30 seconds", ErrorContext.NETWORK),
        ("OpenAI API key is invalid or expired", ErrorContext.API),
        ("Motor controller returned error code 0x7A: torque limit exceeded", ErrorContext.MOVEMENT),
        ("Out of memory: Killed process", ErrorContext.GENERAL),
        ("FLAC conversion utility not available - consider installing flac", ErrorContext.MICROPHONE)
    ]
    
    print("\n=== Testing Error Translator ===\n")
    for error, context in test_errors:
        print(f"Original: {error}")
        print(f"Context: {context.value}")
        translation = translator.translate_error(error, context)
        print(f"Translation: {translation}")
        print("-" * 50)
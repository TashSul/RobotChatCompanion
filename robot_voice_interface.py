import time
import signal
import sys
from logger_config import setup_logger
from device_manager import DeviceManager
from ai_processor import AIProcessor

class RobotVoiceInterface:
    def __init__(self):
        self.logger = setup_logger()
        self.device_manager = DeviceManager(self.logger)
        self.ai_processor = AIProcessor(self.logger)
        self.running = True

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Shutdown signal received")
        self.running = False

    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            self.device_manager.initialize_devices()
            self.logger.info("Robot voice interface initialized - ready for operation on Raspberry Pi")
            return True
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            return False

    def run(self):
        """Main operation loop"""
        if not self.initialize():
            self.logger.warning("Initialization incomplete - some features may not work until running on Raspberry Pi")

        try:
            self.device_manager.speak_text("Hello, I'm ready to talk")
        except Exception as e:
            self.logger.warning(f"Initial greeting failed (will work on Raspberry Pi): {str(e)}")

        while self.running:
            try:
                # Capture audio input
                user_input = self.device_manager.capture_audio()

                if user_input:
                    # Process through AI
                    ai_response = self.ai_processor.process_input(user_input)

                    if ai_response:
                        # Convert response to speech
                        self.device_manager.speak_text(ai_response)
                    else:
                        self.device_manager.speak_text("I'm sorry, I couldn't process that request")

                time.sleep(0.1)  # Small delay to prevent CPU overuse

            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                try:
                    self.device_manager.speak_text("I encountered an error. Please try again")
                except:
                    self.logger.error("Could not provide error feedback through speech")

    def cleanup(self):
        """Clean up resources"""
        try:
            self.device_manager.cleanup()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

def main():
    robot_interface = RobotVoiceInterface()
    try:
        robot_interface.run()
    except Exception as e:
        print(f"Critical error: {str(e)}")
    finally:
        robot_interface.cleanup()

if __name__ == "__main__":
    main()
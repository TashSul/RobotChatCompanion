#!/usr/bin/env python3
"""
ROS Controller for Hiwonder Ainex Humanoid Robot

This module integrates the voice interface with ROS to control 
the physical movements of the Ainex humanoid robot.

Usage:
    Import this module in robot_voice_interface.py
"""

import os
import time
import logging
import threading
import subprocess
from typing import Dict, List, Optional, Tuple

# ROS imports - these will work on the actual robot
# but are wrapped in try/except for development environment
try:
    import rospy
    from std_msgs.msg import String, Bool
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge
    has_ros = True
except ImportError:
    has_ros = False

class RosController:
    """ROS Controller for Ainex Humanoid Robot"""
    
    def __init__(self, logger: logging.Logger, simulation_enabled: bool = True):
        """Initialize ROS controller
        
        Args:
            logger: Logger instance
            simulation_enabled: Whether to use simulation when ROS is unavailable
        """
        self.logger = logger
        self.simulation_enabled = simulation_enabled
        self.ros_initialized = False
        self.is_moving = False
        self.is_tracking = False
        self.current_action = None
        self.action_start_time = None
        self.action_timeout = None
        self.bridge = None  # CV bridge for converting images
        
        # Initialize ROS if available
        self.initialize_ros()
        
    def initialize_ros(self) -> bool:
        """Initialize ROS node and publishers/subscribers
        
        Returns:
            bool: True if ROS initialized successfully
        """
        if not has_ros:
            self.logger.warning("ROS Python package not available - using simulation")
            return False
            
        try:
            # Initialize ROS node
            self.logger.info("Initializing ROS node...")
            rospy.init_node('robot_voice_controller', anonymous=True)
            
            # Create publishers for various commands
            self.cmd_vel_pub = rospy.Publisher('/ainex/cmd_vel', Twist, queue_size=10)
            self.head_pub = rospy.Publisher('/ainex/head_position', String, queue_size=10)
            self.arm_pub = rospy.Publisher('/ainex/arm_movement', String, queue_size=10)
            self.action_pub = rospy.Publisher('/ainex/execute_action', String, queue_size=10)
            self.stop_pub = rospy.Publisher('/ainex/stop_all', Bool, queue_size=10)
            
            # Subscribe to robot state
            rospy.Subscriber('/ainex/robot_state', String, self.robot_state_callback)
            
            # Initialize CV bridge for image processing
            self.bridge = CvBridge()
            
            self.logger.info("ROS initialization completed successfully")
            self.ros_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ROS: {str(e)}")
            return False
    
    def robot_state_callback(self, msg):
        """Callback for robot state messages
        
        Args:
            msg: ROS message containing robot state
        """
        try:
            state_str = msg.data
            self.logger.info(f"Robot state update: {state_str}")
            
            # Parse the state message
            if "moving" in state_str.lower():
                self.is_moving = True
            elif "stopped" in state_str.lower():
                self.is_moving = False
                
            if "tracking" in state_str.lower():
                self.is_tracking = True
            elif "not_tracking" in state_str.lower():
                self.is_tracking = False
                
        except Exception as e:
            self.logger.error(f"Error processing robot state: {str(e)}")
    
    def execute_command(self, command: str) -> str:
        """Execute a robot command from voice input
        
        Args:
            command: Natural language command
            
        Returns:
            str: Response message about the action taken
        """
        # Process and normalize the command
        command = command.lower().strip()
        
        # Check for stop command first (highest priority)
        if "stop" in command:
            return self.stop_action()
            
        # Handle basic movement commands
        if "move" in command or "step" in command or "walk" in command:
            return self.handle_movement_command(command)
            
        # Handle hand/arm gestures
        if "wave" in command:
            return self.wave_hand()
            
        # Handle object interactions
        if "kick" in command and "ball" in command:
            return self.kick_ball()
            
        # Handle object tracking
        if "track" in command and ("object" in command or "target" in command):
            return self.track_object()
        
        # If no specific command matched, return None to indicate
        # this should be handled by conversation AI instead
        return None
        
    def stop_action(self) -> str:
        """Stop all robot movements and actions
        
        Returns:
            str: Response message
        """
        if not self.ros_initialized and not self.simulation_enabled:
            return "I can't stop because I'm not connected to the robot's movement system."
            
        self.logger.info("Stopping all robot actions")
        
        if self.ros_initialized:
            # Publish stop command
            stop_msg = Bool()
            stop_msg.data = True
            self.stop_pub.publish(stop_msg)
            
            # Also send zero velocity command
            zero_vel = Twist()
            self.cmd_vel_pub.publish(zero_vel)
        
        # Reset state variables
        self.is_moving = False
        self.is_tracking = False
        self.current_action = None
        
        return "I've stopped all movements."
        
    def handle_movement_command(self, command: str) -> str:
        """Process and execute movement commands
        
        Args:
            command: Movement command string
            
        Returns:
            str: Response message
        """
        # Check if ROS is available
        if not self.ros_initialized and not self.simulation_enabled:
            return "I can't move because I'm not connected to the robot's movement system."
            
        # Parse direction
        direction = "forward"  # Default
        if "back" in command or "backward" in command:
            direction = "backward"
        elif "left" in command:
            direction = "left"
        elif "right" in command:
            direction = "right"
            
        # Parse steps/distance
        import re
        steps = 1  # Default to 1 step
        step_match = re.search(r'(\d+)\s*(steps?|paces?)', command)
        if step_match:
            steps = int(step_match.group(1))
            
        # Limit to reasonable range
        steps = min(max(steps, 1), 10)
        
        self.logger.info(f"Moving {direction} {steps} steps")
        
        if self.ros_initialized:
            # Create velocity command
            vel_msg = Twist()
            
            # Set linear/angular velocity based on direction and steps
            if direction == "forward":
                vel_msg.linear.x = 0.2 * steps  # Adjust speed based on steps
            elif direction == "backward":
                vel_msg.linear.x = -0.2 * steps
            elif direction == "left":
                vel_msg.angular.z = 0.5  # Turn left
            elif direction == "right":
                vel_msg.angular.z = -0.5  # Turn right
                
            # Send command to robot
            self.cmd_vel_pub.publish(vel_msg)
            
            # For steps, we would need a more sophisticated approach with
            # odometry feedback, but this is a simplified version
            timeout_duration = steps * 1.5  # 1.5 seconds per step
            
            # Schedule a stop after timeout
            self.current_action = "moving"
            self.action_start_time = time.time()
            self.action_timeout = timeout_duration
            
            # Start a timer thread to stop after duration
            threading.Timer(timeout_duration, self.stop_action).start()
        
        # Return response
        return f"Moving {direction} for {steps} steps."
        
    def wave_hand(self) -> str:
        """Make the robot wave its right hand
        
        Returns:
            str: Response message
        """
        if not self.ros_initialized and not self.simulation_enabled:
            return "I can't wave because I'm not connected to the robot's movement system."
            
        self.logger.info("Waving right hand")
        
        if self.ros_initialized:
            # Send arm movement command
            arm_msg = String()
            arm_msg.data = "wave_right_arm"
            self.arm_pub.publish(arm_msg)
            
            # Schedule a stop after 5 seconds
            self.current_action = "waving"
            self.action_start_time = time.time()
            self.action_timeout = 5.0
            
            # Start a timer thread to stop after duration
            threading.Timer(5.0, self.stop_action).start()
        
        return "I'm waving my right hand for 5 seconds."
        
    def kick_ball(self) -> str:
        """Make the robot look for and kick a ball
        
        Returns:
            str: Response message
        """
        if not self.ros_initialized and not self.simulation_enabled:
            return "I can't kick the ball because I'm not connected to the robot's movement system."
            
        self.logger.info("Looking for ball to kick")
        
        # In a real implementation, this would involve:
        # 1. Using computer vision to detect a ball
        # 2. Positioning the robot properly
        # 3. Executing the kick action
        
        if self.ros_initialized:
            # First send command to look for ball
            action_msg = String()
            action_msg.data = "find_and_kick_ball"
            self.action_pub.publish(action_msg)
            
            # The robot should report back if it found the ball through the state topic
            # For now, we'll simulate success
            ball_found = True  # In reality, this would come from vision system
            
            if not ball_found:
                return "I looked for a ball but couldn't find one."
        
        return "I'm looking for the ball and will kick it when I find it."
        
    def track_object(self) -> str:
        """Track an object using the robot's camera
        
        Returns:
            str: Response message
        """
        if not self.ros_initialized and not self.simulation_enabled:
            return "I can't track objects because I'm not connected to the robot's vision system."
            
        self.logger.info("Starting object tracking")
        
        if self.ros_initialized:
            # Send tracking command
            track_msg = String()
            track_msg.data = "start_tracking"
            self.action_pub.publish(track_msg)
            
            # Update state
            self.is_tracking = True
        
        return "I'm now tracking objects in front of me. Say 'stop tracking' when you want me to stop."
    
    def check_timeouts(self):
        """Check if current action has timed out and stop if needed"""
        if self.current_action and self.action_start_time and self.action_timeout:
            elapsed = time.time() - self.action_start_time
            if elapsed > self.action_timeout:
                self.logger.info(f"Action '{self.current_action}' timed out")
                self.stop_action()
                
    def cleanup(self):
        """Clean up ROS resources"""
        if self.ros_initialized:
            try:
                self.stop_action()
                # In a real ROS application, we'd do additional cleanup here
                self.logger.info("ROS controller resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during ROS cleanup: {str(e)}")
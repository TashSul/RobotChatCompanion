import os
import openai
import logging
from typing import Dict, Optional

class AIProcessor:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.conversation_history = []
        
        # Object recognition training state
        self.training_mode_active = False
        self.trained_objects = {}  # Dictionary mapping object names to their descriptions
        self.current_training_object = None

    def process_input(self, user_input: str) -> Optional[str]:
        """Process user input through ChatGPT and return response"""
        try:
            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})

            # Keep conversation history limited to last 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for a Hiwonder Ainex humanoid robot. You have access to a camera and can identify objects when asked. Keep your responses concise and natural for spoken conversation. If users ask you to identify objects, suggest they try phrases like 'What do you see?' or 'What am I holding?'"}, 
                    *self.conversation_history
                ]
            )

            ai_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            self.logger.info(f"AI Response: {ai_response}")
            return ai_response

        except Exception as e:
            self.logger.error(f"Error processing AI response: {str(e)}")
            return None

    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []
        self.logger.info("Conversation history reset")
        
    def start_object_training_mode(self, object_name: str) -> str:
        """Start interactive object recognition training for a specific object
        
        Args:
            object_name: The name of the object to train
            
        Returns:
            str: Response message
        """
        self.training_mode_active = True
        self.current_training_object = object_name
        self.logger.info(f"Starting training mode for object: {object_name}")
        
        return (f"Starting training mode for {object_name}. Please show me the {object_name} "
                f"from different angles. Say 'finished training' when done or 'cancel training' to abort.")
    
    def add_training_sample(self, image_description: str) -> str:
        """Add a training sample for the current object in training
        
        Args:
            image_description: The description of the object from vision API
            
        Returns:
            str: Response message
        """
        if not self.training_mode_active or not self.current_training_object:
            return "No active training session. Start training first with 'train object [name]'."
        
        # If this is the first sample for this object, initialize the list
        if self.current_training_object not in self.trained_objects:
            self.trained_objects[self.current_training_object] = []
            
        # Add the sample
        self.trained_objects[self.current_training_object].append(image_description)
        
        sample_count = len(self.trained_objects[self.current_training_object])
        self.logger.info(f"Added training sample {sample_count} for {self.current_training_object}")
        
        if sample_count >= 5:
            return (f"Added sample {sample_count} for {self.current_training_object}. "
                   f"You now have enough samples. Say 'finished training' to complete or 'show me more angles' to continue.")
        else:
            return (f"Added sample {sample_count} for {self.current_training_object}. "
                   f"Please show me {self.current_training_object} from a different angle, or say 'finished training'.")
    
    def finish_training(self) -> str:
        """Complete the current object training session
        
        Returns:
            str: Response message
        """
        if not self.training_mode_active or not self.current_training_object:
            return "No active training session to complete."
            
        object_name = self.current_training_object
        sample_count = len(self.trained_objects.get(object_name, []))
        
        if sample_count == 0:
            self.trained_objects.pop(object_name, None)
            result = f"Training for {object_name} canceled. No samples were collected."
        else:
            # Save training data (in a real implementation, this would use a database or file)
            # Here we're just keeping it in memory
            result = f"Training for {object_name} completed with {sample_count} samples."
            
        # Reset training state
        self.training_mode_active = False
        self.current_training_object = None
        self.logger.info(f"Finished training for {object_name} with {sample_count} samples")
        
        return result
        
    def cancel_training(self) -> str:
        """Cancel the current object training session
        
        Returns:
            str: Response message
        """
        if not self.training_mode_active or not self.current_training_object:
            return "No active training session to cancel."
            
        object_name = self.current_training_object
        
        # Remove any samples collected for this object
        self.trained_objects.pop(object_name, None)
        
        # Reset training state
        self.training_mode_active = False
        self.current_training_object = None
        self.logger.info(f"Canceled training for {object_name}")
        
        return f"Training for {object_name} has been canceled."
        
    def is_trained_object(self, image_description: str) -> Optional[str]:
        """Check if an image description matches any trained objects
        
        Args:
            image_description: The description from the vision API
            
        Returns:
            Optional[str]: The name of the recognized trained object or None
        """
        if not self.trained_objects:
            return None
            
        # In a real implementation, this would use ML-based similarity matching
        # For this simulation, we'll use a simple text similarity approach
        
        # For each trained object
        for object_name, descriptions in self.trained_objects.items():
            # Check if any of the keywords from our training samples appear in the new description
            for description in descriptions:
                # Extract key terms (nouns, adjectives) from the description
                # This is simplified - in reality would use NLP
                key_terms = [term.lower().strip() for term in description.split()
                            if len(term) > 3 and term.lower() not in ["this", "that", "with", "like", "appears"]]
                
                # Count how many key terms from this training description appear in the new image
                matching_terms = sum(1 for term in key_terms if term in image_description.lower())
                matched_terms = [term for term in key_terms if term in image_description.lower()]
                
                # If enough terms match, consider it the same object
                if matching_terms >= 2 or (matching_terms > 0 and object_name.lower() in image_description.lower()):
                    self.logger.info(f"Recognized trained object: {object_name} (matched {matching_terms} terms)")
                    self.logger.info(f"Matching terms: {matched_terms}")
                    self.logger.info(f"Original key terms: {key_terms}")
                    return object_name
                    
        return None
        
    def change_voice(self, device_manager, voice_name: str = None) -> str:
        """Change the robot's voice
        
        Args:
            device_manager: The DeviceManager instance to update
            voice_name: Name of the voice to use, or None to list available voices
            
        Returns:
            str: Response message
        """
        # If no voice name provided, list available voices
        if not voice_name:
            available_voices = device_manager.voice_settings.get("available_voices", {})
            voice_list = "\n".join([f"- {name}: {desc}" for name, desc in available_voices.items()])
            return f"Available voices:\n{voice_list}\n\nSay 'use voice [name]' to change my voice."
        
        # Convert to lowercase for case-insensitive matching
        voice_name = voice_name.lower()
        
        # Get list of available voices
        available_voices = device_manager.voice_settings.get("available_voices", {})
        
        # Check if the requested voice is available
        voice_match = None
        for voice_id, description in available_voices.items():
            if voice_id.lower() == voice_name or voice_name in description.lower():
                voice_match = voice_id
                break
        
        if voice_match:
            # Update the voice setting
            device_manager.voice_settings["voice_type"] = voice_match
            self.logger.info(f"Changed voice to: {voice_match}")
            return f"Voice changed to {voice_match}. {available_voices.get(voice_match, '')}"
        else:
            return f"Voice '{voice_name}' not found. Available voices are: {', '.join(available_voices.keys())}"
            
    def adjust_voice_speed(self, device_manager, speed_factor: float) -> str:
        """Adjust the speaking speed of the robot's voice
        
        Args:
            device_manager: The DeviceManager instance to update
            speed_factor: Speed factor (0.5 to 1.5)
            
        Returns:
            str: Response message
        """
        # Ensure speed is within allowed range
        if speed_factor < 0.5:
            speed_factor = 0.5
        elif speed_factor > 1.5:
            speed_factor = 1.5
            
        # Update the speed setting
        device_manager.voice_settings["speed"] = speed_factor
        self.logger.info(f"Changed voice speed to: {speed_factor}")
        
        return f"Voice speed adjusted to {speed_factor}x"

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
                    {"role": "system", "content": "You are a helpful assistant for a humanoid robot. Keep your responses concise and natural for spoken conversation."}, 
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

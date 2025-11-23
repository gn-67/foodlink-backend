"""
Base Agent class for FoodLink LA
Provides shared functionality for all AI agents
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from models.schemas import Message


class BaseAgent(BaseModel, ABC):
    """
    Abstract base class for all AI agents
    Handles conversation management and Claude API integration
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    conversation_history: List[Message] = Field(default_factory=list)
    
    # Exclude from serialization (set at runtime)
    model_config = {"arbitrary_types_allowed": True}
    _client: Optional[AsyncAnthropic] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self._client = AsyncAnthropic(api_key=api_key)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Each agent must define its own system prompt
        This is the core personality and behavior of the agent
        """
        pass
    
    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response
        
        Args:
            user_message: The user's input message
        
        Returns:
            The agent's response text
        """
        # Add user message to history
        self.conversation_history.append(
            Message(role="user", content=user_message)
        )
        
        # Prepare messages for Claude API
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]
        
        try:
            # Call Claude API
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=self.get_system_prompt(),
                messages=messages
            )
            
            # Extract response text
            assistant_message = response.content[0].text
            
            # Add assistant response to history
            self.conversation_history.append(
                Message(role="assistant", content=assistant_message)
            )
            
            return assistant_message
        
        except Exception as e:
            error_message = f"I apologize, but I encountered an error: {str(e)}"
            print(f"❌ Error in agent processing: {e}")
            return error_message
    
    def get_conversation_context(self) -> str:
        """Get a text representation of the conversation history"""
        if not self.conversation_history:
            return "No conversation history yet."
        
        lines = []
        for msg in self.conversation_history:
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        
        return "\n".join(lines)
    
    def clear_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message"""
        for msg in reversed(self.conversation_history):
            if msg.role == "user":
                return msg.content
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant message"""
        for msg in reversed(self.conversation_history):
            if msg.role == "assistant":
                return msg.content
        return None

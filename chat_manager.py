"""
Chat Manager Module
This module handles chat history and conversation memory management.
It provides functions to save, load, and manage conversation state.
"""

import os
import json
import logging
from langchain.memory import ConversationBufferMemory


class ChatManager:
    """Manages chat history and conversation memory."""
    
    def __init__(self, chat_history_file='chat_history.json', 
                 conversation_memory_file='conversation_memory.json'):
        """
        Initialize ChatManager with file paths.
        
        Args:
            chat_history_file (str): Path to chat history file
            conversation_memory_file (str): Path to conversation memory file
        """
        self.chat_history_file = chat_history_file
        self.conversation_memory_file = conversation_memory_file
        self.memory = None
        self.initialize_files()
        self.initialize_memory()
    
    def initialize_files(self):
        """Initialize chat history files if they don't exist."""
        for file_path in [self.chat_history_file, self.conversation_memory_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as file:
                    json.dump([], file)
                logging.info(f"Created {file_path}")
    
    def load_chat_history(self):
        """
        Load chat history from file.
        
        Returns:
            list: Chat history
        """
        if os.path.exists(self.chat_history_file):
            try:
                with open(self.chat_history_file, 'r') as file:
                    data = json.load(file)
                    return data if data else []
            except json.JSONDecodeError:
                logging.error(f"Error loading {self.chat_history_file}")
                return []
        return []
    
    def save_chat_history(self, chat_history):
        """
        Save chat history to file.
        
        Args:
            chat_history (list): Chat history to save
        """
        with open(self.chat_history_file, 'w') as file:
            json.dump(chat_history, file, indent=4)
        logging.info(f"Saved chat history to {self.chat_history_file}")
    
    def load_conversation_memory(self):
        """
        Load conversation memory from file.
        
        Returns:
            list: Conversation memory
        """
        if os.path.exists(self.conversation_memory_file):
            try:
                with open(self.conversation_memory_file, 'r') as file:
                    data = json.load(file)
                    return data if data else []
            except json.JSONDecodeError:
                logging.error(f"Error loading {self.conversation_memory_file}")
                return []
        return []
    
    def save_conversation_memory(self, memory):
        """
        Save conversation memory to file.
        
        Args:
            memory (list): Conversation memory to save
        """
        with open(self.conversation_memory_file, 'w') as file:
            json.dump(memory, file, indent=4)
        logging.info(f"Saved conversation memory to {self.conversation_memory_file}")
    
    def initialize_memory(self):
        """Initialize conversation memory with previous conversations."""
        previous_memory = self.load_conversation_memory()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True, 
            k=3
        )
        
        # Load previous conversations into memory
        for item in previous_memory:
            if "user" in item and "assistant" in item:
                self.memory.chat_memory.add_user_message(item["user"])
                self.memory.chat_memory.add_ai_message(item["assistant"])
        
        logging.info(f"Initialized memory with {len(previous_memory)} previous conversations")
    
    def add_conversation(self, user_message, assistant_message):
        """
        Add a conversation to memory.
        
        Args:
            user_message (str): User's message
            assistant_message (str): Assistant's response
        """
        if self.memory:
            self.memory.chat_memory.add_user_message(user_message)
            self.memory.chat_memory.add_ai_message(assistant_message)
            
            # Also save to persistent storage
            memory_data = self.load_conversation_memory()
            memory_data.append({
                "user": user_message,
                "assistant": assistant_message
            })
            self.save_conversation_memory(memory_data)
    
    def get_memory(self):
        """
        Get the conversation memory object.
        
        Returns:
            ConversationBufferMemory: The memory object
        """
        return self.memory
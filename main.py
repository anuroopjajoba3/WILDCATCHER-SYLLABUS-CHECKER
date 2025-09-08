"""
Main Application Entry Point
This module serves as the main entry point for the chatbot application.
It initializes all components and starts the Flask server.
"""

from flask import Flask
from config import Config, AIModels
from chat_manager import ChatManager
from api_routes import create_routes


def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application
    """
    # Initialize Flask app
    app = Flask(__name__)
    
    # Initialize AI models
    ai_models = AIModels()
    
    # Initialize chat manager
    chat_manager = ChatManager()
    
    # Create routes
    create_routes(app, ai_models, chat_manager)
    
    return app


def main():
    """Main function to run the application."""
    app = create_app()
    
    # Run the Flask application
    app.run(
        debug=Config.DEBUG,
        host=Config.HOST,
        port=Config.PORT,
        threaded=Config.THREADED
    )


if __name__ == '__main__':
    main()
"""
Configuration Module
This module handles application configuration, initialization of AI models,
and database connections. It centralizes all configuration settings.
"""

import os
import logging
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("gunicorn.log"),
        logging.StreamHandler()
    ]
)


class Config:
    """Application configuration class."""
    
    # Flask settings
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 8001
    THREADED = True
    
    # File settings
    UPLOAD_FOLDER = 'uploads'
    MAX_UPLOAD_FILES = 5
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    TEMPERATURE = 0
    TOP_P = 1
    
    # Email settings
    GMAIL_USER = os.getenv("GMAIL_USER")
    GMAIL_PASS = os.getenv("GMAIL_PASS")
    
    # Database settings
    CHROMA_PERSIST_DIR = 'chroma_db'
    
    # Text processing settings
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 200
    TEXT_SEPARATORS = ["\n\n", "\n", " "]
    
    # Retrieval settings
    RETRIEVAL_K = 5
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Create upload folder if it doesn't exist
        if not os.path.exists(cls.UPLOAD_FOLDER):
            os.makedirs(cls.UPLOAD_FOLDER)
            logging.info(f"Created upload folder: {cls.UPLOAD_FOLDER}")


class AIModels:
    """Manages AI model initialization."""
    
    def __init__(self):
        """Initialize AI models and vector store."""
        Config.validate()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            openai_api_key=Config.OPENAI_API_KEY,
            temperature=Config.TEMPERATURE,
            top_p=Config.TOP_P
        )
        logging.info(f"Initialized LLM: {Config.MODEL_NAME}")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            openai_api_key=Config.OPENAI_API_KEY
        )
        logging.info(f"Initialized embeddings: {Config.EMBEDDING_MODEL}")
        
        # Initialize vector store
        self.db = self._initialize_vector_store()
        
        # Initialize retriever
        self.retriever = self.db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": Config.RETRIEVAL_K}
        )
        logging.info("Initialized retriever")
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=Config.TEXT_SEPARATORS
        )
        logging.info("Initialized text splitter")
    
    def _initialize_vector_store(self):
        """
        Initialize the vector store with error handling.
        
        Returns:
            Chroma: Vector store instance
        """
        try:
            if os.path.exists(Config.CHROMA_PERSIST_DIR):
                db = Chroma(
                    persist_directory=Config.CHROMA_PERSIST_DIR,
                    embedding_function=self.embeddings
                )
                logging.info(f"Loaded existing vector store from {Config.CHROMA_PERSIST_DIR}")
            else:
                db = Chroma(
                    persist_directory=Config.CHROMA_PERSIST_DIR,
                    embedding_function=self.embeddings
                )
                logging.info(f"Created new vector store at {Config.CHROMA_PERSIST_DIR}")
            return db
        except Exception as e:
            logging.error(f"Error with vector database: {e}")
            # Create new database with timestamp
            new_dir = f'chroma_db_new_{int(time.time())}'
            db = Chroma(
                persist_directory=new_dir,
                embedding_function=self.embeddings
            )
            logging.info(f"Created fallback vector store at {new_dir}")
            return db
    
    def get_llm(self):
        """Get the LLM instance."""
        return self.llm
    
    def get_embeddings(self):
        """Get the embeddings instance."""
        return self.embeddings
    
    def get_db(self):
        """Get the vector store instance."""
        return self.db
    
    def get_retriever(self):
        """Get the retriever instance."""
        return self.retriever
    
    def get_text_splitter(self):
        """Get the text splitter instance."""
        return self.text_splitter
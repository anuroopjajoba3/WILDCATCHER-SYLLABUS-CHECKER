import os
from dotenv import load_dotenv
load_dotenv() 

class Config:
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 5001
    THREADED = True
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = 'gemini-2.0-flash'

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in .env")
        print("✅ Config validated")
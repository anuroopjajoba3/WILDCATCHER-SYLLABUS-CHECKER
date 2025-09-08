# Chatbot Application Refactoring Documentation

## Overview

This document describes the comprehensive refactoring of the chatbot application from a single monolithic file (`chatbot.py` - 759 lines) into a modular, maintainable architecture with 7 separate modules.

## Problem Statement

The original `chatbot.py` file had grown to over 500 lines, making it:
- Difficult to navigate and find specific functions
- Hard to maintain and modify
- Challenging for code review and collaboration
- Prone to merge conflicts in team environments

## Refactoring Strategy

The code was intelligently reorganized into logical chunks that group related functionality together, following the single responsibility principle and separation of concerns.

## New Module Structure

### 1. `document_processing.py`
**Purpose**: Handles extraction of text from various document formats

**Key Functions**:
- `extract_text_from_pdf(pdf_path)`: Extracts text and tables from PDF files
- `extract_text_from_docx(docx_path)`: Extracts text, tables, headers, and footers from DOCX files

**Dependencies**: `pdfplumber`, `python-docx`

### 2. `prompts.py`
**Purpose**: Centralizes all prompt templates and text constants

**Key Components**:
- `EXTRACTION_PROMPT`: Comprehensive prompt for course information extraction
- `CHAT_PROMPT_TEMPLATE`: Template for chat interactions with syllabus content

**Benefits**: Easy modification of prompts without touching business logic

### 3. `course_extraction.py`
**Purpose**: Handles course information extraction and validation

**Key Functions**:
- `extract_course_information(text, llm)`: Main extraction function with caching
- `validate_extracted_info(info)`: Validates and cleans extracted data
- `enhanced_post_process(info, original_text)`: Pattern matching for missed fields

**Features**:
- Text caching using MD5 hashes
- Smart text limiting for large documents
- Enhanced post-processing with regex patterns

### 4. `chat_manager.py`
**Purpose**: Manages chat history and conversation memory

**Key Components**:
- `ChatManager` class: Handles persistent chat storage
- File-based conversation memory
- Integration with LangChain's ConversationBufferMemory

**Methods**:
- `load_chat_history()` / `save_chat_history()`
- `load_conversation_memory()` / `save_conversation_memory()`
- `add_conversation()`: Adds new conversations to memory

### 5. `config.py`
**Purpose**: Configuration management and AI model initialization

**Key Classes**:
- `Config`: Application configuration settings
- `AIModels`: Manages initialization of LLM, embeddings, and vector store

**Features**:
- Environment variable validation
- Centralized configuration management
- AI model initialization with error handling
- Vector store setup with fallback mechanisms

### 6. `api_routes.py`
**Purpose**: Contains all Flask route handlers

**Key Routes**:
- `/`: Homepage
- `/upload_pdf`: Single file upload
- `/ask`: Chat functionality
- `/upload_folder`: Folder upload handling
- `/upload_zip`: ZIP file processing
- `/email_report`: Email functionality

**Benefits**: Clean separation of API logic from business logic

### 7. `main.py`
**Purpose**: Application entry point and initialization

**Key Functions**:
- `create_app()`: Flask app factory pattern
- `main()`: Application startup
- Component initialization and wiring

## Key Improvements

### 1. **Modularity**
- Each module has a single, clear responsibility
- Dependencies are explicit and minimal
- Easy to test individual components

### 2. **Maintainability**
- Functions are smaller and focused
- Code is easier to navigate and understand
- Changes can be made to specific modules without affecting others

### 3. **Reusability**
- Components can be imported and used independently
- Business logic separated from presentation logic
- Easy to create unit tests for individual modules

### 4. **Documentation**
- Each module has comprehensive docstrings
- Clear explanation of purpose and functionality
- Function parameters and return values documented

### 5. **Configuration Management**
- Centralized configuration in `config.py`
- Environment variables properly managed
- Easy to modify settings without code changes

## Migration Guide

### Running the Application

**Before** (single file):
```bash
python chatbot.py
```

**After** (modular):
```bash
python main.py
```

### Import Changes

If you were importing functions from the original file, update imports:

**Before**:
```python
from chatbot import extract_text_from_pdf, extract_course_information
```

**After**:
```python
from document_processing import extract_text_from_pdf
from course_extraction import extract_course_information
```

### Configuration Changes

Configuration is now centralized in `config.py`. Modify the `Config` class instead of scattered variables:

```python
class Config:
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 8001
    # ... other settings
```

## File Structure

```
Fall2025-Team-Alpha/
├── main.py                    # Application entry point
├── config.py                  # Configuration and AI models
├── api_routes.py              # Flask route handlers
├── chat_manager.py            # Chat history management
├── course_extraction.py       # Course information extraction
├── document_processing.py     # Document text extraction
├── prompts.py                 # LLM prompts and templates
├── database.py                # Database models (unchanged)
├── chatbot.py                 # Original file (can be removed)
└── templates/                 # HTML templates
    └── index.html
```

## Benefits Achieved

1. **Reduced Complexity**: Each file is now focused and manageable
2. **Improved Navigation**: Easy to find specific functionality
3. **Better Testing**: Individual modules can be unit tested
4. **Enhanced Collaboration**: Team members can work on different modules
5. **Easier Debugging**: Issues can be isolated to specific modules
6. **Future-Proof**: Easy to add new features or modify existing ones

## Backward Compatibility

The refactored application maintains full backward compatibility:
- All API endpoints work exactly the same
- No changes to frontend integration required
- Database structure unchanged
- Environment variables remain the same

## Conclusion

This refactoring transforms a monolithic 759-line file into a clean, modular architecture that's easier to maintain, test, and extend. The application now follows Python best practices and is better prepared for future enhancements and team collaboration.
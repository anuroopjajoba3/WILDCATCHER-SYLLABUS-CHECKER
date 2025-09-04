# Project Cleanup Documentation

## Date: September 4, 2025

This document details the cleanup performed on the Spring2025-Team-Marvel project to prepare it for GitHub repository upload.

## Summary
Reduced project from 30+ files/directories to essential files only, and trimmed requirements.txt from 164 lines to 14 lines.

## Files and Directories Removed

### 1. SQLite Executable Files
**Removed:** `sqlite3.exe`, `sqldiff.exe`, `sqlite3_analyzer.exe`, `sqlite3_rsync.exe`
- **Why:** These are Windows SQLite executables that should not be in version control
- **Impact:** None - SQLite functionality is provided by Python packages
- **Size saved:** ~14 MB

### 2. Python Cache Directory
**Removed:** `__pycache__/`
- **Why:** Contains compiled Python bytecode files (.pyc) that are auto-generated
- **Impact:** None - Python recreates these automatically when needed
- **Note:** Already listed in .gitignore

### 3. Virtual Environment
**Removed:** `venv/`
- **Why:** Virtual environments should be created locally by each developer
- **Impact:** None - recreate with `python -m venv venv`
- **Size saved:** ~500+ MB
- **Note:** Already listed in .gitignore

### 4. Runtime Database Files
**Removed:** 
- `documents.db` (1.1 MB)
- `document.db` (empty)
- `db/` directory (contains chroma.sqlite3)
- **Why:** Database files contain runtime data and should not be in version control
- **Impact:** Will be recreated when application runs
- **Note:** .db files already listed in .gitignore

### 5. Application Cache
**Removed:** `cache/` directory
- **Why:** Contains temporary cached data from application runtime
- **Impact:** None - cache rebuilds automatically

### 6. User Upload Directory
**Removed:** `uploads/` directory
- **Why:** Contains user-uploaded files during runtime
- **Impact:** None - directory recreated when needed
- **Note:** Already listed in .gitignore

### 7. Runtime Data Files
**Removed:**
- `chat_history.json` - Stores conversation history
- `conversation_memory.json` - Stores conversation memory state
- `gunicorn.log` - Application server logs
- **Why:** These are runtime-generated files specific to each deployment
- **Impact:** None - recreated during application use
- **Note:** Already listed in .gitignore

### 8. Empty Placeholder Files
**Removed:** `Advanced`, `App`, `Apps`
- **Why:** Empty files (0 bytes) with no purpose
- **Impact:** None - no functionality loss

### 9. Git Command Artifact
**Removed:** `et --hard 591f1f48`
- **Why:** Accidental file creation from incomplete git command
- **Impact:** None - not part of project

### 10. Migration Script
**Removed:** `migrate_to_normalized.py`
- **Why:** One-time database migration script, already executed
- **Impact:** None - migration already completed

### 11. Duplicate Directory
**Removed:** `Spring2025-Team-Marvel/` subdirectory
- **Why:** Nested duplicate of project directory
- **Impact:** None - appears to be accidental duplication

### 12. Test Configuration File
**Removed:** `pytest.init`
- **Why:** Likely typo (should be pytest.ini) or unnecessary
- **Impact:** None - pytest works without it

## Requirements.txt Cleanup

### Before: 164 lines
- Contained dependencies for multiple unused frameworks
- Included transitive dependencies (automatically installed)
- Had packages for features not used in the codebase

### After: 14 lines
```
flask==3.0.3
python-dotenv==1.0.1
langchain==0.3.7
langchain-community==0.3.5
langchain-openai==0.2.5
chromadb==0.5.7
openai==1.52.2
pdfplumber==0.11.4
python-docx==1.1.0
sqlalchemy==2.0.35
pytest==8.3.3
lxml>=4.9.0
```

### Removed Dependencies (Examples):
- **Deep learning packages:** torch, transformers, sentence-transformers (not used)
- **Data science packages:** pandas, numpy, scipy, scikit-learn (not actively used)
- **Testing packages:** pytest-xdist, pytest-repeat, deepeval, ragas (excessive for current tests)
- **Monitoring packages:** sentry-sdk, posthog, opentelemetry-* (not configured)
- **Async packages:** aiohttp, aiohappyeyeballs, uvicorn, fastapi (using Flask sync)
- **Duplicate packages:** Multiple JSON/YAML parsers, HTTP clients

## Files Kept

### Core Application
- `chatbot.py` - Main Flask application
- `database.py` - Database models
- `test_chatbot.py` - Test file
- `testing/` - Test directory

### Configuration
- `.env.example` - Environment template
- `.gitignore` - Git ignore rules
- `requirements.txt` - Dependencies (cleaned)

### Resources
- `templates/` - HTML templates
- `static/` - CSS/JS/Images
- `data/` - Data files

### Documentation
- `README.md` - Project documentation
- `documentation/` - Additional docs (this file)

### Development
- `.vscode/` - VS Code settings (optional but useful)
- `.git/` - Git repository data

## Total Impact
- **Files/Directories removed:** 20+
- **Project size reduction:** ~600+ MB to ~50 MB
- **Dependencies reduced:** 164 to 14
- **Result:** Clean, professional repository ready for GitHub

## Recommendations for Developers

1. After cloning the repository:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a `.env` file based on `.env.example`

3. The application will automatically create necessary directories and database files on first run

4. Use Python 3.12 for best compatibility (Python 3.13 has limited library support as of 2025)
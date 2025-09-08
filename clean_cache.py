#!/usr/bin/env python3
"""
NECHE Compliance Checker - Cache Cleaner Script

This script cleans all cached data, uploaded files, and stored memories
to provide a fresh start for testing the system.

Run this script whenever you want to reset the system completely.
"""

import os
import shutil
import sqlite3
from pathlib import Path
import subprocess
import time

def kill_chatbot_processes():
    """Kill any running chatbot.py processes to unlock database files."""
    try:
        # Kill any Python processes running chatbot.py
        result = subprocess.run([
            "taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq *chatbot*"
        ], capture_output=True, text=True)
        
        # Also try to kill processes that might be using the port
        subprocess.run([
            "netstat", "-ano", "|", "findstr", ":8001"
        ], shell=True, capture_output=True)
        
        time.sleep(2)  # Give processes time to terminate
        print("[INFO] Attempted to stop any running chatbot processes")
        
    except Exception as e:
        print(f"[INFO] Could not kill processes: {e}")

def clean_cache():
    """Clean all cached data and memories from the system."""
    
    print("NECHE Compliance Checker - Cache Cleaner")
    print("=" * 50)
    
    # First, try to stop any running processes
    kill_chatbot_processes()
    
    # Get the current directory (where the script is located)
    base_dir = Path(__file__).parent
    
    # List of items to clean
    items_to_clean = [
        {
            'name': 'ChromaDB Vector Store',
            'path': base_dir / 'chroma_db',
            'action': 'remove_contents'
        },
        {
            'name': 'SQLite Database',
            'path': base_dir / 'documents.db',
            'action': 'remove_file'
        },
        {
            'name': 'Chat History',
            'path': base_dir / 'chat_history.json',
            'action': 'reset_json'
        },
        {
            'name': 'Conversation Memory',
            'path': base_dir / 'conversation_memory.json', 
            'action': 'reset_json'
        },
        {
            'name': 'Uploaded Files',
            'path': base_dir / 'uploads',
            'action': 'remove_contents'
        },
        {
            'name': 'Python Cache',
            'path': base_dir / '__pycache__',
            'action': 'remove_contents'
        }
    ]
    
    cleaned_items = 0
    total_items = len(items_to_clean)
    
    for item in items_to_clean:
        name = item['name']
        path = item['path']
        action = item['action']
        
        try:
            if action == 'remove_file' and path.exists():
                path.unlink()
                print(f"[OK] {name}: File removed")
                cleaned_items += 1
                
            elif action == 'remove_contents' and path.exists():
                if path.is_dir():
                    # Remove all contents but keep the directory
                    for item_path in path.iterdir():
                        if item_path.is_file():
                            item_path.unlink()
                        elif item_path.is_dir():
                            shutil.rmtree(item_path)
                    print(f"[OK] {name}: Contents removed")
                    cleaned_items += 1
                    
            elif action == 'reset_json':
                # Reset JSON files to empty arrays
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('[]')
                print(f"[OK] {name}: Reset to empty array")
                cleaned_items += 1
                
            else:
                print(f"[SKIP] {name}: Not found (already clean)")
                
        except Exception as e:
            print(f"[ERROR] {name}: Error - {str(e)}")
    
    print("=" * 50)
    print(f"Cache cleaning completed!")
    print(f"Cleaned {cleaned_items}/{total_items} items")
    print()
    print("The system is now ready for fresh testing.")
    print("You can restart the server with: python chatbot.py")
    print()
    
    return cleaned_items

def main():
    """Main function to run the cache cleaner."""
    
    # Check if we're in the right directory
    if not Path('chatbot.py').exists():
        print("[ERROR] This script must be run from the project root directory")
        print("   (where chatbot.py is located)")
        return False
    
    # Ask for confirmation
    print("This will delete all cached data, uploaded files, and conversation history.")
    confirm = input("Are you sure you want to continue? (y/N): ").lower().strip()
    
    if confirm not in ['y', 'yes']:
        print("[CANCELLED] Operation cancelled.")
        return False
    
    # Clean the cache
    cleaned = clean_cache()
    
    if cleaned > 0:
        print("TIP: Make sure to stop the server before running this script")
        print("   to avoid file locking issues.")
    
    return True

if __name__ == "__main__":
    main()
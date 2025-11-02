#!/usr/bin/env python3
"""
Script to add 'grading_process' field to all entries in ground_truth.json
"""

import json

def add_grading_process_field():
    # Read the current ground truth file
    with open('ground_truth.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Add grading_process field to each entry
    count = 0
    for entry in data:
        if 'final_grade_scale' in entry and 'grading_process' not in entry:
            entry['grading_process'] = ""
            count += 1
    
    # Write back to file with proper formatting
    with open('ground_truth.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Added 'grading_process' field to {count} entries")
    print(f"Total entries in file: {len(data)}")

if __name__ == '__main__':
    add_grading_process_field()

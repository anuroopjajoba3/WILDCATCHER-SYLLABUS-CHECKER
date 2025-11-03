#!/usr/bin/env python3

"""
Debug script to test why "Late Work" titles aren't being detected
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from detectors.late_missing_work_detector import LateDetector

def test_simple_cases():
    detector = LateDetector()
    
    # Test cases that should work
    test_cases = [
        "Late Work",
        "Late Work:",
        "Late Work Policy",
        "Late Submissions",
        "Late Submissions:",
        "Late submissions and make-up exams",
        "Late submissions and make‐up exams",  # with em-dash
    ]
    
    print("Testing simple title detection:")
    for case in test_cases:
        # Test as standalone text
        result = detector.detect(case)
        print(f"'{case}' -> Found: {result['found']}, Content: {result.get('content', 'None')}")
        
        # Test embedded in document
        doc_text = f"Course Syllabus\n\n{case}\nThis is the policy content.\n\nNext Section"
        result2 = detector.detect(doc_text)
        print(f"  Embedded: Found: {result2['found']}, Content: {result2.get('content', 'None')[:50]}...")
        print()

if __name__ == "__main__":
    test_simple_cases()

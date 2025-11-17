#!/usr/bin/env python3
"""
Debug test for grading scale detector.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.grading_scale_detection import GradingScaleDetector

def debug_test():
    """Test with one specific example."""
    
    detector = GradingScaleDetector()
    
    # Test case 1: Standard grading scale (like in ground truth)
    test1 = """
    Course Policies
    
    Grading Scale:
    A: 93 - 100 A-: 90 - 92.9 B+: 87 - 89.9 B: 83 - 86.9 B-: 80 - 82.9 C+: 77 - 79.9 C: 73 - 76.9 C-: 70 - 72.9 D+: 67 - 69.9 D: 63 - 66.9 D-: 60 - 62.9 F: 59.9 or below
    
    Assignment breakdown will be provided later.
    """
    
    print("Testing simple detector with debug...")
    result = detector.detect(test1)
    print(f"Result: {result}")

if __name__ == "__main__":
    debug_test()

#!/usr/bin/env python3
"""
Test script for grading scale detector.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.grading_scale_detection import GradingScaleDetector

def test_grading_scale_detector():
    """Test the grading scale detector with various examples."""
    
    detector = GradingScaleDetector()
    
    # Test case 1: Standard grading scale (like in ground truth)
    test1 = """
    Course Policies
    
    Grading Scale:
    A: 93 - 100 A-: 90 - 92.9 B+: 87 - 89.9 B: 83 - 86.9 B-: 80 - 82.9 C+: 77 - 79.9 C: 73 - 76.9 C-: 70 - 72.9 D+: 67 - 69.9 D: 63 - 66.9 D-: 60 - 62.9 F: 59.9 or below
    
    Assignment breakdown will be provided later.
    """
    
    # Test case 2: Vertical grading scale
    test2 = """
    GRADING CRITERIA
    
    A+ 97-100
    A  93-96
    A- 90-92
    B+ 87-89
    B  83-86
    B- 80-82
    C+ 77-79
    C  73-76
    C- 70-72
    D+ 67-69
    D  63-66
    D- 60-62
    F  Below 60
    
    Additional policies follow.
    """
    
    # Test case 3: Missing some required grades (should fail)
    test3 = """
    Grading:
    A 90-100  B+ 85-89  B 80-84  C+ 75-79  C 70-74  F Below 70
    """
    
    # Test case 4: Grading scale with extra text
    test4 = """
    The following grading scale will be used:
    A (93-100 Excellent work) A- (90-92 Very good) B+ (87-89 Good) B (83-86 Satisfactory) B- (80-82 Below average) C+ (77-79 Adequate) C (73-76 Acceptable) C- (70-72 Poor) D+ (67-69 Very poor) D (63-66 Minimal) D- (60-62 Failing) F (0-59 Failure)
    This scale is non-negotiable.
    """
    
    # Test case 5: GPA format (like in ground truth)
    test5 = """
    Grading Scale:
    94-100 A 4.0 90-93 A- 3.67 87-89 B+ 3.33 84-86 B 3.0 80-83 B- 2.67 77-79 C+ 2.33 74-76 C 2.0 70-73 C- 1.67 67-69 D+ 1.33 64-66 D 1.0 60-63 D- 0.67 59-Below F 0.0
    """
    
    # Test case 6: Vertical Letter Range format
    test6 = """
    Letter Range
    A 100 % to 94 %
    A- < 94 % to 90 %
    B+ < 90 % to 87 %
    B < 87 % to 84 %
    B- < 84 % to 80 %
    C+ < 80 % to 77 %
    C < 77 % to 74 %
    C- < 74 % to 70 %
    D+ < 70 % to 67 %
    D < 67 % to 64 %
    D- < 64 % to 60 %
    F < 60 % to 0 %
    """
    
    # Test case 7: Equals format
    test7 = """
    Final grades: 94-100=A; 90-93.9=A-; 87-89.9=B+; 83-86.9=B; 80-82.9=B-; 77-79.9=C+; 73-76.9=C; 70-72.9=C-; 67-69.9=D+; 63-66.9=D; 60-62.9=D-; Below 60=F
    """
    
    # Test case 8: Simple format
    test8 = """
    Grades:
    A A- B+ B B- C+ C C- D+ D D- F
    93 90 87 83 80 77 73 70 67 63 60 <60
    """
    
    test_cases = [
        ("Standard horizontal scale", test1),
        ("Vertical scale with A+", test2), 
        ("Incomplete scale (missing grades)", test3),
        ("Scale with descriptions", test4),
        ("GPA format", test5),
        ("Vertical Letter Range", test6),
        ("Equals format", test7),
        ("Simple format", test8)
    ]
    
    print("Testing Grading Scale Detector")
    print("=" * 50)
    
    for i, (name, test_text) in enumerate(test_cases, 1):
        print(f"\nTest {i}: {name}")
        print("-" * 30)
        
        result = detector.detect(test_text)
        
        print(f"Found: {result['found']}")
        if result['found']:
            print(f"Scale text: {result['content']}")
            print(f"Grades found: {result['grades_found']}")
            print(f"Length: {len(result['content'])} characters")
        else:
            print("No valid grading scale detected")
        print()

if __name__ == "__main__":
    test_grading_scale_detector()

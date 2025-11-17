#!/usr/bin/env python3
"""
Test the improved grading scale comparison logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from test_runner import compare_grading_scale

def test_comparison_improvements():
    """Test cases that were failing due to formatting differences."""
    
    print("Testing Grading Scale Comparison Improvements")
    print("=" * 55)
    
    test_cases = [
        {
            "name": "CPRM 860 - Extra prefix text",
            "gt": "A 100 % to 94 % A- < 94 % to 90 % B+ < 90 % to 87 % B < 87 % to 84 % B- < 84 % to 80 % C+ < 80 % to 77 % C < 77 % to 74 % C- < 74 % to 70 % D+ < 70 % to 67 % D < 67 % to 64 % D- < 64 % to 60 % F < 60 % to 0 %",
            "pred": "guidelines using this schema: A 100 % to 94 % A- < 94 % to 90 % B+ < 90 % to 87 % B < 87 % to 84 % B- < 84 % to 80 % C+ < 80 % to 77 % C < 77 % to 74 % C- < 74 % to 70 % D+ < 70 % to 67 % D < 67 % to 64 % D- < 64 % to 60 % F < 60 % to 0 %"
        },
        {
            "name": "ENGL401M1 - Extra assignment percentage",
            "gt": "A 100-94, A- <94-90, B+ <90-87, B <87-84, B- <84-80, C+ <80-77, C <77-74, C- <74-70, D+ <70-67, D <67-64, D- <64-60, F <60-0",
            "pred": "A 100-94 A- <94-90 B+ <90-87 B <87-84 E-Portfolio 20% B- <84-80 C+ <80-77 C <77-74 C- <74-70 D+ <70-67 D <67-64 D- <64-60 F <60-0"
        },
        {
            "name": "HIST 497 - Table vs linear format",
            "gt": "Letter | Range | Range | Range\nA | 100 % | to | 94 %\nA- | < 94 % | to | 90 %\nB+ | < 90 % | to | 87 %\nB | < 87 % | to | 84 %\nB- | < 84 % | to | 80 %\nC+ | < 80 % | to | 77 %\nC | < 77 % | to | 74 %\nC- | < 74 % | to | 70 %\nD+ | < 70 % | to | 67 %\nD | < 67 % | to | 64 %\nD- | < 64 % | to | 60 %\nF | < 60 % | to | 0 %",
            "pred": "A | 100 % | to | 94 % A- | < 94 % | to | 90 % B+ | < 90 % | to | 87 % B | < 87 % | to | 84 % B- | < 84 % | to | 80 % C+ | < 80 % | to | 77 % C | < 77 % | to | 74 % C- | < 74 % | to | 70 % D+ | < 70 % | to | 67 % D | < 67 % | to | 64 % D- | < 64 % | to | 60 % F | < 60 % | to | 0 %"
        },
        {
            "name": "Both missing should match",
            "gt": "Missing",
            "pred": "Missing"
        },
        {
            "name": "GT missing, pred found (false positive)",
            "gt": "Missing",
            "pred": "A 90-100 B 80-89 C 70-79 D 60-69 F below 60"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 40)
        result = compare_grading_scale(test['gt'], test['pred'])
        print(f"Match: {result}")
        
        if i <= 3:  # First 3 should match now
            expected = True
            status = "✅ PASS" if result == expected else "❌ FAIL"
        elif i == 4:  # Both missing
            expected = True
            status = "✅ PASS" if result == expected else "❌ FAIL"
        else:  # GT missing but pred found
            expected = False
            status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"Expected: {expected} | {status}")

if __name__ == "__main__":
    test_comparison_improvements()

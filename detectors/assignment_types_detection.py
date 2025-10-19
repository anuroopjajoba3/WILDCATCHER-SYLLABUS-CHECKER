"""
Assignment Types Title Detector
Detects section headers for assignment types in syllabi
"""

import re
from typing import Dict, Any


class AssignmentTypesDetector:
    """Detector for assignment types section titles in syllabi"""
    
    def __init__(self):
        # Patterns based on ground truth data
        self.patterns = [
            # Direct assignment-related patterns
            r'(?i)^\s*assignments?\s*&\s*grades?\s*:?\s*$',
            r'(?i)^\s*assignments?\s*:?\s*$',
            r'(?i)^\s*homework\s*assignments?\s*:?\s*$',
            r'(?i)^\s*homework\s*:?\s*$',
            r'(?i)^\s*class\s+assignments?\s*:?\s*$',
            r'(?i)^\s*major\s+projects?\s*:?\s*$',
            
            # Activity and requirement patterns
            r'(?i)^\s*course\s+activities\s*:?\s*$',
            r'(?i)^\s*required\s+paperwork\s+and\s+submissions?\s*\.?\s*$',
            r'(?i)^\s*course\s+requirements?\s+and\s+assessments?\s+overview\s*:?\s*$',
            
            # Evaluation patterns
            r'(?i)^\s*methods\s+of\s+testing\s*/?\s*evaluation\s*:?\s*$',
            r'(?i)^\s*summary\s+of\s+student\s+evaluation\s*:?\s*$',
            r'(?i)^\s*student\s+evaluation\s*:?\s*$',
            r'(?i)^\s*assessment\s*:?\s*$',
            r'(?i)^\s*assessment\s*,\s*participation\s+assignments?\s*:?\s*$',
            
            # Grading-related patterns (when used for assignments)
            r'(?i)^\s*grading\s+and\s+evaluation\s+of\s+student\s+work\s*:?\s*$',
            r'(?i)^\s*grading\s+distribution\s*:?\s*$',
            r'(?i)^\s*assignment\s+and\s+grading\s+details?\s+lab\s*:?\s*$',
            r'(?i)^\s*assignment\s+details?\s*:?\s*$',
            
            # Combined patterns
            r'(?i)^\s*assignments?\s+and\s+grading\s*:?\s*$',
            r'(?i)^\s*assignments?\s+and\s+course\s+specific\s+policies\s*:?\s*$',
            
            # Specific quiz/exam patterns
            r'(?i)^\s*quizzes\s+and\s+exams?\s*:?\s*$',
            r'(?i)^\s*textbook\s+chapter\s+quizzes',
            
            # Grade-focused patterns
            r'(?i)^\s*grades?\s*:?\s*$',
            r'(?i)^\s*methods\s*,\s*grade\s+components',
            r'(?i)^\s*evaluation\s*:?\s*$',
        ]
    
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect assignment types section title in syllabus text.
        
        Args:
            text: Full syllabus text
            
        Returns:
            Dict with 'found' (bool) and 'content' (str) keys
        """
        if not text:
            return {"found": False, "content": ""}
        
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip very long lines (unlikely to be section headers)
            if len(line_stripped) > 200 or len(line_stripped) < 3:
                continue
            
            # Try each pattern
            for pattern in self.patterns:
                if re.match(pattern, line_stripped, re.MULTILINE):
                    return {
                        "found": True,
                        "content": line_stripped
                    }
        
        return {"found": False, "content": ""}


# For backwards compatibility
def detect_assignment_types_title(text: str) -> str:
    """
    Standalone function for detecting assignment types title.
    
    Args:
        text: Full syllabus text
        
    Returns:
        The detected title or empty string
    """
    detector = AssignmentTypesDetector()
    result = detector.detect(text)
    return result.get("content", "") if result.get("found") else ""


if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("Homework:\nStudents will complete assignments", "Homework:"),
        ("SUMMARY OF STUDENT EVALUATION\nExams: 50%", "SUMMARY OF STUDENT EVALUATION"),
        ("Course Activities\n1. Labs\n2. Projects", "Course Activities"),
        ("Assignments & Grades\nHomework 30%", "Assignments & Grades"),
        ("No assignment section here", ""),
    ]
    
    detector = AssignmentTypesDetector()
    
    print("Testing Assignment Types Detector:")
    print("-" * 60)
    
    for text, expected in test_cases:
        result = detector.detect(text)
        found = result.get("content", "")
        status = "✓" if found == expected else "✗"
        print(f"{status} Input: {text[:40]}...")
        print(f"  Expected: '{expected}'")
        print(f"  Got: '{found}'")
        print()
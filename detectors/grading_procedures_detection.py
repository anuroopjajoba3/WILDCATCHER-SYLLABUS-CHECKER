"""
Grading Procedures Title Detector
Detects section headers for grading procedures in syllabi
"""

import re
import logging
from typing import Dict, Any

# Detection Configuration
MIN_LINE_LENGTH = 3
MAX_LINE_LENGTH = 200


class GradingProceduresDetector:
    """Detector for grading procedures section titles in syllabi"""

    def __init__(self):
        self.field_name = 'grading_procedures'
        self.logger = logging.getLogger('detector.grading_procedures')

        # Patterns based on ground truth data
        self.patterns = [
            # Direct grading patterns
            r'(?i)^\s*grading\s+procedures?\s*:?\s*$',
            r'(?i)^\s*grading\s+policy\s*:?\s*$',
            r'(?i)^\s*grading\s*:?\s*$',
            r'(?i)^\s*course\s+grade\s*:?\s*$',
            r'(?i)^\s*student\s+grades?\s*:?\s*$',
            
            # Assignment of grade patterns
            r'(?i)^\s*assignment\s+of\s+a\s+letter\s+grade\s*:?\s*$',
            
            # Distribution patterns
            r'(?i)^\s*grading\s+distribution\s*:?\s*$',
            
            # Evaluation patterns
            r'(?i)^\s*summary\s+of\s+student\s+evaluation\s*:?\s*$',
            r'(?i)^\s*grading\s+and\s+evaluation\s+of\s+student\s+work\s*:?\s*$',
            r'(?i)^\s*student\s+evaluation\s*:?\s*$',
            r'(?i)^\s*evaluation\s*:?\s*$',
            
            # Assessment patterns
            r'(?i)^\s*assessment\s*:?\s*$',
            r'(?i)^\s*rubric\s+and\s+evaluation\s+methods?\s*:?\s*$',
            
            # Specific rubric patterns
            r'(?i)^\s*homework\s+grading\s+rubric\s*:?\s*$',
            
            # Combined patterns
            r'(?i)^\s*assignments?\s*&?\s*grading\s*:?\s*$',
            r'(?i)^\s*assignments?\s+and\s+grading\s*:?\s*$',
            
            # System patterns
            r'(?i)^\s*course\s+grading\s+system\s*:?\s*$',
            
            # General grade patterns
            r'(?i)^\s*grades?\s*:?\s*$',
            
            # Component patterns
            r'(?i)^\s*methods\s*,\s*grade\s+components',
            
            # Requirements patterns
            r'(?i)^\s*course\s+requirements?\s+and\s+assessments?\s+overview\s*:?\s*$',
        ]

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text for consistent matching.
        Handles:
        - Lowercasing
        - Unicode punctuation (full-width colon, em-dash, etc.)
        - Extra whitespace
        """
        if not text:
            return ""

        # Lowercase first
        normalized = text.lower()

        # Replace Unicode punctuation with ASCII equivalents
        normalized = normalized.replace('：', ':')  # Full-width colon
        normalized = normalized.replace('—', '-')  # Em-dash
        normalized = normalized.replace('–', '-')  # En-dash
        normalized = normalized.replace('\u2014', '-')  # Em-dash (unicode)
        normalized = normalized.replace('\u2013', '-')  # En-dash (unicode)

        # Normalize whitespace (multiple spaces -> single space)
        normalized = ' '.join(normalized.split())

        return normalized

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect grading procedures section title in syllabus text.

        Args:
            text: Full syllabus text

        Returns:
            Dict with 'found' (bool) and 'content' (str) keys
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        if not text:
            self.logger.info(f"NOT_FOUND: {self.field_name} (empty text)")
            return {"found": False, "content": ""}

        lines = text.split('\n')

        for line in lines:
            line_stripped = line.strip()

            # Skip lines outside valid length range (unlikely to be section headers)
            if len(line_stripped) > MAX_LINE_LENGTH or len(line_stripped) < MIN_LINE_LENGTH:
                continue

            # Normalize the line for matching
            normalized_line = self._normalize_text(line_stripped)

            # Try each pattern against the normalized line
            for pattern in self.patterns:
                # Note: patterns already have (?i) flag for case-insensitive matching
                if re.match(pattern, normalized_line):
                    self.logger.info(f"FOUND: {self.field_name} - '{line_stripped}'")
                    return {
                        "found": True,
                        "content": line_stripped  # Return original, not normalized
                    }

        self.logger.info(f"NOT_FOUND: {self.field_name}")
        return {"found": False, "content": ""}


# For backwards compatibility
def detect_grading_procedures_title(text: str) -> str:
    """
    Standalone function for detecting grading procedures title.
    
    Args:
        text: Full syllabus text
        
    Returns:
        The detected title or empty string
    """
    detector = GradingProceduresDetector()
    result = detector.detect(text)
    return result.get("content", "") if result.get("found") else ""


if __name__ == "__main__":
    # Test cases (Windows-compatible output)
    test_cases = [
        ("Grading Policy:\nGrades are based on performance", "Grading Policy:"),
        ("SUMMARY OF STUDENT EVALUATION\nExams: 50%", "SUMMARY OF STUDENT EVALUATION"),
        ("Course Grade:\nCalculated as follows", "Course Grade:"),
        ("Rubric and Evaluation Methods\nDetailed rubric", "Rubric and Evaluation Methods"),
        ("No grading section here", ""),
    ]

    detector = GradingProceduresDetector()

    print("Testing Grading Procedures Detector:")
    print("-" * 60)

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = detector.detect(text)
        found = result.get("content", "")
        match = (found == expected)

        if match:
            status = "[PASS]"
            passed += 1
        else:
            status = "[FAIL]"
            failed += 1

        print(f"{status} Input: {text[:40]}...")
        print(f"  Expected: '{expected}'")
        print(f"  Got: '{found}'")
        print()

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
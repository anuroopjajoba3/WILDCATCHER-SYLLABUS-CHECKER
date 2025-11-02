"""
Email Detector
=========================================
Detects instructor email addresses in syllabus documents.
Prefers emails near typical headings; falls back to first valid email.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Detection Configuration
MAX_HEADING_SCAN_LINES = 150
MAX_HEADER_CHARS = 1200
EMAIL_CONFIDENCE_SCORE = 0.95
DEFAULT_PHONE_SEARCH_LIMIT = 2000

EMAIL_RX = re.compile(
    r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@(?:unh|usnh)\.edu"
)

#        digit_pattern = r'([(\d][\d\s().-]{8,14})'
PHONE_RX = re.compile(
        r'([(\d][\d\s().-]{8,14})'
)
# Heading keywords to look for (will be normalized during search)


PRIMARY_HEADING_CLUES = [
    "preferred contact method", "best way to reach me", "primary contact method", "contact me by", "reach out via", "contact me through"
]
HEADING_CLUES = [
    "email", "e-mail", "contact", "phone", "phone number", "telephone"
    "contact information", "instructor", "professor"
]

import re

class PreferredContactDetector:
    def __init__(self):
        # Regex for contact methods
        self.contact_patterns = {
            "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
            "phone": re.compile(r"\b(call|text|phone|telephone|cell|mobile)\b"),
            "zoom": re.compile(r"\b(zoom|teams|video call|meeting)\b"),
            "office": re.compile(r"\b(office hours|in office|on campus|visit my office)\b"),
            "canvas": re.compile(r"\b(canvas|blackboard|moodle|portal message)\b")
        }

        # Regex for phrases that signal preference
        self.preference_indicator = re.compile(
            r"(preferred contact|please reach out via|best way to contact|contact me by|"
            r"should contact|email is the best|check my email|respond within)",
            re.IGNORECASE
        )

    def detect(self, text):
        lines = text.split('\n')
        preferred = None
        content = []

        for line in lines:
            if self.preference_indicator.search(line):
                for method, pattern in self.contact_patterns.items():
                    if pattern.search(line.lower()):
                        preferred = method
                        content.append(line.strip())
                        break

        # fallback if no preference phrase but email is present
        if not preferred:
            for method, pattern in self.contact_patterns.items():
                if pattern.search(text.lower()):
                    preferred = method
                    content.append(f"No preference phrase, but found {method} pattern.")
                    break

        return {
            "preferred_contact_method": preferred,
            "content": content
        }

if __name__ == "__main__":
    # Test cases (avoiding Unicode in console output for Windows compatibility)
    test_cases = [
        ("Email: jane.doe@unh.edu", "Standard email with colon"),
        ("E-mail: john.smith@unh.edu", "E-mail variant"),
        ("contact me by test@unh.edu", "Extra spaces around colon"),
        ("Instructor\nEmail: prof@unh.edu", "Email on next line"),
    ]
    print("HI")

    detector = PreferredContactDetector()
    print("Testing Email Detector:")
    print("=" * 60)
    for test_text, description in test_cases:
        result = detector.detect(test_text)
        print(f"\nTest: {test_text}")
        print(f"\nTest: {description}")
        print(f"Found: {result.get('found')}")
        print(f"Email: {result.get('content')}")
        print(f"Method: {result.get('metadata', {}).get('method')}")

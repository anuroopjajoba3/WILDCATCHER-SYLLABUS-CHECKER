"""
email Detector
=========================================

This detector identifies Student Learning Outcomes in syllabus documents.
It uses pattern matching and keyword detection to find email sections.

Developer Notes:
---------------
This is a simple example of a field detector. When creating new detectors,
use this as a template for structure and patterns.
"""

import re
import logging
from typing import Dict, Any


class emailDetector:
    """
    Detector for email.

    This detector looks for common email patterns including:
    - Keywords like "Email", "Contact Information", "Contact"
    - structure of email addresses string space to @ to string until dot to string to end space 
    - example Contact StartSpaceString1@String2.String3EndSpace
    """

    def __init__(self):
        """Initialize the email detector."""
        self.field_name = 'email'
        self.logger = logging.getLogger('detector.email')
        self.email_keywords = [
            "email",
            "emails",
            "contact information",
            "contact",
            "e-mail",
            "preferred contact method",
            "contact info",
        ]

        # Action verbs commonly found in email
        self.action_verbs = [
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect Student Learning Outcomes in the text.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with email content if found
        """
        self.logger.info("Starting detection for field: email")

        # Limit text size to prevent hanging on large documents
        original_length = len(text)
        if len(text) > 20000:
            text = text[:20000]
            self.logger.info(f"Truncated large document from {original_length} to 20,000 characters")

        try:
            # Method 1: Keyword-based detection
            found, content, method = self._detect_by_keywords(text)
            #potentially put in a method 2 here that looks for email patterns directly

            if found:
                result = {
                    'field_name': self.field_name,
                    'found': True,
                    'content': content,
                    'confidence': 0.95,  # or another value
                    'metadata': {'method': method}
                }
                self.logger.info(f"FOUND: {self.field_name}")
                self.logger.info(f"SUCCESS: Found email via {method}")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None,
                    'confidence': 0.0,
                    'metadata': {}
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No emails found")

            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            self.logger.info(f"Detection complete for {self.field_name}: {'content' if found else 'no content'}")
            return result

        except Exception as e:
            self.logger.error(f"Error in email detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None,
                'confidence': 0.0,      
                'metadata': {}          
            }

    def _detect_by_keywords(self, text: str) -> tuple[bool, str, str]:
        """
        Detect email using keyword matching.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content, method_name)
        """
        text_lower = text.lower()
        text_lower = text_lower.replace(':', '').strip()

        for keyword in self.email_keywords:
            self.logger.info(f"Checking for keyword: {keyword} in email detector")

            if keyword in text_lower:
                # Found keyword, try to extract content around it
                pos = text_lower.find(keyword)
                if pos != -1:
                    # Get text section after the keyword
                    start = pos
                    end = min(pos +254, len(text)) #max length of an email address is 254 characters and shouldn't excede the pdf limits
                    section = text[start:end]

                    # Look for bullet points or numbered lists
                    email_content = self._extract_structured_content(section)

                    if email_content:
                        return True, email_content, f"keyword '{keyword}'"

        return False, "", "keyword_search"

    def _extract_structured_content(self, section: str) -> str:
        """
        Extract structured email content from a text section.

        Args:
            section (str): Text section containing potential email

        Returns:
            str: Extracted email content or empty string
        """
        pattern = r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@(?:unh|usnh)\.edu"
        return re.findall(pattern, section)

    def _clean_list_item(self, line: str) -> str:
        """
        Remove list markers from a line.

        Args:
            line (str): Line to clean

        Returns:
            str: Cleaned line without list markers
        """
        pattern = r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@(unh|usnh)\.edu"
        email_match = re.search(pattern, line)
        return email_match.group(0) if email_match else ""
    #this returns the email found through regex

# =============================================================================
# EXAMPLE USAGE FOR DEVELOPERS
# =============================================================================

if __name__ == "__main__":
    """
    Example usage - developers can run this file directly to test email detection.
    """
    # Test text with email
    test_text = """
    Course Objectives:
    Students will be able to:
    • Analyze complex data structures
    • Evaluate different algorithms
    • Demonstrate problem-solving skills
    • Apply theoretical concepts to practical problems
    """

    # Test the detector
    detector = emailDetector()
    result = detector.detect(test_text)

    print("email Detection Test Results:")
    print(f"Found: {result['found']}")
    print(f"Content: {result['content']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Metadata: {result['metadata']}")
"""
Student Learning Outcomes (SLO) Detector
=========================================

This detector identifies Student Learning Outcomes in syllabus documents.
It uses pattern matching and keyword detection to find SLO sections.

Developer Notes:
---------------
This is a simple example of a field detector. When creating new detectors,
use this as a template for structure and patterns.
"""

import re
import logging
from typing import Dict, Any


class SLODetector:
    """
    Detector for Student Learning Outcomes.

    This detector looks for common SLO patterns including:
    - Keywords like "Student Learning Outcomes", "Learning Objectives"
    - Action verbs in bulleted lists
    - Structured learning outcome statements
    """

    def __init__(self):
        """Initialize the SLO detector."""
        self.field_name = 'slos'
        self.logger = logging.getLogger('detector.slos')

        # SLO keywords to search for
        self.slo_keywords = [
            "student learning outcomes",
            "learning outcomes",
            "course objectives",
            "learning objectives",
            "students will be able to",
            "upon completion"
        ]

        # Action verbs commonly found in SLOs
        self.action_verbs = [
            'analyze', 'evaluate', 'demonstrate', 'understand', 'apply',
            'identify', 'describe', 'explain', 'create', 'synthesize',
            'compare', 'interpret', 'solve', 'design', 'construct'
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect Student Learning Outcomes in the text.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with SLO content if found
        """
        self.logger.info("Starting detection for field: slos")

        # Limit text size to prevent hanging on large documents
        original_length = len(text)
        if len(text) > 20000:
            text = text[:20000]
            self.logger.info(f"Truncated large document from {original_length} to 20,000 characters")

        try:
            # Method 1: Keyword-based detection
            found, content, method = self._detect_by_keywords(text)

            if not found:
                # Method 2: Action verb detection
                found, content, method = self._detect_by_action_verbs(text)

            if found:
                result = {
                    'field_name': self.field_name,
                    'found': True,
                    'content': content
                }
                self.logger.info(f"FOUND: {self.field_name}")
                self.logger.info(f"SUCCESS: Found SLOs via {method}")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No SLOs found")

            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            return result

        except Exception as e:
            self.logger.error(f"Error in SLO detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None
            }

    def _detect_by_keywords(self, text: str) -> tuple[bool, str, str]:
        """
        Detect SLOs using keyword matching.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content, method_name)
        """
        text_lower = text.lower()

        for keyword in self.slo_keywords:
            if keyword in text_lower:
                # Found keyword, try to extract content around it
                pos = text_lower.find(keyword)
                if pos != -1:
                    # Get text section after the keyword
                    start = pos
                    end = min(pos + 1000, len(text))
                    section = text[start:end]

                    # Look for bullet points or numbered lists
                    slo_content = self._extract_structured_content(section)

                    if slo_content:
                        return True, slo_content, f"keyword '{keyword}'"

        return False, "", "keyword_search"

    def _detect_by_action_verbs(self, text: str) -> tuple[bool, str, str]:
        """
        Detect SLOs using action verb patterns.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content, method_name)
        """
        lines = text.split('\n')
        verb_lines = []

        for line in lines:
            line = line.strip()
            # Check for reasonable line length and action verbs
            if 20 < len(line) < 200:
                line_lower = line.lower()
                verb_count = sum(1 for verb in self.action_verbs if verb in line_lower)

                # Look for bulleted/numbered lines with action verbs
                if verb_count >= 1 and self._is_list_item(line):
                    cleaned = self._clean_list_item(line)
                    if len(cleaned) > 10:
                        verb_lines.append(cleaned)

        # Need at least 2 lines to consider it SLOs
        if len(verb_lines) >= 2:
            content = '\n'.join(verb_lines[:5])  # Limit to first 5 items
            return True, content, "action_verb_detection"

        return False, "", "action_verb_search"

    def _extract_structured_content(self, section: str) -> str:
        """
        Extract structured SLO content from a text section.

        Args:
            section (str): Text section containing potential SLOs

        Returns:
            str: Extracted SLO content or empty string
        """
        lines = section.split('\n')
        slo_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line looks like an SLO item
            if self._is_potential_slo_line(line):
                cleaned = self._clean_list_item(line)
                if len(cleaned) > 10:  # Meaningful content
                    slo_lines.append(cleaned)

        if len(slo_lines) >= 1:
            return '\n'.join(slo_lines[:5])  # Limit to first 5 items

        return ""

    def _is_potential_slo_line(self, line: str) -> bool:
        """
        Check if a line looks like a potential SLO.

        Args:
            line (str): Line to check

        Returns:
            bool: True if line might contain an SLO
        """
        # Check for list markers or action verbs
        if self._is_list_item(line):
            return True

        # Check for action verbs
        line_lower = line.lower()
        verb_count = sum(1 for verb in self.action_verbs if verb in line_lower)
        return verb_count >= 1

    def _is_list_item(self, line: str) -> bool:
        """
        Check if line starts with list markers.

        Args:
            line (str): Line to check

        Returns:
            bool: True if line is a list item
        """
        return (line.startswith(('•', '-', '*', '▪')) or
                re.match(r'^\d+\.?\s', line))

    def _clean_list_item(self, line: str) -> str:
        """
        Remove list markers from a line.

        Args:
            line (str): Line to clean

        Returns:
            str: Cleaned line without list markers
        """
        return re.sub(r'^[\s•\-\*▪\d\.)]+', '', line).strip()


# =============================================================================
# EXAMPLE USAGE FOR DEVELOPERS
# =============================================================================

if __name__ == "__main__":
    """
    Example usage - developers can run this file directly to test SLO detection.
    """
    # Test text with SLOs
    test_text = """
    Course Objectives:
    Students will be able to:
    • Analyze complex data structures
    • Evaluate different algorithms
    • Demonstrate problem-solving skills
    • Apply theoretical concepts to practical problems
    """

    # Test the detector
    detector = SLODetector()
    result = detector.detect(test_text)

    print("SLO Detection Test Results:")
    print(f"Found: {result['found']}")
    print(f"Content: {result['content']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Metadata: {result['metadata']}")
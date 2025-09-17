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

        # The approved SLO titles we accept (both singular and plural)
        self.approved_titles = [
            "student learning outcomes",
            "student learning outcome",
            "student learning objectives",
            "student learning objective",
            "learning outcomes",
            "learning outcome",
            "learning objectives",
            "learning objective"
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect Student Learning Outcomes in the text.
        Simplified approach: just look for specific approved titles.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with SLO content if found
        """
        self.logger.info("Starting simplified SLO detection")

        # Limit text size to prevent hanging on large documents
        original_length = len(text)
        if len(text) > 20000:
            text = text[:20000]
            self.logger.info(f"Truncated large document from {original_length} to 20,000 characters")

        try:
            # Simple title-based detection
            found, content = self._simple_title_detection(text)

            if found:
                result = {
                    'field_name': self.field_name,
                    'found': True,
                    'content': content
                }
                self.logger.info(f"FOUND: {self.field_name}")
                self.logger.info("SUCCESS: Found approved SLO title")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No approved SLO titles found")

            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            return result

        except Exception as e:
            self.logger.error(f"Error in SLO detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None
            }

    def _simple_title_detection(self, text: str) -> tuple[bool, str]:
        """
        Simple title-based SLO detection.
        Just looks for exact approved titles and extracts following content.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content)
        """
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_clean = line.strip().lower()

            # Remove common punctuation for comparison
            line_for_comparison = line_clean.replace(':', '').replace('.', '').strip()

            # Check if this line starts with one of our approved titles
            if any(line_for_comparison.startswith(title) for title in self.approved_titles):
                # Found an approved title! Extract the title and some following content
                title = line.strip()

                # Get the next few lines as content (up to 10 lines or 500 characters)
                content_lines = [title]
                content_length = len(title)

                for j in range(i + 1, min(i + 10, len(lines))):
                    if j >= len(lines):
                        break

                    next_line = lines[j].strip()
                    if not next_line:
                        continue

                    # Stop if we hit another section title
                    if any(section in next_line.lower() for section in
                           ['course description', 'course objectives', 'course goals',
                            'prerequisites', 'textbook', 'grading', 'schedule']):
                        break

                    content_lines.append(next_line)
                    content_length += len(next_line)

                    # Stop after reasonable amount of content
                    if content_length > 500:
                        break

                content = '\n'.join(content_lines)
                return True, content

        return False, ""


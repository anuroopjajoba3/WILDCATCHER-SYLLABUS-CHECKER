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
from typing import Dict, Any, Tuple


class SLODetector:
    """
    Detector for Student Learning Outcomes.

    This detector looks for common SLO patterns including:
    - Keywords like "Student Learning Outcomes", "Learning Objectives"
    - Action verbs in bulleted lists
    - Structured learning outcome statements
    """

    # Detection Configuration Constants
    MAX_DOCUMENT_LENGTH = 20000
    MAX_CONTENT_LINES = 10
    MAX_CONTENT_LENGTH = 500

    # Scoring thresholds for header detection
    SCORE_STARTS_WITH_TITLE = 10
    SCORE_SHORT_LINE = 5
    SCORE_LONG_LINE_PENALTY = -5
    SCORE_HAS_COLON = 3
    SCORE_ALL_CAPS = 2
    MIN_SCORE_THRESHOLD = 5

    # Line length thresholds for header detection
    SHORT_LINE_THRESHOLD = 50
    LONG_LINE_THRESHOLD = 100
    MAX_EXTRA_WORDS_HEADER = 2
    MAX_EXTRA_WORDS_START = 4
    MAX_EXTRA_WORDS_END = 3

    # Section headers that indicate end of SLO content
    SECTION_HEADERS = [
        'course description', 'course objectives', 'course goals',
        'prerequisites', 'textbook', 'grading', 'schedule'
    ]

    def __init__(self):
        """Initialize the SLO detector with strict business rules."""
        self.field_name = 'slos'
        self.logger = logging.getLogger('detector.slos')

        # STRICT BUSINESS RULE: Only these specific titles are considered valid SLO sections
        # Must contain "Student Learning" or just "Learning" (without "Course")
        # "Course Objectives", "Course Goals", etc. are NOT valid SLO sections
        self.approved_titles = [
            "student learning outcomes",
            "student learning outcome",
            "student learning objectives",
            "student learning objective",
            "student/program learning outcomes",  # Program variant
            "learning outcomes",
            "learning outcome",
            "learning objectives",
            "learning objective"
        ]

        # Also accept abbreviated forms
        self.approved_abbreviations = [
            "slos",
            "slo"
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
        if len(text) > self.MAX_DOCUMENT_LENGTH:
            text = text[:self.MAX_DOCUMENT_LENGTH]
            self.logger.info(f"Truncated large document from {original_length} to {self.MAX_DOCUMENT_LENGTH} characters")

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

    def _simple_title_detection(self, text: str) -> Tuple[bool, str]:
        """
        Simple title-based SLO detection.
        Just looks for exact approved titles and extracts following content.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content)
        """
        lines = text.split('\n')

        # Find all potential matches first, then pick the best one
        potential_matches = []

        for i, line in enumerate(lines):
            line_normalized = line.strip().lower()
            line_without_punctuation = line_normalized.replace(':', '').replace('.', '').strip()

            # Check if any approved title appears properly (not just as part of a sentence)
            contains_approved_title = False
            for title in self.approved_titles:
                if title in line_without_punctuation:
                    # Additional check: line should be relatively short and not part of a long sentence
                    # or the title should be at the start/end of the line
                    line_words = line_without_punctuation.split()
                    title_words = title.split()

                    # Much stricter check: title must appear in header-like format
                    is_valid_header = False

                    # Case 1: Very short line (title + max 2 extra words) with proper formatting
                    if len(line_words) <= len(title_words) + self.MAX_EXTRA_WORDS_HEADER:
                        has_proper_formatting = (
                            ':' in line or                           # Has colon (section header)
                            line.strip().isupper() or              # All caps
                            (len(line_words) == len(title_words) and  # Exact title match
                             not line_normalized.endswith((',', ';', '.', '!', '?')))
                        )
                        if has_proper_formatting:
                            is_valid_header = True

                    # Case 2: Title at the very beginning of line (starts with title)
                    elif line_without_punctuation.startswith(title):
                        # But only if it looks like a header (has colon or is short)
                        if ':' in line or len(line_words) <= len(title_words) + self.MAX_EXTRA_WORDS_START:
                            is_valid_header = True

                    # Case 3: Title at the very end of line (ends with title)
                    elif line_without_punctuation.endswith(title):
                        # Only if it's a short line
                        if len(line_words) <= len(title_words) + self.MAX_EXTRA_WORDS_END:
                            is_valid_header = True

                    if is_valid_header:
                        contains_approved_title = True
                        break

            if contains_approved_title:
                # Score this match based on how likely it is to be a section header
                score = 0

                # Higher score for lines that start with approved titles
                starts_with_approved = False
                for title in self.approved_titles:
                    if line_without_punctuation.startswith(title):
                        starts_with_approved = True
                        break
                if starts_with_approved:
                    score += self.SCORE_STARTS_WITH_TITLE

                # Higher score for shorter lines (more likely to be headers)
                if len(line_without_punctuation) < self.SHORT_LINE_THRESHOLD:
                    score += self.SCORE_SHORT_LINE

                # Lower score for very long lines (likely mentions in text)
                if len(line_without_punctuation) > self.LONG_LINE_THRESHOLD:
                    score += self.SCORE_LONG_LINE_PENALTY

                # Higher score for lines with colons (section headers often have colons)
                if ':' in line:
                    score += self.SCORE_HAS_COLON

                # Higher score for lines in ALL CAPS
                if line.strip().isupper():
                    score += self.SCORE_ALL_CAPS

                potential_matches.append((score, i, line))

        # Sort by score (highest first) and pick the best match
        if potential_matches:
            potential_matches.sort(key=lambda x: x[0], reverse=True)
            best_score, best_i, best_line = potential_matches[0]

            # Only accept matches with a reasonable score (likely section headers)
            if best_score < self.MIN_SCORE_THRESHOLD:
                return False, ""

            # Extract content from the best match
            title = best_line.strip()
            content_lines = [title]
            content_length = len(title)

            for j in range(best_i + 1, min(best_i + self.MAX_CONTENT_LINES, len(lines))):
                if j >= len(lines):
                    break

                next_line = lines[j].strip()
                if not next_line:
                    continue

                # Stop if we hit another section title
                if any(section in next_line.lower() for section in self.SECTION_HEADERS):
                    break

                content_lines.append(next_line)
                content_length += len(next_line)

                # Stop after reasonable amount of content
                if content_length > self.MAX_CONTENT_LENGTH:
                    break

            content = '\n'.join(content_lines)
            return True, content

        return False, ""


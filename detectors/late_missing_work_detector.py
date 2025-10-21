"""
Late Missing Work Detector
=========================================

This detector identifies late work policies in syllabus documents.
It uses pattern matching and keyword detection to find late sections.

Developer Notes:
---------------
This is a simple example of a field detector. When creating new detectors,
use this as a template for structure and patterns.
"""

import re
import logging
from typing import Dict, Any, Tuple

# Detection Configuration Constants
MAX_DOCUMENT_LENGTH = 20000
MAX_CONTENT_LINES = 10
MAX_CONTENT_LENGTH = 500
MAX_EXTRA_WORDS_HEADER = 2
MAX_EXTRA_WORDS_START = 4
MAX_EXTRA_WORDS_END = 3

# Scoring thresholds for header detection
SCORE_STARTS_WITH_TITLE = 10
SCORE_SHORT_LINE = 5
SCORE_LONG_LINE_PENALTY = -5
SCORE_HAS_COLON = 3
SCORE_ALL_CAPS = 2
MIN_SCORE_THRESHOLD = 5
SHORT_LINE_THRESHOLD = 50
LONG_LINE_THRESHOLD = 100

# Section headers that indicate end of late work content
SECTION_HEADERS = [
    'course description', 'course objectives', 'course goals',
    'prerequisites', 'textbook', 'grading', 'schedule',
    'extra credit', 'attendance'
]


class LateDetector:
    """
    Detector for late work policies.

    This detector looks for common late patterns including:
    - Keywords like "late homework policy", "late assignments"
    - Action verbs in bulleted lists
    """

    def __init__(self):
        """Initialize the late detector."""
        self.field_name = 'late'
        self.logger = logging.getLogger('detector.late')

        # Approved titles for late missing work detection
        self.approved_titles = [
            "assessments",
            "assignment deadlines",
            "assignments",
            "attendance and late work",
            "expectations regarding assignment deadlines, late, or missing work",
            "grading (late policy: 10% deduction per day, up to 5 days)",
            "late assignments",
            "late assignments and make-up exams",
            "late homework policy",
            "late submissions",
            "late work",
            "late/make-up work",
            "makeups",
            "paper assignment / powerpoint presentations",
            "penalty for late assignments",
            "policy on attendance, late submissions",
            "policy on late submissions",
            "policy on late work",
            "summary/critique paper (late policy)"
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
        Detect late work policies in the text.
        Simplified approach: just look for specific approved titles.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with late content if found
        """
        self.logger.info("Starting simplified late detection")

        # Limit text size to prevent hanging on large documents
        original_length = len(text)
        if len(text) > MAX_DOCUMENT_LENGTH:
            text = text[:MAX_DOCUMENT_LENGTH]
            self.logger.info(f"Truncated large document from {original_length} to {MAX_DOCUMENT_LENGTH} characters")

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
                self.logger.info("SUCCESS: Found approved late title")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No approved late titles found")

            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            return result

        except Exception as e:
            self.logger.error(f"Error in late detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None
            }

    def _simple_title_detection(self, text: str) -> Tuple[bool, str]:
        """
        Simple title-based late detection.
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
            line_normalized = self._normalize_text(line.strip())
            line_without_punctuation = line_normalized.replace(':', '').replace('.', '').strip()

            # Check if any approved title appears properly (not just as part of a sentence)
            contains_approved_title = False
            for title in self.approved_titles:
                normalized_title = self._normalize_text(title)
                if normalized_title in line_without_punctuation:
                    # Additional check: line should be relatively short and not part of a long sentence
                    # or the title should be at the start/end of the line
                    line_words = line_without_punctuation.split()
                    title_words = normalized_title.split()

                    # Much stricter check: title must appear in header-like format
                    is_valid_header = False

                    # Case 1: Very short line (title + max 2 extra words) with proper formatting
                    if len(line_words) <= len(title_words) + MAX_EXTRA_WORDS_HEADER:
                        has_proper_formatting = (
                            ':' in line or                           # Has colon (section header)
                            line.strip().isupper() or              # All caps
                            (len(line_words) == len(title_words) and  # Exact title match
                             not line_normalized.endswith((',', ';', '.', '!', '?')))
                        )
                        if has_proper_formatting:
                            is_valid_header = True

                    # Case 2: Title at the very beginning of line (starts with title)
                    elif line_without_punctuation.startswith(normalized_title):
                        # But only if it looks like a header (has colon or is short)
                        if ':' in line or len(line_words) <= len(title_words) + MAX_EXTRA_WORDS_START:
                            is_valid_header = True

                    # Case 3: Title at the very end of line (ends with title)
                    elif line_without_punctuation.endswith(normalized_title):
                        # Only if it's a short line
                        if len(line_words) <= len(title_words) + MAX_EXTRA_WORDS_END:
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
                    normalized_title = self._normalize_text(title)
                    if line_without_punctuation.startswith(normalized_title):
                        starts_with_approved = True
                        break
                if starts_with_approved:
                    score += SCORE_STARTS_WITH_TITLE

                # Higher score for shorter lines (more likely to be headers)
                if len(line_without_punctuation) < SHORT_LINE_THRESHOLD:
                    score += SCORE_SHORT_LINE

                # Lower score for very long lines (likely mentions in text)
                if len(line_without_punctuation) > LONG_LINE_THRESHOLD:
                    score += SCORE_LONG_LINE_PENALTY

                # Higher score for lines with colons (section headers often have colons)
                if ':' in line:
                    score += SCORE_HAS_COLON

                # Higher score for lines in ALL CAPS
                if line.strip().isupper():
                    score += SCORE_ALL_CAPS

                potential_matches.append((score, i, line))

        # Sort by score (highest first) and pick the best match
        if potential_matches:
            potential_matches.sort(key=lambda x: x[0], reverse=True)
            best_score, best_i, best_line = potential_matches[0]

            # Only accept matches with a reasonable score (likely section headers)
            if best_score < MIN_SCORE_THRESHOLD:
                return False, ""

            # Extract content from the best match
            title = best_line.strip()
            content_lines = [title]
            content_length = len(title)

            for j in range(best_i + 1, min(best_i + MAX_CONTENT_LINES, len(lines))):
                if j >= len(lines):
                    break

                next_line = lines[j].strip()
                if not next_line:
                    continue

                # Stop if we hit another section title
                if any(section in next_line.lower() for section in SECTION_HEADERS):
                    break

                content_lines.append(next_line)
                content_length += len(next_line)

                # Stop after reasonable amount of content
                if content_length > MAX_CONTENT_LENGTH:
                    break

            content = '\n'.join(content_lines)
            return True, content

        return False, ""


"""
late missing work (late) Detector
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
from typing import Dict, Any


class lateDetector:
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

        # need to get approved titles for late missing work also include colons and without colons
        #may not need the colons if we are removing them in case 2
        #line_for_comparison seems to take out the colon so may not need them here
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

    def _simple_title_detection(self, text: str) -> tuple[bool, str]:
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
            line_clean = line.strip().lower()
            line_for_comparison = line_clean.replace(':', '').replace('.', '').strip()
#            clean_line = line.lower().rstrip(':').strip()

#            self.logger.info(f"line being compared {line_for_comparison} ")

            # Check if any approved title appears properly (not just as part of a sentence)
            contains_approved_title = False
            for title in self.approved_titles:
#                self.logger.info("line being compared")
                if title in line_for_comparison:
                    # Additional check: line should be relatively short and not part of a long sentence
                    # or the title should be at the start/end of the line
                    line_words = line_for_comparison.split()
                    title_words = title.split()

                    # Much stricter check: title must appear in header-like format
                    is_valid_header = False

                    # Case 1: Very short line (title + max 2 extra words) with proper formatting
                    if len(line_words) <= len(title_words) + 2:
                        has_proper_formatting = (
                            ':' in line or                           # Has colon (section header)
                            line.strip().isupper() or              # All caps
                            (len(line_words) == len(title_words) and  # Exact title match
                             not line_clean.endswith((',', ';', '.', '!', '?')))
                        )
                        if has_proper_formatting:
                            is_valid_header = True

                    # Case 2: Title at the very beginning of line (starts with title)
                    elif line_for_comparison.startswith(title):
                        # But only if it looks like a header (has colon or is short)
                        if ':' in line or len(line_words) <= len(title_words) + 4:
                            is_valid_header = True

                    # Case 3: Title at the very end of line (ends with title)
                    elif line_for_comparison.endswith(title):
                        # Only if it's a short line
                        if len(line_words) <= len(title_words) + 3:
                            is_valid_header = True

                    if is_valid_header:
#                        self.logger.info("contains approved title {line_for_comparison}")
                        contains_approved_title = True
                        break

            if contains_approved_title:
                # Score this match based on how likely it is to be a section header
                score = 0
#                self.logger.info("contains approved title {line_for_comparison}")
#            self.logger.info(f"line being compared {line_for_comparison} ")

                # Higher score for lines that start with approved titles
                starts_with_approved = False
                for title in self.approved_titles:
                    if line_for_comparison.startswith(title):
                        starts_with_approved = True
                        break
                if starts_with_approved:
                    score += 10

                # Higher score for shorter lines (more likely to be headers)
                if len(line_for_comparison) < 50:
                    score += 5

                # Lower score for very long lines (likely mentions in text)
                if len(line_for_comparison) > 100:
                    score -= 5

                # Higher score for lines with colons (section headers often have colons)
                if ':' in line:
                    score += 3

                # Higher score for lines in ALL CAPS
                if line.strip().isupper():
                    score += 2

                potential_matches.append((score, i, line))

        # Sort by score (highest first) and pick the best match
        if potential_matches:
            potential_matches.sort(key=lambda x: x[0], reverse=True)
            best_score, best_i, best_line = potential_matches[0]
#            self.logger.info(f"potential match has been entered ")

            # Only accept matches with a reasonable score (likely section headers)
            if best_score < 5:  # Minimum threshold to avoid false positives
                return False, ""

            # Extract content from the best match
            title = best_line.strip()
            content_lines = [title]
            content_length = len(title)

            for j in range(best_i + 1, min(best_i + 10, len(lines))):
                if j >= len(lines):
                    break

                next_line = lines[j].strip()
                if not next_line:
                    continue



# check this part to see if it makes sense for late missing work or if it needs to be adjusted
                # Stop if we hit another section title
                if any(section in next_line.lower() for section in
                       ['course description', 'course objectives', 'course goals',
                        'prerequisites', 'textbook', 'grading', 'schedule', 'extra credit', 'attendance']):
                    break

                content_lines.append(next_line)
                content_length += len(next_line)

                # Stop after reasonable amount of content
                if content_length > 500:
                    break

            content = '\n'.join(content_lines)
            return True, content

        return False, ""


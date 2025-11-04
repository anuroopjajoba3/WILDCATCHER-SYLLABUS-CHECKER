"""
Class Location Detector
=========================================

This detector identifies PHYSICAL classroom locations only.
Does NOT detect "Online" - that's handled by the modality detector.

Focus: Extract physical room/building where class meets in person.
For online-only courses, this detector returns empty (not found).
For hybrid courses, extracts the physical location component.

Examples of detected formats:
- "Room 105", "Rm 139, Pandora Mill building"
- "Hamilton Smith 129", "P380"
- "Classroom: 302"
"""

import re
import logging
import unicodedata
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Detection Configuration Constants
MAX_LINES_TO_SCAN = 150
CONTEXT_WINDOW_BEFORE = 2
CONTEXT_WINDOW_AFTER = 15  # Increased from 5 to handle form layouts with large gaps
HEADER_LINE_THRESHOLD = 20  # Lines considered part of header section
HEADER_CONFIDENCE_BOOST = 0.15  # Boost for locations in header
EXPLICIT_KEYWORD_BOOST = 0.25  # Boost for explicit location keywords (higher than header)

# Confidence levels
HIGH_CONFIDENCE = 0.95
MEDIUM_CONFIDENCE = 0.85
LOW_CONFIDENCE = 0.70


class ContextType(Enum):
    """Enumeration for context types to avoid magic strings."""
    CLASS = 'class'
    OFFICE = 'office'
    NEUTRAL = 'neutral'


@dataclass
class LocationCandidate:
    """Data class for location candidates to improve maintainability."""
    location: str
    confidence: float
    line_idx: int
    context_type: ContextType
    has_explicit_label: bool


class ClassLocationDetector:
    """
    Detector for physical class meeting locations.

    This detector looks for:
    - Physical locations: "Room 105", "Pandora Mill Rm 139", "Hamilton Smith 129"
    - Classroom designations: "Classroom: 302", "P380"

    Uses advanced disambiguation to distinguish between:
    - Class meeting location (what we want)
    - Office hours location (reject)
    - Instructor office location (reject)
    - Support/admin offices (reject)
    """

    def __init__(self):
        """Initialize the class location detector with disambiguation rules."""
        self.field_name = 'class_location'
        self.logger = logging.getLogger('detector.class_location')

        # POSITIVE indicators: class location section keywords
        self.class_location_keywords = [
            r'class\s+location',
            r'class\s+meets?',
            r'class\s+meeting',
            r'meeting\s+location',
            r'meeting\s+place',
            r'meeting\s+time\s+and\s+place',
            r'location\s+and\s+time',
            r'time\s+and\s+location',
            r'where\s+we\s+meet',
            r'where\s+the\s+class\s+meets',
            r'course\s+location',
            r'lecture\s+location',
            r'when\s+and\s+where',
            r'schedule\s+and\s+location',
            r'classroom',
            r'lecture\s+room',
        ]

        # NEGATIVE indicators: non-class location contexts (REJECT these)
        self.non_class_keywords = [
            r'office\s+hours?',
            r'office\s+location',
            r'instructor\s+office',
            r'professor\s+office',
            r'my\s+office',
            r'office\s+address',
            r'\boffice:',  # Simple "Office:" label
            r'instructor\s+location',
            r'contact\s+information',
            r'contact\s+info',
            r'tutoring\s+center',
            r'writing\s+center',
            r'help\s+center',
            r'support\s+center',
            r'academic\s+support',
            r'drop[-\s]in\s+hours',
            r'consultation\s+hours',
            r'availability',
            r'\blab:',  # Lab location (different from class)
            r'lab\s+location',
            r'lab\s+sessions?',
            # Support/Admin offices
            r'tech\s+consultancy',
            r'tech\s+consultant',
            r'workroom',
            r'student\s+tech',
            r'title\s+ix',
            r'deputy\s+intake',
            r'coordinator.*room',
            r'advisors?\s+office',
            r'loan.*laptop',
            r'borrow.*laptop',
        ]

        # PRE-COMPILED regex patterns for performance (compiled once at init)
        self.course_code_patterns = [
            re.compile(r'\b[A-Z]{2,4}\s+\d{3,4}[A-Z]?\b'),  # COMP 405, BIOL 413A
            re.compile(r'\b[A-Z]{2,4}-\d{3,4}[A-Z]?\b'),    # COMP-405
            re.compile(r'\b[A-Z]{2,4}\d{3,4}[A-Z]?\b'),     # COMP405
        ]

        # PRE-COMPILED room extraction patterns (performance optimization)
        # Format: (compiled_pattern, confidence_level)
        self.room_patterns = [
            # Pattern 1: "Room/Rm [Number]" possibly followed by building
            (re.compile(r'\b((?:room|rm\.?)\s+[A-Za-z]?\d{2,4}(?:\s*[,\-]?\s*[\w\s]+?(?:hall|building|bldg|mill|lab))?)\b', re.IGNORECASE),
             HIGH_CONFIDENCE),

            # Pattern 2: Known building name followed by room number
            (re.compile(r'\b((?:pandora|pandra|hamilton\s+smith|dimond|parsons|kingsbury|morse|rudman|murkland)'
                       r'(?:\s+mill|\s+hall|\s+building)?\s*[,\-]?\s*(?:room|rm\.?)?\s*[A-Za-z]?\d{2,4})\b', re.IGNORECASE),
             HIGH_CONFIDENCE),

            # Pattern 3: Just "Room [Number]" or "Rm [Number]"
            (re.compile(r'\b((?:room|rm\.?)\s+[A-Za-z]?\d{2,4})\b', re.IGNORECASE),
             LOW_CONFIDENCE),

            # Pattern 4: "Classroom: [Number]" or "Classroom [Number]"
            (re.compile(r'\b(classroom:?\s+[A-Za-z]?\d{2,4})\b', re.IGNORECASE),
             MEDIUM_CONFIDENCE),

            # Pattern 5: "Rm" or "Room" directly attached to number (no space)
            (re.compile(r'\b((?:room|rm)\.?[A-Za-z]?\d{2,4})\b', re.IGNORECASE),
             MEDIUM_CONFIDENCE),

            # Pattern 6: Single letter + 3-4 digits (like P380, R540)
            (re.compile(r'\b([A-Z]\d{3,4})\b'),
             MEDIUM_CONFIDENCE),
        ]

        # PRE-COMPILED patterns for context checking
        self.explicit_location_pattern = re.compile(r'\b(?:class\s+)?location\s*:', re.IGNORECASE)
        self.year_pattern = re.compile(r'\b20\d{2}\b')
        self.course_code_context_pattern = re.compile(r'[A-Z]{2,4}\s*$')
        self.room_normalize_pattern = re.compile(r'((?:room|rm)\.?)([A-Za-z]?\d)', re.IGNORECASE)

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching."""
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", text)
        t = re.sub(r'[ \t]+', ' ', t)
        return t.strip()

    def _check_line_context(self, lines: List[str], line_index: int) -> ContextType:
        """
        Check the context of a specific line by examining surrounding lines.
        Returns: ContextType enum value

        Priority:
        1. If CURRENT line has class keywords -> 'CLASS' (overrides everything)
        2. If CURRENT line has office keywords -> 'OFFICE' (reject)
        3. Check surrounding lines for context
        """
        if line_index >= len(lines):
            return ContextType.NEUTRAL

        current_line = lines[line_index].lower()

        # PRIORITY 1: Current line has explicit class location keywords -> ACCEPT as 'CLASS'
        for pattern in self.class_location_keywords:
            if re.search(pattern, current_line):
                return ContextType.CLASS

        # PRIORITY 2: Current line has office keywords -> REJECT as 'OFFICE'
        for pattern in self.non_class_keywords:
            if re.search(pattern, current_line):
                return ContextType.OFFICE

        # PRIORITY 3: Check surrounding lines for additional context
        start_idx = max(0, line_index - CONTEXT_WINDOW_BEFORE)
        end_idx = min(len(lines), line_index + CONTEXT_WINDOW_AFTER + 1)
        context_lines = lines[start_idx:end_idx]
        context_text = ' '.join(context_lines).lower()

        # Check if surrounding context mentions class keywords
        for pattern in self.class_location_keywords:
            if re.search(pattern, context_text):
                return ContextType.CLASS

        # Check if surrounding context is office-related
        # (but be less aggressive - only reject if office keywords are close)
        for pattern in self.non_class_keywords:
            if re.search(pattern, context_text):
                # Only reject if office keyword is in immediate context (within 1 line)
                immediate_context = ' '.join(lines[max(0, line_index-1):min(len(lines), line_index+2)]).lower()
                if re.search(pattern, immediate_context):
                    return ContextType.OFFICE

        return ContextType.NEUTRAL

    def _is_course_code(self, text: str) -> bool:
        """
        Check if text looks like a course code (e.g., COMP 405, BIOL 413, DATA 557).
        Uses pre-compiled patterns for performance.
        """
        for pattern in self.course_code_patterns:
            if pattern.search(text):
                return True
        return False

    def _extract_room_with_building(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Extract room number with optional building name.
        Returns (location_string, confidence) or None.

        Examples:
        - "Room 105" -> ("Room 105", 0.85)
        - "Rm 139, Pandora Mill building" -> ("Rm 139, Pandora Mill", 0.95)
        - "Hamilton Smith 129" -> ("Hamilton Smith 129", 0.90)
        - "P380" -> ("P380", 0.70)
        """
        for pattern, confidence in self.room_patterns:
            match = pattern.search(text)
            if match:
                location = match.group(1).strip()

                # REJECT if it looks like a course code
                if self._is_course_code(location):
                    continue

                # REJECT if it looks like a year (2020-2029, Fall 2025, etc.)
                if self.year_pattern.search(location):
                    continue

                # For pattern6 (single letter + digits), only accept if NOT a course code context
                if pattern == self.room_patterns[5][0]:  # Pattern 6
                    # Check if this is in a course code context (e.g., "COMP 405")
                    context_before = text[max(0, match.start()-10):match.start()]
                    if self.course_code_context_pattern.search(context_before):
                        continue  # Skip if preceded by capital letters (likely course code)

                # Clean up extra spaces and normalize format
                location = re.sub(r'\s+', ' ', location)
                # Add space after Rm/Room if missing: "Rm126" → "Rm 126"
                location = self.room_normalize_pattern.sub(r'\1 \2', location)
                return (location, confidence)

        return None

    def _find_all_location_candidates(self, lines: List[str]) -> List[LocationCandidate]:
        """
        Find all potential location candidates in the document.
        Returns list of LocationCandidate objects.
        """
        candidates = []

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check context of this line
            context_type = self._check_line_context(lines, i)

            # REJECT if in office/non-class context
            if context_type == ContextType.OFFICE:
                self.logger.debug(f"Line {i}: Rejected (office context) - {line[:50]}")
                continue

            # Check if line has a class location header/keyword
            has_class_header = any(
                re.search(pattern, line_lower)
                for pattern in self.class_location_keywords
            )

            # Check for EXPLICIT location labels (strongest signal)
            has_explicit_label = bool(self.explicit_location_pattern.search(line_lower))

            # Extract room from this line
            room_result = self._extract_room_with_building(line)
            if room_result:
                location, base_conf = room_result

                # Boost confidence if we have a positive class header
                if has_class_header or context_type == ContextType.CLASS:
                    confidence = HIGH_CONFIDENCE
                elif context_type == ContextType.NEUTRAL:
                    confidence = base_conf * 0.7  # Reduce for neutral context
                else:
                    confidence = base_conf

                candidate = LocationCandidate(
                    location=location,
                    confidence=confidence,
                    line_idx=i,
                    context_type=context_type,
                    has_explicit_label=has_explicit_label
                )
                candidates.append(candidate)
                self.logger.debug(f"Line {i}: Candidate '{location}' (conf: {confidence}, ctx: {context_type.value}, explicit: {has_explicit_label})")

        return candidates

    def _select_best_candidate(self, candidates: List[LocationCandidate]) -> Optional[Tuple[str, float]]:
        """
        Select the best location from multiple candidates.

        Prioritization (in order):
        1. Context type: CLASS > NEUTRAL > other
        2. Explicit keyword bonus: "Location: [room]" gets highest boost
        3. Header bonus: Locations in first HEADER_LINE_THRESHOLD lines get boost
        4. Confidence score (higher is better)
        5. Line index (earlier in document is better)
        """
        if not candidates:
            return None

        # Calculate scores for all candidates
        scored_candidates = []
        for candidate in candidates:
            # Priority 1: Context type (CLASS=0, NEUTRAL=1, other=2)
            if candidate.context_type == ContextType.CLASS:
                context_priority = 0
            elif candidate.context_type == ContextType.NEUTRAL:
                context_priority = 1
            else:
                context_priority = 2

            # Priority 2-4: Confidence with boosts
            adjusted_confidence = candidate.confidence

            # Explicit keyword boost (highest priority - stronger than header)
            if candidate.has_explicit_label:
                adjusted_confidence += EXPLICIT_KEYWORD_BOOST

            # Header boost (second priority)
            in_header = candidate.line_idx < HEADER_LINE_THRESHOLD
            if in_header:
                adjusted_confidence += HEADER_CONFIDENCE_BOOST

            # Create sort key
            sort_key = (context_priority, -adjusted_confidence, candidate.line_idx)
            scored_candidates.append((sort_key, candidate, in_header))

        # Sort by the key
        scored_candidates.sort(key=lambda x: x[0])

        # Get the best
        _, best_candidate, in_header = scored_candidates[0]

        self.logger.info(f"Best candidate: '{best_candidate.location}' at line {best_candidate.line_idx} "
                        f"(conf: {best_candidate.confidence}, ctx: {best_candidate.context_type.value}, "
                        f"explicit: {best_candidate.has_explicit_label}, in_header: {in_header})")
        self.logger.debug(f"Total candidates considered: {len(candidates)}")

        if len(scored_candidates) > 1:
            # Log runner-up for debugging
            _, runner_up, ru_header = scored_candidates[1]
            self.logger.debug(f"Runner-up: '{runner_up.location}' at line {runner_up.line_idx} "
                            f"(conf: {runner_up.confidence}, ctx: {runner_up.context_type.value}, "
                            f"explicit: {runner_up.has_explicit_label}, in_header: {ru_header})")

        return (best_candidate.location, best_candidate.confidence)

    def _find_location_in_document(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Search entire document for PHYSICAL class location only.
        Returns (location, confidence) or None.

        Strategy:
        1. Find ALL potential physical location candidates
        2. Filter out office/non-class contexts
        3. Score each candidate
        4. Select best candidate

        NOTE: Does NOT detect "Online" - that's the modality detector's job.
        For online-only courses, this returns None (not found).
        """
        lines = text.split('\n')[:MAX_LINES_TO_SCAN]

        # Find all physical location candidates with context analysis
        candidates = self._find_all_location_candidates(lines)

        # Select best candidate (only physical locations)
        if candidates:
            return self._select_best_candidate(candidates)

        # No physical location found - return None
        # (This is expected for online-only courses)
        return None

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect class meeting location in the text.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with location if found
                {
                    'field_name': 'class_location',
                    'found': bool,
                    'content': str or None,
                    'confidence': float
                }
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        # Input validation
        if not isinstance(text, str):
            self.logger.error(f"Invalid input type: {type(text)}, expected str")
            return self._not_found()

        if not text:
            return self._not_found()

        text = self._normalize_text(text)

        try:
            result = self._find_location_in_document(text)

            if result:
                location, confidence = result
                self.logger.info(f"FOUND: {self.field_name} = '{location}' (confidence: {confidence})")
                return {
                    'field_name': self.field_name,
                    'found': True,
                    'content': location,
                    'confidence': confidence
                }
            else:
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                return self._not_found()

        except (ValueError, AttributeError, re.error) as e:
            self.logger.error(f"Error in class location detection: {e}", exc_info=True)
            return self._not_found()

    def _not_found(self) -> Dict[str, Any]:
        """Return not found result."""
        return {
            'field_name': self.field_name,
            'found': False,
            'content': None,
            'confidence': 0.0
        }


if __name__ == "__main__":
    # Unit tests for class location detector
    # NOTE: This detector ONLY finds physical locations, not "Online"
    test_cases = [
        # Basic physical location detection
        ("Class Location: Room 105", "Simple class room", True, "Room 105"),
        ("Meeting Location: Rm 139, Pandora Mill building", "Room with building", True, "Rm 139"),
        ("Class meets in Hamilton Smith 129", "Building with room", True, "Hamilton Smith 129"),

        # Disambiguation tests - should find class room, not office
        ("Office Hours: Room 201\nClass Location: Room 105", "Distinguish office from class", True, "Room 105"),
        ("Instructor Office: Room 301\nOffice Hours: Room 301\nClass meets in Room 105",
         "Multiple rooms - pick class", True, "Room 105"),
        ("Contact Info\nEmail: prof@unh.edu\nOffice: Room 201", "Only office location", False, None),

        # Online courses - should return NOT FOUND (physical location only)
        ("This course is fully online via Zoom", "Online with platform", False, None),
        ("100% online - no classroom meetings", "Definitive online statement", False, None),
        ("Location: Online", "Online explicit", False, None),

        # Complex syllabus structure
        ("Instructor: Dr. Smith\nOffice: Hamilton Smith 201\nOffice Hours: MWF 2-3pm\n\n"
         "Class Schedule:\nLocation: Kingsbury Hall 101\nTime: TR 10-11:30am",
         "Complex syllabus structure", True, "Kingsbury Hall 101"),

        # Edge cases
        ("Lab: Room 205\nTutoring Center: Room 110\nClass Location: Room 105",
         "Multiple non-class locations", True, "Room 105"),
    ]

    detector = ClassLocationDetector()
    print("Testing Class Location Detector (Physical Locations Only):")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_text, description, should_find, expected_content in test_cases:
        result = detector.detect(test_text)
        found = result.get('found', False)
        content = result.get('content')

        # Check if result matches expectation
        success = (found == should_find)
        if should_find and expected_content:
            success = success and (expected_content in str(content) if content else False)

        status = "[PASS]" if success else "[FAIL]"
        if success:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} - Test: {description}")
        print(f"  Input: {test_text[:60].replace(chr(10), ' | ')}...")
        print(f"  Expected: Found={should_find}, Content={expected_content}")
        print(f"  Got:      Found={found}, Content={content}")

    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"Success rate: {passed/len(test_cases)*100:.1f}%")

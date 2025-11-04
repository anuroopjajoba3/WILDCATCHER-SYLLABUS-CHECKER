"""
Assignment Types Title Detector - FIXED
"""
import re
from typing import Dict, Any

class AssignmentTypesDetector:
    """Detector for assignment types section titles in syllabi"""
    
    def __init__(self):
        # Exact patterns - must be standalone
        self.exact_patterns = [
            (r'(?i)^\s*assignments?\s*&\s*grades?\s*:?\s*$', 150),
            (r'(?i)^\s*assignments?\s*&\s*grading\s*:?\s*$', 150),
            (r'(?i)^\s*textbook\s+chapter\s+quizzes\s*,?\s*discussions', 140),
            (r'(?i)^\s*methods\s+of\s+testing\s+/\s+evaluation\s*:?\s*$', 135),
            (r'(?i)^\s*course\s+requirements?\s+and\s+assessments?\s+overview\s*:?\s*$', 135),
            (r'(?i)^\s*required\s+paperwork\s+and\s+submissions?\s*\.?\s*$', 130),
            (r'(?i)^\s*assignments?\s+and\s+course\s+specific\s+policies\s*:?\s*$', 130),
            (r'(?i)^\s*assignment\s+and\s+grading\s+details?\s+lab\s*:?\s*$', 125),
            (r'(?i)^\s*summary\s+of\s+student\s+evaluation\s*:?\s*$', 120),
            (r'(?i)^\s*methods\s*,\s*grade\s+components', 115),
        ]
        
        # Multiword patterns - standalone (higher score)
        # Added pattern to capture titles with weights like "Homework Problems (10%)"
        self.multiword_standalone = [
            (r'(?i)^\s*homework\s+assignments?\s+and\s+projects?\s*(?:\([^)]+\))?\s*:?\s*$', 112),  # ADDED - compound title
            (r'(?i)^\s*reading\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 110),  # ADDED
            (r'(?i)^\s*laboratory\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 110),  # ADDED
            (r'(?i)^\s*lab\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 110),
            (r'(?i)^\s*homework\s+problems\s*(?:\([^)]+\))?\s*:?\s*$', 110),
            (r'(?i)^\s*homework\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 110),
            (r'(?i)^\s*course\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 108),
            (r'(?i)^\s*class\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$', 108),
            (r'(?i)^\s*assessment\s+overview\s*:?\s*$', 106),
            (r'(?i)^\s*major\s+projects?\s*:?\s*$', 105),
            (r'(?i)^\s*course\s+activities\s*:?\s*$', 105),
            (r'(?i)^\s*assignment\s+details?\s*:?\s*$', 102),
            (r'(?i)^\s*quizzes\s+and\s+exams?\s*:?\s*$', 100),
            (r'(?i)^\s*assignments?\s+and\s+grading\s*:?\s*$', 98),
            (r'(?i)^\s*student\s+evaluation\s*:?\s*$', 90),
            (r'(?i)^\s*assessment\s*,\s*participation\s+assignments?\s*:?\s*$', 88),
        ]
        
        # Multiword patterns - with content after (lower score, extract header only)
        self.multiword_with_content = [
            (r'(?i)^\s*(homework\s+assignments?\s+and\s+projects?)\s*(?:\([^)]+\))?\s*:', 87),  # ADDED
            (r'(?i)^\s*(reading\s+assignments?)\s*(?:\([^)]+\))?\s*:', 85),  # ADDED
            (r'(?i)^\s*(laboratory\s+assignments?)\s*(?:\([^)]+\))?\s*:', 85),  # ADDED
            (r'(?i)^\s*(lab\s+assignments?)\s*(?:\([^)]+\))?\s*:', 85),
            (r'(?i)^\s*(homework\s+problems)\s*(?:\([^)]+\))?\s*:', 85),
            (r'(?i)^\s*(homework\s+assignments?)\s*(?:\([^)]+\))?\s*:', 85),
            (r'(?i)^\s*(course\s+assignments?)\s*:', 83),
            (r'(?i)^\s*(class\s+assignments?)\s*:', 83),
            (r'(?i)^\s*(assessment\s+overview)\s*:', 81),
            (r'(?i)^\s*(major\s+projects?)\s*:', 80),
            (r'(?i)^\s*(course\s+activities)\s*:', 80),
            (r'(?i)^\s*(assignment\s+details?)\s*:', 77),
            (r'(?i)^\s*(quizzes\s+and\s+exams?)\s*:', 75),
            (r'(?i)^\s*(assignments?\s+and\s+grading)\s*:', 73),
            (r'(?i)^\s*(methods\s+of\s+testing\s*/\s*evaluation)\s*:', 130),  # For ANTH 411W
        ]
        
        # Singleword patterns - standalone (higher score)
        self.singleword_standalone = [
            (r'(?i)^\s*assessment\s*:?\s*$', 70),
            (r'(?i)^\s*homework\s*(?:\([^)]+\))?\s*:?\s*$', 65),
            (r'(?i)^\s*assignments?\s*:?\s*$', 60),
            (r'(?i)^\s*evaluation\s*:?\s*$', 50),
        ]
        
        # Singleword patterns - with content after (lower score, extract header only)
        self.singleword_with_content = [
            (r'(?i)^\s*(assessment)\s*:', 55),
            (r'(?i)^\s*(homework)\s*(?:\([^)]+\))?\s*:', 50),
            (r'(?i)^\s*(assignments?)\s*:', 45),
        ]
        
        self.schedule_patterns = [
            r'(?i)week\s*#?\d+',
            r'(?i)homework\s*:\s*(reading|complete|work\s+on|finish|continue|start)',
            r'(?i)due\s+(by\s+)?next\s+week',
            r'(?i)lecture\s*[-–]\s*review',
        ]
        
        # CRITICAL: Patterns to EXCLUDE - these belong to grading_procedures_title, NOT assignment_types_title
        self.exclude_patterns = [
            r'(?i)grading\s+and\s+evaluation\s+of\s+student\s+work',
            r'(?i)evaluation\s+of\s+student\s+work',
            r'(?i)grading\s+policy',
            r'(?i)grading\s+procedure',
            r'(?i)grading\s+distribution',
            r'(?i)grading\s+scale',
            r'(?i)grade\s+distribution',
            r'(?i)final\s+grade\s+(calculation|scale)',
            r'(?i)course\s+grading',
            r'(?i)rubric\s+and\s+evaluation',
        ]
    
    def _is_in_schedule(self, line: str, context: str) -> bool:
        """Check if line is part of a schedule/timeline section"""
        for p in self.schedule_patterns:
            if re.search(p, line):
                return True
        context_lower = context.lower()
        for kw in ['week #', 'homework: reading', 'due by next week']:
            if kw in context_lower:
                return True
        return False
    
    def _should_exclude(self, line: str) -> bool:
        """
        Check if line should be excluded because it's a grading section header.
        These belong to grading_procedures_title, not assignment_types_title.
        """
        line_lower = line.lower().strip()
        
        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, line_lower):
                return True
        
        # Additional heuristic: if line contains "grading" and "evaluation", it's likely grading_procedures
        if 'grading' in line_lower and 'evaluation' in line_lower:
            return True
            
        return False
    
    def _normalize_title(self, line: str) -> str:
        """
        Normalize title by removing weight/percentage information in parentheses.
        Example: "Homework Problems (10%)" -> "Homework Problems"
        """
        # Remove content in parentheses (usually percentages/weights)
        line = re.sub(r'\s*\([^)]+\)\s*', ' ', line)
        # Clean up whitespace
        line = ' '.join(line.split())
        return line.strip()
    
    def _is_valid_with_content(self, line: str) -> bool:
        """Check if a line with content after the header is valid"""
        # Line shouldn't be too long
        if len(line) > 200:
            return False
        # Should not be schedule-like
        if re.search(r'(?i)(reading|complete|work\s+on|due|week\s+\d+)', line):
            return False
        return True
    
    def detect(self, text: str) -> Dict[str, Any]:
        """Detect assignment types section title"""
        if not text:
            return {"found": False, "content": ""}
        
        lines = text.split("\n")
        candidates = []
        
        for i, line in enumerate(lines):
            l = line.strip()
            
            # Skip invalid line lengths
            if len(l) < 2 or len(l) > 250:
                continue
            
            # CRITICAL: Skip if this is a grading-related header (MUST CHECK FIRST)
            if self._should_exclude(l):
                continue
            
            # Get context for schedule detection
            start, end = max(0, i - 5), min(len(lines), i + 6)
            context = " ".join(lines[start:end])
            
            # Skip if in schedule section
            if self._is_in_schedule(l, context):
                continue
            
            # Try exact patterns first
            for pat, score in self.exact_patterns:
                if re.match(pat, l):
                    candidates.append({"content": l, "score": score, "line": i})
                    break
            else:
                # Try multiword standalone patterns
                for pat, score in self.multiword_standalone:
                    if re.match(pat, l):
                        # Normalize the title to remove weight info
                        normalized = self._normalize_title(l)
                        candidates.append({"content": normalized, "score": score, "line": i})
                        break
                else:
                    # Try multiword with content patterns
                    matched = False
                    for pat, score in self.multiword_with_content:
                        match = re.match(pat, l)
                        if match and self._is_valid_with_content(l):
                            # Extract just the header part (group 1 + colon)
                            header = match.group(1) + ":"
                            candidates.append({"content": header, "score": score, "line": i})
                            matched = True
                            break
                    
                    if not matched:
                        # Try singleword standalone patterns
                        for pat, score in self.singleword_standalone:
                            if re.match(pat, l):
                                # Normalize the title to remove weight info
                                normalized = self._normalize_title(l)
                                candidates.append({"content": normalized, "score": score, "line": i})
                                matched = True
                                break
                        
                        if not matched:
                            # Try singleword with content patterns
                            for pat, score in self.singleword_with_content:
                                match = re.match(pat, l)
                                if match and self._is_valid_with_content(l):
                                    # Extract just the header part (group 1 + colon)
                                    header = match.group(1) + ":"
                                    candidates.append({"content": header, "score": score, "line": i})
                                    break
        
        if candidates:
            # Return highest scoring candidate
            best = max(candidates, key=lambda x: (x["score"], -x["line"]))
            return {"found": True, "content": best["content"]}
        
        return {"found": False, "content": ""}


def detect_assignment_types_title(text: str) -> str:
    """Standalone convenience function."""
    detector = AssignmentTypesDetector()
    result = detector.detect(text)
    return result.get("content", "") if result.get("found") else "Missing"
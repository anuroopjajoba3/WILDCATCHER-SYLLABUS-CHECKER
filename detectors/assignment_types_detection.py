"""
Assignment Types Title Detector - FIXED VERSION
Returns the section TITLE/HEADER, not the list of assignments
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
            (r'(?i)^\s*grading\s+and\s+evaluation\s+of\s+student\s+work\s*:?\s*$', 125),
            (r'(?i)^\s*assignment\s+and\s+grading\s+details?\s+lab\s*:?\s*$', 125),
            (r'(?i)^\s*summary\s+of\s+student\s+evaluation\s*:?\s*$', 120),
            (r'(?i)^\s*methods\s*,\s*grade\s+components', 115),
            (r'(?i)^\s*grading\s+scheme\s*:?\s*$', 160),
            (r'(?i)^\s*grading\s+breakdown\s*:?\s*$', 155),
            (r'(?i)^\s*grade\s+distribution\s*:?\s*$', 155),
            (r'(?i)^\s*grade\s+composition\s*:?\s*$', 150),
            (r'(?i)^\s*grading\s+components?\s*:?\s*$', 150),
        ]
        
        # Multiword patterns - standalone (higher score)
        self.multiword_standalone = [
            (r'(?i)^\s*homework\s+assignments?\s*:?\s*$', 110),
            (r'(?i)^\s*course\s+assignments?\s*:?\s*$', 108),
            (r'(?i)^\s*class\s+assignments?\s*:?\s*$', 108),
            (r'(?i)^\s*major\s+projects?\s*:?\s*$', 105),
            (r'(?i)^\s*course\s+activities\s*:?\s*$', 105),
            (r'(?i)^\s*assignment\s+details?\s*:?\s*$', 102),
            (r'(?i)^\s*quizzes\s+and\s+exams?\s*:?\s*$', 100),
            (r'(?i)^\s*assignments?\s+and\s+grading\s*:?\s*$', 98),
            (r'(?i)^\s*grading\s+distribution\s*:?\s*$', 95),
            (r'(?i)^\s*student\s+evaluation\s*:?\s*$', 90),
            (r'(?i)^\s*assessment\s*,\s*participation\s+assignments?\s*:?\s*$', 88),
        ]
        
        # Multiword patterns - with content after (lower score, extract header only)
        self.multiword_with_content = [
            (r'(?i)^\s*(homework\s+assignments?)\s*:', 85),
            (r'(?i)^\s*(course\s+assignments?)\s*:', 83),
            (r'(?i)^\s*(class\s+assignments?)\s*:', 83),
            (r'(?i)^\s*(major\s+projects?)\s*:', 80),
            (r'(?i)^\s*(course\s+activities)\s*:', 80),
            (r'(?i)^\s*(assignment\s+details?)\s*:', 77),
            (r'(?i)^\s*(quizzes\s+and\s+exams?)\s*:', 75),
            (r'(?i)^\s*(assignments?\s+and\s+grading)\s*:', 73),
            (r'(?i)^\s*(methods\s+of\s+testing\s*/\s*evaluation)\s*:', 130),
        ]
        
        # Singleword patterns - standalone (higher score)
        self.singleword_standalone = [
            (r'(?i)^\s*assessment\s*:?\s*$', 70),
            (r'(?i)^\s*homework\s*:?\s*$', 65),
            (r'(?i)^\s*assignments?\s*:?\s*$', 60),
            (r'(?i)^\s*grades?\s*:?\s*$', 60),
            (r'(?i)^\s*evaluation\s*:?\s*$', 50),
        ]
        
        # Singleword patterns - with content after (lower score, extract header only)
        self.singleword_with_content = [
            (r'(?i)^\s*(assessment)\s*:', 55),
            (r'(?i)^\s*(homework)\s*:', 50),
            (r'(?i)^\s*(assignments?)\s*:', 45),
            (r'(?i)^\s*(grades?)\s*:', 45),
        ]
        
        self.schedule_patterns = [
            r'(?i)week\s*#?\d+',
            r'(?i)homework\s*:\s*(reading|complete|work\s+on|finish|continue|start)',
            r'(?i)due\s+(by\s+)?next\s+week',
            r'(?i)lecture\s*[-–]\s*review',
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
        """Detect assignment types section TITLE/HEADER"""
        if not text:
            return {"found": False, "content": "Missing"}
        
        lines = text.split("\n")
        candidates = []
        
        for i, line in enumerate(lines):
            l = line.strip()
            
            # Skip invalid line lengths
            if len(l) < 2 or len(l) > 250:
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
                    candidates.append({"line_idx": i, "score": score, "content": l})
                    break
            else:
                # Try multiword standalone patterns
                for pat, score in self.multiword_standalone:
                    if re.match(pat, l):
                        candidates.append({"line_idx": i, "score": score, "content": l})
                        break
                else:
                    # Try multiword with content patterns
                    matched = False
                    for pat, score in self.multiword_with_content:
                        match = re.match(pat, l)
                        if match and self._is_valid_with_content(l):
                            # Extract just the header part (group 1)
                            header = match.group(1) + ":"
                            candidates.append({"line_idx": i, "score": score, "content": header})
                            matched = True
                            break
                    
                    if not matched:
                        # Try singleword standalone patterns
                        for pat, score in self.singleword_standalone:
                            if re.match(pat, l):
                                candidates.append({"line_idx": i, "score": score, "content": l})
                                matched = True
                                break
                        
                        if not matched:
                            # Try singleword with content patterns
                            for pat, score in self.singleword_with_content:
                                match = re.match(pat, l)
                                if match and self._is_valid_with_content(l):
                                    # Extract just the header part (group 1)
                                    header = match.group(1) + ":"
                                    candidates.append({"line_idx": i, "score": score, "content": header})
                                    break
        
        if candidates:
            # Return highest scoring candidate - just the section TITLE
            best = max(candidates, key=lambda x: (x["score"], -x["line_idx"]))
            
            return {
                "found": True,
                "content": best["content"]  # Return the section title/header
            }
        
        return {"found": False, "content": "Missing"}


def detect_assignment_types_title(text: str) -> str:
    """
    Standalone convenience function.
    
    Returns: The section title/header or "Missing" if not found
    Example: "Assignments:", "Homework:", "Required Paperwork and Submissions."
    """
    detector = AssignmentTypesDetector()
    result = detector.detect(text)
    return result.get("content", "Missing")
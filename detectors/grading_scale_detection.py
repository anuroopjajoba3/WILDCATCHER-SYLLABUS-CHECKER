"""Grading scale detector (strict):
This detector only looks for canonical A..F letter->numeric range mappings
and returns a normalized canonical string when a conservative match is found.

It intentionally does NOT attempt to extract broader grading procedure text
such as grouped percentage lists or letter-blocks; those belong in the
separate grading_process_detection detector.
"""

from typing import Dict, Any
import re


# Detection Configuration Constants
MAX_HEADING_SCAN_LINES = 8
MAX_HEADING_WORDS_CAPS = 12
MAX_HEADING_WORDS_ANCHOR = 15
MAX_HEADING_WORDS_TITLE = 10
MIN_TITLE_CASE_CAPS = 2
MIN_REQUIRED_LETTER_GRADES = 4  # Lowered to be more lenient - just need A, B, C, F minimum
MIN_WINDOW_SCORE = 2
MAX_SHORT_LINE_WORDS = 15
MAX_SHORT_LINE_LENGTH = 120
MAX_NEXT_LINE_WORDS = 20
MAX_UPWARD_SCAN = 7
MAX_DOWNWARD_SCAN = 9
MAX_FORWARD_SCAN = 7
PERCENT_CLUSTER_WINDOW = 3


class GradingScaleDetector:
    """Detects canonical letter->range mappings (A..F) and returns
    a normalized canonical string when a conservative match is found.
    """

    def __init__(self):
        # Multiple patterns for different grading scale formats
        self.patterns = [
            # Pattern 1: "A: 93 - 100", "A = 94-100" 
            re.compile(r"(?P<letter>[A-F][+-]?)\s*[:=]\s*(?P<low>\d{1,3}(?:\.\d+)?)\s*[-\u2013\u2014to]+\s*(?P<high>\d{1,3}(?:\.\d+)?)", re.I),
            
            # Pattern 2: "94-100=A", "93.0-100.0 = A"
            re.compile(r"(?P<low>\d{1,3}(?:\.\d+)?)\s*[-\u2013\u2014to]+\s*(?P<high>\d{1,3}(?:\.\d+)?)\s*[=:]\s*(?P<letter>[A-F][+-]?)", re.I),
            
            # Pattern 3: "A 100 % to 94 %", "A- < 94 % to 90 %"  
            re.compile(r"(?P<letter>[A-F][+-]?)\s*<?<?\s*(?P<high>\d{1,3}(?:\.\d+)?)\s*%\s*to\s*(?P<low>\d{1,3}(?:\.\d+)?)\s*%", re.I),
            
            # Pattern 4: "F: 59.9 or below", "F < 60"
            re.compile(r"(?P<letter>F[+-]?)\s*[:<]\s*(?P<threshold>\d{1,3}(?:\.\d+)?)\s*(?:%?\s*(?:or\s+below|and\s+below)?)", re.I),
            
            # Pattern 5: "Below 60=F"
            re.compile(r"(?:Below|Under)\s+(?P<threshold>\d{1,3}(?:\.\d+)?)\s*[=:]\s*(?P<letter>F[+-]?)", re.I),
            
            # Pattern 6: "A: 93% – 100%" (with percentages and em dash)
            re.compile(r"(?P<letter>[A-F][+-]?)\s*:\s*(?P<low>\d{1,3}(?:\.\d+)?)%\s*[–\u2013\u2014-]+\s*(?P<high>\d{1,3}(?:\.\d+)?)%", re.I),
            
            # Pattern 7: "F = below 60" (F grade with "below" threshold)
            re.compile(r"(?P<letter>F[+-]?)\s*=\s*below\s+(?P<threshold>\d{1,3}(?:\.\d+)?)", re.I),
            
            # Pattern 8: "90% to 100% | A" (percentage ranges with pipe separator) - more specific
            re.compile(r"(?P<low>\d{2,3})%\s+to\s+(?P<high>\d{2,3})%\s*\|\s*(?P<letter>[A-F][+-]?)(?=\s|$|\n)", re.I),
        ]
        
        # Pattern for horizontal table format: "A A- B+ B B- C+ C C- D+ D D- F\n93 90 87 83 80 77 73 70 67 63 60 <60"
        self.horizontal_table_pattern = re.compile(
            r"([A-F][+-]?(?:\s+[A-F][+-]?)*)\s*\n\s*(\d+(?:\s+\d+)*(?:\s*<?<?\d+)?)", 
            re.MULTILINE | re.IGNORECASE
        )
        
        # Alternative horizontal pattern with pipes/bars: "A | A- | B+ | B | B- | C+ | C | C- | D+ | D | D- | F\n93 90 87..."
        self.horizontal_pipe_pattern = re.compile(
            r"([A-F][+-]?(?:\s*\|\s*[A-F][+-]?)*)\s*\n\s*(.+)", 
            re.MULTILINE | re.IGNORECASE
        )
        
        # Inline multiple grades pattern: "94-100 A (4.0) Excellent, 90-93 A- (3.67), 87-89 B+ (3.33)"
        self.inline_grades_pattern = re.compile(
            r"(?:\d+\s*[-\u2013\u2014]+\s*\d+\s+[A-F][+-]?\s+\(?\d\.\d+\)?(?:\s+\w+)?[,\s]*)+",
            re.IGNORECASE
        )

        # preferred canonical ordering for output
        self.canonical_order = [
            'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'
        ]

    @staticmethod
    def _normalize_number(s: str) -> str:
        try:
            f = float(s)
            # prefer integer form when appropriate
            return str(int(f)) if f.is_integer() else str(int(round(f)))
        except Exception:
            return s.strip()
    
    def _parse_horizontal_table(self, text: str) -> dict:
        """Parse horizontal table format: grades on one line, thresholds on next line"""
        match = self.horizontal_table_pattern.search(text)
        is_pipe_format = False
        
        if not match:
            # Try pipe-separated format
            match = self.horizontal_pipe_pattern.search(text)
            if not match:
                return {}
            is_pipe_format = True
        
        grades_line = match.group(1).strip()
        numbers_line = match.group(2).strip()
        
        if is_pipe_format:
            # Handle pipe-separated format for grades
            grades = [g.strip().upper() for g in grades_line.split('|') if g.strip()]
            # Check if numbers are also pipe-separated or space-separated
            if '|' in numbers_line:
                numbers = [n.strip() for n in numbers_line.split('|') if n.strip()]
            else:
                # Numbers are space-separated even though grades were pipe-separated
                numbers = []
                for num_str in re.split(r'\s+', numbers_line):
                    num_str = num_str.strip()
                    if not num_str:
                        continue
                    # Remove < or <= prefix and extract number
                    clean_num = re.sub(r'^<?<?', '', num_str)
                    numbers.append(clean_num)
        else:
            # Handle space-separated format
            grades = [g.strip().upper() for g in re.split(r'\s+', grades_line) if g.strip()]
            numbers = []
            
            # Handle numbers including special cases like "<60"
            for num_str in re.split(r'\s+', numbers_line):
                num_str = num_str.strip()
                if not num_str:
                    continue
                # Remove < or <= prefix and extract number
                clean_num = re.sub(r'^<?<?', '', num_str)
                numbers.append(clean_num)
        
        # Convert numbers to floats for processing
        numeric_values = []
        for num_str in numbers:
            try:
                # Handle special case of "<60" - extract just the number
                clean_num = re.sub(r'^<?<?', '', num_str)
                numeric_values.append(float(clean_num))
            except ValueError:
                continue
        
        # Allow for one fewer number if we have F grade (F can go to 0)
        if len(grades) != len(numeric_values) and len(grades) != len(numeric_values) + 1:
            return {}
        
        # Build ranges: each grade gets from its threshold to the previous one (or 100 for A)
        found_ranges = {}
        for i, grade in enumerate(grades):
            # Skip if we don't have a corresponding number for this grade
            if i >= len(numeric_values):
                # Special case for F grade when we don't have its threshold
                if grade == 'F' and i > 0:
                    found_ranges[grade] = "0-59"
                continue
                
            if i == 0:  # First grade (usually A) goes to 100
                low = str(int(numeric_values[i]))
                high = "100"
            else:
                low = str(int(numeric_values[i]))
                # High is previous threshold - 1 (for integer thresholds)
                prev_threshold = numeric_values[i-1]
                high = str(int(prev_threshold - 1))
            
            # Special case for F grade - goes down to 0
            if grade == 'F':
                low = "0"
                high = str(int(numeric_values[i] - 1)) if i < len(numeric_values) else "59"
            
            found_ranges[grade] = f"{low}-{high}"
        
        return found_ranges

    def _parse_inline_grades(self, text: str) -> dict:
        """Parse inline grades format: '94-100 A 4.0 90-93 A- 3.67 87-89 B+ 3.33'"""
        match = self.inline_grades_pattern.search(text)
        if not match:
            return {}
        
        inline_text = match.group(0)
        found_ranges = {}
        
        # Pattern to extract individual grade entries (handles optional descriptive words like "Superior")
        grade_entry_pattern = re.compile(r"(\d+)\s*[-\u2013\u2014]+\s*(\d+)\s+([A-F][+-]?)\s+\d\.\d+(?:\s+\w+)?", re.IGNORECASE)
        
        for entry_match in grade_entry_pattern.finditer(inline_text):
            low = entry_match.group(1)
            high = entry_match.group(2)
            grade = entry_match.group(3).upper()
            found_ranges[grade] = f"{low}-{high}"
        
        return found_ranges

    def _find_grade_cluster(self, text: str) -> str:
        """Find clusters of A-F grade letters (excluding E) with +/- and return exactly what's found.
        Allows up to 5 characters between grade letters. Stops after F and includes 2 numbers after F."""
        
        # Pattern to match grade clusters: A-F (excluding E) with optional +/-, allowing up to 5 chars between grades
        # This will capture sequences like "A A- B+ B B- C+ C C- D+ D D- F" with various separators
        cluster_pattern = re.compile(
            r'([A-DF][+-]?)(?:.{0,5}([A-DF][+-]?))*(?:.{0,5}F[+-]?)?(?:\s*\d+(?:\.\d+)?){0,2}',
            re.IGNORECASE
        )
        
        # Look for sequences that contain multiple grades including F
        matches = []
        for match in cluster_pattern.finditer(text):
            match_text = match.group(0)
            
            # Count unique grade letters in this match (excluding E)
            grade_letters = set()
            grade_pattern = re.compile(r'\b([A-DF][+-]?)\b', re.IGNORECASE)
            for grade_match in grade_pattern.finditer(match_text):
                grade = grade_match.group(1).upper()
                if grade not in ['E', 'E+', 'E-']:  # Exclude E grades
                    grade_letters.add(grade)
            
            # Must have F and at least 4 different grades total
            if 'F' in grade_letters and len(grade_letters) >= 4:
                # Must have some A variant (A+, A, or A-)
                has_a_grade = any(g.startswith('A') for g in grade_letters)
                if has_a_grade:
                    matches.append((match.start(), match_text.strip()))
        
        if not matches:
            return ""
        
        # Return the longest/most complete match found
        best_match = max(matches, key=lambda x: len(x[1]))
        return best_match[1]

    def detect(self, text: str) -> Dict[str, Any]:
        """Return {'found': bool, 'content': canonical-string-or-empty}.

        Conservative criteria: require both 'A' and 'F' keys and at least
        MIN_REQUIRED_LETTER_GRADES distinct letter mappings before returning
        a canonical scale. This avoids returning partial/incomplete scales.
        """
        if not text:
            return {'found': False, 'content': ''}

        found_ranges = {}
        
        # First try horizontal table format
        horizontal_ranges = self._parse_horizontal_table(text)
        if horizontal_ranges and 'A' in horizontal_ranges and 'F' in horizontal_ranges:
            found_ranges.update(horizontal_ranges)
        
        # Try inline grades format if horizontal table didn't find a complete scale
        if len(found_ranges) < 4:  # If we don't have at least 4 grades, try inline
            inline_ranges = self._parse_inline_grades(text)
            if inline_ranges and len(inline_ranges) > len(found_ranges):
                # Use inline if it found more grades
                if 'A' in inline_ranges and 'F' in inline_ranges:
                    found_ranges = inline_ranges  # Replace rather than update
        
        # Try each pattern on the text
        for pattern in self.patterns:
            for m in pattern.finditer(text):
                letter = None
                low = None
                high = None
                
                if 'letter' in m.groupdict() and m.group('letter'):
                    letter = m.group('letter').upper().replace('\u2212', '-')
                    
                    # Handle different pattern types
                    if 'low' in m.groupdict() and 'high' in m.groupdict():
                        # Standard range patterns
                        if m.group('low') and m.group('high'):
                            low = self._normalize_number(m.group('low'))
                            high = self._normalize_number(m.group('high'))
                        elif 'threshold' in m.groupdict() and m.group('threshold'):
                            # F: below threshold patterns
                            threshold = self._normalize_number(m.group('threshold'))
                            if letter == 'F':
                                low = "0"
                                high = threshold
                    elif 'threshold' in m.groupdict() and m.group('threshold'):
                        # F: below threshold patterns (including "F = below 60")
                        threshold = self._normalize_number(m.group('threshold'))
                        if letter == 'F':
                            low = "0"
                            # For "below X", the range is 0 to X-1 (or 0 to X)
                            try:
                                high = str(int(float(threshold)) - 1)
                            except:
                                high = threshold
                
                if letter and low is not None and high is not None:
                    # Ensure low <= high for consistency
                    try:
                        if float(low) > float(high):
                            low, high = high, low
                    except ValueError:
                        continue
                    found_ranges[letter] = f"{low}-{high}"

        if 'A' in found_ranges and 'F' in found_ranges and len(found_ranges) >= MIN_REQUIRED_LETTER_GRADES:
            # Check if we have actual numerical ranges, not just letters
            has_numbers = False
            for grade_range in found_ranges.values():
                if any(char.isdigit() for char in grade_range):
                    has_numbers = True
                    break
            
            # Only return if we found actual numerical ranges
            if has_numbers:
                lines = [f"{L} = {found_ranges[L]}" for L in self.canonical_order if L in found_ranges]
                content = '\n'.join(lines)
                return {'found': True, 'content': content}

        # Fallback: try grade cluster detection - return exactly what we find
        cluster_content = self._find_grade_cluster(text)
        if cluster_content:
            return {'found': True, 'content': cluster_content}

        return {'found': False, 'content': ''}


def detect_grading_scale(text: str) -> str:
    """Backwards compatible simple API returning content string or ''."""
    d = GradingScaleDetector()
    res = d.detect(text)
    return res.get('content', '') if res.get('found') else ''


if __name__ == '__main__':
    # Test with your specific format
    d = GradingScaleDetector()
    tests = [
        # example format
        ("A: 93 - 100 A-: 90 - 92.9 B+: 87 - 89.9 B: 83 - 86.9 B-: 80 - 82.9 C+: 77 - 79.9 C: 73 - 76.9 C-: 70 - 72.9 D+: 67 - 69.9 D: 63 - 66.9 D-: 60 - 62.9 F: 59.9 or below", True),
        # Original format  
        ("A = 94-100 A- = 90-93 B+ = 87-89 B = 83-86 B- = 80-82 C+ = 77-79 C = 73-76 C- = 70-72 D+ = 67-69 D = 63-66 D- = 60-62 F = 0-59", True),
        # New percentage format from test results
        ("A 100 % to 94 % A- < 94 % to 90 % B+ < 90 % to 87 % B < 87 % to 84 % B- < 84 % to 80 % C+ < 80 % to 77 % C < 77 % to 74 % C- < 74 % to 70 % D+ < 70 % to 67 % D < 67 % to 64 % D- < 64 % to 60 % F < 60 % to 0 %", True),
        # Multi-line format
        ("Course grades will be assigned based on your final total percentage as follows:\nA: 93 - 100\nA-: 90 - 92.9\nB+: 87 - 89.9\nB: 83 - 86.9\nB-: 80 - 82.9\nC+: 77 - 79.9\nC: 73 - 76.9\nC-: 70 - 72.9\nD+: 67 - 69.9\nD: 63 - 66.9\nD-: 60 - 62.9\nF: 59.9 or below", True),
        # Equals format from BIOL courses
        ("Final grades in this course will be based on the following scale: 94-100=A; 90-93.9=A-; 87-89.9=B+; 83-86.9=B; 80-82.9=B-; 77-79.9=C+; 73-76.9=C; 70-72.9=C-; 67-69.9=D+; 63-66.9=D; 60-62.9=D-; Below 60=F", True),
        # New em dash percentage format
        ("A: 93% – 100% A-: 90% – 92.99% B+: 87% – 89.99% B: 83% – 86.99% B-: 80% – 82.99% C+: 77% – 79.99% C: 73% – 76.99% C-: 70% – 72.99% D+: 67% – 69.99% D: 63% – 66.99% D-: 60% – 62.99% F: 0% – 59.99%", True),
        # Horizontal table format
        ("A A- B+ B B- C+ C C- D+ D D- F\n93 90 87 83 80 77 73 70 67 63 60 <60", True),
        # No grading scale
        ("This syllabus has no grading info", False),
    ]
    
    print("Testing grading scale detection...")
    for i, (text, expect) in enumerate(tests):
        print(f"\nTest {i+1}:")
        r = d.detect(text)
        print('FOUND' if r['found'] else 'NO_MATCH')
        if r['found']:
            print("Content:")
            print(r['content'])
        print('-' * 50)

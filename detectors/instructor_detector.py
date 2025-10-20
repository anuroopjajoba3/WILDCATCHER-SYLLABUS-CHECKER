"""
Instructor information extraction module.

This module provides the InstructorDetector class for extracting instructor name, title, and department from syllabus text using regex and context-aware logic.

Typical usage example:
    detector = InstructorDetector()
    result = detector.detect(syllabus_text)
    print(result)
"""

from typing import Dict, Any
import re

class InstructorDetector:
    """
    Regex-based instructor info detector.

    Attributes:
        name_keywords (list): Keywords to identify instructor name lines.
        title_keywords (list): Keywords to identify instructor title lines.
        dept_keywords (list): Keywords to identify department lines.
        name_stopwords (set): Words to exclude from valid names.
        name_non_personal (set): Non-personal words to exclude from names.
    """
    def __init__(self):
        """
        Initializes the InstructorDetector with keyword lists and stopword sets.
        Loads common last names for confidence scoring and fallback extraction.
        """
        self.name_keywords = [
            'Instructor', 'Instructor Name', 'Instructor Name:', 'Professor', 'Professor:', 'Instructor name:', 'Ms', 'Mr', 'Mrs', 'name', 'Name', 'Adjunct Instructor:', 'Contact Information', 'Dr'
        ]
        self.title_keywords = [
            'assistant professor', 'associate professor', 'senior lecturer', 'lecturer', 'adjunct professor', 'adjunct instructor', 'professor'
        ]
        self.dept_keywords = [
            'Department', 'Dept.', 'School of', 'Division of', 'Program', 'College of', 'Department/Program', 'Department and Program'
        ]
        self.name_stopwords = set([
            'of', 'in', 'on', 'for', 'to', 'by', 'with', 'security', 'studies', 'department', 'college', 'school', 'division', 'program', 'phd', 'ph.d', 'professor', 'lecturer', 'assistant', 'associate', 'adjunct', 'mr', 'ms', 'mrs', 'dr'
        ])
        self.name_non_personal = set([
            'internship', 'practice', 'course', 'syllabus', 'description', 'outcomes', 'policy', 'schedule', 'grading', 'assignment', 'exam', 'final', 'midterm', 'attendance', 'office', 'email', 'phone', 'building', 'room', 'hall', 'mill', 'university', 'college', 'school', 'class', 'section', 'semester', 'year', 'hours', 'days', 'spring', 'summer', 'fall', 'winter', 'ta', 'teaching', 'staff', 'master', "master's", 'capstone', 'project', 'thesis', 'dissertation', 'portfolio'
        ])

    def is_valid_name(self, candidate):
        """
        Checks if a candidate string is a valid instructor name.

        Args:
            candidate (str): The candidate name string.

        Returns:
            bool: True if valid, False otherwise.
        """
        parts = candidate.split()
        if not 2 <= len(parts) <= 4:
            return False
        for part in parts:
            # Allow middle initial with period (e.g., W.)
            if re.match(r'^[A-Z]\.$', part):
                continue
            if sum(1 for c in part if c.isupper()) > 1 or len(part) < 2 or not re.match(r"^[A-Z][a-zA-Z\-\.]+$", part) or part.isupper() or part.lower() in self.name_stopwords | self.name_non_personal or "'" in part:
                return False
        if any(word.lower() in self.name_non_personal or word.lower() in ['course', 'syllabus', 'outline', 'schedule', 'description'] for word in parts):
            return False
        return True

    def extract_name(self, lines):
        """
        Extracts the instructor's name from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted name, or None if not found.
        """
        lines_for_name = lines[1:] if len(lines) > 1 else lines
        name = None
        found_keyword = False
        patterns = [
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)', # First M Last
            r'([A-Z][a-zA-Z\-]+\s+[A-Z]\.[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+[A-Z]\.[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)'
        ]
        # Search all but the first line
        for i, line in enumerate(lines_for_name):
            for keyword in self.name_keywords:
                if keyword.lower() in line.lower():
                    found_keyword = True
                    after = re.split(rf'{keyword}[:\-]*', line, flags=re.IGNORECASE)
                    candidate = after[1].strip() if len(after) > 1 else ''
                    if not candidate:
                        if i+2 < len(lines):
                            candidate = lines[i+2].strip()
                    for pat in patterns:
                        match = re.search(pat, candidate)
                        if match:
                            possible_name = match.group(1)
                            if self.is_valid_name(possible_name):
                                name = possible_name
                                break
                    if name:
                        break
                    words = candidate.split()
                    name_candidate = []
                    for w in words:
                        if re.match(r'^[A-Z][a-zA-Z\-\.]*$', w) or re.match(r'^[A-Z]\.$', w):
                            name_candidate.append(w)
                            if len(name_candidate) == 3:
                                break
                        else:
                            break
                    if 2 <= len(name_candidate) <= 3:
                        possible_name = ' '.join(name_candidate)
                        if self.is_valid_name(possible_name):
                            name = possible_name
                            break
            if name:
                break
        # If no name found, check the first line
        if not name and len(lines) > 0:
            first_line = lines[0]
            for keyword in self.name_keywords:
                if keyword.lower() in first_line.lower():
                    after = re.split(rf'{keyword}[:\-]*', first_line, flags=re.IGNORECASE)
                    candidate = after[1].strip() if len(after) > 1 else ''
                    for pat in patterns:
                        match = re.search(pat, candidate)
                        if match:
                            possible_name = match.group(1)
                            if self.is_valid_name(possible_name):
                                name = possible_name
                                break
                    if name:
                        break
                    words = candidate.split()
                    name_candidate = []
                    for w in words:
                        if re.match(r'^[A-Z][a-zA-Z\-\.]*$', w) or re.match(r'^[A-Z]\.$', w):
                            name_candidate.append(w)
                            if len(name_candidate) == 3:
                                break
                        else:
                            break
                    if 2 <= len(name_candidate) <= 3:
                        possible_name = ' '.join(name_candidate)
                        if self.is_valid_name(possible_name):
                            name = possible_name
                            break

        # 2. Only if NO instructor/name keyword was found at all, fall back to pattern search
        if not name and not found_keyword:
            for pat in patterns:
                for line in lines_for_name:
                    for possible_name in re.findall(pat, line.strip()):
                        if self.is_valid_name(possible_name):
                            name = possible_name
                            break
                    if name:
                        break
                if name:
                    break
        if not name:
            indices = [i for i, l in enumerate(lines_for_name) if re.search(r'@|office|room|building', l, re.IGNORECASE)]
            checked = set()
            for idx in indices:
                for offset in range(-2, 3):
                    j = idx + offset
                    if 0 <= j < len(lines_for_name) and j not in checked:
                        checked.add(j)
                        for pat in patterns:
                            for possible_name in re.findall(pat, lines_for_name[j].strip()):
                                if self.is_valid_name(possible_name):
                                    name = possible_name
                                    break
                            if name:
                                break
                    if name:
                        break
                if name:
                    break

        # return name if found, else None
        return name

    def extract_title(self, lines):
        """
        Extracts the instructor's title from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted title, or None if not found.
        """
        # First, look for any title except 'Dr'/'Dr.' and 'Phd'/'Ph.D'
        found_title = None
        for line in lines:
            for kw in self.title_keywords:
                if kw not in ['Dr', 'Dr.']:
                    if kw.lower() in line.lower():
                        return kw.title() if kw.islower() else kw
                elif kw.lower() in ['phd', 'ph.d']:
                    if kw.lower() in line.lower():
                        found_title = kw.title() if kw.islower() else kw
        # If no other title found, use 'Dr'/'Dr.' if present
        for line in lines:
            for kw in ['Dr', 'Dr.']:
                if kw in line:
                    return kw

    def extract_department(self, lines):
        """
        Extracts the instructor's department from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted department, or None if not found.
        """
        # First, require a capital D when matching 'Department' or 'Dept.' to avoid
        # lower-case false positives (e.g., 'department' inside sentences).
        dept_pattern_cs = re.compile(r"\b(Department|Dept\.)[\s:,-]*([A-Za-z &\-.,]+)")
        # Fallback patterns (case-insensitive) for School/Division/Program/College
        other_pattern = re.compile(r"\b(School of|Division of|Program|College of|Department and Program|Department/Program)[\s:,-]*([A-Za-z &\-.,]+)", re.IGNORECASE)

        for line in lines:
            # try case-sensitive Department/Dept. first
            m = dept_pattern_cs.search(line)
            if m:
                    # Only treat 'program' as a separate label when it's actually used as a label
                    # (e.g., 'Program: X' or 'Department and Program: X'). If 'program' appears
                    # as a trailing word in the department name (e.g., 'Bio/Biotech program'),
                    # leave it in the captured value.
                    dept_and_prog = re.search(r'Department\s*(?:and|/)\s*Program\s*[:\-]', line, re.IGNORECASE)
                    prog_label = re.search(r'\bprogram\b\s*[:\-]', line, re.IGNORECASE)
                    if dept_and_prog:
                        value = line[dept_and_prog.end():].strip()
                    elif prog_label:
                        value = line[prog_label.end():].strip()
                    else:
                        value = m.group(2).strip()
            else:
                m2 = other_pattern.search(line)
                if m2:
                    value = m2.group(2).strip()
                else:
                    continue

            # cleanup leading punctuation/labels
            value = re.sub(r'^[\s:,-]+', '', value)
            value = re.sub(r'^(Department|Dept\.|Program|School of|Division of|College of)[\s:,-]*', '', value, flags=re.IGNORECASE)

            # normalize whitespace and strip trailing punctuation
            value = re.sub(r'\s+', ' ', value).strip().strip('.,;-')

            # Skip very generic or empty values
            low = value.lower()
            if not value or low in ['dept.', 'department', 'department and program', 'school of', 'division of', 'program', 'college of', 'department/program']:
                continue
            if low in self.name_non_personal or low in self.name_stopwords:
                continue

            # limit returned department to up to 5 words
            words = [w for w in re.split(r'\s+', value) if w]
            if len(words) > 5:
                words = words[:5]
            return ' '.join(words).strip()

        return None

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detects instructor name, title, and department from syllabus text.

        Args:
            text (str): The syllabus text to search.

        Returns:
            Dict[str, Any]: Dictionary with keys 'found', 'name', 'title', 'department'.
        """
        lines = text.split('\n')[:30]
        name = self.extract_name(lines)
        title = self.extract_title(lines)
        department = self.extract_department(lines)

        # Fallback: if no name was found by the normal logic, scan every
        # 30-line "page" for a simple "Dr. Lastname" pattern and return
        # the first match. This bypasses the stricter is_valid_name checks
        # because syllabus text often uses the short form 'Dr. Smith'.
        if not name:
            all_lines = text.split('\n')
            page_size = 30
            dr_pattern = re.compile(r"\bDr\.?\s+([A-Z][a-zA-Z\-]+)\b")
            for i in range(0, len(all_lines), page_size):
                page = all_lines[i:i+page_size]
                for pline in page:
                    m = dr_pattern.search(pline)
                    if m:
                        lastname = m.group(1)
                        # Standardize to 'Dr. Lastname'
                        name = f"Dr. {lastname}"
                        break
                if name:
                    break

        found = bool(name and title and department and name != 'N/A' and title != 'N/A' and department != 'N/A')
        return {'found': found, 'name': name, 'title': title, 'department': department}

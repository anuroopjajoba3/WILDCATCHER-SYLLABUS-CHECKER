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
            'Instructor', 'Professor', 'Dr', 'Ms', 'Mr', 'Mrs', 'Lecturer', 'name', 'Name'
        ]
        self.title_keywords = [
            'assistant professor', 'associate professor', 'professor', 'lecturer', 'adjunct', 'phd', 'ph.d', 'dr', 'dr.'
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
        self.common_last_names = self.load_common_last_names()

    def load_common_last_names(self, filename='common-last-names.txt'):
        """
        Loads common last names from a file into a set.

        Args:
            filename (str): Path to the file with last names (one per line).
        Returns:
            set: Set of common last names (lowercase).
        """
        try:
            with open(filename, encoding='utf-8') as f:
                return set(line.strip().lower() for line in f if line.strip())
        except Exception:
            return set()

    def is_valid_name(self, candidate):
        """
        Checks if a candidate string is a valid instructor name.

        Args:
            candidate (str): The candidate name string.

        Returns:
            bool: True if valid, False otherwise.
        """
        parts = candidate.split()
        if not 2 <= len(parts) <= 3:
            return False
        for part in parts:
            if sum(1 for c in part if c.isupper()) > 1 or len(part) < 3 or not part.isalpha() or part.isupper() or part.lower() in self.name_stopwords | self.name_non_personal or "'" in part or not re.match(r"^[A-Z][a-zA-Z\-]+$", part):
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
        for i, line in enumerate(lines_for_name):
            for keyword in self.name_keywords:
                if keyword.lower() in line.lower():
                    found_keyword = True
                    after = re.split(rf'{keyword}[:\-]*', line, flags=re.IGNORECASE)
                    candidate = after[1].strip() if len(after) > 1 else ''
                    if not candidate or not re.search(r'[A-Z]', candidate):
                        for j in range(i+1, min(i+4, len(lines_for_name))):
                            next_line = lines_for_name[j].strip()
                            if next_line:
                                candidate = next_line
                                break
                    for pat in [r'^([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)', r'^([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)']:
                        match = re.match(pat, candidate)
                        if match and self.is_valid_name(match.group(1)):
                            name = match.group(1)
                            break
                    if name:
                        break
            if name:
                break
        if not name and not found_keyword:
            for pat in [r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)', r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)']:
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
                        for pat in [r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)', r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)']:
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
        if not name:
            for line in lines_for_name:
                words = line.strip().split()
                for i in range(len(words)-1):
                    first, last = words[i], words[i+1]
                    if first.istitle() and last.istitle() and last.lower() in self.common_last_names:
                        candidate = f"{first} {last}"
                        if self.is_valid_name(candidate):
                            name = candidate
                            break
                if name:
                    break
        return name

    def extract_title(self, lines):
        """
        Extracts the instructor's title from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted title, or None if not found.
        """
        for line in lines:
            for kw in self.title_keywords:
                if kw.lower() in line.lower():
                    return kw.title() if kw.islower() else kw
        return None

    def extract_department(self, lines):
        """
        Extracts the instructor's department from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted department, or None if not found.
        """
        dept_pattern = re.compile(r"(Department and Program|Department/Program|Department|Dept\.|School of|Division of|Program|College of)[\s:,-]*([A-Za-z &\-.,]+)", re.IGNORECASE)
        for line in lines:
            match = dept_pattern.search(line)
            if match:
                value = match.group(2).strip()
                value = re.sub(r'^[\s:,-]+', '', value)
                value = re.sub(r'^(Department|Dept\.|Program|School of|Division of|College of)[\s:,-]*', '', value, flags=re.IGNORECASE)
                if value.lower() in ['dept.', 'department', 'department and program', 'school of', 'division of', 'program', 'college of', 'department/program']:
                    continue
                if value.lower() not in self.name_non_personal and value.lower() not in self.name_stopwords:
                    return value.strip()
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
        found = bool(name and title and department and name != 'N/A' and title != 'N/A' and department != 'N/A')
        return {'found': found, 'name': name, 'title': title, 'department': department}

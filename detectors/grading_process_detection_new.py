"""
Grading Process Detector
Detects grading processes in syllabi: focuses on clusters containing
percentages (%) or points keywords with assignment-related terms.
Does NOT focus on letter grades (A-F).
"""

import re
import logging
from typing import Dict, Any

# Detection Configuration Constants
MAX_HEADING_SCAN_LINES = 8
MAX_HEADING_WORDS_CAPS = 12
MAX_HEADING_WORDS_ANCHOR = 15
MAX_HEADING_WORDS_TITLE = 10
MIN_TITLE_CASE_CAPS = 2


class GradingProcessDetector:
    """Detector for grading processes focusing on percent/points clusters."""

    def __init__(self):
        self.field_name = 'grading_process'
        self.logger = logging.getLogger('detector.grading_process')

        # Focus on percent and points patterns (not letter grades)
        self.percent_pattern = re.compile(r"\d+\s*%")
        self.points_pattern = re.compile(r"\b\d+\s*(points?|pts?)\b", re.I)
        
        # Look for clusters containing these keywords along with percents/points
        self.cluster_keywords = [
            'exam', 'exams', 'test', 'tests', 'quiz', 'quizzes', 'assignment', 'assignments',
            'homework', 'project', 'projects', 'paper', 'papers', 'participation', 'attendance',
            'lab', 'labs', 'midterm', 'final', 'presentation', 'presentations', 'discussion',
            'portfolio', 'report', 'reports', 'essay', 'essays', 'case study', 'case studies'
        ]

        # Anchor keywords for context
        self.anchor_keywords = [
            'grade', 'grading', 'grades', 'grade breakdown', 'course grades',
            'how grades are determined', 'final grade', 'grade distribution', 
            'assessment', 'evaluation', 'total = 100', 'total=100', 'total 100'
        ]

    def _get_heading_before(self, lines, line_index: int, max_scan: int = MAX_HEADING_SCAN_LINES) -> str:
        """Return a nearby short heading above line_index or empty string."""
        if not lines:
            return ''
        for i in range(line_index - 1, max(-1, line_index - max_scan - 1), -1):
            if i < 0 or i >= len(lines):
                break
            ln = lines[i].strip()
            if not ln:
                continue
            words = ln.split()
            if ln.isupper() and len(words) <= MAX_HEADING_WORDS_CAPS:
                return ln
            low = ln.lower()
            if any(k in low for k in self.anchor_keywords) and len(words) <= MAX_HEADING_WORDS_ANCHOR:
                return ln
            cap_count = sum(1 for w in words if w and w[0].isupper())
            if MIN_TITLE_CASE_CAPS <= cap_count and len(words) <= MAX_HEADING_WORDS_TITLE and '.' not in ln and ',' not in ln:
                return ln
        return ''

    def _is_heading_line(self, s: str) -> bool:
        """Return True if s looks like a short section heading."""
        if not s or not s.strip():
            return False
        s_stripped = s.strip()
        words = [w for w in s_stripped.split() if w]

        # All-caps short headings are strong indicator
        if s_stripped.isupper() and len(words) <= MAX_HEADING_WORDS_CAPS:
            return True

        low = s_stripped.lower()
        # Anchor keywords are useful, but require the line to be reasonably short
        if any(k in low for k in self.anchor_keywords) and len(words) <= MAX_HEADING_WORDS_ANCHOR:
            return True

        # Title-Case heuristic: short lines with multiple capitalized words and no sentence punctuation
        cap_count = sum(1 for w in words if w and w[0].isupper())
        if MIN_TITLE_CASE_CAPS <= cap_count and len(words) <= MAX_HEADING_WORDS_TITLE and '.' not in s_stripped and ',' not in s_stripped:
            return True

        return False

    def detect(self, text: str) -> Dict[str, Any]:
        """Detect grading process by looking for clusters containing:
        - Percentages (%)
        - Points/pts keywords
        - Assignment-related keywords
        
        Does NOT focus on letter grades (A-F).
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        if not text:
            self.logger.info(f"NOT_FOUND: {self.field_name} (empty text)")
            return {'found': False, 'content': ''}

        # Normalize line endings
        lines = [ln.rstrip() for ln in text.split('\n')]

        # Look for lines that contain both:
        # 1) Percentages or points
        # 2) Assignment/grading keywords
        candidate_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if line has percent or points
            has_percent = bool(self.percent_pattern.search(line))
            has_points = bool(self.points_pattern.search(line))
            
            # Check if line has relevant keywords
            has_keywords = any(keyword in line_lower for keyword in self.cluster_keywords)
            
            # Check if it looks like a grading item (assignment name followed by percent/points)
            looks_like_grading = bool(re.match(r"^[A-Za-z].{0,60}(\d+\s*%|\(\d+%\)|\d+\s*points?|\d+\s*pts?)", line, re.I))
            
            if (has_percent or has_points) and (has_keywords or looks_like_grading):
                candidate_lines.append(i)

        if not candidate_lines:
            self.logger.info(f"NOT_FOUND: {self.field_name} (no percent/points with keywords)")
            return {'found': False, 'content': ''}

        # Find clusters of candidate lines (group nearby lines together)
        clusters = []
        current_cluster = [candidate_lines[0]]
        
        for i in range(1, len(candidate_lines)):
            # If lines are within 3 lines of each other, group them
            if candidate_lines[i] - candidate_lines[i-1] <= 3:
                current_cluster.append(candidate_lines[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [candidate_lines[i]]
        
        if current_cluster:
            clusters.append(current_cluster)

        # Find the best cluster (largest one with most percent/points lines)
        best_cluster = None
        best_score = 0
        
        for cluster in clusters:
            # Score based on number of lines and percent/points density
            score = len(cluster)
            
            # Bonus for having grading-related keywords nearby
            start_idx = max(0, min(cluster) - 2)
            end_idx = min(len(lines), max(cluster) + 3)
            context = ' '.join(lines[start_idx:end_idx])
            
            if any(keyword in context.lower() for keyword in self.anchor_keywords):
                score += 2
            
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if not best_cluster or best_score < 2:
            self.logger.info(f"NOT_FOUND: {self.field_name} (no good clusters found)")
            return {'found': False, 'content': ''}

        # Extract content from the best cluster
        start_idx = min(best_cluster)
        end_idx = max(best_cluster)
        
        # Try to include a heading before the cluster
        heading_start = start_idx
        for i in range(start_idx - 1, max(-1, start_idx - 5), -1):
            if i < 0 or not lines[i].strip():
                break
            if self._is_heading_line(lines[i]):
                heading_start = i
                break
        
        # Expand to include context lines that might be part of the grading breakdown
        final_start = heading_start
        final_end = min(len(lines) - 1, end_idx + 2)
        
        # Include lines that are part of the grading structure
        content_lines = []
        for i in range(final_start, final_end + 1):
            line = lines[i].strip()
            if line:
                content_lines.append(line)
        
        if content_lines:
            content = '\n'.join(content_lines)
            self.logger.info(f"FOUND: {self.field_name} (percent/points cluster)")
            return {'found': True, 'content': content}

        self.logger.info(f"NOT_FOUND: {self.field_name}")
        return {'found': False, 'content': ''}


# Backwards compatibility
def detect_grading_process(text: str) -> str:
    d = GradingProcessDetector()
    res = d.detect(text)
    return res.get('content', '') if res.get('found') else ''


if __name__ == '__main__':
    tests = [
        ("Exam 1 - 22%\nExam 2 - 22%\nExam 3 - 22%\nOnline Quizzes - 10%\nExperiments - 20%\nAttendance - 4%\nTotal = 100%", True),
        ("PROJECTS (70%) 70 Points\nProject #1 - 10 points\nProject #2 - 10 points\nQuiz & Mid-Term (20%) 20 Points\nOTHER (10%) 10 Points\nTOTAL 100%", True),
        ("Case Studies (4)\t\t\t\t24% (6% each)\nExams (2) \t\t\t\t30% (15% each)\nEthics Position Papers (3)\t\t21% (7% each)\nTeam Debate\t\t\t\t15%\nParticipation \t\t\t \t10%", True),
        ("This syllabus has no grading info", False),
    ]

    d = GradingProcessDetector()
    for text, expect in tests:
        r = d.detect(text)
        print('FOUND' if r['found'] else 'NO_MATCH')
        if r['found']:
            print(r['content'])
        print('-' * 40)

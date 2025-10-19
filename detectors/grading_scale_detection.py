"""
Grading Scale Detector
Detects grading scales in syllabi: letter-grade mappings (A: 93-100 ... F), percentage breakdowns (Exam 1 - 22%),
and grouped assignment->percentage lists.
"""

import re
from typing import Dict, Any


class GradingScaleDetector:
    """Detector for grading scales in syllabi."""

    def __init__(self):
        self.field_name = 'grading_scale'

        # Keywords that suggest a grading scale block
        self.percent_pattern = re.compile(r"\d+\s*%")
        self.points_pattern = re.compile(r"\b\d+\s*(points|pts)\b", re.I)
        # Letter-grade block pattern (A:, B:, C:, D:, F: in same area)
        self.letter_block_pattern = re.compile(
            r"A\s*[:\-].{0,80}B\s*[:\-].{0,80}C\s*[:\-].{0,80}D\s*[:\-].{0,80}F\s*[:\-]",
            re.I | re.S,
        )

        # small list of common labels to help anchor sections
        self.anchor_keywords = [
            'grade', 'grading', 'grades', 'grade breakdown', 'grade scale', 'grading scale', 'course grades',
            'how grades are determined', 'final grade', 'grade distribution', 'assignment', 'exam', 'quiz', 'project',
            'total = 100', 'total=100', 'total 100', 'total: 100', 'total - 100'
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """Detect grading scale. Returns dict with found and content.

        Strategy:
        - Search for explicit letter-grade block via regex.
        - Otherwise, scan lines for windows that contain several percentage/points lines.
        - Or find grouped lines where an assignment label is followed by a percentage within a short window.
        """
        if not text:
            return {'found': False, 'content': ''}

        # Normalize line endings
        lines = [ln.rstrip() for ln in text.split('\n')]
        joined = '\n'.join(lines)

        # 1) Try letter-grade block
        m = self.letter_block_pattern.search(joined)
        if m:
            # expand to nearest line boundaries
            span = m.span()
            start = joined.rfind('\n', 0, span[0]) + 1
            end = joined.find('\n', span[1])
            if end == -1:
                end = len(joined)
            content = joined[start:end].strip()
            return {'found': True, 'content': content}

        # 2) Look for contiguous percentage/points lines (window detection)
        windows = []
        current_block = []
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                # break block
                if current_block:
                    windows.append((i - len(current_block), current_block))
                    current_block = []
                continue

            has_percent = bool(self.percent_pattern.search(s))
            has_points = bool(self.points_pattern.search(s))
            looks_like_item = bool(re.match(r"^[A-Za-z].{0,60}(\d+\s*%|\(\d+%\)|\d+\s*points|\d+\s*pts)", s, re.I))

            if has_percent or has_points or looks_like_item:
                current_block.append(s)
            else:
                # if block already has multiple percent lines, we end it
                if current_block:
                    windows.append((i - len(current_block), current_block))
                    current_block = []
        if current_block:
            windows.append((len(lines) - len(current_block), current_block))

        # Choose the best window: one with most percent/points lines
        best = None
        best_score = 0
        for idx, block in windows:
            score = sum(1 for ln in block if self.percent_pattern.search(ln) or self.points_pattern.search(ln))
            # bonus if there is an anchor keyword near the block
            context = ' '.join(lines[max(0, idx-3): min(len(lines), idx+len(block)+3)])
            if any(k in context.lower() for k in self.anchor_keywords):
                score += 1
            if score > best_score and score >= 2:
                best_score = score
                best = (idx, block)

        if best:
            start_idx, block = best
            end_idx = start_idx + len(block) - 1

            # Helper to detect candidate heading lines above the block
            def is_heading_line(s: str) -> bool:
                """Return True for short lines that look like section headings.

                Avoid treating long, sentence-like paragraphs as headings.
                """
                if not s or not s.strip():
                    return False
                s_stripped = s.strip()
                words = [w for w in s_stripped.split() if w]

                # All-caps short headings are strong indicator
                if s_stripped.isupper() and len(words) <= 12:
                    return True

                low = s_stripped.lower()
                # Anchor keywords are useful, but require the line to be reasonably short
                if any(k in low for k in self.anchor_keywords) and len(words) <= 15:
                    return True

                # Title-Case heuristic: short lines with multiple capitalized words and no sentence punctuation
                cap_count = sum(1 for w in words if w and w[0].isupper())
                if 2 <= cap_count and len(words) <= 10 and '.' not in s_stripped and ',' not in s_stripped:
                    return True

                return False

            # Try to extend upwards to include a nearby heading (scan up to 6 lines)
            start = start_idx
            for i in range(start_idx - 1, max(-1, start_idx - 7), -1):
                if i < 0:
                    break
                if not lines[i].strip():
                    break
                if is_heading_line(lines[i]):
                    start = i
                    # once we include a heading, stop scanning further up
                    break
                # otherwise do not include long paragraph lines as heading

            # Extend down to capture multi-line items (up to 8 lines), but stop at long sentence paragraphs
            end = end_idx
            for j in range(end_idx + 1, min(len(lines), end_idx + 9)):
                if not lines[j].strip():
                    break
                nxt = lines[j].strip()
                # If the line looks like a long sentence (many words and contains a period), stop
                if '.' in nxt and len(nxt.split()) > 20:
                    break
                end = j

            content_lines = [lines[i].rstrip() for i in range(start, end + 1) if lines[i].strip()]
            content = '\n'.join(content_lines).strip()
            return {'found': True, 'content': content}

        # 3) fallback: look for lines containing a cluster of assignment labels followed shortly by percentages
        # find lines where a percentage exists and gather +/-3 lines around it
        percent_lines_idx = [i for i, ln in enumerate(lines) if self.percent_pattern.search(ln)]
        for idx in percent_lines_idx:
            # gather a slightly larger window and then try to expand to heading/context
            start = max(0, idx - 3)
            end = min(len(lines), idx + 4)
            block_lines = [lines[j] for j in range(start, end) if lines[j].strip()]
            if sum(1 for ln in block_lines if self.percent_pattern.search(ln)) >= 2:
                # expand similarly to the window case
                # find nearest non-empty start before 'start' that looks like a heading
                heading_start = start
                for i in range(start - 1, max(-1, start - 9), -1):
                    if i < 0 or not lines[i].strip():
                        break
                    if any(k in lines[i].lower() for k in self.anchor_keywords) or lines[i].strip().isupper():
                        heading_start = i
                        break
                final_start = heading_start
                final_end = min(len(lines) - 1, end + 3)
                for j in range(end, min(len(lines), end + 9)):
                    if not lines[j].strip():
                        break
                    final_end = j
                content_lines = [lines[k].rstrip() for k in range(final_start, final_end + 1) if lines[k].strip()]
                return {'found': True, 'content': '\n'.join(content_lines).strip()}

        return {'found': False, 'content': ''}


# Backwards compatibility
def detect_grading_scale(text: str) -> str:
    d = GradingScaleDetector()
    res = d.detect(text)
    return res.get('content', '') if res.get('found') else ''


if __name__ == '__main__':
    tests = [
        ("Course grades will be assigned based on your final total percentage as follows:\nA: 93 - 100 A-: 90 - 92.9 B+: 87 - 89.9 B: 83 - 86.9 B-: 80 - 82.9\nC+: 77 - 79.9 C: 73 - 76.9 C-: 70 - 72.9 D+: 67 - 69.9 D: 63 - 66.9\nD-: 60 - 62.9 F: 59.9 or below", True),
        ("Exam 1 - 22%\nExam 2 - 22%\nExam 3 - 22%\nOnline Quizzes - 10%\nExperiments - 20%\nAttendance - 4%\nTotal = 100%", True),
        ("PROJECTS (70%) 70 Points\nProject #1 - 10 points\nProject #2 - 10 points\nQuiz & Mid-Term (20%) 20 Points\nOTHER (10%) 10 Points\nTOTAL 100%", True),
        ("This syllabus has no grading info", False),
    ]

    d = GradingScaleDetector()
    for text, expect in tests:
        r = d.detect(text)
        print('FOUND' if r['found'] else 'NO_MATCH', '\n', r['content'])
        print('-' * 40)

"""
Grading Scale Detector
Detects grading scales in syllabi: letter-grade mappings (A: 93-100 ... F), percentage breakdowns (Exam 1 - 22%),
and grouped assignment->percentage lists.
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
MIN_REQUIRED_LETTER_GRADES = 8
MIN_WINDOW_SCORE = 2
MAX_SHORT_LINE_WORDS = 15
MAX_SHORT_LINE_LENGTH = 120
MAX_NEXT_LINE_WORDS = 20
MAX_UPWARD_SCAN = 7
MAX_DOWNWARD_SCAN = 9
MAX_FORWARD_SCAN = 7
PERCENT_CLUSTER_WINDOW = 3


class GradingScaleDetector:
    """Detector for grading scales in syllabi."""

    def __init__(self):
        self.field_name = 'grading_scale'
        self.logger = logging.getLogger('detector.grading_scale')

        # Keywords that suggest a grading scale block
        self.percent_pattern = re.compile(r"\d+\s*%")
        self.points_pattern = re.compile(r"\b\d+\s*(points|pts)\b", re.I)
        # Letter-grade block pattern (A:, B:, C:, D:, F: in same area)
        self.letter_block_pattern = re.compile(
            r"A\s*[:\-].{0,80}B\s*[:\-].{0,80}C\s*[:\-].{0,80}D\s*[:\-].{0,80}F\s*[:\-]",
            re.I | re.S,
        )

        # compact letter->range patterns: "A = 94-100", "94-100 = A", or "A 94-100"
        # captures letter and numeric range pairs
        self.letter_range_pattern = re.compile(
            r"([A-F][+-]?)[\s:=]*?(\d{1,3}(?:\.\d+)?)[\s*\-\u2013\u2014to]{1,4}(\d{1,3}(?:\.\d+)?)%?",
            re.I,
        )

        # small list of common labels to help anchor sections
        self.anchor_keywords = [
            'grade', 'grading', 'grades', 'grade breakdown', 'grade scale', 'grading scale', 'course grades',
            'how grades are determined', 'final grade', 'grade distribution', 'assignment', 'exam', 'quiz', 'project',
            'total = 100', 'total=100', 'total 100', 'total: 100', 'total - 100'
        ]

    def _get_heading_before(self, lines, line_index: int, max_scan: int = MAX_HEADING_SCAN_LINES) -> str:
        """Return a nearby short heading above line_index or empty string.

        Scans up to ``max_scan`` non-empty lines looking for short ALL-CAPS
        headings, anchor keywords, or short Title-Case phrases.
        """
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
        """Return True if ``s`` looks like a short section heading.

        This is a lightweight heuristic used when extending blocks to
        include nearby headings.
        """
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

    @staticmethod
    def _normalize_number(s: str) -> str:
        """Normalize number strings (strip trailing .0, remove percent)."""
        try:
            f = float(s)
            i = int(f) if f.is_integer() else int(round(f))
            return str(i)
        except Exception:
            return s.strip()

    def detect(self, text: str) -> Dict[str, Any]:
        """Detect grading scale and return a result dict with keys:
        - 'found': bool
        - 'content': str

        The detector tries (in order):
        1) canonical letter->range mappings (A..F),
        2) explicit letter-grade block (A:, B:, C:, D:, F:),
        3) contiguous percent/points windows, and
        4) local percentage clusters near labels.
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        if not text:
            self.logger.info(f"NOT_FOUND: {self.field_name} (empty text)")
            return {'found': False, 'content': ''}

        # Normalize line endings
        lines = [ln.rstrip() for ln in text.split('\n')]
        joined = '\n'.join(lines)

        # Testing for grade block scale
        # Try to detect canonical letter->range mappings and return a normalized
        # canonical scale (A..F) if enough mappings found. This prioritizes returning
        # a compact canonical scale string that matches the preferred output format.
        # We require the presence of both A and F and at least MIN_REQUIRED_LETTER_GRADES mappings to be
        # conservative.
        found_ranges = {}
        for match in self.letter_range_pattern.finditer(joined):
            letter = match.group(1).upper().replace('\u2212', '-')
            low = match.group(2)
            high = match.group(3)
            # normalize numbers (strip trailing .0, remove percent)
            low_n = self._normalize_number(low)
            high_n = self._normalize_number(high)
            found_ranges[letter] = f"{low_n}-{high_n}"

        # canonical order
        canonical_order = [
            'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'
        ]
        if 'A' in found_ranges and 'F' in found_ranges and len(found_ranges) >= MIN_REQUIRED_LETTER_GRADES:
            # build normalized canonical string
            result_lines = []
            for letter in canonical_order:
                if letter in found_ranges:
                    result_lines.append(f"{letter} = {found_ranges[letter]}")
            content = '\n'.join(result_lines)
            # Per request: return only the canonical scale lines (no heading/context)
            self.logger.info(f"FOUND: {self.field_name} (canonical letter grades)")
            return {'found': True, 'content': content}

        block_match = self.letter_block_pattern.search(joined)
        if block_match:
            # expand to nearest line boundaries
            span = block_match.span()
            start = joined.rfind('\n', 0, span[0]) + 1
            end = joined.find('\n', span[1])
            if end == -1:
                end = len(joined)
            content = joined[start:end].strip()
            # prepend a nearby heading if present
            line_idx = joined[:span[0]].count('\n')
            heading = self._get_heading_before(lines, line_idx)
            if heading and not content.startswith(heading):
                content = heading + '\n' + content
            self.logger.info(f"FOUND: {self.field_name} (letter block pattern)")
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
            context = ' '.join(lines[max(0, idx-PERCENT_CLUSTER_WINDOW): min(len(lines), idx+len(block)+PERCENT_CLUSTER_WINDOW)])
            if any(k in context.lower() for k in self.anchor_keywords):
                score += 1
            if score > best_score and score >= MIN_WINDOW_SCORE:
                best_score = score
                best = (idx, block)

        if best:
            start_idx, block = best
            end_idx = start_idx + len(block) - 1

            # Try to extend upwards to include a nearby heading (scan up to MAX_UPWARD_SCAN lines)
            start = start_idx
            for i in range(start_idx - 1, max(-1, start_idx - MAX_UPWARD_SCAN - 1), -1):
                if i < 0:
                    break
                if not lines[i].strip():
                    break
                if self._is_heading_line(lines[i]):
                    start = i
                    # once we include a heading, stop scanning further up
                    break
                # otherwise do not include long paragraph lines as heading

            # Extend down to capture multi-line items (up to MAX_DOWNWARD_SCAN lines), but stop at long sentence paragraphs
            end = end_idx
            for j in range(end_idx + 1, min(len(lines), end_idx + MAX_DOWNWARD_SCAN)):
                if not lines[j].strip():
                    break
                next_line = lines[j].strip()
                # If the line looks like a long sentence (many words and contains a period), stop
                if '.' in next_line and len(next_line.split()) > MAX_NEXT_LINE_WORDS:
                    break
                end = j

            # Prefer to return only the percent/points lines and very short context
            percent_idxs = [i for i in range(start, end + 1) if self.percent_pattern.search(lines[i]) or self.points_pattern.search(lines[i])]
            if percent_idxs:
                selected = []
                for idx in percent_idxs:
                    # include one short preceding line if it looks like a heading/context
                    if idx - 1 >= start and lines[idx-1].strip():
                        prev = lines[idx-1].strip()
                        if len(prev.split()) <= MAX_SHORT_LINE_WORDS and len(prev) <= MAX_SHORT_LINE_LENGTH:
                            selected.append(idx-1)
                    selected.append(idx)
                    # include one short following line if it's short and not a long sentence
                    if idx + 1 <= end and lines[idx+1].strip():
                        next_line = lines[idx+1].strip()
                        if len(next_line.split()) <= MAX_NEXT_LINE_WORDS and not ('.' in next_line and len(next_line.split()) > MAX_NEXT_LINE_WORDS):
                            selected.append(idx+1)
                # dedupe while preserving order
                seen = set()
                final_idxs = []
                for i in selected:
                    if i not in seen:
                        seen.add(i)
                        final_idxs.append(i)

                # If percent lines are separated by short label lines that appear later,
                # scan forward up to a few lines to capture them (e.g., 'Quizzes:' then later 'Quiz1: 40%')
                if final_idxs:
                    start_block = min(final_idxs)
                    end_block = max(final_idxs)
                    for j in range(end_block + 1, min(len(lines), end_block + MAX_FORWARD_SCAN)):
                        if self.percent_pattern.search(lines[j]):
                            # include intervening short lines
                            for k in range(end_block + 1, j + 1):
                                if k not in seen and lines[k].strip():
                                    # only include short label/context lines
                                    if k == j or len(lines[k].split()) <= MAX_SHORT_LINE_WORDS:
                                        seen.add(k)
                                        final_idxs.append(k)
                            end_block = j
                            break

                content_lines = [lines[i].rstrip() for i in final_idxs if lines[i].strip()]
                # prepend heading if found above original block
                heading = self._get_heading_before(lines, start_idx)
                if heading and (not content_lines or not content_lines[0].startswith(heading)):
                    content_lines.insert(0, heading)
                content = '\n'.join(content_lines).strip()
                self.logger.info(f"FOUND: {self.field_name} (percent/points window)")
                return {'found': True, 'content': content}
            else:
                # fallback to returning the short block (should be rare)
                content_lines = [lines[i].rstrip() for i in range(start, end + 1) if lines[i].strip()]
                content = '\n'.join(content_lines).strip()
                self.logger.info(f"FOUND: {self.field_name} (short block fallback)")
                return {'found': True, 'content': content}

        # 3) fallback: look for lines containing a cluster of assignment labels followed shortly by percentages
        # find lines where a percentage exists and gather +/-PERCENT_CLUSTER_WINDOW lines around it
        percent_lines_idx = [i for i, ln in enumerate(lines) if self.percent_pattern.search(ln)]
        for idx in percent_lines_idx:
            # gather a slightly larger window and then try to expand to heading/context
            start = max(0, idx - PERCENT_CLUSTER_WINDOW)
            end = min(len(lines), idx + PERCENT_CLUSTER_WINDOW + 1)
            block_lines = [lines[j] for j in range(start, end) if lines[j].strip()]
            if sum(1 for ln in block_lines if self.percent_pattern.search(ln)) >= MIN_WINDOW_SCORE:
                # expand similarly to the window case
                # find nearest non-empty start before 'start' that looks like a heading
                heading_start = start
                for i in range(start - 1, max(-1, start - MAX_DOWNWARD_SCAN), -1):
                    if i < 0 or not lines[i].strip():
                        break
                    if any(k in lines[i].lower() for k in self.anchor_keywords) or lines[i].strip().isupper():
                        heading_start = i
                        break
                final_start = heading_start
                final_end = min(len(lines) - 1, end + PERCENT_CLUSTER_WINDOW)
                for j in range(end, min(len(lines), end + MAX_DOWNWARD_SCAN)):
                    if not lines[j].strip():
                        break
                    final_end = j
                # prefer to return only percent/points lines near the cluster
                percent_idxs2 = [k for k in range(final_start, final_end + 1) if self.percent_pattern.search(lines[k]) or self.points_pattern.search(lines[k])]
                if percent_idxs2:
                    selected = []
                    for idx in percent_idxs2:
                        if idx - 1 >= final_start and lines[idx-1].strip():
                            prev = lines[idx-1].strip()
                            if len(prev.split()) <= MAX_SHORT_LINE_WORDS and len(prev) <= MAX_SHORT_LINE_LENGTH:
                                selected.append(idx-1)
                        selected.append(idx)
                        if idx + 1 <= final_end and lines[idx+1].strip():
                            next_line = lines[idx+1].strip()
                            if len(next_line.split()) <= MAX_NEXT_LINE_WORDS and not ('.' in next_line and len(next_line.split()) > MAX_NEXT_LINE_WORDS):
                                selected.append(idx+1)
                    seen = set()
                    final_idxs2 = []
                    for i in selected:
                        if i not in seen:
                            seen.add(i)
                            final_idxs2.append(i)

                    # expand forward to include percent lines that appear after short labels
                    if final_idxs2:
                        start_block2 = min(final_idxs2)
                        end_block2 = max(final_idxs2)
                        for j in range(end_block2 + 1, min(len(lines), end_block2 + MAX_FORWARD_SCAN)):
                            if self.percent_pattern.search(lines[j]):
                                for k in range(end_block2 + 1, j + 1):
                                    if k not in seen and lines[k].strip():
                                        if k == j or len(lines[k].split()) <= MAX_SHORT_LINE_WORDS:
                                            seen.add(k)
                                            final_idxs2.append(k)
                                end_block2 = j
                                break

                    content_lines = [lines[k].rstrip() for k in final_idxs2 if lines[k].strip()]
                    heading = self._get_heading_before(lines, final_start)
                    if heading and (not content_lines or not content_lines[0].startswith(heading)):
                        content_lines.insert(0, heading)
                    self.logger.info(f"FOUND: {self.field_name} (percent cluster)")
                    return {'found': True, 'content': '\n'.join(content_lines).strip()}
                content_lines = [lines[k].rstrip() for k in range(final_start, final_end + 1) if lines[k].strip()]
                self.logger.info(f"FOUND: {self.field_name} (cluster fallback)")
                return {'found': True, 'content': '\n'.join(content_lines).strip()}

        self.logger.info(f"NOT_FOUND: {self.field_name}")
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

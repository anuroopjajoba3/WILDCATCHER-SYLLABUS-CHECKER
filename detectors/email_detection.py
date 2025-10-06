"""
email Detector
=========================================
Detects instructor email addresses in syllabus documents.
Prefers emails near typical headings; falls back to first valid email.
"""

import re
import logging
from typing import Dict, Any, Tuple, List

EMAIL_RX = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

HEADING_CLUES = [
    "email", "e-mail", "contact", "contact information",
    "preferred contact method", "instructor", "professor"
]

class emailDetector:
    def __init__(self):
        self.field_name = 'email'
        self.logger = logging.getLogger('detector.email')

    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info("Starting detection for field: email")

        if not text:
            return self._not_found()

        # 1) Try: scan first ~150 lines for heading + email on the same/next line
        lines = text.splitlines()
        window_lines = lines[:150] if len(lines) > 150 else lines
        candidate = self._find_near_heading(window_lines)
        if candidate:
            return self._found([candidate], method="heading_window")

        # 2) Try: any valid email in the first ~1200 chars (header area)
        header = text[:1200]
        header_emails = EMAIL_RX.findall(header)
        if header_emails:
            return self._found([header_emails[0]], method="header_any")

        # 3) Fallback: first valid email anywhere in the doc
        all_emails = EMAIL_RX.findall(text)
        if all_emails:
            return self._found([all_emails[0]], method="fallback_any")

        return self._not_found()

    # ---------------- helpers ----------------

    def _find_near_heading(self, lines: List[str]) -> str | None:
        """Find an email on a line that contains a clue word, or the next line."""
        for i, raw in enumerate(lines):
            line = raw.strip()
            low = line.lower()
            if any(k in low for k in HEADING_CLUES):
                # same line
                m = EMAIL_RX.search(line)
                if m:
                    return m.group(0)
                # next line
                if i + 1 < len(lines):
                    m2 = EMAIL_RX.search(lines[i+1])
                    if m2:
                        return m2.group(0)
        return None

    def _found(self, content: List[str], method: str) -> Dict[str, Any]:
        self.logger.info(f"FOUND: email via {method}")
        return {
            "field_name": self.field_name,
            "found": True,
            "content": content,
            "confidence": 0.95,
            "metadata": {"method": method}
        }

    def _not_found(self) -> Dict[str, Any]:
        self.logger.info("NOT_FOUND: email")
        return {
            "field_name": self.field_name,
            "found": False,
            "content": None,
            "confidence": 0.0,
            "metadata": {}
        }

if __name__ == "__main__":
    demo = """Instructor: Jane Doe
    Email: jane.doe@unh.edu
    Office Hours: Tue 2–4pm (Zoom)
    """
    print(emailDetector().detect(demo))

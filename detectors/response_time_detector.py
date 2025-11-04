"""
Response Time Detector
Extracts instructor response time from syllabus contact sections
"""

import re
from typing import Dict, Any


class ResponseTimeDetector:
    """Detects instructor response time in contact areas"""

    def __init__(self):
        self.time_patterns = [
            r'(?i)response\s+time\s*:?\s*([^\n.;]{0,100}?(?:\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?[^\n.;]{0,50}?))',
            r'(?i)(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?(?:\s+on\s+\w+)?(?:\s*\([^)]{0,30}\))?)',
            r'(?i)(?:respond(?:s)?|reply|replies?)\s+(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?(?:\s+on\s+\w+)?)',
            r'(?i)(typically|usually)\s+(?:respond(?:s)?|reply|replies?)?\s*(?:to\s+emails?\s*)?(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day)s?(?:\s*\([^)]{0,30}\))?)',
            r'(?i)(?:I\'ll|I\s+will|you\'ll\s+get\s+a)\s+(?:respond|reply)\s+(?:no\s+later\s+than\s+)?(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day)s?)',
            r'(?i)(\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?)\s+response\s+time',
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(24-48\s*hours?)',
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(24\s*hours?)(?:\s+on\s+\w+)?',
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(48\s*hours?)(?:\s+on\s+\w+)?',
            r'(?i)(within\s+)?\d+\s+business\s+days?',
            r'(?i)((?:by\s+)?(?:the\s+)?next\s+(?:business\s+)?day)',
        ]
        
        self.contact_keywords = [
            'contact', 'email', 'office hour', 'communication',
            'preferred contact', 'reach me', 'get in touch',
            'response time', 'availability'
        ]

    def _find_contact_windows(self, text: str) -> list:
        if not text:
            return []
        
        windows = []
        for keyword in self.contact_keywords:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(text):
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 800)
                windows.append((start, end))
        
        if not windows:
            return []
        
        windows.sort()
        merged = [windows[0]]
        for start, end in windows[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged

    def _extract_contact_text(self, text: str) -> str:
        windows = self._find_contact_windows(text)
        
        if not windows:
            first_chunk = text[:2000]
            if re.search(r'(?i)(email|contact)', first_chunk):
                return first_chunk
            return ""
        
        contact_text = ""
        for start, end in windows:
            contact_text += text[start:end] + "\n"
        
        return contact_text

    def _has_explicit_time(self, text: str) -> bool:
        if not text:
            return False
        
        text_lower = text.lower()
        has_time_unit = bool(re.search(r'\d+\s*(?:hour|hr|day|business\s+day)s?', text_lower))
        if not has_time_unit:
            has_time_unit = bool(re.search(r'next\s+(?:business\s+)?day', text_lower))
        
        vague_terms = ['may vary', 'varies', 'depends', 'as soon as possible', 'asap', 'promptly']
        has_vague = any(term in text_lower for term in vague_terms)
        
        return has_time_unit and not has_vague

    def _is_false_positive(self, text: str, context: str = "") -> bool:
        if not text:
            return False
        
        text_lower = text.lower()
        context_lower = context.lower() if context else ""
        combined = (text_lower + " " + context_lower).strip()
        
        deadline_patterns = [
            r'\bassignments?\b', r'\bhomeworks?\b', r'\bsubmit\b', r'\bdue\b', r'\bdeadline\b',
            r'\bexams?\b', r'\bquizz?(?:es)?\b', r'\btests?\b', r'\bprojects?\b', 
            r'\blate\b', r'\bturn\s+in\b'
        ]
        for pattern in deadline_patterns:
            matches = re.finditer(pattern, combined, re.IGNORECASE)
            for match in matches:
                start = match.start()
                end = match.end()
                prefix = combined[max(0, start-5):start]
                suffix = combined[end:min(len(combined), end+5)]
                if '@' in prefix or '@' in suffix or '.com' in suffix or '.edu' in suffix or '.org' in suffix:
                    continue
                return True
        
        tech_support_patterns = [
            r'tech\s+help.*hours?\s+a\s+day',
            r'technical\s+support.*hours?\s+a\s+day',
            r'help\s+desk.*available',
            r'support\s+hours?:',
            r'hours?\s+a\s+day.*seven\s+days',
            r'hours?\s+a\s+day.*7\s+days',
            r'available\s+24.*hours',
            r'canvas\s+support',
            r'\bit\s+support',
            r'24/7.*support',
            r'\d+-\d+-\d+\(24\s?hours?\)',
            r'24\s?hours?\)',
            r'hotline.*24\s?hours?',
            r'24\s?hours?.*hotline',
            r'sharpp|ywca|crisis|domestic\s+violence|sexual\s+assault',
            r'emergency.*\d{3}-\d{3}-\d{4}',
        ]
        for pattern in tech_support_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        
        duration_terms = [
            'course runs', 'total hours', 'credit hours', 'per week',
            'hours of instruction', 'contact hours', 'lecture hours'
        ]
        if any(term in combined for term in duration_terms):
            return True
        
        return False

    def _clean_response_time(self, text: str) -> str:
        if not text:
            return ""
        
        text = ' '.join(text.split())
        text = re.sub(r'(?i)^response\s+time\s*:?\s*', '', text)
        text = text.lstrip('-–—').strip()
        text = text.rstrip('.,;:')
        text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', text)
        text = re.sub(r'(\d+)(hours?|hrs?|days?)', r'\1 \2', text)
        text = re.sub(r'(\d+)\s+(hour|hr|day)\b', r'\1 \2s', text)
        
        return text.strip()

    def detect(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"found": False, "content": "Missing"}
        
        contact_text = self._extract_contact_text(text)
        if not contact_text:
            return {"found": False, "content": "Missing"}
        
        best_match = None
        best_score = 0
        
        for pattern in self.time_patterns:
            for match in re.finditer(pattern, contact_text, re.MULTILINE | re.IGNORECASE):
                candidate = match.group(1) if match.lastindex else match.group(0)
                candidate = candidate.strip()
                
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(contact_text), match.end() + 100)
                context = contact_text[start_pos:end_pos]
                
                if not self._has_explicit_time(candidate):
                    continue
                
                if self._is_false_positive(candidate, context):
                    continue
                
                score = 1
                if 'response time' in candidate.lower():
                    score += 3
                if 'within' in candidate.lower():
                    score += 2
                if re.search(r'\d+\s*(?:hour|day)', candidate, re.IGNORECASE):
                    score += 2
                if '(' in candidate or 'business' in candidate.lower():
                    score += 1
                
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        if best_match:
            cleaned = self._clean_response_time(best_match)
            if cleaned and self._has_explicit_time(cleaned):
                return {"found": True, "content": cleaned}
        
        return {"found": False, "content": "Missing"}


def detect_response_time(text: str) -> str:
    detector = ResponseTimeDetector()
    result = detector.detect(text)
    return result.get("content", "Missing")
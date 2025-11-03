"""
Response Time Detector - Focused Version
Only searches near contact/email areas and requires explicit time mentions.
Returns 'Missing' when not found or when time is vague.
"""

import re
from typing import Dict, Any, Optional


class ResponseTimeDetector:
    """Detects instructor response time ONLY in contact areas with explicit times."""

    def __init__(self):
        # ✅ Only patterns that capture EXPLICIT time values (hours/days)
        self.time_patterns = [
            # "Response time: X hours/days" format
            r'(?i)response\s+time\s*:?\s*([^\n.;]{0,100}?(?:\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?[^\n.;]{0,50}?))',
            
            # "within X hours/days" - must have number + unit
            r'(?i)(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?(?:\s+on\s+\w+)?(?:\s*\([^)]{0,30}\))?)',
            
            # "respond/reply within X hours/days"
            r'(?i)(?:respond(?:s)?|reply|replies?)\s+(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?(?:\s+on\s+\w+)?)',
            
            # "typically/usually within X hours/days"
            r'(?i)(typically|usually)\s+(?:respond(?:s)?|reply|replies?)?\s*(?:to\s+emails?\s*)?(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day)s?(?:\s*\([^)]{0,30}\))?)',
            
            # "I'll respond/reply within X"
            r'(?i)(?:I\'ll|I\s+will|you\'ll\s+get\s+a)\s+(?:respond|reply)\s+(?:no\s+later\s+than\s+)?(within\s+\d+(?:-\d+)?\s*(?:hour|hr|day)s?)',
            
            # "X hours/days response time"
            r'(?i)(\d+(?:-\d+)?\s*(?:hour|hr|day|business\s+day)s?)\s+response\s+time',
            
            # "24 hours", "48 hours", "24-48 hours" (standalone with context)
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(24-48\s*hours?)',
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(24\s*hours?)(?:\s+on\s+\w+)?',
            r'(?i)(?:within\s+|typically\s+|usually\s+)?(48\s*hours?)(?:\s+on\s+\w+)?',
            
            # "X business days"
            r'(?i)(within\s+)?\d+\s+business\s+days?',
            
            # "next business day" / "next day"
            r'(?i)((?:by\s+)?(?:the\s+)?next\s+(?:business\s+)?day)',
        ]
        
        # Keywords that indicate we're in the contact section
        self.contact_keywords = [
            'contact', 'email', 'office hour', 'communication',
            'preferred contact', 'reach me', 'get in touch',
            'response time', 'availability'
        ]

    def _find_contact_windows(self, text: str) -> list:
        """
        Find specific text windows around contact-related keywords.
        Returns list of (start, end) positions for contact areas.
        """
        if not text:
            return []
        
        windows = []
        text_lower = text.lower()
        
        # Search for each contact keyword
        for keyword in self.contact_keywords:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(text):
                # Create a window: 200 chars before, 800 chars after the keyword
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 800)
                windows.append((start, end))
        
        # Merge overlapping windows
        if not windows:
            return []
        
        windows.sort()
        merged = [windows[0]]
        for start, end in windows[1:]:
            if start <= merged[-1][1]:  # Overlapping
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged

    def _extract_contact_text(self, text: str) -> str:
        """Extract only the text from contact-related areas."""
        windows = self._find_contact_windows(text)
        
        if not windows:
            # Fallback: check first 2000 chars if it mentions email/contact
            first_chunk = text[:2000]
            if re.search(r'(?i)(email|contact)', first_chunk):
                return first_chunk
            return ""
        
        # Combine all contact windows
        contact_text = ""
        for start, end in windows:
            contact_text += text[start:end] + "\n"
        
        return contact_text

    def _has_explicit_time(self, text: str) -> bool:
        """
        Check if text has explicit time mention (numbers + hours/days).
        Reject vague terms like "may vary", "as soon as possible", etc.
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Must have explicit time unit
        has_time_unit = bool(re.search(r'\d+\s*(?:hour|hr|day|business\s+day)s?', text_lower))
        if not has_time_unit:
            # Allow "next day" / "next business day"
            has_time_unit = bool(re.search(r'next\s+(?:business\s+)?day', text_lower))
        
        # Reject vague terms
        vague_terms = ['may vary', 'varies', 'depends', 'as soon as possible', 'asap', 'promptly']
        has_vague = any(term in text_lower for term in vague_terms)
        
        return has_time_unit and not has_vague

    def _is_false_positive(self, text: str, context: str = "") -> bool:
        """
        Check if this is a false positive (not actually response time).
        Checks both the extracted text and surrounding context.
        """
        if not text:
            return False
        
        text_lower = text.lower()
        context_lower = context.lower() if context else ""
        combined = (text_lower + " " + context_lower).strip()
        
        # Assignment/homework deadlines - but exclude if part of email/domain
        deadline_patterns = [
            r'\bassignments?\b', r'\bhomeworks?\b', r'\bsubmit\b', r'\bdue\b', r'\bdeadline\b',
            r'\bexams?\b', r'\bquizz?(?:es)?\b', r'\btests?\b', r'\bprojects?\b', 
            r'\blate\b', r'\bturn\s+in\b'
        ]
        for pattern in deadline_patterns:
            matches = re.finditer(pattern, combined, re.IGNORECASE)
            for match in matches:
                # Check if this match is part of an email/domain
                start = match.start()
                end = match.end()
                # Look at surrounding chars to see if it's in an email
                prefix = combined[max(0, start-5):start]
                suffix = combined[end:min(len(combined), end+5)]
                # If surrounded by email/domain indicators, skip it
                if '@' in prefix or '@' in suffix or '.com' in suffix or '.edu' in suffix or '.org' in suffix:
                    continue
                # Otherwise, it's a real deadline term
                return True
        
        # Tech support / help desk / hotline availability (not instructor response)
        tech_support_patterns = [
            r'tech\s+help.*hours?\s+a\s+day',  # "tech help 24 hours a day"
            r'technical\s+support.*hours?\s+a\s+day',  # "technical support 24 hours a day"
            r'help\s+desk.*available',  # "help desk available"
            r'support\s+hours?:',  # "support hours:"
            r'hours?\s+a\s+day.*seven\s+days',  # "24 hours a day, seven days"
            r'hours?\s+a\s+day.*7\s+days',  # "24 hours a day, 7 days"
            r'available\s+24.*hours',  # "available 24 hours"
            r'canvas\s+support',  # "canvas support"
            r'\bit\s+support',  # "IT support"
            r'24/7.*support',  # "24/7 support"
            r'\d+-\d+-\d+\(24\s?hours?\)',  # "603-668-2299(24hour)" - phone with 24hour
            r'24\s?hours?\)',  # "24hour)" - closing paren indicates phone context
            r'hotline.*24\s?hours?',  # "hotline 24 hour"
            r'24\s?hours?.*hotline',  # "24 hour hotline"
            r'sharpp|ywca|crisis|domestic\s+violence|sexual\s+assault',  # Crisis resources
            r'emergency.*\d{3}-\d{3}-\d{4}',  # Emergency contact numbers
        ]
        for pattern in tech_support_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        
        # Course duration / total hours
        duration_terms = [
            'course runs', 'total hours', 'credit hours', 'per week',
            'hours of instruction', 'contact hours', 'lecture hours'
        ]
        if any(term in combined for term in duration_terms):
            return True
        
        return False

    def _clean_response_time(self, text: str) -> str:
        """Clean and normalize the extracted response time."""
        if not text:
            return ""
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove leading "response time:" if present
        text = re.sub(r'(?i)^response\s+time\s*:?\s*', '', text)
        
        # Remove leading dash/hyphen
        text = text.lstrip('-–—').strip()
        
        # Remove trailing punctuation
        text = text.rstrip('.,;:')
        
        # Normalize spacing around hyphens in ranges: "24- 48" -> "24-48"
        text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', text)
        
        # Normalize "24hours" -> "24 hours"
        text = re.sub(r'(\d+)(hours?|hrs?|days?)', r'\1 \2', text)
        
        # Normalize singular to plural: "24 hour" -> "24 hours", "2 day" -> "2 days"
        text = re.sub(r'(\d+)\s+(hour|hr|day)\b', r'\1 \2s', text)
        
        return text.strip()

    def detect(self, text: str) -> Dict[str, Any]:
        """Main detection - only return if explicit time found in contact area."""
        if not text:
            return {"found": False, "content": "Missing"}
        
        # Step 1: Extract only contact-related text
        contact_text = self._extract_contact_text(text)
        
        if not contact_text:
            return {"found": False, "content": "Missing"}
        
        # Step 2: Search for time patterns in contact text only
        best_match = None
        best_score = 0
        
        for pattern in self.time_patterns:
            for match in re.finditer(pattern, contact_text, re.MULTILINE | re.IGNORECASE):
                candidate = match.group(1) if match.lastindex else match.group(0)
                candidate = candidate.strip()
                
                # Get surrounding context (100 chars before and after)
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(contact_text), match.end() + 100)
                context = contact_text[start_pos:end_pos]
                
                # Validate: must have explicit time and not be false positive
                if not self._has_explicit_time(candidate):
                    continue
                
                if self._is_false_positive(candidate, context):
                    continue
                
                # Score based on specificity (prefer more specific patterns)
                score = 1
                if 'response time' in candidate.lower():
                    score += 3
                if 'within' in candidate.lower():
                    score += 2
                if re.search(r'\d+\s*(?:hour|day)', candidate, re.IGNORECASE):
                    score += 2
                if '(' in candidate or 'business' in candidate.lower():
                    score += 1
                
                # Keep the best match
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        # Step 3: Return best match if found
        if best_match:
            cleaned = self._clean_response_time(best_match)
            if cleaned and self._has_explicit_time(cleaned):
                return {"found": True, "content": cleaned}
        
        return {"found": False, "content": "Missing"}


def detect_response_time(text: str) -> str:
    """
    Detect response time from syllabus text.
    Returns explicit time or 'Missing' if not found.
    """
    detector = ResponseTimeDetector()
    result = detector.detect(text)
    return result.get("content", "Missing")


# ✅ TEST CASES
if __name__ == "__main__":
    test_cases = [
        # Should FIND
        ("Contact: email@test.com. Response time: within 24 hours", "within 24 hours"),
        ("Preferred contact: Email. I typically respond within 48 hours (business days).", "within 48 hours (business days)"),
        ("Email me at test@test.com. I'll reply within 24 hours on weekdays.", "within 24 hours on weekdays"),
        ("Contact info: Response time - 24-48 hours", "24-48 hours"),
        ("Office Hours: Mon 2-4pm. Email response: typically within 2 business days", "within 2 business days"),
        ("Get in touch via email. I usually reply within 24 hours.", "within 24 hours"),
        ("Contact: test@test.com. Expect response within 48 hours.", "within 48 hours"),
        
        # Should return MISSING - False Positives
        ("Assignments are due within 24 hours of posting.", "Missing"),  # Assignment deadline
        ("Response time may vary depending on volume.", "Missing"),  # Vague
        ("I'll respond as soon as possible.", "Missing"),  # No explicit time
        ("Email: test@test.com", "Missing"),  # No response time mentioned
        ("The course runs for 24 hours of instruction.", "Missing"),  # Not response time
        ("Submit homework within 48 hours", "Missing"),  # Assignment, not response
        ("No contact information provided", "Missing"),
        
        # NEW: Crisis hotline false positives (the new bug!)
        ("YWCA, NH – 603-668-2299(24hour), 72 Concord St. Manchester", "Missing"),  # Hotline availability
        ("SHARPP: 603-862-7233(24hour), 8 Ballard Street", "Missing"),  # Hotline availability
        ("24 Hour NH Sexual Violence Hotline: 1-800-277-5570", "Missing"),  # Hotline
        ("24 Hour NH Domestic Violence Hotline: 1-866-644-3574", "Missing"),  # Hotline
        
        # Test singular hour normalization
        ("Contact: test@test.com. I will respond within 24 hour", "within 24 hours"),  # Should normalize to plural
    ]

    print("\n" + "="*70)
    print("FOCUSED RESPONSE TIME DETECTOR - TEST RESULTS")
    print("="*70 + "\n")
    
    passed = 0
    failed = 0
    
    for i, (text, expected) in enumerate(test_cases, 1):
        result = detect_response_time(text)
        is_correct = (result.lower() == expected.lower())
        
        status = "✓ PASS" if is_correct else "✗ FAIL"
        
        print(f"Test {i}: {status}")
        print(f"  Input: {text[:80]}{'...' if len(text) > 80 else ''}")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        
        if is_correct:
            passed += 1
        else:
            failed += 1
        print()
    
    print("="*70)
    print(f"RESULTS: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.1f}%)")
    print(f"         {failed} failed")
    print("="*70 + "\n")
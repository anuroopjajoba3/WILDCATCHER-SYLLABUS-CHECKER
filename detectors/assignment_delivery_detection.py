"""
Assignment Delivery Detector - Improved Version
Detects where/how assignments are submitted in syllabi
Optimized based on ground truth analysis
"""

import re
from typing import Dict, Any, List, Set


class AssignmentDeliveryDetector:
    """Detector for assignment delivery platforms/methods in syllabi"""
    
    def __init__(self):
        # Platform detection patterns - order matters!
        self.platform_patterns = [
            # MyCourses variations (check these first before Canvas)
            (r'(?i)\bunh\s+mycourses\b', 'UNH MyCourses'),
            (r'(?i)\bmycourses\b', 'MyCourses'),
            
            # Canvas with MyCourses in parentheses
            (r'(?i)\bcanvas\s*\(\s*mycourses\s*\)', 'Canvas (MyCourses)'),
            
            # Plain Canvas (after checking for MyCourses variations)
            (r'(?i)\bcanvas\b', 'Canvas'),
            
            # Assignment-specific platforms
            (r'(?i)\bmyopenmath\b', 'MyOpenMath'),
            (r'(?i)\bmastering\s*(?:a\s*&\s*p|anatomy\s*(?:and|&)\s*physiology)', 'Mastering A&P'),
            (r'(?i)\bmasteringphysics\b', 'MasteringPhysics'),
            (r'(?i)\bmastering\s+physics\b', 'MasteringPhysics'),
            
            # Other LMS platforms
            (r'(?i)\bblackboard\b', 'Blackboard'),
            (r'(?i)\bgoogle\s+classroom\b', 'Google Classroom'),
            (r'(?i)\bmoodle\b', 'Moodle'),
            (r'(?i)\bturnitin\b', 'Turnitin'),
            
            # Physical delivery methods - check for longer phrases first
            (r'(?i)\bwritten\s+assignments?\s+collected\s+in\s+class\b', 'Written assignments collected in class'),
            (r'(?i)\bcollected\s+in\s+class\b', 'Collected in class'),
            (r'(?i)\bin\s*-?\s*person\s+submission\b', 'In-person submission'),
            (r'(?i)\bhanded?\s+in\b', 'Handed in'),
        ]
        
        # Noise phrases to remove when extracting platforms
        self.noise_patterns = [
            r'\(embedded\s+in\s+[^)]+\)',  # (embedded in Canvas)
            r'\([^)]*grades?[^)]*\)',      # (grades)
            r'\bembedded\s+in\b',
            r'\bfor\s+grades?\b',
        ]
        
        # Strong section indicators
        self.section_indicators = [
            r'(?i)^\s*assignment\s+(?:delivery|submission|platform)\s*:?',
            r'(?i)^\s*submission\s+(?:method|platform|process)\s*:?',
            r'(?i)^\s*how\s+to\s+submit\s*:?',
            r'(?i)^\s*where\s+to\s+submit\s*:?',
            r'(?i)^\s*(?:course|class)\s+(?:platform|management\s+system)\s*:?',
        ]
        
        # Context patterns indicating assignment delivery
        self.context_patterns = [
            r'(?i)assignments?\s+(?:are\s+)?(?:submitted|uploaded|turned\s+in|posted|delivered)\s+(?:via|on|to|through|using|in)',
            r'(?i)submit\s+(?:all\s+)?(?:your\s+)?(?:assignments?|work|papers?|homework)\s+(?:via|on|to|through|using|in)',
            r'(?i)(?:upload|post|turn\s+in)\s+(?:your\s+)?(?:assignments?|work|homework)\s+(?:via|on|to|through|in)',
            r'(?i)all\s+(?:assignments?|work|homework)\s+(?:will\s+be\s+)?(?:submitted|posted|uploaded)\s+(?:via|on|to|in)',
            r'(?i)(?:assignments?|homework)\s+(?:should|must)\s+be\s+(?:submitted|uploaded|posted|turned\s+in)\s+(?:via|on|to|in)',
        ]
        
        # Weak signals (grades posting, course materials location)
        self.weak_signal_patterns = [
            r'(?i)\bgrades?\s+(?:are\s+)?(?:posted|available|viewable)\s+(?:on|in)',
            r'(?i)\bcourse\s+materials?\s+(?:are\s+)?(?:on|in|available\s+(?:on|in))',
            r'(?i)\bsyllabus\s+(?:is\s+)?(?:posted\s+)?(?:on|in)',
            r'(?i)\bresources?\s+(?:are\s+)?(?:on|in)',
        ]
    
    def _clean_line_for_extraction(self, line: str) -> str:
        """Remove noise phrases from line"""
        cleaned = line
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def _extract_platforms_from_text(self, text: str) -> Set[str]:
        """Extract all platform names from text"""
        platforms = set()
        
        # Clean the text
        cleaned = self._clean_line_for_extraction(text)
        
        # Apply each pattern
        for pattern, platform_name in self.platform_patterns:
            if re.search(pattern, cleaned):
                platforms.add(platform_name)
        
        return platforms
    
    def _has_section_indicator(self, line: str) -> bool:
        """Check if line is a section header about assignment delivery"""
        return any(re.search(p, line) for p in self.section_indicators)
    
    def _has_delivery_context(self, line: str) -> bool:
        """Check if line has strong assignment delivery context"""
        return any(re.search(p, line) for p in self.context_patterns)
    
    def _is_weak_signal(self, line: str) -> bool:
        """Check if line is just about grades/materials (not submission)"""
        return any(re.search(p, line) for p in self.weak_signal_patterns)
    
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect assignment delivery platform/method in syllabus text.
        
        Args:
            text: Full syllabus text
            
        Returns:
            Dict with:
                - 'found' (bool): Whether delivery info was detected
                - 'content' (str): The detected platform(s)
                - 'confidence' (float): Confidence score (0-100)
        """
        if not text or not text.strip():
            return {
                "found": False,
                "content": "",
                "confidence": 0.0
            }
        
        lines = text.split('\n')
        candidates = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty, very short, or very long lines
            if not line_stripped or len(line_stripped) < 5 or len(line_stripped) > 500:
                continue
            
            # Skip weak signal lines (grades posting, etc.)
            if self._is_weak_signal(line_stripped) and not self._has_delivery_context(line_stripped):
                continue
            
            # Check for section indicators and context
            is_section = self._has_section_indicator(line_stripped)
            has_context = self._has_delivery_context(line_stripped)
            
            # Extract platforms from this line
            platforms = self._extract_platforms_from_text(line_stripped)
            
            if not platforms:
                continue
            
            # Calculate score
            score = 50  # Base score for finding platform(s)
            
            # Major boost for section headers
            if is_section:
                score += 40
            
            # Boost for explicit delivery context
            if has_context:
                score += 35
            
            # Position boost (earlier in document = more authoritative)
            position_ratio = i / max(len(lines), 1)
            if position_ratio < 0.15:
                score += 25
            elif position_ratio < 0.35:
                score += 18
            elif position_ratio < 0.55:
                score += 10
            elif position_ratio < 0.75:
                score += 5
            
            # Boost for multiple platforms
            if len(platforms) > 1:
                score += 12
            
            # Format content - join multiple platforms
            # Sort for consistency but preserve original casing
            platform_list = sorted(list(platforms), key=lambda x: x.lower())
            content = '; '.join(platform_list)
            
            candidates.append({
                'content': content,
                'score': score,
                'line': i,
                'has_context': has_context,
                'is_section': is_section,
                'platform_count': len(platforms)
            })
        
        # Select best candidate
        if candidates:
            # Sort by multiple criteria
            best = max(candidates, key=lambda x: (
                x['score'],
                x['is_section'],
                x['has_context'],
                x['platform_count'],
                -x['line']  # Earlier is better (negative for max)
            ))
            
            # Calculate confidence (max theoretical score ~162)
            confidence = min(100.0, (best['score'] / 162.0) * 100)
            
            # Set minimum confidence
            if confidence < 45:
                confidence = 45
            
            return {
                'found': True,
                'content': best['content'],
                'confidence': round(confidence, 2)
            }
        
        return {
            'found': False,
            'content': '',
            'confidence': 0.0
        }


def detect_assignment_delivery(text: str) -> str:
    """
    Standalone convenience function.
    
    Args:
        text: Full syllabus text
        
    Returns:
        The detected platform(s) or empty string
    """
    detector = AssignmentDeliveryDetector()
    result = detector.detect(text)
    return result.get('content', '') if result.get('found') else ''


if __name__ == "__main__":
    # Test cases based on actual ground truth
    test_cases = [
        ("Assignments are submitted via myCourses.", "MyCourses"),
        ("Submit all work through Canvas.", "Canvas"),
        ("MyOpenMath (embedded in Canvas); Written Assignments collected in class", 
         "Canvas; MyOpenMath; Written assignments collected in class"),
        ("Use MasteringPhysics for homework.", "MasteringPhysics"),
        ("Assignments delivered through UNH MyCourses", "UNH MyCourses"),
        ("Upload assignments to Canvas (myCourses)", "Canvas (MyCourses)"),
        ("Grades are posted on Canvas. Submit work via MyCourses and Mastering A&P", 
         "Mastering A&P; MyCourses"),
        ("All assignments submitted via Canvas (MyCourses)", "Canvas (MyCourses)"),
        ("Submit homework on MyCourses; Mastering A&P", "Mastering A&P; MyCourses"),
    ]
    
    detector = AssignmentDeliveryDetector()
    
    print("Testing Assignment Delivery Detector:")
    print("=" * 70)
    
    for text, expected in test_cases:
        result = detector.detect(text)
        found = result.get('content', '')
        confidence = result.get('confidence', 0)
        
        # Normalize for comparison
        found_norm = {p.strip().lower() for p in found.split(';') if p.strip()}
        expected_norm = {p.strip().lower() for p in expected.split(';') if p.strip()}
        
        match = found_norm == expected_norm
        status = "✓" if match else "✗"
        
        print(f"\n{status} Test case:")
        print(f"  Input: {text}")
        print(f"  Expected: {expected}")
        print(f"  Got: {found} (confidence: {confidence}%)")
        if not match:
            print(f"  Expected set: {expected_norm}")
            print(f"  Got set: {found_norm}")
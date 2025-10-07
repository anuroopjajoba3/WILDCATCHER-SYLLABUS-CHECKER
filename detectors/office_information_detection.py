"""
Detects professor office location, office hours, and phone number from syllabus text.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class DetectionResult:
    """
    Result of a detection operation.
    """
    found: bool = False
    content: Optional[str] = None
    all_matches: List[str] = None

    def __post_init__(self):
        """Initialize all_matches as empty list if None."""
        if self.all_matches is None:
            self.all_matches = []

class BaseDetector:
    """
    Base class for field detection with common functionality.
    """
    def __init__(self, field_name: str, search_limit: int = 5000):
        self.field_name = field_name
        self.search_limit = search_limit
        self.logger = logging.getLogger(f'detector.{field_name}')
        self.patterns = self._init_patterns()

    def _init_patterns(self) -> List[re.Pattern]:
        raise NotImplementedError

    def detect(self, text: str) -> DetectionResult:
        search_text = text[:self.search_limit] if len(text) > self.search_limit else text
        matches = self._find_all_matches(search_text)
        if matches:
            processed = self._process_matches(matches, text)
            if processed:
                return DetectionResult(
                    found=True,
                    content=processed[0],
                    all_matches=processed
                )
        return DetectionResult()

    def _find_all_matches(self, text: str) -> List[str]:
        all_matches = []
        for i, pattern in enumerate(self.patterns):
            matches = pattern.findall(text)
            if matches:
                self.logger.debug(f"Pattern {i+1} found: {matches}")
                all_matches.extend(matches)
        return all_matches

    def _process_matches(self, matches: List, text: str) -> List[str]:
        raise NotImplementedError

class LocationDetector(BaseDetector):
    def __init__(self):
        super().__init__('location', 5000)
        self.classroom_indicators = [
            r'Class\s*Meeting',
            r'Lab\s*Meeting',
            r'Time\s*and\s*Location.*room'
        ]
    def _init_patterns(self) -> List[re.Pattern]:
        patterns = [
            r'Office\s*Hours?:.*?,\s*Room\s*(\d+[A-Z]?)',
            r'Office:\s*Room\s*(\d+[A-Z]?)',
            r'Pand[o]?ra\s+(?:Rm\.?|Room)\s*(\d+[A-Z]?)',
            r'Office:\s*Pand[o]?ra\s*(?:Building)?,?\s*Room\s*(\d+[A-Z]?)',
            r'Office\s*(?:Location)?/?(?:Hours)?:\s*Pand[o]?ra\s*(?:Building)?,?\s*Room\s*(\d+[A-Z]?)',
            r'\(office:\s*room\s*(\d+[A-Z]?)',
            r'Pand[o]?ra\s+Lab\s*(\d+[A-Z]?)',
            r'(?:Office|Contact\s*Information)[^\n]{0,50}Room\s*(\d+[A-Z]?)',
            r'(?:Instructor|Professor|Faculty|Office|OFFICE)[^\n]{0,150}(?:Room|Rm\.?)\s*(\d+[A-Z]?)',
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]
    def _process_matches(self, matches: List[str], text: str) -> List[str]:
        unique_rooms = []
        seen = set()
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ''
            room = match.strip() if match else ''
            if room and re.match(r'^\d+[A-Z]?$', room) and room not in seen:
                if self._is_office_context(room, text):
                    formatted = f"Pandora Room {room}"
                    unique_rooms.append(formatted)
                    seen.add(room)
        return unique_rooms
    def _is_office_context(self, room: str, text: str) -> bool:
        room_pattern = rf'(?:Room|Rm\.?)\s*{re.escape(room)}'
        for indicator in self.classroom_indicators:
            pattern = rf'{indicator}.{{0,100}}{room_pattern}'
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                self.logger.debug(f"Room {room} appears to be classroom")
                return False
        office_patterns = [
            rf'Office[^{{}}]*{room_pattern}',
            rf'Instructor[^{{}}]*{room_pattern}',
            rf'Professor[^{{}}]*{room_pattern}',
            rf'{room_pattern}[^{{}}]*(?:Phone|Email|Hours)'
        ]
        for pattern in office_patterns:
            if re.search(pattern, text[:2000], re.IGNORECASE | re.DOTALL):
                return True
        return True

class HoursDetector(BaseDetector):
    INVALID_PHRASES = [
        'to discuss', 'ideas and', 'material', 'students are encouraged',
        'encourage', 'question', 'problem', 'assignment', 'to join',
        'meeting)', 'click here', 'available for', 'feel free'
    ]
    VALID_INDICATORS = [
        r'\d{1,2}:\d{2}',
        r'\d{1,2}\s*[ap]\.m',
        r'monday|tuesday|wednesday|thursday|friday',
        r'\b[MTWRF]\s+\d',
        r'appointment',
        r'zoom',
        r'virtual',
        r'TBD',
        r'anytime',
        r'available',
        r'scheduled',
        r'office\s*hours?'
    ]
    def __init__(self):
        super().__init__('hours', 2000)
    def _init_patterns(self) -> List[re.Pattern]:
        patterns = [
            r'(?:Office\s*)?Hours?\s*[:]\s*(TBD)',
            r'hours\s+(TBD)',
            r'Office\s+hours\s+(TBD)',
            r'Office\s*(?:Hours?|Hrs?)[\s:]+([^\n]{5,100}?)(?=\n|$|Phone|Email|Web)',
            r'OFFICE\s*HOURS?[\s:]+([^\n]{5,100}?)(?=\n|$|PHONE|EMAIL)',
            r'virtual\s*office\s*hrs?\.?[:]?\s*([^\n]{5,100}?)(?=\n|$|I am)',
            r'Virtual\s*office\s*hours?\s*([^\n]{5,100}?)(?=\n|$)',
            r'Office\s*Location/?Hours?:[^;]+;\s*([TWMRF]\s+\d{1,2}:\d{2}[^.\n]+)',
            r'(?:Office\s*)?Hours?[\s:]+([^;\n]+(?:[;\n]+[^;\n]+)*?)(?=\s*(?:Phone|Email|Course|$))',
            r'(?:Office\s*)?Hours?[\s:]+\n((Monday|Tuesday|Wednesday|Thursday|Friday)\s*[-:]\s*\d{1,2}:\d{2}\s*[-�\u2013\u2014]\s*\d{1,2}:\d{2}\s*(?:\n(Monday|Tuesday|Wednesday|Thursday|Friday)\s*[-:]\s*\d{1,2}:\d{2}\s*[-�\u2013\u2014]\s*\d{1,2}:\d{2})+)',
            r'(?:Office\s*)?Hours?[\s:]+((Monday|Tuesday|Wednesday|Thursday|Friday)\s*[-:]\s*\d{1,2}:\d{2}\s*[-�]\s*\d{1,2}:\d{2}\s*(?:\s+(Monday|Tuesday|Wednesday|Thursday|Friday)\s*[-:]\s*\d{1,2}:\d{2}\s*[-�]\s*\d{1,2}:\d{2})+)',
            r'(?:Hours?|Hrs?)[\s:]+([MTWRF][a-z]*[^.\n]{5,80}?)(?=\.|$|\n|Phone)',
            r'(?:Hours?|Hrs?)[\s:]+(\d{1,2}:\d{2}\s*[ap]m[^.\n]{0,80}?)(?=\.|$|\n)',
            r'(?:Office\s*)?Hours?[\s:]+([Bb]y\s+appointment[^.\n]{0,80})(?=\.|$|\n)',
            r'Office\s*hours?\s+are\s+(schedule[d]?\s+by\s+appointment[^\n]{0,50})',
            r'(?:Office\s*)?Hours?[\s:]+([Bb]y\s+appointment[^;]*;\s*(?:available\s+)?in\s+person\s+or\s+virtual[^\n]*)',
            r'(?:Office\s*)?Hours?[\s:]+([Aa]vailable\s+in\s+person\s+or\s+virtually[^\n.]{0,100})',
            r'(?:Office\s*)?Hours?[\s:]+([Aa]vailable\s+(?:in\s+person|virtually)[^\n]{0,80})',
            r'OFFICE\s*HOURS?[\s:]+([Aa]nytime\s+by\s+(?:ZOOM|zoom|Zoom)[^\n]{0,80})(?=\.|$|\n)',
            r'(?:Office\s*hours?\s+are\s+)?([Mm]ondays?\s+\d{1,2}(?:[-:]\d{1,2})?\s*[ap]m\s*via\s*Zoom[^\n]{0,50})',
            r'([Mm]ondays?\s+\d{1,2}[-:]\d{1,2}\s*[ap]m[^,\n]*(?:,\s*plus\s+by\s+appointment)?)',
            r'(?:Office\s*)?Hours?[\s:]+(?:on\s+)?([MTWRF][^\n]{5,80}?)(?=\.|$|\n|,\s*Room)',
            r'(?:Office\s*)?Hours?[\s:]+(\d{1,2}(?::\d{2})?\s*[ap]m[^\n]{0,80}?)(?=\.|$|\n|,\s*Room)',
        ]
        return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
    def detect(self, text: str) -> DetectionResult:
        search_text = text[:self.search_limit] if len(text) > self.search_limit else text
        tbd_patterns = [
            re.compile(r'(?:Office\s*)?Hours?\s*[:]\s*(TBD)', re.IGNORECASE),
            re.compile(r'hours\s+(TBD)', re.IGNORECASE),
            re.compile(r'Office\s+hours\s+(TBD)', re.IGNORECASE),
        ]
        for pattern in tbd_patterns:
            if pattern.search(search_text):
                return DetectionResult(found=True, content='TBD', all_matches=['TBD'])
        return super().detect(text)
    def _process_matches(self, matches: List[str], text: str) -> List[str]:
        valid_hours = []
        seen = set()
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ''
            if match:
                cleaned = match.strip()
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    valid_hours.append(cleaned)
        return valid_hours

class PhoneDetector(BaseDetector):
    def __init__(self):
        super().__init__('phone', 2000)
    def _init_patterns(self) -> List[re.Pattern]:
        digit_pattern = r'([(\d][\d\s().-]{8,14})'
        patterns = [
            rf'(?:Office\s*)?Phone[\s:]+{digit_pattern}',
            rf'PHONE[\s:]+{digit_pattern}',
            rf'Contact:.*?Phone[\s:]+{digit_pattern}',
            rf'(?:Room|Rm\.?)\s*\d+[A-Z]?\s*[\n,]\s*(?:Office\s*)?Phone[\s:]+{digit_pattern}',
            rf'Office:.*?,\s*{digit_pattern}',
            rf'Telephone[\s:]+{digit_pattern}',
            r'603[\s.-]?\d{3}[\s.-]?\d{4}',
            r'\(603\)[\s.-]?\d{3}[\s.-]?\d{4}',
            r'434[\s.-]?\d{3}[\s.-]?\d{4}',
        ]
        return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
    def _process_matches(self, matches: List[str], text: str) -> List[str]:
        unique_phones = []
        seen_normalized = set()
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ''
            if match:
                cleaned = self._clean_phone(match)
                if cleaned and self._validate_phone(cleaned):
                    normalized = re.sub(r'\D', '', cleaned)
                    if normalized not in seen_normalized:
                        unique_phones.append(cleaned)
                        seen_normalized.add(normalized)
        return unique_phones
    def _clean_phone(self, phone: str) -> str:
        phone = re.sub(r'[^0-9().\-\s]', '', phone)
        phone = ' '.join(phone.split())
        return phone.strip()
    def _validate_phone(self, phone: str) -> bool:
        digits = re.sub(r'\D', '', phone)
        return len(digits) in [7, 10]

class OfficeInformationDetector:
    def __init__(self):
        self.field_name = 'office_information'
        self.logger = logging.getLogger('detector.office_information')
        self.location_detector = LocationDetector()
        self.hours_detector = HoursDetector()
        self.phone_detector = PhoneDetector()
    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info(f"Starting detection for field: {self.field_name}")
        location_result = self.location_detector.detect(text)
        hours_result = self.hours_detector.detect(text)
        phone_result = self.phone_detector.detect(text)
        result = {
            'field_name': self.field_name,
            'office_location': {
                'found': location_result.found,
                'content': location_result.content,
                'all_matches': location_result.all_matches
            },
            'office_hours': {
                'found': hours_result.found,
                'content': hours_result.content,
                'all_matches': hours_result.all_matches
            },
            'phone': {
                'found': phone_result.found,
                'content': phone_result.content,
                'all_matches': phone_result.all_matches
            }
        }
        result['found'] = any([
            location_result.found,
            hours_result.found,
            phone_result.found
        ])
        return result

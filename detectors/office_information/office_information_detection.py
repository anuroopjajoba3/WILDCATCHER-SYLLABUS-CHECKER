"""
Office Information Detector - FIXED VERSION
===========================================
Handles all office location patterns found in UNH Manchester syllabi
"""

import re
import logging
from typing import Dict, Any, List


class OfficeInformationDetector:
    """
    Detector for office location information.
    """

    def __init__(self):
        """Initialize the office information detector."""
        self.field_name = 'office_information'
        self.logger = logging.getLogger('detector.office_information')

        # Comprehensive patterns to catch all variations
        self.office_patterns = [
            # Pattern 1: "Office Hours: ..., Room 105"
            re.compile(
                r'Office\s*Hours?:.*?,\s*Room\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 2: "Office: Room 628"
            re.compile(
                r'Office:\s*Room\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 3: "Pandora Rm. 103" or "Pandora Room 103"
            re.compile(
                r'Pandora\s+(?:Rm\.?|Room)\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 4: "Office: Pandora Building, Room 244"
            re.compile(
                r'Office:\s*Pandora\s*(?:Building)?,?\s*Room\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 5: "Office Location/Hours: Pandora Building, Room 481"
            re.compile(
                r'Office\s*(?:Location)?/?(?:Hours)?:\s*Pandora\s*(?:Building)?,?\s*Room\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 6: Parenthetical "(office: room 141)"
            re.compile(
                r'\(office:\s*room\s*(\d+[A-Z]?)',
                re.IGNORECASE
            ),
            
            # Pattern 7: Generic - any Room/Rm followed by number in instructor section
            re.compile(
                r'(?:Instructor|Professor|Faculty|Office|OFFICE)[^\n]{0,150}(?:Room|Rm\.?)\s*(\d+[A-Z]?)',
                re.IGNORECASE
            )
        ]
        
        # Patterns that indicate classroom, not office
        self.classroom_indicators = [
            r'Class\s*Meeting',
            r'Lab\s*Meeting',
            r'room\s*\d+\s*\n\s*Office',  # If room number appears before Office Hours
            r'Time\s*and\s*Location.*room'  # Class time and location
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect office location information in the text.
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        # Focus on first 5000 chars
        search_text = text[:5000] if len(text) > 5000 else text

        try:
            found_rooms = []
            
            # Try each pattern
            for i, pattern in enumerate(self.office_patterns):
                matches = pattern.findall(search_text)
                if matches:
                    self.logger.debug(f"Pattern {i+1} found: {matches}")
                    for match in matches:
                        # Extract just the room number
                        if match and match.strip():
                            room_num = match.strip()
                            # Validate it's a room number (digits possibly followed by letter)
                            if re.match(r'^\d+[A-Z]?$', room_num):
                                found_rooms.append(room_num)
            
            if found_rooms:
                # Remove duplicates and validate
                unique_rooms = []
                seen = set()
                
                for room in found_rooms:
                    if room not in seen:
                        # Check if it's an office (not classroom)
                        if self._is_office_context(room, search_text):
                            # Format consistently as "Pandora Room XXX"
                            formatted = f"Pandora Room {room}"
                            unique_rooms.append(formatted)
                            seen.add(room)
                
                if unique_rooms:
                    result = {
                        'field_name': self.field_name,
                        'found': True,
                        'content': unique_rooms[0],
                        'all_matches': unique_rooms
                    }
                    
                    self.logger.info(f"FOUND: {unique_rooms[0]}")
                    return result
            
            # No office found
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None,
                'all_matches': []
            }

        except Exception as e:
            self.logger.error(f"Error in detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None,
                'all_matches': []
            }

    def _is_office_context(self, room_number: str, text: str) -> bool:
        """
        Check if room number is in office context (not classroom).
        """
        # Look for the room number in context
        room_pattern = rf'(?:Room|Rm\.?)\s*{re.escape(room_number)}'
        
        # Check for classroom indicators
        for indicator in self.classroom_indicators:
            # Check within 100 chars before/after room mention
            pattern = rf'{indicator}.{{0,100}}{room_pattern}'
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                self.logger.debug(f"Room {room_number} appears to be classroom")
                return False
        
        # Check for positive office indicators
        office_patterns = [
            rf'Office[^{{}}]*{room_pattern}',
            rf'Instructor[^{{}}]*{room_pattern}',
            rf'Professor[^{{}}]*{room_pattern}',
            rf'{room_pattern}[^{{}}]*(?:Phone|Email|Hours)'
        ]
        
        for pattern in office_patterns:
            if re.search(pattern, text[:1000], re.IGNORECASE | re.DOTALL):
                return True
        
        # # Special case: room 142 in Comp855 is classroom (room 141 is office)
        # if room_number == "142":
        #     # Check if room 141 also exists (which would be the office)
        #     if re.search(r'room\s*141', text, re.IGNORECASE):
        #         return False  # 142 is classroom, 141 is office
        
        return True  # Default to office if uncertain
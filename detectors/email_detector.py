"""
email Detector
=========================================

This detector identifies Student Learning Outcomes in syllabus documents.
It uses pattern matching and keyword detection to find email sections.

Developer Notes:
---------------
This is a simple example of a field detector. When creating new detectors,
use this as a template for structure and patterns.
"""

import re
import logging
from typing import Dict, Any


class emailDetector:
    """
    Detector for email.

    This detector looks for common email patterns including:
    - Keywords like "Email", "Contact Information", "Contact"
    - structure of email addresses string space to @ to string until dot to string to end space 
    - example Contact StartSpaceString1@String2.String3EndSpace
    """

    def __init__(self):
        """Initialize the email detector."""
        self.field_name = 'email'
        self.logger = logging.getLogger('detector.email')
#may want to add something to do with the colons
#may want to look into what happens if there are multiple emails in a document
#may want to look into what happens if the keywords are mentioned elsewhere 
#maybe if keyword immediatly followed by an email address
#one is             "primary e-mail:" but it also contains e-mail:
        # email keywords to search for
        self.email_keywords = [
            "email:",
            "emails:",
            "contact information:",
            "contact:",
            "e-mail:",
            "preferred contact method:",
            "contact info",
        ]

        # Action verbs commonly found in email
        self.action_verbs = [
            'analyze', 'evaluate', 'demonstrate', 'understand', 'apply',
            'identify', 'describe', 'explain', 'create', 'synthesize',
            'compare', 'interpret', 'solve', 'design', 'construct'
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect Student Learning Outcomes in the text.

        Args:
            text (str): Document text to analyze

        Returns:
            Dict[str, Any]: Detection result with email content if found
        """
        self.logger.info("Starting detection for field: email")

        # Limit text size to prevent hanging on large documents
        original_length = len(text)
        if len(text) > 20000:
            text = text[:20000]
            self.logger.info(f"Truncated large document from {original_length} to 20,000 characters")

        try:
            # Method 1: Keyword-based detection
            found, content, method = self._detect_by_keywords(text)

            if not found:
                #this means look for email address by format and context
                # context will elimanate things such as too far down the page and look to see what words if any surround the email address 
                # Method 2: format/pattern detection
                found, content, method = self._detect_by_action_verbs(text)

            if found:
                result = {
                    'field_name': self.field_name,
                    'found': True,
                    'content': content,
                    'confidence': 0.95,  # or another value
                    'metadata': {'method': method}
                }
                self.logger.info(f"FOUND: {self.field_name}")
                self.logger.info(f"SUCCESS: Found email via {method}")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None,
                    'confidence': 0.0,
                    'metadata': {}
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No emails found")

            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            self.logger.info(f"Detection complete for {self.field_name}: {'content' if found else 'no content'}")
            return result

        except Exception as e:
            self.logger.error(f"Error in email detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None,
                'confidence': 0.0,      
                'metadata': {}          
            }

    def _detect_by_keywords(self, text: str) -> tuple[bool, str, str]:
        """
        Detect email using keyword matching.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content, method_name)
        """
        text_lower = text.lower()
        for keyword in self.email_keywords:
            self.logger.info(f"Checking for keyword: {keyword} in email detector")

            if keyword in text_lower:
                # Found keyword, try to extract content around it
                pos = text_lower.find(keyword)
                if pos != -1:
                    # Get text section after the keyword
                    start = pos
#                    end = min(pos + 1000, len(text))
                    end = min(pos +254, len(text)) #max length of an email address is 254 characters and shouldn't excede the pdf limits
                    section = text[start:end]

                    # Look for bullet points or numbered lists
                    email_content = self._extract_structured_content(section)

                    if email_content:
                        return True, email_content, f"keyword '{keyword}'"

        return False, "", "keyword_search"
#
#        for keyword in self.email_keywords:
#            if keyword in text_lower:
#                # Found keyword, try to extract content around it
#                pos = text_lower.find(keyword)
#                if pos != -1:
                    # Get text section after the keyword
#                    start = pos
                    
#                    space = text.find (' ', pos) #find the first space after the keyword
#                    if space == -1: #if there is no space then just go to the end of the document
#                        space = len(text)
#                    end = min(pos + 1000, len(text))#may also want to make a length restriction
#                    section = text[start:space]
#at = email.find ('@')
#after_at = email.find ('  ' , at)
#host = email [at+1 : after_at]
                    # Look for bullet points or numbered lists
#                    email_content = self._extract_structured_content(section)

#                    if email_content:
#                        return True, email_content, f"keyword '{keyword}'"

#        return False, "", "keyword_search"

    def _detect_by_action_verbs(self, text: str) -> tuple[bool, str, str]:
        """
        Detect emails using action verb patterns.

        Args:
            text (str): Text to search

        Returns:
            tuple: (found, content, method_name)
        """
        lines = text.split('\n')
        verb_lines = []

        for line in lines:
            line = line.strip()
            # Check for reasonable line length and action verbs
            if 20 < len(line) < 200:
                line_lower = line.lower()
                verb_count = sum(1 for verb in self.action_verbs if verb in line_lower)

                # Look for bulleted/numbered lines with action verbs
                if verb_count >= 1 and self._is_list_item(line):
                    cleaned = self._clean_list_item(line)
                    if len(cleaned) > 10:
                        verb_lines.append(cleaned)
#not true for email probably won't need the following if statement
        # Need at least 2 lines to consider it email
        if len(verb_lines) >= 2:
            content = '\n'.join(verb_lines[:5])  # Limit to first 5 items
            return True, content, "action_verb_detection"

        return False, "", "action_verb_search"

    def _extract_structured_content(self, section: str) -> str:
        """
        Extract structured email content from a text section.

        Args:
            section (str): Text section containing potential email

        Returns:
            str: Extracted email content or empty string
        """
        pattern = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*" \
                  r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?" \
                  r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
        return re.findall(pattern, section, re.VERBOSE)#may need something else than verbose
        #this also seems to get multiple emails if they are in the same section
        #may want to just return the first instance of an email found

        #email = section.strip()#gets rid of leading and trailing spaces to focus only on email
        #parts = section.split('@')#this was altered to look for the @ symbol
#        email_lines = []#I think this something that can be rid of as only one email is needed
 
        #for part in parts:#this may be needed for cases in which email is on the next line
            #part = part.strip()#gets rid of leading and trailing spaces to focus only on email
            #if not line:#if nothing then go to next instance
            #    continue
#shouldn't make a difference if this is included or not as it is two parts of the same email
            # Check if line looks like an email
        #    if self._is_potential_email_line(part):#this will be modified to look for email format
        #        cleaned = self._clean_list_item(part)#this was used to get rid of the bullet points or numbers now may not be needed
        #        if len(cleaned) > 10:  # maybe change to something else the maximum length of an email possibly with minimum length
        #            return cleaned
#                    email_lines.append(cleaned)#this may just be changed to be a return instead due to only needing one email
#may also want to include something to exclude some other common emails such as food pantry or mental health emails that are usually included in other parts
#        if len(email_lines) >= 1:
#            return '\n'.join(email_lines[:5])  # Limit to first 5 items

#        return ""

    def _is_potential_email_line(self, line: str) -> bool:
        """
        Check if a line looks like a potential email.

        Args:
            line (str): Line to check

        Returns:
            bool: True if line might contain an email
        """
        # Check for list markers or action verbs
        if self._is_list_item(line):
            return True

        # Check for action verbs
        line_lower = line.lower()
        #verb_count = sum(1 for verb in self.action_verbs if verb in line_lower)
        verb_count = sum(1 for verb in self.action_verbs if verb in line_lower)
        return verb_count >= 1

    def _is_list_item(self, line: str) -> bool:
        """
        Check if line starts with list markers.

        Args:
            line (str): Line to check

        Returns:
            bool: True if line is a list item
        """
        return (line.startswith(('•', '-', '*', '▪')) or
                re.match(r'^\d+\.?\s', line))

    def _clean_list_item(self, line: str) -> str:
        """
        Remove list markers from a line.

        Args:
            line (str): Line to clean

        Returns:
            str: Cleaned line without list markers
        """
        pattern = r"^(?=.{1,254}$)(?!.*\.\.)(?=.{1,64}@)[A-Za-z0-9!#$%&'*+/=?^_`{|}~-](?:[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]*[A-Za-z0-9!#$%&'*+/=?^_`{|}~-])?@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"

        email_match = re.search(pattern, line)
#        email_match = re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        #b stands for word boundary so that it doesn't pick up things that aren't email addresses
        #w stands for word character which includes letters, digits, and underscores
        #dot and hyphen are included as they are commonly found in email addresses
        #@ stands for the at symbol
        #+ means one or more of the preceding element
        # put together it looks for a sequence that includes letters, digits, dots, hyphens
        # then an @ symbol
        # then another sequence of letters, digits, dots, hyphens
        # then a dot
        # then a sequence of letters (the domain)
        # \b at the end ensures it ends at a word boundary

        #if email_match:
        #   print(f"Email found: {email_match.group(0)}")
        #return re.sub(r'^[\s•\-\*▪\d\.)]+', '', line).strip()
        return email_match.group(0) if email_match else ""
    #this returns the email found through regex

# =============================================================================
# EXAMPLE USAGE FOR DEVELOPERS
# =============================================================================

if __name__ == "__main__":
    """
    Example usage - developers can run this file directly to test email detection.
    """
    # Test text with email
    test_text = """
    Course Objectives:
    Students will be able to:
    • Analyze complex data structures
    • Evaluate different algorithms
    • Demonstrate problem-solving skills
    • Apply theoretical concepts to practical problems
    """

    # Test the detector
    detector = emailDetector()
    result = detector.detect(test_text)

    print("email Detection Test Results:")
    print(f"Found: {result['found']}")
    print(f"Content: {result['content']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Metadata: {result['metadata']}")
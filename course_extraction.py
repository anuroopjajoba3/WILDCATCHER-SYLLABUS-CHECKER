"""
Course Extraction Module
This module handles the extraction and validation of course information from documents.
It uses LLM to analyze text and extract structured information about courses.
"""

import re
import json
import hashlib
import logging
from database import DocumentInfo, Session
from prompts import EXTRACTION_PROMPT

session = Session()


def validate_extracted_info(info):
    """
    Validates and cleans extracted information.
    
    Args:
        info (dict): Extracted information dictionary
        
    Returns:
        dict: Validated and cleaned information
    """
    if not info or not isinstance(info, dict):
        return info
    
    # Check email format
    if "Instructor Email" in info:
        email = info["Instructor Email"]
        if "@" not in email:
            del info["Instructor Email"]
    
    # Check credits is a number
    if "Credits" in info:
        credits = str(info["Credits"])
        # Extract just the number
        match = re.search(r'\d+', credits)
        if match:
            info["Credits"] = match.group()
    
    # Validate phone number format
    if "Phone Number" in info:
        phone = str(info["Phone Number"])
        # Remove non-digits and check length
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 15:
            del info["Phone Number"]
    
    # Remove empty or placeholder values
    keys_to_remove = []
    for key, value in info.items():
        if value in [None, "", "N/A", "Not Specified", "Unknown", "Not Found"]:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del info[key]
    
    return info


def smart_text_truncation(text, max_length=60000):
    """
    Intelligently truncate text while preserving key sections containing important information.
    
    Args:
        text (str): Full document text
        max_length (int): Maximum allowed text length
        
    Returns:
        str: Truncated text preserving key information
    """
    if len(text) <= max_length:
        return text.strip()
    
    # Keywords that indicate important sections - EXPANDED FOR SLOs
    key_sections = {
        'course_info': ['course id', 'course name', 'credits', 'prerequisites', 'department'],
        'instructor': ['instructor', 'professor', 'email', 'office hours', 'phone'],
        'learning': [
            'learning outcome', 'learning objective', 'course objective',
            'student learning outcome', 'learning outcomes',
            'students that successfully complete', 'upon completion',
            'students will be able', 'students should be able',
            'homeland security program', 'program outcomes',
            'slo', 'competenc', 'goal', 'by the end of this course',
            'apply', 'conduct', 'critique', 'demonstrate', 'define',
            'distinguish', 'assess', 'understand', 'evaluate', 'design',
            'analyze', 'create', 'develop', 'identify', 'gain'
        ],
        'grading': ['grading', 'grade scale', 'assessment', 'evaluation', 'percentage', '%'],
        'schedule': ['schedule', 'topic', 'week', 'date', 'calendar', 'timeline'],
        'requirements': ['requirement', 'textbook', 'material', 'software', 'technical'],
        'policies': ['attendance', 'late', 'academic integrity', 'plagiarism', 'policy']
    }
    
    # Find positions of key sections
    section_positions = {}
    text_lower = text.lower()
    
    for section_name, keywords in key_sections.items():
        positions = []
        for keyword in keywords:
            pos = 0
            while True:
                pos = text_lower.find(keyword, pos)
                if pos == -1:
                    break
                positions.append(pos)
                pos += len(keyword)
        
        if positions:
            # Store the earliest position for this section type
            section_positions[section_name] = min(positions)
    
    # Sort sections by position
    sorted_sections = sorted(section_positions.items(), key=lambda x: x[1])
    
    # Build truncated text preserving key sections
    result_parts = []
    chars_per_section = max_length // (len(sorted_sections) + 2)  # +2 for intro and end
    
    # Always include beginning
    result_parts.append(text[:chars_per_section])
    
    # Include samples from each key section
    for section_name, position in sorted_sections:
        start = max(0, position - 500)  # Include some context before
        end = min(len(text), position + chars_per_section)
        section_text = text[start:end]
        
        if section_text not in ''.join(result_parts):  # Avoid duplicates
            result_parts.append("\n\n[...]\n\n" + section_text)
    
    # Always include end
    if text[-chars_per_section:] not in ''.join(result_parts):
        result_parts.append("\n\n[...]\n\n" + text[-chars_per_section:])
    
    result = ''.join(result_parts)
    
    # If still too long, fall back to balanced sampling
    if len(result) > max_length:
        text_length = len(text)
        intro_size = max_length // 3
        middle_size = max_length // 3
        end_size = max_length // 3
        
        middle_start = (text_length // 2) - (middle_size // 2)
        middle_end = middle_start + middle_size
        
        result = (
            text[:intro_size] + 
            "\n\n[... section trimmed ...]\n\n" +
            text[middle_start:middle_end] + 
            "\n\n[... section trimmed ...]\n\n" +
            text[-end_size:]
        )
    
    logging.info(f"Smart truncation: {len(text)} -> {len(result)} chars, preserved {len(sorted_sections)} key sections")
    return result


def extract_students_will_be_able_to(text):
    """
    Specifically search for and extract 'students will be able to' sections.
    This addresses the most common SLO format that's being missed.
    
    Args:
        text (str): Document text to search
        
    Returns:
        str or None: Extracted SLO text if found
    """
    text_lower = text.lower()
    
    # Find "students will be able to" phrase (with variations)
    swtba_patterns = [
        r"students will be able to:?\s*(.*?)(?:\n\n|\n[A-Z][^a-z]|\Z)",
        r"upon completion.*students will be able to:?\s*(.*?)(?:\n\n|\n[A-Z][^a-z]|\Z)",
        r"by the end.*students will be able to:?\s*(.*?)(?:\n\n|\n[A-Z][^a-z]|\Z)",
        r"after completing.*students will be able to:?\s*(.*?)(?:\n\n|\n[A-Z][^a-z]|\Z)"
    ]
    
    for pattern in swtba_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            
            # Clean up the content - extract bullet points or numbered items
            lines = content.split('\n')
            slo_items = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line starts with bullet, number, or action verb
                if (re.match(r'^[\s•\-\*\d\.)]+', line) or 
                    re.match(r'^\s*(distinguish|assess|understand|evaluate|design|apply|analyze|create|demonstrate|develop)', line, re.IGNORECASE)):
                    
                    # Clean up the line
                    cleaned = re.sub(r'^[\s•\-\*\d\.)]+', '', line).strip()
                    if len(cleaned) > 10:  # Meaningful content
                        slo_items.append(cleaned)
                elif len(slo_items) == 0 and len(line) > 20:  # First substantial line might not have bullets
                    slo_items.append(line)
            
            if len(slo_items) >= 2:  # At least 2 SLO items
                return '\n'.join(slo_items)
    
    return None


def extract_learning_objectives_sections(text):
    """
    Extract any section labeled as Learning Objectives, Course Objectives, SLO, etc.
    Much more flexible to catch various formats including singular forms.
    
    Args:
        text (str): Document text to search
        
    Returns:
        str or None: Extracted objectives text if found
    """
    # EXPANDED patterns based on actual syllabus formats
    objective_patterns = [
        # Pattern 1: Direct headers with introductory text
        r"learning objectives?:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        r"student learning outcomes?:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        r"student learning outcome:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        r"learning outcomes?:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        r"course objectives?:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        
        # Pattern 2: "Upon completion" variations
        r"upon completion of this course,?\s*students\s*(?:will\s*|should\s*)?be able to:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        r"students that successfully complete this course will be able to:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        
        # Pattern 3: Mixed Program Outcomes and Learning Objectives
        r"(?:homeland security program and student learning outcomes|program.*?outcomes).*?\n(?:.*?\n)*?(?:\*?learning objectives?\*?|students.*?able to:?)\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        
        # Pattern 4: Simple header patterns (fallback)
        r"learning objectives?:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        r"student learning outcomes?:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        r"student learning outcome:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        r"course objectives?:?\s*\n((?:[-\*•▪\d\.].*?\n?)+)",
        
        # Pattern 5: SLO abbreviations
        r"slos?:?\s*\n(?:.*?students.*?able to:?\s*\n)?((?:[-\*•▪\d\.].*?\n?)+)",
        
        # Pattern 6: Catch broader context around these keywords
        r"(?:student\s+)?(?:course\s+)?(?:program\s+)?(?:learning\s+)?(?:outcome|objective|goal)s?:?\s*\n(?:[^\n]*\n)*((?:[-\*•▪\d\.].*?\n?)+)",
    ]
    
    for pattern in objective_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            
            if not content or len(content) < 20:
                continue
                
            # Extract meaningful content - much more flexible
            lines = content.split('\n')
            objective_items = []
            
            for line in lines:
                line = line.strip()
                if not line or len(line) < 15:  # Lowered minimum length
                    continue
                
                # FLEXIBLE detection - accept various formats from real syllabi
                is_likely_slo = False
                
                # Check for bullet/number formatting (expanded for special characters)
                if re.match(r'^[\s•\-\*▪▫◦‣⁃\d\.)]+', line):
                    is_likely_slo = True
                
                # Check for action verbs (based on your examples)
                action_verbs = [
                    'apply', 'conduct', 'critique', 'demonstrate', 'define', 'describe',
                    'identify', 'analyze', 'gain', 'distinguish', 'assess', 'understand', 
                    'evaluate', 'design', 'create', 'develop', 'implement', 'explain', 
                    'compare', 'synthesize', 'interpret', 'formulate', 'construct',
                    'examine', 'investigate', 'solve', 'calculate', 'measure',
                    'recognize', 'determine', 'establish', 'integrate', 'use',
                    'build', 'produce', 'plan', 'select', 'organize', 'manage'
                ]
                
                # More flexible verb detection - check first few words
                first_words = line.lower().split()[:3]  # Check first 3 words
                if any(verb in word for word in first_words for verb in action_verbs):
                    is_likely_slo = True
                
                # Accept lines that look like learning outcomes
                if (re.match(r'^[A-Z][a-z]', line) and len(line) > 20 and
                    ('.' in line or 'analysis' in line.lower() or 'concepts' in line.lower())):
                    is_likely_slo = True
                
                if is_likely_slo:
                    # Clean up the line (handle all bullet types)
                    cleaned = re.sub(r'^[\s•\-\*▪▫◦‣⁃\d\.)]+', '', line).strip()
                    if len(cleaned) > 10:
                        objective_items.append(cleaned)
            
            if len(objective_items) >= 1:  # Even 1 item is worth capturing
                logging.info(f"Found {len(objective_items)} SLO items using pattern matching")
                return '\n'.join(objective_items)
            elif len(content) > 50:  # Return raw content if structured extraction failed
                logging.info("Returning raw SLO content - couldn't parse into items")
                return content.strip()
    
    return None


def enhanced_post_process(info, original_text):
    """
    Enhanced post-processing with pattern matching for missed fields.
    
    Args:
        info (dict): Extracted information
        original_text (str): Original document text
        
    Returns:
        dict: Enhanced extracted information
    """
    if not info or not isinstance(info, dict):
        return info
    
    text_lower = original_text.lower()
    
    # Check for instructor department in original text if missing
    if "Instructor Department" not in info or not info.get("Instructor Department"):
        # Pattern: "Professor of [Department]"
        dept_pattern = r"Professor of ([^,\n]+)"
        match = re.search(dept_pattern, original_text, re.IGNORECASE)
        if match:
            info["Instructor Department"] = match.group(1).strip()
    
    # ENHANCED: Phone Contact detection - CRITICAL FOR YOUR ISSUE
    if "Phone Number" not in info or not info.get("Phone Number"):
        logging.info("DEBUG: STARTING ENHANCED PHONE CONTACT DETECTION")
        
        # STEP 1: Look for actual phone numbers first
        phone_patterns = [
            r"\b(\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4})\b",  # 555-123-4567, 555.123.4567, 555 123 4567
            r"\b(\(\d{3}\)\s?\d{3}[-\.\s]?\d{4})\b",   # (555) 123-4567, (555)123-4567
            r"\b(\d{3}\.\d{3}\.\d{4})\b",              # 555.123.4567
            r"\b(\+1[-\.\s]?\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4})\b",  # +1-555-123-4567
            r"\b(\d{10})\b",                           # 5551234567 (10 digits)
        ]
        
        phone_found = None
        
        # Search for actual phone numbers
        for pattern in phone_patterns:
            matches = re.findall(pattern, original_text)
            if matches:
                # Take the first valid phone number found
                candidate = matches[0]
                # Validate it has enough digits
                digits_only = re.sub(r'\D', '', candidate)
                if 10 <= len(digits_only) <= 15:  # Valid phone number length
                    phone_found = candidate
                    logging.info(f"SUCCESS: Found actual phone number: {candidate}")
                    break
        
        # Look for phone numbers near keywords
        if not phone_found:
            phone_keywords = ['phone', 'tel', 'telephone', 'office', 'call', 'contact']
            for keyword in phone_keywords:
                if keyword in text_lower:
                    # Find position and look for numbers nearby (within 100 characters)
                    pos = text_lower.find(keyword)
                    nearby_text = original_text[max(0, pos-50):pos+100]
                    
                    for pattern in phone_patterns:
                        matches = re.findall(pattern, nearby_text)
                        if matches:
                            candidate = matches[0]
                            digits_only = re.sub(r'\D', '', candidate)
                            if 10 <= len(digits_only) <= 15:
                                phone_found = candidate
                                logging.info(f"SUCCESS: Found phone number near '{keyword}': {candidate}")
                                break
                    if phone_found:
                        break
        
        # STEP 2: If no actual number found, look for phone availability indicators
        if not phone_found:
            logging.info("DEBUG: No actual phone number found, checking for phone availability...")
            
            # Patterns for phone availability without specific numbers
            availability_patterns = [
                # Direct mentions of phone contact availability
                (r"telephone contact.*available", "Phone contact available"),
                (r"phone.*contact.*available", "Phone contact available"), 
                (r"phone.*available", "Phone contact available"),
                (r"telephone.*available", "Phone contact available"),
                
                # By appointment/request patterns
                (r"phone.*by appointment", "Phone by appointment"),
                (r"telephone.*by appointment", "Phone by appointment"),
                (r"phone.*call.*by appointment", "Phone by appointment"),
                (r"request.*phone.*call", "Phone by request"),
                (r"request.*telephone", "Phone by request"),
                (r"phone.*calls.*by appointment", "Phone by appointment"),
                (r"schedule.*phone.*call", "Phone by appointment"),
                (r"contact.*me.*to.*schedule.*phone", "Phone by appointment"),
                
                # Secondary/backup method patterns
                (r"telephone.*secondary.*method", "Phone contact available"),
                (r"phone.*secondary.*method", "Phone contact available"),
                (r"telephone.*backup", "Phone contact available"),
                (r"phone.*backup", "Phone contact available"),
                
                # General phone mention without number
                (r"phone\s*:", "Phone contact available (no number provided)"),
                (r"telephone\s*:", "Phone contact available (no number provided)"),
                (r"phone.*contact", "Phone contact available"),
                (r"telephone.*contact", "Phone contact available"),
            ]
            
            # Search for availability patterns
            for pattern, description in availability_patterns:
                if re.search(pattern, text_lower):
                    phone_found = description
                    logging.info(f"SUCCESS: Found phone availability indicator: '{description}' (pattern: {pattern})")
                    break
            
            # STEP 3: Check for general phone mentions (without specific availability language)
            if not phone_found:
                general_phone_keywords = ['phone', 'telephone', 'tel']
                for keyword in general_phone_keywords:
                    if keyword in text_lower:
                        # Check if it's in a contact context (not just random mention)
                        pos = text_lower.find(keyword)
                        context = text_lower[max(0, pos-30):pos+30]
                        
                        # Look for contact context words
                        context_words = ['contact', 'call', 'reach', 'available', 'office', 'email']
                        if any(word in context for word in context_words):
                            phone_found = "Phone contact mentioned (details unclear)"
                            logging.info(f"SUCCESS: Found general phone mention near contact context: '{keyword}'")
                            break
        
        # Set the result
        if phone_found:
            info["Phone Number"] = phone_found
            logging.info(f"SUCCESS: Set Phone contact info: {phone_found}")
        else:
            logging.info("INFO: No phone contact information found in document")
    
    # ENHANCED: Flexible SLO detection with comprehensive debugging
    if "Student Learning Outcomes" not in info or not info.get("Student Learning Outcomes"):
        logging.info("DEBUG: STARTING SLO DETECTION PIPELINE")
        logging.info(f"Text length: {len(original_text)} characters")
        
        # FIRST: Try the flexible Learning Objectives section mapping (most comprehensive)
        logging.info("DEBUG: Step 1 - Trying learning objectives section mapping...")
        objectives_result = extract_learning_objectives_sections(original_text)
        if objectives_result:
            # CRITICAL: Ensure we're storing the actual content, not a count
            info["Student Learning Outcomes"] = objectives_result
            logging.info(f"SUCCESS: SLOs found via learning objectives section mapping: {len(objectives_result)} chars")
            logging.info(f"CONTENT: SLO Preview: {objectives_result[:200]}...")
            logging.info(f"DEBUG: SLO type check: type={type(objectives_result)}, is_string={isinstance(objectives_result, str)}")
            
        # SECOND: Try "students will be able to" (only if not found above)
        elif not info.get("Student Learning Outcomes"):
            logging.info("DEBUG: Step 2 - Trying 'students will be able to' pattern...")
            swtba_result = extract_students_will_be_able_to(original_text)
            if swtba_result:
                info["Student Learning Outcomes"] = swtba_result
                logging.info(f"SUCCESS: SLOs found via 'students will be able to' pattern: {len(swtba_result)} chars")
                logging.info(f"CONTENT: SLO Preview: {swtba_result[:200]}...")
        
        # THIRD: Direct action verb detection anywhere in document
        if not info.get("Student Learning Outcomes"):
            logging.info("DEBUG: Step 3 - Trying direct action verb detection...")
            # Look for any bulleted/numbered lists with action verbs
            action_verbs = [
                'distinguish', 'assess', 'understand', 'evaluate', 'design', 
                'apply', 'analyze', 'create', 'demonstrate', 'develop',
                'implement', 'identify', 'explain', 'compare', 'synthesize',
                'interpret', 'formulate', 'construct', 'define', 'describe',
                'examine', 'investigate', 'solve', 'calculate', 'measure',
                'recognize', 'determine', 'establish', 'integrate', 'use',
                'build', 'produce', 'plan', 'select', 'organize', 'manage',
                'conduct', 'critique', 'gain'  # Added from your examples
            ]
            
            # Look for patterns like "• Analyze..." or "1. Design..." or "▪ Apply..." 
            action_pattern = r"(?:^|\n)\s*[\d\.\-\*•▪▫◦‣⁃]\s*([A-Z][a-z]*[^\n]+)"
            all_bullets = re.findall(action_pattern, original_text, re.MULTILINE)
            logging.info(f"Found {len(all_bullets)} total bullet points in document")
            
            # Filter for ones that start with action verbs (more flexible matching)
            slo_bullets = []
            for i, bullet in enumerate(all_bullets):
                # Check if any of the first 3 words contain action verbs
                first_words = bullet.lower().split()[:3]
                has_action_verb = any(verb in word for word in first_words for verb in action_verbs)
                
                if has_action_verb and len(bullet) > 15:  # Lowered threshold
                    slo_bullets.append(bullet.strip())
                    logging.info(f"MATCH: Bullet {i+1} matched: {bullet[:100]}...")
                elif has_action_verb:
                    logging.info(f"SHORT: Bullet {i+1} has verb but too short ({len(bullet)} chars): {bullet}")
                elif len(bullet) > 15:
                    logging.info(f"NO_VERB: Bullet {i+1} long enough but no verb: {bullet[:50]}...")
            
            if len(slo_bullets) >= 1:  # Accept even 1 if it's clearly an SLO
                slo_content = "\n".join(slo_bullets)
                info["Student Learning Outcomes"] = slo_content
                logging.info(f"SUCCESS: SLOs found via action verb detection: {len(slo_bullets)} items")
                logging.info(f"CONTENT: SLO Content: {slo_content}")
        
        # FOURTH: Last resort - look for any section with "outcome" or "objective" keywords
        if not info.get("Student Learning Outcomes"):
            logging.info("DEBUG: Step 4 - Trying keyword-based search...")
            # Simple keyword search for any outcomes/objectives section
            keywords = ["outcome", "objective", "goal", "competenc", "slo"]
            
            for keyword in keywords:
                if keyword in text_lower:
                    logging.info(f"Found keyword '{keyword}' in text")
                    # Find the position and extract surrounding context
                    pos = text_lower.find(keyword)
                    # Look for content after the keyword (next 1000 characters)
                    excerpt = original_text[pos:pos+1000]
                    
                    # Look for any structured content (bullets, numbers, etc.)
                    lines = excerpt.split('\n')[1:6]  # Skip the header line, take next 5
                    content_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if (len(line) > 20 and 
                            (re.match(r'[\d\.\-\*•▪]', line) or 
                             any(verb in line.lower() for verb in action_verbs[:10]))):  # Top 10 verbs
                            content_lines.append(line)
                    
                    if content_lines:
                        slo_content = "\n".join(content_lines)
                        info["Student Learning Outcomes"] = slo_content
                        logging.info(f"SUCCESS: SLOs found via keyword '{keyword}' search: {len(content_lines)} items")
                        logging.info(f"CONTENT: SLO Content: {slo_content}")
                        break
        
        # Final status check
        if info.get("Student Learning Outcomes"):
            final_slo = info["Student Learning Outcomes"]
            logging.info(f"FINAL: SLO RESULT: {len(final_slo)} characters")
            logging.info(f"CONTENT: FINAL SLO: {final_slo}")
        else:
            logging.warning("ERROR: NO SLOs FOUND by any method")
            # Log some context for debugging
            logging.info("DEBUG INFO:")
            logging.info(f"  - Text contains 'learning': {'learning' in text_lower}")
            logging.info(f"  - Text contains 'objective': {'objective' in text_lower}")
            logging.info(f"  - Text contains 'outcome': {'outcome' in text_lower}")
            logging.info(f"  - Text contains 'students': {'students' in text_lower}")
            logging.info(f"  - Text sample: {original_text[:500]}...")
    
    # ENHANCED: More comprehensive grading procedures patterns
    if "Grading Procedures" not in info or not info.get("Grading Procedures"):
        # Multiple patterns for grading
        grading_patterns = [
            r"(\d+%[^:\n]*:[^\n]+)",  # Original pattern
            r"([A-Za-z\s]+)[\s\-–—]+(\d+%)",  # "Assignment - 20%"
            r"([A-Za-z\s]+)\s*\((\d+%)\)",  # "Assignment (20%)"
            r"([A-Za-z\s]+):\s*(\d+)\s*points",  # "Assignment: 20 points"
            r"•\s*([A-Za-z\s]+)[\s\-–—]+(\d+%)",  # Bullet points
        ]
        
        all_matches = []
        for pattern in grading_patterns:
            matches = re.findall(pattern, original_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    all_matches.append(" - ".join(match))
                else:
                    all_matches.append(match)
        
        if all_matches:
            info["Grading Procedures"] = "; ".join(all_matches)
    
    # NEW: Final Grade Scale pattern - CRITICAL FOR YOUR ISSUE
    if "Final Grade Scale" not in info or not info.get("Final Grade Scale"):
        # Multiple patterns for grade scales
        grade_scale_patterns = [
            r"([A-F][+\-]?)\s*[:=]\s*(\d+[\.\d]*)\s*[-–—]\s*(\d+[\.\d]*)",  # "A: 93-100"
            r"([A-F][+\-]?)\s*[:=]\s*(\d+[\.\d]*)\s*(?:and above|or higher)",  # "A: 93 and above"
            r"(\d+[\.\d]*)\s*[-–—]\s*(\d+[\.\d]*)\s*[:=]\s*([A-F][+\-]?)",  # "93-100: A"
            r"Grade\s+([A-F][+\-]?)[^0-9]*(\d+)",  # "Grade A requires 93"
        ]
        
        grade_info = []
        for pattern in grade_scale_patterns:
            matches = re.findall(pattern, original_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    grade_info.append(" ".join(str(m) for m in match))
        
        if grade_info:
            info["Final Grade Scale"] = "; ".join(grade_info)
        elif "standard" in text_lower and "grading scale" in text_lower:
            info["Final Grade Scale"] = "Standard university grading scale"
    
    # NEW: Course Topics & Dates - CRITICAL FOR YOUR ISSUE
    if "Course Topics & Dates" not in info or not info.get("Course Topics & Dates"):
        # Look for schedule patterns
        schedule_patterns = [
            r"Week\s+(\d+)[^:]*:\s*([^\n]+)",  # "Week 1: Introduction"
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^:]*):?\s*([^\n]+)",  # Date-based
            r"(?:Module|Unit|Session)\s+(\d+)[^:]*:\s*([^\n]+)",  # Module/Unit based
            r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)[^:]*:\s*([^\n]+)",  # Date format MM/DD
        ]
        
        schedule_items = []
        for pattern in schedule_patterns:
            matches = re.findall(pattern, original_text, re.IGNORECASE)
            for match in matches:
                schedule_items.append(f"{match[0]}: {match[1]}")
        
        if schedule_items:
            info["Course Topics & Dates"] = "; ".join(schedule_items[:10])  # Limit to first 10
        elif "schedule" in text_lower or "calendar" in text_lower:
            # At least note that a schedule exists
            info["Course Topics & Dates"] = "See course schedule in syllabus"
    
    # ENHANCED: Assignment Types and Delivery - CRITICAL FOR YOUR ISSUE
    if "Assignment Types and Delivery" not in info or not info.get("Assignment Types and Delivery"):
        types = set()  # Use set to avoid duplicates
        
        # More comprehensive keywords including specific patterns you mentioned
        assignment_keywords = {
            "homework": "Homework",
            "assignment": "Assignments",
            "project": "Projects",
            "sprint": "Sprint deliverables",
            "report": "Reports",
            "exam": "Exams",
            "quiz": "Quizzes",
            "presentation": "Presentations",
            "discussion": "Discussions",
            "lab": "Lab work",
            "paper": "Papers",
            "portfolio": "Portfolio",
            "participation": "Class participation",
            "weekly work logs": "Weekly work logs",  # SPECIFIC PATTERN
            "work logs": "Work logs"
        }
        
        for keyword, label in assignment_keywords.items():
            if keyword in text_lower:
                types.add(label)
        
        # ENHANCED: Look specifically in "GRADING AND EVALUATION" section
        grading_section_patterns = [
            "grading and evaluation",
            "grading & evaluation", 
            "evaluation and grading",
            "evaluation & grading"
        ]
        
        for pattern in grading_section_patterns:
            if pattern in text_lower:
                # Find the section and extract content around it
                pos = text_lower.find(pattern)
                if pos != -1:
                    # Extract 1000 characters after this section header
                    section_content = original_text[pos:pos + 1000].lower()
                    
                    # Look for additional assignment types in this section
                    if "weekly work logs" in section_content:
                        types.add("Weekly work logs")
                    if "report" in section_content:
                        types.add("Reports") 
                    if "presentation" in section_content:
                        types.add("Presentations")
                    
                    logging.info(f"DEBUG: Found grading section at position {pos}, extracted assignment types: {types}")
                    break
        
        # ENHANCED: Look for "Part I", "Part II", "Part III", "Part IV" deliverables
        part_patterns = ["part i", "part ii", "part iii", "part iv", "part 1", "part 2", "part 3", "part 4"]
        found_parts = []
        
        for part in part_patterns:
            if part in text_lower:
                found_parts.append(part.title())
        
        if found_parts:
            types.add(f"Multi-part deliverables ({', '.join(found_parts)})")
            logging.info(f"DEBUG: Found multi-part deliverables: {found_parts}")
        
        # Look for delivery methods
        delivery = []
        if "canvas" in text_lower:
            delivery.append("Canvas")
        if "in-person" in text_lower or "in person" in text_lower:
            delivery.append("In-person")
        if "online" in text_lower:
            delivery.append("Online")
        if "submit via" in text_lower or "turn in" in text_lower:
            delivery.append("Submission required")
        
        if types:
            result = ", ".join(sorted(types))  # Sort for consistency
            if delivery:
                result += f" (via {', '.join(delivery)})"
            info["Assignment Types and Delivery"] = result
            logging.info(f"SUCCESS: Set Assignment Types and Delivery: {result}")
        else:
            logging.warning("WARNING: No assignment types found in text")
            # Fallback - check if any grading percentages exist (means there are assignments)
            if any(char in text_lower for char in ['%', 'percent']) and any(word in text_lower for word in ['grade', 'grading', 'evaluation']):
                info["Assignment Types and Delivery"] = "Coursework types described in grading section"
                logging.info("FALLBACK: Found grading info, setting generic coursework description")
    
    # ENHANCED: Other Materials
    if "Other Materials" not in info or not info.get("Other Materials"):
        materials = []
        
        if "no textbook" in text_lower or "no required text" in text_lower:
            materials.append("No required textbook")
        
        if "canvas" in text_lower:
            if "posted" in text_lower or "available" in text_lower:
                materials.append("Materials posted on Canvas")
        
        if "reading" in text_lower:
            materials.append("Additional readings provided")
            
        if materials:
            info["Other Materials"] = "; ".join(materials)
    
    # Enhanced: Course format
    if "Course Format" not in info or not info.get("Course Format"):
        # Look for meeting pattern
        format_pattern = r"(In-person|Online|Hybrid|Asynchronous|Synchronous)[^.]*"
        match = re.search(format_pattern, original_text, re.IGNORECASE)
        if match:
            info["Course Format"] = match.group(0).strip()[:100]  # Limit length
    
    # ENHANCED: Email response time detection - VERY STRICT to avoid false positives
    if "Instructor Response Time" not in info or not info.get("Instructor Response Time"):
        logging.info("DEBUG: Checking for explicit email response time discussions...")
        
        # STRICT: Only detect actual response time discussions, not just email addresses
        # Look for explicit response time patterns with CONTEXT
        strict_response_patterns = [
            # Specific time commitments
            r"(?:generally|typically|usually)\s+respond[s]?\s+within\s+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
            r"respond[s]?\s+(?:to\s+(?:email|messages?))?\s+within\s+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
            r"will\s+(?:reply|respond)\s+(?:to\s+(?:email|messages?))?\s+within\s+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
            r"(?:email|message)\s+response\s+time[:\s]+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
            r"aim\s+to\s+respond\s+within\s+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
            r"expect\s+(?:a\s+)?response\s+within\s+(\d+[-\s]?\d*\s*(?:hour|day|week)s?)",
        ]
        
        response_found = None
        for pattern in strict_response_patterns:
            match = re.search(pattern, text_lower)
            if match:
                response_found = f"Responds within {match.group(1)}"
                logging.info(f"SUCCESS: Found explicit response time commitment: {response_found}")
                break
        
        # STRICT: Only detect actual communication method discussions (not just addresses)
        if not response_found:
            communication_patterns = [
                # Must include action words about communication, not just listing email
                (r"(?:prefer|best|primary)\s+(?:way|method)\s+(?:to\s+)?(?:reach|contact)\s+(?:me\s+)?(?:is\s+)?(?:via\s+)?email", "Email is preferred contact method"),
                (r"email\s+(?:is|will\s+be)\s+the\s+(?:best|primary|main)\s+(?:way|method)", "Email is primary communication method"),
                (r"communicate\s+(?:with\s+me\s+)?via\s+email", "Communication via email specified"),
                (r"contact\s+me\s+(?:via\s+|through\s+|by\s+)?email", "Contact via email specified"),
                (r"reach\s+(?:out\s+to\s+)?me\s+(?:via\s+|through\s+|by\s+)?email", "Contact via email specified"),
                (r"email\s+(?:me\s+)?(?:if|when)\s+you\s+(?:have|need)", "Email for questions specified"),
                (r"(?:please\s+)?email\s+(?:me\s+)?(?:for|with)\s+(?:questions|concerns|issues)", "Email for questions specified"),
                (r"check\s+(?:my\s+)?email\s+(?:regularly|daily|frequently)", "Email checking frequency mentioned"),
                (r"monitor\s+(?:my\s+)?email", "Email monitoring mentioned"),
            ]
            
            for pattern, description in communication_patterns:
                if re.search(pattern, text_lower):
                    # Additional validation: make sure it's not just in a contact info list
                    match_obj = re.search(pattern, text_lower)
                    if match_obj:
                        # Get context around the match (50 chars before and after)
                        start = max(0, match_obj.start() - 50)
                        end = min(len(original_text), match_obj.end() + 50)
                        context = original_text[start:end].lower()
                        
                        # Exclude if it's just in a contact info table/list (basic indicators)
                        exclusion_indicators = [
                            'email:', '@unh.edu', 'phone:', 'office:', 'address:', 
                            'contact information', 'instructor information'
                        ]
                        
                        # If context suggests it's just a contact listing, skip it
                        if any(indicator in context for indicator in exclusion_indicators):
                            logging.info(f"SKIP: Found '{description}' but appears to be in contact listing context")
                            continue
                        
                        response_found = description
                        logging.info(f"SUCCESS: Found email communication method discussion: {description}")
                        break
        
        if response_found:
            info["Instructor Response Time"] = response_found
            logging.info(f"SUCCESS: Set email response time/availability: {response_found}")
        else:
            logging.info("INFO: No email response time or communication method discussion found - leaving empty")
            # CRITICAL: Do not auto-fill anything - only explicit mentions count
    
    # Enhanced: Technical requirements
    if "Technical Requirements" not in info or not info.get("Technical Requirements"):
        tech_items = []
        
        tech_keywords = {
            "canvas": "Canvas LMS",
            "zoom": "Zoom",
            "teams": "Microsoft Teams",
            "computer": "Computer with internet",
            "webcam": "Webcam",
            "microphone": "Microphone",
            "software": "Required software as specified"
        }
        
        for keyword, label in tech_keywords.items():
            if keyword in text_lower:
                tech_items.append(label)
        
        if tech_items:
            info["Technical Requirements"] = ", ".join(tech_items)
    
    return info


async def extract_course_information(text, llm):
    """
    Enhanced extraction with much better field detection patterns.
    
    Args:
        text (str): Document text to analyze
        llm: Language model instance
        
    Returns:
        dict: Extracted course information
    """
    if not text:
        return {"error": "No text provided"}
    
    # Use smart truncation to preserve key sections
    limited_text = smart_text_truncation(text, max_length=60000)
    
    # Generate hash for caching
    text_hash = hashlib.md5(limited_text.encode()).hexdigest()
    
    # Check cache
    existing_doc = session.query(DocumentInfo).filter_by(doc_hash=text_hash).first()
    if existing_doc:
        logging.info("Using cached document info")
        return json.loads(existing_doc.extracted_info)
    
    # Format prompt with text
    prompt = EXTRACTION_PROMPT.format(limited_text=limited_text)
    
    try:
        # Call LLM
        logging.info("DEBUG: Calling LLM for extraction...")
        response = await llm.ainvoke(prompt)
        raw_text = response.content.strip()
        
        logging.info(f"DEBUG: LLM Response length: {len(raw_text)} characters")
        
        # Check if LLM mentioned SLOs in raw response
        if "student learning outcome" in raw_text.lower():
            logging.info("SUCCESS: LLM response contains 'Student Learning Outcome'")
        if "learning objective" in raw_text.lower():
            logging.info("SUCCESS: LLM response contains 'Learning Objective'")
        
        # Extract JSON from response
        original_raw = raw_text
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
            logging.info("DEBUG: Extracted JSON from ```json``` blocks")
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
            logging.info("DEBUG: Extracted JSON from ``` blocks")
        else:
            logging.info("DEBUG: No code blocks found, using raw response")
        
        # Clean JSON
        raw_text = raw_text.strip()
        if not raw_text.startswith("{"):
            start_idx = raw_text.find("{")
            if start_idx != -1:
                raw_text = raw_text[start_idx:]
                logging.info("DEBUG: Found JSON start after cleaning")
        if not raw_text.endswith("}"):
            end_idx = raw_text.rfind("}")
            if end_idx != -1:
                raw_text = raw_text[:end_idx + 1]
                logging.info("DEBUG: Found JSON end after cleaning")
        
        logging.info(f"DEBUG: Final JSON to parse: {len(raw_text)} characters")
        
        # Parse and validate
        extracted_info = json.loads(raw_text)
        logging.info(f"SUCCESS: Successfully parsed JSON with {len(extracted_info)} fields")
        
        # CRITICAL FIX: Convert lists to strings for compliance checker
        
        # Convert SLO lists to strings
        if "Student Learning Outcomes" in extracted_info:
            slo_content = extracted_info["Student Learning Outcomes"]
            logging.info(f"SUCCESS: Found SLO field in parsed JSON: {len(str(slo_content))} chars")
            logging.info(f"DEBUG: SLO field type from LLM: {type(slo_content)}")
            
            # If LLM returned a list, convert to string
            if isinstance(slo_content, list):
                if slo_content:  # Non-empty list
                    converted_slo = '\n'.join(str(item) for item in slo_content if item)
                    extracted_info["Student Learning Outcomes"] = converted_slo
                    logging.info(f"CONVERSION: Converted SLO list to string: {len(converted_slo)} chars")
                else:
                    extracted_info["Student Learning Outcomes"] = ""
                    logging.warning("CONVERSION: Empty SLO list converted to empty string")
            else:
                logging.info(f"CONTENT: SLO field content: {slo_content}")
        else:
            logging.warning("ERROR: NO 'Student Learning Outcomes' field in parsed JSON")
            logging.info(f"DEBUG: Available fields: {list(extracted_info.keys())}")
            
            # Check if LLM used a different field name
            for key in extracted_info.keys():
                if any(word in key.lower() for word in ['outcome', 'objective', 'slo']):
                    logging.info(f"DEBUG: Found related field '{key}': {extracted_info[key]}")
        
        # CRITICAL FIX: Convert Assignment Types and Delivery lists to strings
        if "Assignment Types and Delivery" in extracted_info:
            types_content = extracted_info["Assignment Types and Delivery"]
            logging.info(f"SUCCESS: Found Types & Delivery field in parsed JSON: {len(str(types_content))} chars")
            logging.info(f"DEBUG: Types & Delivery field type from LLM: {type(types_content)}")
            
            # If LLM returned a list, convert to string
            if isinstance(types_content, list):
                if types_content:  # Non-empty list
                    converted_types = ', '.join(str(item) for item in types_content if item)
                    extracted_info["Assignment Types and Delivery"] = converted_types
                    logging.info(f"CONVERSION: Converted Types & Delivery list to string: {len(converted_types)} chars")
                else:
                    extracted_info["Assignment Types and Delivery"] = ""
                    logging.warning("CONVERSION: Empty Types & Delivery list converted to empty string")
            else:
                logging.info(f"CONTENT: Types & Delivery field content: {types_content}")
        else:
            logging.info("DEBUG: NO 'Assignment Types and Delivery' field in parsed JSON")
        
        # CRITICAL FIX: Convert Final Grade Scale specifically (special handling)
        if "Final Grade Scale" in extracted_info:
            grade_content = extracted_info["Final Grade Scale"]
            logging.info(f"SUCCESS: Found Final Grade Scale in parsed JSON: {len(str(grade_content))} chars")
            logging.info(f"DEBUG: Final Grade Scale type from LLM: {type(grade_content)}")
            
            # Handle different formats the LLM might return
            if isinstance(grade_content, list):
                if grade_content:  # Non-empty list
                    # Convert list to newline-separated string for better readability
                    converted_grades = '\n'.join(str(item) for item in grade_content if item)
                    extracted_info["Final Grade Scale"] = converted_grades
                    logging.info(f"CONVERSION: Converted Final Grade Scale list to string: {len(converted_grades)} chars")
                else:
                    extracted_info["Final Grade Scale"] = ""
                    logging.warning("CONVERSION: Empty Final Grade Scale list converted to empty string")
            elif isinstance(grade_content, dict):
                # If it's an object, convert to readable string format
                grade_items = []
                for grade, range_val in grade_content.items():
                    grade_items.append(f"{grade}: {range_val}")
                converted_grades = '\n'.join(grade_items)
                extracted_info["Final Grade Scale"] = converted_grades
                logging.info(f"CONVERSION: Converted Final Grade Scale dict to string: {len(converted_grades)} chars")
            else:
                logging.info(f"CONTENT: Final Grade Scale field content: {grade_content}")
        else:
            logging.info("DEBUG: NO 'Final Grade Scale' field in parsed JSON")
        
        # CRITICAL FIX: Convert any other critical fields that might be lists  
        list_to_string_fields = [
            "Grading Procedures",
            "Course Topics & Dates",
            "Other Materials", 
            "Technical Requirements",
            "Phone Number",           # Phone numbers might come as lists  
            "Office Hours",           # Office hours might come as lists
            "Instructor Email"        # Emails might come as lists
        ]
        
        for field in list_to_string_fields:
            if field in extracted_info:
                field_content = extracted_info[field]
                if isinstance(field_content, list):
                    if field_content:  # Non-empty list
                        # Use appropriate separator based on field type
                        separator = '\n' if field in ["Grading Procedures", "Course Topics & Dates"] else ', '
                        converted_field = separator.join(str(item) for item in field_content if item)
                        extracted_info[field] = converted_field
                        logging.info(f"CONVERSION: Converted {field} list to string: {len(converted_field)} chars")
                    else:
                        extracted_info[field] = ""
                        logging.warning(f"CONVERSION: Empty {field} list converted to empty string")
        
        # Log sample of original response for debugging
        logging.info(f"DEBUG: LLM Response sample: {original_raw[:500]}...")
        
        # Enhanced post-processing - ALWAYS run this to catch missed fields
        logging.info("DEBUG: Running enhanced post-processing...")
        if "Student Learning Outcomes" in extracted_info:
            slo_before = extracted_info['Student Learning Outcomes']
            logging.info(f"CONTENT: SLOs BEFORE post-processing: type={type(slo_before)}, content='{slo_before}'")
        else:
            logging.info("ERROR: NO SLOs in extracted_info before post-processing")
            
        extracted_info = enhanced_post_process(extracted_info, limited_text)
        
        if "Student Learning Outcomes" in extracted_info:
            slo_after = extracted_info['Student Learning Outcomes']
            logging.info(f"CONTENT: SLOs AFTER post-processing: type={type(slo_after)}, content='{slo_after}'")
            
            # CHECK FOR CORRUPTION
            if isinstance(slo_after, (int, float)) or (isinstance(slo_after, str) and slo_after.isdigit()):
                logging.error(f"ERROR: SLO content was corrupted to numeric: '{slo_after}' (type: {type(slo_after)})")
        else:
            logging.info("ERROR: NO SLOs in extracted_info after post-processing")
        
        # Less aggressive filtering - keep partial information with debugging
        logging.info("DEBUG: Applying field filtering...")
        before_count = len(extracted_info)
        slo_before_filter = extracted_info.get("Student Learning Outcomes")
        
        filtered_info = {}
        for k, v in extracted_info.items():
            # CRITICAL FIX: Don't modify the value during filtering
            original_value = v
            
            # Check if value is meaningful (but don't convert it)
            if v is not None and v != "" and str(v).strip() != "":
                # PRESERVE ORIGINAL VALUE - don't convert or modify
                filtered_info[k] = original_value
                
                if k == "Student Learning Outcomes":
                    logging.info(f"DEBUG: Preserving SLO field: type={type(original_value)}, content='{original_value}'")
            else:
                logging.info(f"FILTER: Filtered out field '{k}': empty or whitespace only - value was: '{v}'")
        
        extracted_info = filtered_info
        after_count = len(extracted_info)
        slo_after_filter = extracted_info.get("Student Learning Outcomes")
        
        logging.info(f"DEBUG: Filtering result: {before_count} to {after_count} fields")
        
        if slo_before_filter and not slo_after_filter:
            logging.error(f"ERROR: SLO FIELD WAS FILTERED OUT! Content was: {slo_before_filter}")
        elif slo_after_filter:
            # CRITICAL BUG CHECK: Make sure we didn't accidentally store the length instead of content
            if isinstance(slo_after_filter, str) and slo_after_filter.isdigit() and int(slo_after_filter) < 10:
                logging.error(f"CRITICAL BUG: SLO field contains just a number '{slo_after_filter}' instead of actual content!")
                logging.error(f"This suggests len() was used somewhere instead of preserving content")
                # Try to recover from before filter
                if slo_before_filter and not slo_before_filter.isdigit():
                    extracted_info["Student Learning Outcomes"] = slo_before_filter
                    logging.info(f"RECOVERY: Restored SLO content from before filter: {slo_before_filter}")
            else:
                logging.info(f"SUCCESS: SLO field survived filtering: {len(str(slo_after_filter))} chars")
                logging.info(f"DEBUG: Final SLO content type: {type(slo_after_filter)}")
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        extracted_info = {"error": "Failed to parse response"}
    except Exception as e:
        logging.error(f"Extraction error: {e}")
        extracted_info = {"error": str(e)}
    
    # Cache result
    try:
        new_doc = DocumentInfo(doc_hash=text_hash, extracted_info=json.dumps(extracted_info))
        session.add(new_doc)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Cache error: {e}")
    
    return extracted_info
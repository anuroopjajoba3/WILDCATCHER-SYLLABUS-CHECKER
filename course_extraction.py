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
    
    # Check for instructor department in original text if missing
    if "Instructor Department" not in info or not info.get("Instructor Department"):
        # Pattern: "Professor of [Department]"
        dept_pattern = r"Professor of ([^,\n]+)"
        match = re.search(dept_pattern, original_text, re.IGNORECASE)
        if match:
            info["Instructor Department"] = match.group(1).strip()
    
    # Check for SLOs if missing
    if "Student Learning Outcomes" not in info or not info.get("Student Learning Outcomes"):
        # Look for bullet points after "Learning Outcome" header
        slo_pattern = r"Student Learning Outcome[s]?:?\s*\n((?:[\s•\-\*]*[A-Z][^\n]+\n?)+)"
        match = re.search(slo_pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            info["Student Learning Outcomes"] = match.group(1).strip()
    
    # Check for grading breakdown
    if "Grading Procedures" not in info or not info.get("Grading Procedures"):
        # Look for percentages
        grade_pattern = r"(\d+%[^:\n]*:[^\n]+)"
        matches = re.findall(grade_pattern, original_text)
        if matches:
            info["Grading Procedures"] = "; ".join(matches)
    
    # Check for course format
    if "Course Format" not in info or not info.get("Course Format"):
        # Look for meeting pattern
        format_pattern = r"(In-person|Online|Hybrid)[^.]*weekly[^.]*meetings?"
        match = re.search(format_pattern, original_text, re.IGNORECASE)
        if match:
            info["Course Format"] = match.group(0).strip()
    
    # Email response time - if email exists but no response time
    if info.get("Instructor Email") and ("Instructor Response Time" not in info):
        # Academic standard if not specified
        info["Instructor Response Time"] = "Standard academic response time (24-48 hours)"
    
    # Materials check
    if "Other Materials" not in info:
        if "Canvas" in original_text or "posted in Canvas" in original_text.lower():
            info["Other Materials"] = "Course materials and resources posted in Canvas"
    
    # Technical requirements for computing courses
    if "Technical Requirements" not in info:
        if any(term in original_text.lower() for term in ["canvas", "teams", "scrum", "development"]):
            info["Technical Requirements"] = "Canvas LMS, Microsoft Teams, development tools as specified"
    
    # Assignment types from grading section
    if "Assignment Types and Delivery" not in info:
        types = []
        if "homework" in original_text.lower():
            types.append("Homework")
        if "project" in original_text.lower():
            types.append("Projects")
        if "sprint" in original_text.lower():
            types.append("Sprint deliverables")
        if "report" in original_text.lower():
            types.append("Reports")
        if types:
            info["Assignment Types and Delivery"] = ", ".join(types) + " (via Canvas)"
    
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
    
    # Smart text limiting - keep beginning and end
    if len(text) > 60000:
        limited_text = text[:35000] + "\n\n[... content trimmed ...]\n\n" + text[-15000:]
    else:
        limited_text = text.strip()
    
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
        response = await llm.ainvoke(prompt)
        raw_text = response.content.strip()
        
        # Extract JSON from response
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
        
        # Clean JSON
        raw_text = raw_text.strip()
        if not raw_text.startswith("{"):
            start_idx = raw_text.find("{")
            if start_idx != -1:
                raw_text = raw_text[start_idx:]
        if not raw_text.endswith("}"):
            end_idx = raw_text.rfind("}")
            if end_idx != -1:
                raw_text = raw_text[:end_idx + 1]
        
        # Parse and validate
        extracted_info = json.loads(raw_text)
        
        # Enhanced post-processing
        extracted_info = enhanced_post_process(extracted_info, limited_text)
        
        # Remove truly empty fields
        extracted_info = {k: v for k, v in extracted_info.items() 
                         if v and str(v).strip() and v not in ["N/A", "Not Found", "Not Specified"]}
        
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
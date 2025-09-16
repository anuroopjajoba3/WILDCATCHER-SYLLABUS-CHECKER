"""
Simple, fast SLO detection for Windows
This replaces the complex regex patterns that can cause hanging on large documents
"""

import re
import logging

def fast_slo_detection(text):
    """
    Fast SLO detection with size limits to prevent hanging.
    Returns (has_slos: bool, slo_content: str or None)
    """
    logging.info("Starting fast SLO detection...")

    # Limit text size to prevent hanging
    if len(text) > 20000:
        text = text[:20000]
        logging.info("Truncated large document to 20,000 characters for faster processing")

    try:
        return _detect_slos_fast(text)
    except Exception as e:
        logging.error(f"Error in SLO detection: {e}")
        return False, None

def _detect_slos_fast(text):
    """Fast SLO detection without complex regex patterns"""

    # Method 1: Simple keyword search
    slo_keywords = [
        "student learning outcomes",
        "learning outcomes",
        "course objectives",
        "learning objectives",
        "students will be able to",
        "upon completion"
    ]

    text_lower = text.lower()

    for keyword in slo_keywords:
        if keyword in text_lower:
            # Found keyword, try to extract content around it
            pos = text_lower.find(keyword)
            if pos != -1:
                # Get 500 chars after the keyword
                start = pos
                end = min(pos + 1000, len(text))
                section = text[start:end]

                # Look for bullet points or numbered lists
                lines = section.split('\n')
                slo_lines = []

                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue

                    # Check if line looks like an SLO item
                    if (line.startswith(('•', '-', '*', '▪')) or
                        re.match(r'^\d+\.?\s', line) or
                        any(verb in line.lower() for verb in ['analyze', 'evaluate', 'demonstrate', 'understand', 'apply', 'identify'])):

                        # Clean the line
                        cleaned = re.sub(r'^[\s•\-\*▪\d\.)]+', '', line).strip()
                        if len(cleaned) > 10:  # Meaningful content
                            slo_lines.append(cleaned)

                if len(slo_lines) >= 1:
                    content = '\n'.join(slo_lines[:5])  # Limit to first 5 items
                    logging.info(f"SUCCESS: Found SLOs via keyword '{keyword}': {len(slo_lines)} items")
                    return True, content

    # Method 2: Simple action verb detection
    action_verbs = ['analyze', 'evaluate', 'demonstrate', 'understand', 'apply', 'identify', 'describe', 'explain']

    # Split text into chunks and look for multiple action verbs
    lines = text.split('\n')
    verb_lines = []

    for line in lines:
        line = line.strip()
        if len(line) > 20 and len(line) < 200:  # Reasonable length
            line_lower = line.lower()
            verb_count = sum(1 for verb in action_verbs if verb in line_lower)

            if verb_count >= 1 and (line.startswith(('•', '-', '*', '▪')) or re.match(r'^\d+\.?\s', line)):
                cleaned = re.sub(r'^[\s•\-\*▪\d\.)]+', '', line).strip()
                if len(cleaned) > 10:
                    verb_lines.append(cleaned)

    if len(verb_lines) >= 2:
        content = '\n'.join(verb_lines[:5])  # Limit to first 5 items
        logging.info(f"SUCCESS: Found SLOs via action verb detection: {len(verb_lines)} items")
        return True, content

    logging.info("No SLOs found")
    return False, None
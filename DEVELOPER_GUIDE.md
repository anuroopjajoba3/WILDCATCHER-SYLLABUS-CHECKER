# Developer Guide: Adding New Field Detectors

## Overview

This application uses a simple architecture for detecting different fields in syllabus documents. Currently, only Student Learning Outcomes (SLOs) are implemented, but you can easily add more fields.

## Simple Structure

```
Project Structure:
├── detectors/                   # All field detection modules
│   └── slo_detector.py         # SLO detection (example)
├── api_routes.py               # Import your detectors here
└── DEVELOPER_GUIDE.md          # This file
```

That's it. No complex configuration files or engines.

## Adding a New Field Detector

### Step 1: Create Your Detector File

First, create a new file in the detectors folder. See other detectors as examples to base your code on. Each field is unique and has their own patterns, so you'll need to customize the detection logic for your specific field.

Example: `detectors/course_info_detector.py`

```python
import re
import logging
from typing import Dict, Any

class CourseIdDetector:
    def __init__(self):
        self.field_name = 'course_id'
        self.logger = logging.getLogger('detector.course_id')

    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info(f"Starting detection for field: {self.field_name}")

        # Your detection logic here
        pattern = r'([A-Z]{2,4}\s*\d{3,4})'
        matches = re.findall(pattern, text)

        if matches:
            course_id = matches[0]
            result = {
                'field_name': self.field_name,
                'found': True,
                'content': course_id
            }
            self.logger.info(f"FOUND: {self.field_name}")
        else:
            result = {
                'field_name': self.field_name,
                'found': False,
                'content': None
            }
            self.logger.info(f"NOT_FOUND: {self.field_name}")

        return result
```

### Step 2: Edit api_routes.py

Second, edit api_routes.py. The routes are responsible for handling file uploads and calling the detectors to analyze the text. That's why you need to add your new detector there.

```python
# Import your new detector
from detectors.course_detector import CourseDetector

def detect_slos_with_regex(text):
    # Use SLO detector
    slo_detector = SLODetector()
    slo_result = slo_detector.detect(text)

    # Add your new detector
    course_detector = CourseDetector()
    course_result = course_detector.detect(text)

    # Return results (modify as needed)
    has_slos = slo_result.get('found', False)
    slo_content = slo_result.get('content', None)

    return has_slos, slo_content
```

## Required Result Format

Detectors must return this format:

```python
{
    'field_name': 'course_id',      # Name of your field
    'found': True,                  # Whether field was detected
    'content': 'CS 101'             # Extracted content (if found)
}
```

## Quick Start

Ready to add your first field?

1. Copy `detectors/slo_detector.py` to `detectors/course_id_detector.py`
2. Change class name to `CourseIdDetector`
3. Change `field_name = 'course_id'`
4. Update the detection logic for course IDs
5. Import and use it in `api_routes.py`
6. Test it

Start with simple fields like course_id, instructor_email, or instructor_name.
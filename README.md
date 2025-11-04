<<<<<<< HEAD
# Syllabus SLO & Online Modality Detector

## Overview
This application analyzes academic syllabus documents to detect Student Learning Outcomes (SLOs) and determine course delivery modality (Online, In-Person, or Hybrid). It provides a simple web interface for uploading PDF and DOCX files and returns immediate, human-readable feedback.

## What It Does
The system examines uploaded syllabi and:
Checks for the presence of properly formatted Student Learning Outcomes sections.
Classifies course delivery as Online, In-Person, or Hybrid with a confidence score, based on explicit wording (e.g., “asynchronous,” “via Canvas/Zoom”) or clear on-campus signals (e.g., building/room, meeting days/times).

## Supported Formats
Individual PDF files
Word documents (.docx)
ZIP archives containing multiple files
Folder uploads for batch processing

## How It Works
Extracts text from the document and normalizes it for reliable matching.
Uses lightweight, explainable pattern matching to detect SLO sections and modality cues.
Returns results immediately in the UI, including PASS/FAIL for SLOs and an Online/In-Person/Hybrid badge with confidence.

## SLO Requirements
The detector looks for sections with these specific titles:
Student Learning Outcomes
Student Learning Objectives
Learning Outcomes
Learning Objectives
The system is intentionally strict about titles and structure to align with academic compliance expectations.

## Online Modality Detection
The modality detector looks for:
Online indicators: online, asynchronous, synchronous online, Canvas/MyCourses, LMS, Zoom/Teams, delivered remotely.
In-Person indicators: building/room names, “Room ###,” “Hall,” meeting days/times with a physical location.
Hybrid indicators: combinations of on-campus meeting info plus online platforms or “hybrid” wording.
It assigns a confidence score based on the strength and number of signals found.

## Getting Started
Run the application using Python and access the web interface in your browser. Upload your syllabus documents to receive instant SLO and modality results.

## Development
The app is built with Flask and a modular “detectors” pattern. You can add new field detectors easily (for example, instructor email or grading scale) without touching the rest of the system.

## Project Structure

# Core Application Files

**main.py** — Application entry point
Starts the Flask server
Loads configuration and registers routes
Runs on port 8001

**config.py** — Application configuration
Sets logging level and server settings (host, port, debug)

**api_routes.py** — Web request handler
Handles uploads for PDF/DOCX/ZIP/folders
Calls detectors (SLO and Online Modality)
Returns structured results to the frontend

# Document Processing

**document_processing.py** — File text extraction
Extracts text from PDFs (pdfplumber) and DOCX (python-docx)
Normalizes text and handles extraction edge cases
Detectors

**detectors/slo_detector.py** — SLO detection engine
Finds approved SLO section titles
Applies strict header matching and content checks
Returns PASS/FAIL and preview of SLO content

**detectors/online_detection.py** — Course modality detection
Scans for online, in-person, and hybrid indicators
Weights multiple signals to compute a confidence score
Returns modality label and supporting evidence

## Frontend

**templates/index.html** — User interface
Drag-and-drop file upload
Shows SLO status (PASS/FAIL) with messages and SLO preview
Shows modality badge (Online/In-Person/Hybrid) with confidence and evidence
Supports multiple files and ZIP processing

# Documentation

**README.md** — Project overview (this file)
Explains features, formats, and workflow

**DEVELOPER_GUIDE.md** — Development instructions
How to add new detectors
How to wire them into the API and UI
Best practices for patterns and messaging

**requirements.txt** — Dependencies
Minimal stack: Flask, pdfplumber, python-docx, and standard utilities
No LangChain or OpenAI required

## Data Flow
User uploads file via the web interface.
api_routes.py receives the file and calls document_processing.py for text extraction.
Normalized text is passed to detectors/slo_detector.py and detectors/online_detection.py.
The SLO detector returns PASS/FAIL and any extracted SLO content; the modality detector returns Online/In-Person/Hybrid with confidence and evidence.
Results are rendered back to the user in the UI with clear messaging.

Each file has a focused responsibility in the SLO and modality detection pipeline.
=======
# Syllabus Field Detector

## Overview
This application analyzes academic syllabi to automatically extract and validate important course information. Upload a PDF or Word document, and the system will detect everything from Student Learning Outcomes to grading policies, instructor info, and course delivery modality.

## What It Does
The system scans uploaded syllabi and extracts 16 different fields:

**Course Basics**
- Student Learning Outcomes (SLOs)
- Course delivery modality (Online, In-Person, or Hybrid)
- Credit hours
- Expected workload

**Instructor Information**
- Name, title, and department
- Email address
- Office location and hours
- Phone number

**Grading & Assignments**
- Grading scale (A, B, C, etc.)
- Grading procedures
- Assignment types
- Assignment delivery platforms (Canvas, MyCourses, etc.)
- Late/missing work policies

Each field is detected using pattern matching and regex—no AI models required. The results are fast, explainable, and easy to verify.

## Supported Formats
- Individual PDF files
- Word documents (.docx)
- ZIP archives containing multiple files
- Folder uploads for batch processing

## How It Works
1. Extract text from the document
2. Run it through 16 specialized detectors
3. Return results with confidence scores and evidence
4. Display everything in a clean web interface

The detectors use lightweight pattern matching to find specific sections and keywords. For example, the modality detector looks for phrases like "asynchronous," "Zoom," or "Room 204" to figure out if a course is online, in-person, or hybrid.

## Testing & Accuracy
We maintain a ground truth dataset of 40 verified syllabi to test detector accuracy. The automated testing system (`test_runner.py`) compares detector predictions against known-correct values and tracks per-field accuracy.

### Current Test Results

| Field                          | Accuracy | Correct/Total |
|--------------------------------|----------|---------------|
| modality                       | 77.5%    | 31/40         |
| SLOs                          | 100.0%   | 40/40         |
| email                          | 85.0%    | 34/40         |
| credit_hour                    | 85.0%    | 34/40         |
| workload                       | 97.5%    | 39/40         |
| instructor_name                | 80.0%    | 32/40         |
| instructor_title               | 80.0%    | 32/40         |
| instructor_department          | 87.5%    | 35/40         |
| office_address                 | 90.0%    | 36/40         |
| office_hours                   | 77.5%    | 31/40         |
| office_phone                   | 85.0%    | 34/40         |
| assignment_types_title         | 90.0%    | 36/40         |
| grading_procedures_title       | 82.5%    | 33/40         |
| deadline_expectations_title    | 72.5%    | 29/40         |
| assignment_delivery            | 90.0%    | 36/40         |
| final_grade_scale              | 80.0%    | 32/40         |
| **OVERALL**                    | **85.0%** | **544/640**   |

Run tests yourself:
```bash
python test_runner.py
```

Results are saved to `test_results.json` with detailed breakdowns for each field.

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python main.py`
3. Open your browser to `http://localhost:8001`
4. Upload a syllabus and see what gets detected

## Project Structure

**Core Application**
- `main.py` — Entry point, starts the Flask server on port 8001
- `config.py` — Application configuration
- `api_routes.py` — Handles file uploads and orchestrates all detectors
- `document_processing.py` — Extracts text from PDFs and DOCX files

**Detectors** (16 total in `detectors/`)
- `slo_detector.py` — Student Learning Outcomes
- `online_detection.py` — Course delivery modality
- `instructor_detector.py` — Instructor name, title, department
- `email_detector.py` — Email addresses
- `office_information_detection.py` — Office location, hours, phone
- `credit_hours_detection.py` — Credit hours
- `workload_detection.py` — Expected workload
- `grading_scale_detection.py` — Letter grade scales
- `grading_procedures_detection.py` — Grading policy sections
- `assignment_types_detection.py` — Assignment categories
- `assignment_delivery_detection.py` — Submission platforms
- `late_missing_work_detector.py` — Late work policies

**Testing**
- `test_runner.py` — Automated testing framework
- `ground_truth.json` — 40 manually verified syllabi with correct field values
- `ground_truth_syllabus/` — PDF/DOCX files for testing
- `test_results.json` — Latest test results with accuracy metrics

**Frontend**
- `templates/index.html` — Web UI with drag-and-drop upload

**Documentation**
- `README.md` — This file
- `DEVELOPER_GUIDE.md` — How to add new detectors and integrate them

## Development
The app uses a modular detector pattern. Each detector is independent and returns a simple dictionary:
```python
{
  'field_name': 'email',
  'found': True,
  'content': 'professor@university.edu'
}
```

Adding a new detector is straightforward:
1. Create a new file in `detectors/`
2. Implement the `detect(text)` method
3. Import and call it in `api_routes.py`
4. Update the UI to display results

See `DEVELOPER_GUIDE.md` for detailed instructions.

## Tech Stack
- **Flask** — Web framework
- **pdfplumber** — PDF text extraction
- **python-docx** — Word document processing
- **regex** — Pattern matching

No LLMs, no external APIs, no complicated dependencies. Just straightforward Python.

## Data Flow
```
Upload file → Extract text → Run detectors → Return JSON → Display results
```

Each detector examines the extracted text independently, so you can enable/disable fields or add new ones without affecting the others.
>>>>>>> 696656f17af01c822baab3b0cd6215a302accefa

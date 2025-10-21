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

Current overall accuracy: **~81%**

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

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

# Student Learning Outcomes Detector

## Overview

This application analyzes academic syllabus documents to detect Student Learning Outcomes (SLOs) and verify compliance with educational standards. It provides a simple web interface for uploading PDF and DOCX files and returns immediate feedback on whether the required SLO sections are present.

## What It Does

The system examines uploaded syllabus documents and checks for the presence of properly formatted Student Learning Outcomes sections. It looks for specific title formats and validates that the content follows standard academic formatting.

## Supported Formats

The application accepts individual PDF files, Word documents, ZIP archives containing multiple files, and folder uploads for batch processing.

## How It Works

Users upload their syllabus documents through a web interface. The system extracts text from the documents and analyzes it using pattern matching to identify SLO sections. Results are displayed immediately, showing whether the document passes or fails the compliance check.

## SLO Requirements

The detector looks for sections with these specific titles:
- Student Learning Outcomes
- Student Learning Objectives
- Learning Outcomes
- Learning Objectives

The system is designed to be strict about formatting to ensure academic compliance standards are met.

## Getting Started

Run the application using Python and access the web interface through your browser. Upload your syllabus documents and receive instant feedback on SLO compliance.

## Development

The application is built with Flask and uses a modular detector system. New field detectors can be easily added to check for additional syllabus requirements beyond SLOs.

## Project Structure

### Core Application Files

**main.py** - Application Entry Point
- Starts the Flask web server
- Creates the Flask app, loads configuration, registers routes, and runs the server
- Launches the application on port 8001

**config.py** - Application Configuration
- Manages application settings and logging
- Sets up logging, defines server settings (host, port, debug mode)
- Configures host (0.0.0.0), port (8001), and debug mode

**api_routes.py** - Web Request Handler
- Handles all HTTP requests and file uploads
- Processes file uploads (PDF, DOCX, ZIP, folders)
- Calls SLO detector to analyze documents
- Returns results to the frontend
- Manages the upload endpoint and home page routing

### Document Processing

**document_processing.py** - File Text Extraction
- Extracts text from uploaded documents
- Reads PDF files using pdfplumber
- Reads Word documents using python-docx
- Handles extraction errors and provides fallback methods
- Returns clean text for analysis

**detectors/slo_detector.py** - SLO Detection Engine
- Analyzes text to find Student Learning Outcomes
- Searches for approved SLO titles (Student Learning Outcomes, Learning Objectives, etc.)
- Uses smart scoring to distinguish section headers from casual mentions
- Extracts SLO content and returns structured results
- Prevents false positives with strict validation

### Frontend

**templates/index.html** - User Interface
- Provides the web interface users interact with
- File upload interface (drag-and-drop, browse files)
- Displays SLO detection results (PASS/FAIL)
- Shows found SLO content or missing field messages
- Handles multiple file uploads and ZIP processing

### Documentation

**README.md** - Project Overview
- Describes what the application does
- Simple explanation of SLO detection, supported formats, and usage

**DEVELOPER_GUIDE.md** - Development Instructions
- Guide for developers adding new features
- How to create new field detectors
- Backend integration steps
- Frontend display instructions
- Code examples and best practices

**requirements.txt** - Dependencies List
- Lists all Python packages needed to run the application
- Flask, pdfplumber, python-docx, and other required libraries

### Data Flow

1. User uploads file through the web interface
2. File is sent to the server via api_routes.py
3. Text is extracted using document_processing.py
4. Text is analyzed by detectors/slo_detector.py
5. Results are returned to the user through the web interface

Each file has a specific, focused responsibility in the SLO detection pipeline.
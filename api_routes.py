"""
API Routes Module
Flask route handlers for detectors application.
Handles file uploads and  detection.
"""

import os
import logging
import tempfile
import shutil
import zipfile
from flask import request, jsonify, render_template
from concurrent.futures import ThreadPoolExecutor, as_completed

from document_processing import extract_text_from_pdf, extract_text_from_docx
from detectors.slo_detector import SLODetector
from config import Config


def detect_slos_with_regex(text):
    """
    SLO detection using the SLO detector.
    Returns (has_slos: bool, slo_content: str or None)

    Developer Note:
    --------------
    To add more fields in the future, create new detector files in detectors/
    and import them here. For example:

    from detectors.course_detector import CourseDetector
    course_detector = CourseDetector()
    course_result = course_detector.detect(text)
    """
    # Create SLO detector and run detection
    slo_detector = SLODetector()
    result = slo_detector.detect(text)

    # Convert to simple format for API compatibility
    has_slos = result.get('found', False)
    slo_content = result.get('content', None)

    return has_slos, slo_content


def _process_single_file(file, temp_dir):
    """Process a single PDF or DOCX file."""
    filename = file.filename
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)

    logging.info(f"Uploaded file: {filename}")

    try:
        # Extract text
        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)

        if not extracted_text:
            return {
                "filename": filename,
                "slo_status": "ERROR",
                "has_slos": False,
                "message": "Could not extract text from file"
            }

        # Check for SLOs
        has_slos, slo_content = detect_slos_with_regex(extracted_text)

        # Create structured message format with HTML line breaks
        if has_slos:
            message = "SLOs detected"
        else:
            message = "Student Learning Outcome: Not find the acceptable title for SLO<br>• Student Learning Outcomes<br>• Student Learning Objectives<br>• Learning Outcomes<br>• Learning Objectives"

        result = {
            "filename": filename,
            "slo_status": "PASS" if has_slos else "FAIL",
            "has_slos": has_slos,
            "message": message
        }

        # Include SLO content if found (truncated)
        if has_slos and slo_content:
            result["slo_content"] = slo_content[:300] + "..." if len(slo_content) > 300 else slo_content

        return result

    except Exception as e:
        logging.error(f"Error processing {filename}: {e}")
        return {
            "filename": filename,
            "slo_status": "ERROR",
            "has_slos": False,
            "message": f"Error: {str(e)}"
        }


def _process_zip_file(zip_file, temp_dir):
    """Process a ZIP file by extracting and processing each document inside."""
    import zipfile

    zip_path = os.path.join(temp_dir, zip_file.filename)
    zip_file.save(zip_path)

    results = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        # Process all PDF and DOCX files in the extracted contents
        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if filename.endswith('.pdf') or filename.endswith('.docx'):
                    file_path = os.path.join(root, filename)
                    # Create a fake file object to reuse _process_single_file
                    class FakeFile:
                        def __init__(self, filename, path):
                            self.filename = filename
                            self._path = path
                        def save(self, path):
                            # File already exists, just copy it
                            import shutil
                            shutil.copy2(self._path, path)

                    fake_file = FakeFile(filename, file_path)
                    result = _process_single_file(fake_file, temp_dir)
                    if result:
                        results.append(result)

    except Exception as e:
        logging.error(f"Error processing ZIP file: {e}")
        results.append({
            "filename": zip_file.filename,
            "slo_status": "ERROR",
            "has_slos": False,
            "message": f"Error processing ZIP: {str(e)}"
        })

    return results


def create_routes(app):
    """
    Create all Flask routes for the application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/')
    def home():
        """Renders the homepage."""
        return render_template('index.html')
    
    @app.route('/upload', methods=['POST'])
    def upload_files():
        """Handles all file uploads - single files, multiple files, or ZIP files."""
        if 'file' in request.files:
            # Single file upload
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected.'}), 400
            files_to_process = [file]
        elif 'files' in request.files:
            # Multiple file upload
            files_to_process = request.files.getlist('files')
            if not files_to_process:
                return jsonify({'error': 'No files selected'}), 400
        else:
            return jsonify({'error': 'No files provided'}), 400

        temp_dir = tempfile.mkdtemp()
        results = []

        try:
            for file in files_to_process:
                if not file.filename:
                    continue

                # Handle ZIP files by extracting them first
                if file.filename.endswith('.zip'):
                    results.extend(_process_zip_file(file, temp_dir))
                elif file.filename.endswith('.pdf') or file.filename.endswith('.docx'):
                    result = _process_single_file(file, temp_dir)
                    if result:
                        results.append(result)

            if not results:
                return jsonify({'error': 'No valid files processed.'}), 400

            # Return single result or list of results
            if len(results) == 1:
                return jsonify(results[0])
            else:
                return jsonify({'results': results})

        finally:
            shutil.rmtree(temp_dir)
    
    

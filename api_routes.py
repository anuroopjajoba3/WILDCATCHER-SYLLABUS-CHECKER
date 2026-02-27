"""
Created: Spring 2025
updated: Fall 2025
Authors: Spring 2024 team, Fall 2025 Team Alpha
API Routes Module - Updated with Gemini AI integration
"""

from __future__ import annotations

import os
import re
from detectors.instructor_detector import InstructorDetector
import logging
import tempfile
import shutil
import zipfile
from flask import request, jsonify, render_template

from document_processing import extract_text_from_pdf, extract_text_from_docx
from gemini_analyzer import analyze_compliance_summary, answer_syllabus_question

from detectors.slo_detector import SLODetector
from detectors.grading_scale_detection import GradingScaleDetector
from detectors.online_detection import (
    detect_course_delivery,
    format_modality_card,
    quick_course_metadata,
)
from detectors.office_information_detection import OfficeInformationDetector
from detectors.email_detector import EmailDetector
from detectors.preferred_contact_detector import PreferredDetector
from detectors.late_missing_work_detector import LateDetector
from detectors.credit_hours_detection import CreditHoursDetector
from detectors.workload_detection import WorkloadDetector
from detectors.assignment_delivery_detection import AssignmentDeliveryDetector
from detectors.assignment_types_detection import AssignmentTypesDetector
from detectors.grading_process_detection import GradingProcessDetector
from detectors.response_time_detector import ResponseTimeDetector
from detectors.class_location_detector import ClassLocationDetector

# In-memory store for last uploaded syllabus text (for /ask endpoint)
_last_syllabus_text: dict[str, str] = {}


# -----------------------------------------------------------------------------
# Helpers (unchanged)
# -----------------------------------------------------------------------------

def detect_slos_with_regex(text: str) -> tuple[bool, str | None]:
    slo_detector = SLODetector()
    result = slo_detector.detect(text)
    has_slos = bool(result.get("found"))
    slo_content = result.get("content")
    return has_slos, slo_content


def _format_slo_card_from_info(has_slos: bool, slo_content: str | None) -> dict:
    if has_slos:
        first_lines = []
        if slo_content:
            first_lines = [ln.strip() for ln in slo_content.splitlines() if ln.strip()][:3]
        return {
            "status": "PASS",
            "heading": "SLOs detected",
            "message": first_lines[0] if first_lines else "SLO content present.",
            "details": "\n".join(f"- {x}" for x in first_lines) or "- SLO content present.",
        }
    return {
        "status": "FAIL",
        "heading": "SLOs not found",
        "message": (
            "Student Learning Outcome: Not find the acceptable title for SLO<br>"
            "• Student Learning Outcomes<br>• Student Learning Objectives<br>"
            "• Learning Outcomes<br>• Learning Objectives"
        ),
        "details": "- Add a Learning Objectives/SLOs section with clear bullet points.",
    }


def _safe_ext(name: str) -> str:
    return os.path.splitext(name or "")[1].lower()


def _massage_modality_card(card: dict, meta: dict) -> dict:
    if not isinstance(card, dict):
        return card or {}

    label = card.get("label", "Unknown")
    confidence = float(card.get("confidence") or 0.0)

    header_lines = []
    course_line = (meta or {}).get("course") or ""
    instr = (meta or {}).get("instructor") or ""
    email = (meta or {}).get("email") or ""
    instr_email = " — ".join([p for p in [instr, email] if p])

    if course_line:
        header_lines.append(course_line)
    if instr_email:
        header_lines.append(instr_email)

    EVIDENCE_KEEP = re.compile(
        r"\b(in-?person|on\s*campus|room\s+[A-Za-z]?\d{1,4}|hall|building|"
        r"online|zoom|teams|synchronous|asynchronous|hybrid|blended|canvas)\b",
        re.IGNORECASE,
    )
    evidence = [e.strip() for e in (card.get("evidence") or []) if e and EVIDENCE_KEEP.search(e)]
    evidence = evidence[:3]
    final_evidence = header_lines + evidence
    message = f"{label} modality detected" if label != "Unknown" else "Detected delivery"

    return {
        "status": card.get("status", "PASS" if label != "Unknown" else "FAIL"),
        "heading": "Course Delivery",
        "message": message,
        "label": label,
        "modality": label,
        "confidence": round(confidence, 2),
        "evidence": final_evidence,
    }


def _process_single_file(file, temp_dir: str) -> dict:
    filename = file.filename
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)

    logging.info(f"Uploaded file: {filename}")

    try:
        ext = _safe_ext(filename)
        if ext == ".pdf":
            extracted_text = extract_text_from_pdf(file_path)
        elif ext == ".docx":
            extracted_text = extract_text_from_docx(file_path)
        else:
            return {
                "filename": filename,
                "slo_status": "ERROR",
                "has_slos": False,
                "message": f"Unsupported file type: {ext}",
            }

        if not extracted_text:
            return {
                "filename": filename,
                "slo_status": "ERROR",
                "has_slos": False,
                "message": "Could not extract text from file",
            }

        # Store syllabus text for /ask endpoint
        _last_syllabus_text["text"] = extracted_text

        # --- SLO detection ---
        has_slos, slo_content = detect_slos_with_regex(extracted_text)

        result = {
            "filename": filename,
            "slo_status": "PASS" if has_slos else "FAIL",
            "has_slos": has_slos,
            "message": (
                "SLOs detected" if has_slos else
                "Student Learning Outcome: Not find the acceptable title for SLO<br>"
                "• Student Learning Outcomes<br>• Student Learning Objectives<br>"
                "• Learning Outcomes<br>• Learning Objectives"
            ),
        }
        if has_slos and slo_content:
            result["slo_content"] = (slo_content[:300] + "...") if len(slo_content) > 300 else slo_content

        result["slos"] = _format_slo_card_from_info(has_slos, slo_content)

        # --- Instructor detection ---
        instructor_detector = InstructorDetector()
        instructor_info = instructor_detector.detect(extracted_text)
        result["instructor"] = {
            "found": bool(instructor_info.get("found")),
            "name": instructor_info.get("name"),
            "title": instructor_info.get("title"),
            "department": instructor_info.get("department"),
        }

        # --- Grading scale detection ---
        grading_detector = GradingScaleDetector()
        grading_info = grading_detector.detect(extracted_text)
        result['grading_scale'] = {
            'found': bool(grading_info.get('found')),
            'content': grading_info.get('content')
        }

        # --- Modality detection ---
        if not (detect_course_delivery and format_modality_card and quick_course_metadata):
            result.update({
                "modality_status": "ERROR",
                "course_delivery": "Unknown",
                "course_delivery_confidence": 0.0,
                "course_delivery_message": "detectors/online_detection.py not found.",
                "course_delivery_evidence": [],
            })
        else:
            meta = quick_course_metadata(extracted_text)
            delivery_raw = detect_course_delivery(extracted_text)
            pretty = format_modality_card(delivery_raw, meta) or {}
            delivery_card = _massage_modality_card(pretty, meta)

            result["modality_status"] = delivery_card.get("status", "FAIL")
            result["course_delivery"] = delivery_card.get("modality", "Unknown")
            result["course_delivery_confidence"] = delivery_card.get("confidence", 0.0)
            result["course_delivery_message"] = delivery_card.get("message", "")
            result["course_delivery_evidence"] = delivery_card.get("evidence", [])
            result["modality"] = delivery_card

        # --- Office Information detection ---
        if OfficeInformationDetector:
            office_detector = OfficeInformationDetector()
            office_info = office_detector.detect(extracted_text)
            result["office_information"] = {
                "location": office_info.get("office_location", {}).get("content"),
                "hours": office_info.get("office_hours", {}).get("content"),
                "phone": office_info.get("phone", {}).get("content"),
                "found": office_info.get("found", False)
            }
        else:
            result["office_information"] = {"location": None, "hours": None, "phone": None, "found": False}

        # --- Email detection ---
        if EmailDetector:
            email_detector = EmailDetector()
            email_info = email_detector.detect(extracted_text)
            result["email_information"] = {
                "email": email_info.get("content"),
                "found": email_info.get("found", False),
                "confidence": email_info.get("confidence", 0.0)
            }
        else:
            result["email_information"] = {"email": None, "found": False, "confidence": 0.0}

        # --- Preferred Contact detection ---
        if PreferredDetector:
            preferred_detector = PreferredDetector()
            preferred_info = preferred_detector.detect(extracted_text)
            result["preferred_information"] = {
                "preferred": preferred_info.get("content"),
                "found": preferred_info.get("found", False),
                "confidence": preferred_info.get("confidence", 0.0)
            }
        else:
            result["preferred_information"] = {"preferred": None, "found": False, "confidence": 0.0}

        # --- Late detection ---
        if LateDetector:
            late_detector = LateDetector()
            late_info = late_detector.detect(extracted_text)
            result["late_information"] = {
                "late": late_info.get("content"),
                "found": late_info.get("found", False),
                "confidence": late_info.get("confidence", 0.0)
            }
        else:
            result["late_information"] = {"late": None, "found": False, "confidence": 0.0}

        # --- Credit Hours detection ---
        if CreditHoursDetector:
            credit_detector = CreditHoursDetector()
            credit_info = credit_detector.detect(extracted_text)
            result["credit_hours"] = {
                "hours": credit_info.get("content"),
                "found": credit_info.get("found", False)
            }
        else:
            result["credit_hours"] = {"hours": None, "found": False}

        # --- Workload detection ---
        if WorkloadDetector:
            workload_detector = WorkloadDetector()
            workload_info = workload_detector.detect(extracted_text)
            result["workload_information"] = {
                "description": workload_info.get("content"),
                "found": workload_info.get("found", False)
            }
        else:
            result["workload_information"] = {"description": None, "found": False}

        # --- Assignment Delivery detection ---
        assignment_delivery_detector = AssignmentDeliveryDetector()
        ad_info = assignment_delivery_detector.detect(extracted_text)
        result["assignment_delivery"] = {
            "found": bool(ad_info.get("found")),
            "content": ad_info.get("content"),
            "confidence": ad_info.get("confidence", 0.0)
        }

        # --- Assignment Types detection ---
        assignment_types_detector = AssignmentTypesDetector()
        at_info = assignment_types_detector.detect(extracted_text)
        result["assignment_types"] = {
            "found": bool(at_info.get("found")),
            "content": at_info.get("content")
        }

        # --- Grading Process detection ---
        try:
            grading_process_detector = GradingProcessDetector()
            gp_info = grading_process_detector.detect(extracted_text)
            result["grading_process"] = {
                "found": bool(gp_info.get("found")),
                "content": gp_info.get("content"),
                "confidence": gp_info.get("confidence", 0.0)
            }
        except:
            result["grading_process"] = {"found": False, "content": None, "confidence": 0.0}

        # --- Response Time detection ---
        try:
            response_time_detector = ResponseTimeDetector()
            rt_info = response_time_detector.detect(extracted_text)
            result["response_time"] = {
                "found": bool(rt_info.get("found")),
                "content": rt_info.get("content"),
                "confidence": rt_info.get("confidence", 0.0)
            }
        except:
            result["response_time"] = {"found": False, "content": None, "confidence": 0.0}

        # --- Class Location detection ---
        try:
            class_location_detector = ClassLocationDetector()
            cl_info = class_location_detector.detect(extracted_text)
            result["class_location"] = {
                "found": bool(cl_info.get("found")),
                "content": cl_info.get("content"),
                "confidence": cl_info.get("confidence", 0.0)
            }
        except:
            result["class_location"] = {"found": False, "content": None, "confidence": 0.0}

        # ✅ --- Gemini AI Compliance Summary ---
        try:
            gemini_summary = analyze_compliance_summary(extracted_text, result)
            if gemini_summary:
                result["ai_summary"] = gemini_summary
                logging.info(f"Gemini summary generated: score={gemini_summary.get('compliance_score')}")
        except Exception as e:
            logging.error(f"Gemini summary failed: {e}")
            result["ai_summary"] = None

        return result

    except Exception as e:
        logging.exception(f"Error processing {filename}: {e}")
        return {
            "filename": filename,
            "slo_status": "ERROR",
            "has_slos": False,
            "message": f"Error: {str(e)}",
        }


def _process_zip_file(zip_file, temp_dir: str) -> list[dict]:
    zip_path = os.path.join(temp_dir, zip_file.filename)
    zip_file.save(zip_path)

    results: list[dict] = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if _safe_ext(filename) in (".pdf", ".docx"):
                    file_path = os.path.join(root, filename)

                    class _FakeFile:
                        def __init__(self, filename, src_path):
                            self.filename = filename
                            self._src = src_path

                        def save(self, dst_path):
                            shutil.copy2(self._src, dst_path)

                    fake_file = _FakeFile(filename, file_path)
                    result = _process_single_file(fake_file, temp_dir)
                    if result:
                        results.append(result)

    except Exception as e:
        logging.exception(f"Error processing ZIP file: {e}")
        results.append({
            "filename": zip_file.filename,
            "slo_status": "ERROR",
            "has_slos": False,
            "message": f"Error processing ZIP: {str(e)}",
        })

    return results


# -----------------------------------------------------------------------------
# Route factory
# -----------------------------------------------------------------------------

def create_routes(app):

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload_files():
        if 'file' in request.files:
            file = request.files['file']
            if not file or file.filename == '':
                return jsonify({'error': 'No file selected.'}), 400
            files_to_process = [file]
        elif 'files' in request.files:
            files_to_process = request.files.getlist('files')
            if not files_to_process:
                return jsonify({'error': 'No files selected'}), 400
        else:
            return jsonify({'error': 'No files provided'}), 400

        temp_dir = tempfile.mkdtemp()
        results: list[dict] = []

        try:
            for file in files_to_process:
                if not file or not file.filename:
                    continue

                ext = _safe_ext(file.filename)

                if ext == '.zip':
                    results.extend(_process_zip_file(file, temp_dir))
                elif ext in ('.pdf', '.docx'):
                    result = _process_single_file(file, temp_dir)
                    if result:
                        results.append(result)
                else:
                    results.append({
                        "filename": file.filename,
                        "slo_status": "ERROR",
                        "has_slos": False,
                        "message": f"Unsupported file type: {ext}",
                    })

            if not results:
                return jsonify({'error': 'No valid files processed.'}), 400

            if len(results) == 1:
                return jsonify(results[0])
            else:
                return jsonify({'results': results})

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @app.route('/ask', methods=['POST'])
    def ask():
        """
        ✅ Updated: Now uses Gemini to answer questions about the uploaded syllabus.
        """
        try:
            data = request.get_json(silent=True) or {}
            user_msg = (data.get("message") or "").strip()

            if not user_msg:
                return jsonify({
                    "response": "Hi! Upload a syllabus PDF or DOCX and then ask me anything about it."
                })

            # Use Gemini if syllabus has been uploaded
            syllabus_text = _last_syllabus_text.get("text")

            if not syllabus_text:
                return jsonify({
                    "response": "Please upload a syllabus first, then I can answer your questions about it."
                })

            answer = answer_syllabus_question(user_msg, syllabus_text)
            return jsonify({"response": answer})

        except Exception as e:
            logging.exception("Error in /ask")
            return jsonify({"response": f"Server error: {e}"}), 500
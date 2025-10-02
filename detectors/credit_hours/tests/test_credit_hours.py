"""
Credit Hours & Workload Detection Test - Comprehensive
=======================================================
Tests detection against comprehensive syllabus data.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Setup paths
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from detectors.credit_hours_detection import CreditHoursDetector
from detectors.workload_detection import WorkloadDetector

# Import text extraction
try:
    from document_processing import extract_text_from_pdf, extract_text_from_docx
except ImportError:
    import PyPDF2
    from docx import Document

    def extract_text_from_pdf(filepath):
        text = ""
        with open(filepath, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def extract_text_from_docx(filepath):
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)


def normalize_credit_text(text: Optional[str]) -> Optional[str]:
    """Normalize credit hour text for comparison."""
    if text is None or text == "null":
        return None

    text = text.strip().lower()

    # Remove common variations
    text = text.replace("credits:", "").replace("credit:", "")
    text = text.replace("credit hours:", "").replace("credit hour:", "")
    text = text.strip()

    # Extract just the number
    import re
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        return match.group(1)

    return None


def normalize_workload_text(text: Optional[str]) -> Optional[str]:
    """Normalize workload text for comparison."""
    if text is None or text == "null":
        return None

    # Convert to lowercase for comparison
    text = text.strip().lower()

    # Remove extra whitespace
    import re
    text = re.sub(r'\s+', ' ', text)

    return text


def check_match(detected, expected):
    """Check if detected credit hours matches expected."""
    # Normalize both
    det_norm = normalize_credit_text(detected)
    exp_norm = normalize_credit_text(expected)

    # Both None = correct
    if exp_norm is None:
        return det_norm is None

    # Expected something but got nothing = incorrect
    if det_norm is None:
        return False

    # Compare the normalized numbers
    return det_norm == exp_norm


def check_workload_match(detected, expected):
    """Check if detected workload matches expected."""
    # Normalize both
    det_norm = normalize_workload_text(detected)
    exp_norm = normalize_workload_text(expected)

    # Both None = correct
    if exp_norm is None:
        return det_norm is None

    # Expected something but got nothing = incorrect
    if det_norm is None:
        return False

    # Check if the detected text contains the key parts of expected text
    # This handles minor formatting differences
    if exp_norm in det_norm or det_norm in exp_norm:
        return True

    # Extract numbers and compare
    import re
    det_numbers = set(re.findall(r'\d+', det_norm))
    exp_numbers = set(re.findall(r'\d+', exp_norm))

    # If the key numbers match, consider it a match
    if det_numbers and exp_numbers and det_numbers == exp_numbers:
        # Also check for key words
        key_words = ['hour', 'week', 'credit', 'minimum', 'engaged', 'work', 'student', 'academic']
        det_words = set(word for word in key_words if word in det_norm)
        exp_words = set(word for word in key_words if word in exp_norm)

        # If most key words match, consider it correct
        if len(det_words & exp_words) >= min(len(exp_words), 3):
            return True

    return False


def main():
    # Load comprehensive syllabus data
    data_file = project_root / "detectors" / "syllabus_data.json"
    if not data_file.exists():
        print(f"ERROR: syllabus_data.json not found at {data_file}")
        return

    with open(data_file) as f:
        syllabus_data = json.load(f)

    # Find syllabi folder
    syllabi_folder = project_root / "Syllabi"
    if not syllabi_folder.exists():
        print("ERROR: Syllabi folder not found")
        return

    # Initialize detectors
    credit_detector = CreditHoursDetector()
    workload_detector = WorkloadDetector()

    # Store all results
    all_results = []

    print("\n" + "="*150)
    print("CREDIT HOURS & WORKLOAD DETECTION - COMPREHENSIVE TEST")
    print("="*150)

    # Process each file from syllabus data
    for entry in syllabus_data:
        filename = entry.get("filename")
        if not filename:
            continue

        filepath = syllabi_folder / filename

        if not filepath.exists():
            print(f"WARNING: {filename}: File not found")
            continue

        # Extract text
        try:
            if filepath.suffix.lower() == '.pdf':
                text = extract_text_from_pdf(str(filepath))
            else:
                text = extract_text_from_docx(str(filepath))
        except Exception as e:
            print(f"WARNING: {filename}: Extract failed - {e}")
            continue

        # Detect credit hours
        credit_result = credit_detector.detect(text)

        # Get expected credit hours from data
        expected_credit = entry.get("credit_hour")

        # Get detected credit hours
        detected_credit = credit_result.get('content') if credit_result.get('found') else None

        # Check credit hours correctness
        credit_correct = check_match(detected_credit, expected_credit)

        # Detect workload
        workload_result = workload_detector.detect(text)

        # Get expected workload from data
        expected_workload = entry.get("workload")

        # Get detected workload
        detected_workload = workload_result.get('content') if workload_result.get('found') else None

        # Check workload correctness
        workload_correct = check_workload_match(detected_workload, expected_workload)

        all_results.append({
            'file': filename,
            'expected_credit': expected_credit,
            'detected_credit': detected_credit,
            'credit_correct': credit_correct,
            'expected_workload': expected_workload,
            'detected_workload': detected_workload,
            'workload_correct': workload_correct
        })

    # Print results in clean table format
    print("\n[CREDIT HOURS] DETAILED RESULTS:")
    print("-"*150)

    for r in all_results:
        symbol = "[OK]" if r['credit_correct'] else "[FAIL]"
        exp_str = str(r['expected_credit']) if r['expected_credit'] else "null"
        det_str = str(r['detected_credit']) if r['detected_credit'] else "null"

        print(f"{symbol} {r['file']:<55} | Expected: {exp_str:<20} | Detected: {det_str:<20}")

    print("\n[WORKLOAD] DETAILED RESULTS:")
    print("-"*150)

    for r in all_results:
        symbol = "[OK]" if r['workload_correct'] else "[FAIL]"
        exp_str = str(r['expected_workload'])[:50] if r['expected_workload'] else "null"
        det_str = str(r['detected_workload'])[:50] if r['detected_workload'] else "null"

        print(f"{symbol} {r['file']:<55}")
        print(f"    Expected: {exp_str}")
        print(f"    Detected: {det_str}")

    # Calculate accuracy
    credit_correct_count = sum(1 for r in all_results if r['credit_correct'])
    workload_correct_count = sum(1 for r in all_results if r['workload_correct'])
    total_count = len(all_results)
    credit_accuracy = (credit_correct_count / total_count * 100) if total_count > 0 else 0
    workload_accuracy = (workload_correct_count / total_count * 100) if total_count > 0 else 0

    # Print summary
    print("\n" + "="*150)
    print("ACCURACY SUMMARY")
    print("-"*150)
    print(f"  [CREDIT HOURS] Detection: {credit_correct_count}/{total_count} correct ({credit_accuracy:.1f}%)")
    print(f"  [WORKLOAD]     Detection: {workload_correct_count}/{total_count} correct ({workload_accuracy:.1f}%)")
    print("="*150)

    # Print failed detections for debugging
    print("\n[FAILED DETECTIONS] (for debugging):")
    print("-"*150)

    has_failures = False
    for r in all_results:
        if not r['credit_correct'] or not r['workload_correct']:
            has_failures = True
            print(f"\n  {r['file']}:")
            if not r['credit_correct']:
                print(f"    [CREDIT HOURS] Expected: {r['expected_credit']}")
                print(f"    [CREDIT HOURS] Detected: {r['detected_credit']}")
            if not r['workload_correct']:
                print(f"    [WORKLOAD] Expected: {r['expected_workload']}")
                print(f"    [WORKLOAD] Detected: {r['detected_workload']}")

    if not has_failures:
        print("  None - All detections successful!")

    print("\n" + "="*150)


if __name__ == "__main__":
    main()

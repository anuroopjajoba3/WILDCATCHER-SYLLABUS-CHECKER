"""
Office Information Detection Test - Comprehensive
==================================================
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

from detectors.office_information.office_information_detection import OfficeInformationDetector

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


def truncate(text: Optional[str], length: int) -> str:
    """Truncate text to specified length with ellipsis."""
    if text is None or text == "Not listed in syllabus" or text == "Not listed" or text == "not listed":
        return "null"
    if text.strip() == "":
        return "null"
    if len(text) <= length:
        return text
    return text[:length-2] + ".."


def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison."""
    if not text or text == "null":
        return None
    
    # Remove common variations
    normalized = text.lower().strip()
    normalized = normalized.replace("not listed in syllabus", "")
    normalized = normalized.replace("not listed", "")
    normalized = normalized.replace("not specified", "")
    normalized = normalized.replace("no office address listed", "")
    normalized = normalized.replace("no fixed office", "")
    
    # Check if effectively empty
    if not normalized or normalized in ["", "null", "none"]:
        return None
    
    return text


def main():
    # Load comprehensive syllabus data
    expected_file = Path(__file__).parent / "syllabus_data.json"
    if not expected_file.exists():
        print(f"ERROR: syllabus_data.json not found at {expected_file}")
        return
        
    with open(expected_file) as f:
        syllabus_data = json.load(f)
    
    # Find syllabi folder
    syllabi_folder = project_root / "Syllabi"
    if not syllabi_folder.exists():
        print("ERROR: Syllabi folder not found")
        return
    
    # Initialize detector
    detector = OfficeInformationDetector()
    
    # Store all results
    all_results = []
    
    print("\n" + "="*150)
    print("OFFICE INFORMATION DETECTION - COMPREHENSIVE TEST")
    print("="*150)
    
    # Process each file from syllabus data
    for entry in syllabus_data:
        filename = entry.get("filename")
        if not filename:
            continue
            
        # Ensure .pdf extension
        if not filename.endswith(('.pdf', '.docx')):
            filename += '.pdf'
        
        filepath = syllabi_folder / filename
        
        # Try alternate names if file not found
        if not filepath.exists():
            # Try without spaces
            alt_filename = filename.replace(" ", "_")
            filepath = syllabi_folder / alt_filename
            
            if not filepath.exists():
                # Try simplified name
                simplified = filename.replace("_Syllabus_FALL_2025", "").replace("_Syllabus", "")
                filepath = syllabi_folder / simplified
                
                if not filepath.exists():
                    print(f"WARNING: {filename}: File not found (tried multiple variations)")
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
        
        # Detect all office information
        result = detector.detect(text)
        
        # Get expected values from comprehensive data
        exp_loc = normalize_for_comparison(entry.get("office_address"))
        exp_hours = normalize_for_comparison(entry.get("office_hours"))
        exp_phone = normalize_for_comparison(entry.get("office_phone"))
        
        # Get detected values
        if 'office_location' in result:
            det_loc = result['office_location'].get('content') if result['office_location']['found'] else None
        else:
            det_loc = result.get('content') if result.get('found') else None
        
        if 'office_hours' in result:
            det_hours = result['office_hours'].get('content') if result['office_hours']['found'] else None
        else:
            det_hours = None
        
        if 'phone' in result:
            det_phone = result['phone'].get('content') if result['phone']['found'] else None
        else:
            det_phone = None
        
        # Check correctness
        loc_correct = check_match(det_loc, exp_loc)
        hours_correct = check_match(det_hours, exp_hours) if 'office_hours' in result else None
        phone_correct = check_match(det_phone, exp_phone) if 'phone' in result else None
        
        all_results.append({
            'file': filename,
            'exp_loc': exp_loc,
            'det_loc': det_loc,
            'loc_correct': loc_correct,
            'exp_hours': exp_hours,
            'det_hours': det_hours,
            'hours_correct': hours_correct,
            'exp_phone': exp_phone,
            'det_phone': det_phone,
            'phone_correct': phone_correct,
            'instructor': entry.get("instructor_name", "Unknown")
        })
    
    # Print results in clean table format
    print("\nDETAILED RESULTS:")
    print("-"*150)
    
    for r in all_results:
        # Print filename and instructor
        print(f"\nFILE: {r['file'][:60]:<60} | Instructor: {r['instructor']}")
        print(" "*4 + "-"*140)

        # Location row
        loc_symbol = "[OK]" if r['loc_correct'] else "[FAIL]" if r['loc_correct'] is not None else "[?]"
        exp_loc_str = truncate(r['exp_loc'], 30) if r['exp_loc'] else "null"
        det_loc_str = truncate(r['det_loc'], 30) if r['det_loc'] else "null"
        print(f"    {loc_symbol} Location  | Expected: {exp_loc_str:<30} | Detected: {det_loc_str:<30}")

        # Hours row
        if r['hours_correct'] is not None:
            hours_symbol = "[OK]" if r['hours_correct'] else "[FAIL]"
            exp_hours_str = truncate(r['exp_hours'], 30) if r['exp_hours'] else "null"
            det_hours_str = truncate(r['det_hours'], 30) if r['det_hours'] else "null"
            print(f"    {hours_symbol} Hours     | Expected: {exp_hours_str:<30} | Detected: {det_hours_str:<30}")

        # Phone row
        if r['phone_correct'] is not None:
            phone_symbol = "[OK]" if r['phone_correct'] else "[FAIL]"
            exp_phone_str = truncate(r['exp_phone'], 30) if r['exp_phone'] else "null"
            det_phone_str = truncate(r['det_phone'], 30) if r['det_phone'] else "null"
            print(f"    {phone_symbol} Phone     | Expected: {exp_phone_str:<30} | Detected: {det_phone_str:<30}")
    
    # Calculate accuracies
    loc_results = [r['loc_correct'] for r in all_results if r['loc_correct'] is not None]
    hours_results = [r['hours_correct'] for r in all_results if r['hours_correct'] is not None]
    phone_results = [r['phone_correct'] for r in all_results if r['phone_correct'] is not None]
    
    # Print summary
    print("\n" + "="*150)
    print("ACCURACY SUMMARY")
    print("-"*150)
    
    if loc_results:
        loc_acc = sum(loc_results) / len(loc_results) * 100
        print(f"  [LOCATION] Detection: {sum(loc_results)}/{len(loc_results)} correct ({loc_acc:.1f}%)")

    if hours_results:
        hours_acc = sum(hours_results) / len(hours_results) * 100
        print(f"  [HOURS]    Detection: {sum(hours_results)}/{len(hours_results)} correct ({hours_acc:.1f}%)")

    if phone_results:
        phone_acc = sum(phone_results) / len(phone_results) * 100
        print(f"  [PHONE]    Detection: {sum(phone_results)}/{len(phone_results)} correct ({phone_acc:.1f}%)")

    if loc_results and hours_results and phone_results:
        total_correct = sum(loc_results) + sum(hours_results) + sum(phone_results)
        total_tests = len(loc_results) + len(hours_results) + len(phone_results)
        overall_acc = total_correct / total_tests * 100
        print("-"*150)
        print(f"  [OVERALL] ACCURACY:    {total_correct}/{total_tests} correct ({overall_acc:.1f}%)")
    
    print("="*150)
    
    # Print failed detections for debugging
    print("\n[FAILED DETECTIONS] (for debugging):")
    print("-"*150)

    has_failures = False
    for r in all_results:
        failures = []
        if r['loc_correct'] == False and r['exp_loc'] is not None:
            failures.append(f"Location (expected: {r['exp_loc']}, got: {r['det_loc']})")
        if r['hours_correct'] == False and r['exp_hours'] is not None:
            failures.append(f"Hours (expected: {truncate(r['exp_hours'], 25)}, got: {truncate(r['det_hours'], 25)})")
        if r['phone_correct'] == False and r['exp_phone'] is not None:
            failures.append(f"Phone (expected: {r['exp_phone']}, got: {r['det_phone']})")

        if failures:
            has_failures = True
            print(f"\n  {r['file'][:50]} ({r['instructor']}):")
            for failure in failures:
                print(f"    - {failure}")

    if not has_failures:
        print("  None - All detections successful!")
    
    print("\n" + "="*150)


def check_match(detected, expected):
    """Check if detected value matches expected."""
    # Both None = correct
    if expected is None:
        return detected is None
    
    # Expected something but got nothing = incorrect
    if detected is None:
        return False
    
    # For room locations - extract room number
    if "room" in str(expected).lower() or "pandora" in str(expected).lower():
        import re
        # Extract room numbers from both
        exp_room = re.search(r'\d+[A-Z]?', str(expected))
        det_room = re.search(r'\d+[A-Z]?', str(detected))
        
        if exp_room and det_room:
            return exp_room.group() == det_room.group()
        elif "pandora" in str(expected).lower() and "pandora" in str(detected).lower():
            return True
    
    # For phone numbers - compare digits only
    if any(c.isdigit() for c in str(expected)):
        import re
        exp_digits = re.sub(r'\D', '', str(expected))
        det_digits = re.sub(r'\D', '', str(detected))
        
        # Handle partial matches (e.g., "641-4151" vs "603-641-4151")
        if len(exp_digits) == 7 and len(det_digits) == 10:
            return exp_digits == det_digits[-7:]
        return exp_digits == det_digits
    
    # For office hours - flexible matching
    expected_lower = str(expected).lower()
    detected_lower = str(detected).lower()
    
    # Check for key components
    if "appointment" in expected_lower:
        return "appointment" in detected_lower
    
    if "zoom" in expected_lower:
        return "zoom" in detected_lower or "virtual" in detected_lower
    
    if "tbd" in expected_lower or "to be decided" in expected_lower:
        return "tbd" in detected_lower
    
    # Check for day/time patterns
    import re
    # Extract days from both
    days_pattern = r'[MTWRF][a-z]*|monday|tuesday|wednesday|thursday|friday'
    exp_days = re.findall(days_pattern, expected_lower)
    det_days = re.findall(days_pattern, detected_lower)
    
    if exp_days and det_days:
        # Check if at least some days match
        return any(day in detected_lower for day in exp_days)
    
    # Default: substring match
    return expected_lower in detected_lower or detected_lower in expected_lower


if __name__ == "__main__":
    main()
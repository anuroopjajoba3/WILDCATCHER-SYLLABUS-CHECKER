"""
Office Location Detection Performance Test
===========================================
Lean test script to measure detection accuracy against expected results.
"""

import json
import sys
from pathlib import Path

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


def main():
    # Load expected results
    expected_file = Path(__file__).parent / "expected_results.json"
    with open(expected_file) as f:
        expected = json.load(f)
    
    # Find syllabi folder
    syllabi_folder = project_root / "Syllabi"
    if not syllabi_folder.exists():
        print("ERROR: Syllabi folder not found")
        return
    
    # Initialize detector
    detector = OfficeInformationDetector()
    
    # Test each file
    results = []
    print("\nTesting Office Location Detection")
    print("=" * 50)
    
    for filename, expected_data in expected.items():
        filepath = syllabi_folder / filename
        
        if not filepath.exists():
            print(f"⚠ {filename}: File not found")
            continue
        
        # Extract text
        try:
            if filepath.suffix == '.pdf':
                text = extract_text_from_pdf(str(filepath))
            else:
                text = extract_text_from_docx(str(filepath))
        except Exception as e:
            print(f"⚠ {filename}: Extract failed - {e}")
            continue
        
        # Detect office location
        result = detector.detect(text)
        expected_loc = expected_data.get("office_location")
        
        # Check if detection matches expected
        detected = result['content'] if result['found'] else None
        
        if expected_loc is None:
            # Should NOT find
            correct = not result['found']
            symbol = "✓" if correct else "✗"
        else:
            # Should find and match
            correct = result['found'] and expected_loc.lower() in detected.lower()
            symbol = "✓" if correct else "✗"
        
        results.append(correct)
        status = f"Found: {detected}" if detected else "Not found"
        print(f"{symbol} {filename[:35]:<35} | {status}")
        
        if not correct and expected_loc:
            print(f"  → Expected: {expected_loc}")
    
    # Summary
    accuracy = sum(results) / len(results) * 100 if results else 0
    print("=" * 50)
    print(f"Accuracy: {sum(results)}/{len(results)} ({accuracy:.0f}%)")


if __name__ == "__main__":
    main()
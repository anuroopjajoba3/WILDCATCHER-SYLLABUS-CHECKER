# Office Information Detector

Extracts office location information from syllabus documents.

## Structure

```
office_information/
├── README.md                          # This file
├── office_information_detection.py   # Main detector
└── tests/
    └── test_office_detection.py      # Test all syllabi at once
```

## Usage

### Extract Office Locations from All Syllabi

1. Add your PDF/DOCX files to the `Syllabi/` folder (at project root)
2. Run:
```bash
python detectors/office_information/tests/test_office_detection.py
```

The script will:
- Read all PDF/DOCX files in the Syllabi folder
- Extract office locations from each one
- Print results for each file
- Show a summary

## Example Output

```
================================================================================
OFFICE LOCATION EXTRACTOR
================================================================================

Found 3 syllabus files

File: CS101_Syllabus.pdf
   FOUND: Kingsbury Hall Room 234

File: MATH201_Syllabus.pdf
   FOUND: Pandora 204

File: ENG401_Syllabus.pdf
   NOT FOUND

================================================================================
SUMMARY
================================================================================
Total files: 3
Found: 2
Not found: 1
```

## What It Detects

Office location patterns like:
- `Office: Kingsbury Hall Room 234`
- `Office Location: Pandora 204`
- `OFFICE: Building A Rm. 301`

**Regex Pattern:**
```regex
(?:Office|OFFICE|office)(?:\s*Location)?:?\s*([^,\n]+(?:Room|Rm\.?|Building|Pandora)\s*\d+[^\n]*)
```

---

**SCRUM-42: Office Information Extraction**

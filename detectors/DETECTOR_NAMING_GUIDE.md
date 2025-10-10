# Detector Naming Convention Guide

This guide explains how to create new detectors so they work automatically with `test_runner.py` without needing to modify the test runner code.

## File Naming Convention

**Pattern:** `{field_name}_detection.py`

Examples:
- `preferred_contact_method_detection.py`
- `response_time_detection.py`
- `class_location_detection.py`
- `assignment_delivery_detection.py`
- `final_grade_scale_detection.py`

## Class Naming Convention

**Pattern:** `{FieldName}Detector` (PascalCase)

Examples:
- `PreferredContactMethodDetector`
- `ResponseTimeDetector`
- `ClassLocationDetector`
- `AssignmentDeliveryDetector`
- `FinalGradeScaleDetector`

## Required Method

Each detector class must have a `detect(text)` method that:
- Takes a string parameter `text` (the extracted syllabus text)
- Returns a dictionary with at least these keys:
  - `"found"`: Boolean indicating if the field was detected
  - `"content"`: String with the extracted value (or empty string if not found)

## Example Detector Template

```python
class YourFieldDetector:
    """
    Detector for extracting [field description] from syllabus text.
    """

    def detect(self, text: str) -> dict:
        """
        Detect and extract [field name] from the syllabus text.

        Args:
            text: The full text extracted from the syllabus PDF/DOCX

        Returns:
            dict: {
                "found": bool,
                "content": str
            }
        """
        # Your detection logic here

        # Example: Simple keyword search
        if "keyword" in text.lower():
            return {
                "found": True,
                "content": "extracted value"
            }

        # If not found
        return {
            "found": False,
            "content": ""
        }
```

## Adding Your Detector to test_runner.py

Once you create your detector following the naming conventions above, add it to `test_runner.py`:

### Step 1: Add Import (around line 100-133)
```python
try:
    from detectors.your_field_detection import YourFieldDetector
    YOUR_FIELD_AVAILABLE = True
except Exception:
    YOUR_FIELD_AVAILABLE = False
    print("⚠️ Your field detector not available")
```

### Step 2: Add to detect_all_fields() function (around line 271-305)
```python
# Your Field
if YOUR_FIELD_AVAILABLE:
    y = YourFieldDetector().detect(text)
    preds["your_field"] = y.get("content", "") if y.get("found") else ""
else:
    preds["your_field"] = ""
```

### Step 3: Add comparison in main loop (around line 462-495)
```python
# Your Field
if "your_field" in record:
    match = loose_compare(record["your_field"], preds.get("your_field", ""))
    field_stats["your_field"]["total"] += 1
    field_stats["your_field"]["correct"] += int(match)
    result["your_field"] = {"gt": record["your_field"], "pred": preds.get("your_field", ""), "match": match}
```

### Step 4: Add to field list in summary (line 502 and 522)
Add `"your_field"` to the tuple of fields in both locations.

## Current Detectors with Special Return Formats

Some detectors have different return structures:

1. **InstructorDetector** - Returns:
   ```python
   {
       "name": str,
       "title": str,
       "department": str
   }
   ```

2. **OfficeInformationDetector** - Returns:
   ```python
   {
       "office_location": {"found": bool, "content": str},
       "office_hours": {"found": bool, "content": str},
       "phone": {"found": bool, "content": str}
   }
   ```

3. **SLODetector** - Returns:
   ```python
   {
       "found": bool,
       "content": str or list
   }
   ```

## Special Ground Truth Field Types

Some fields in ground_truth.json use different comparison logic:

1. **Boolean Presence Fields** (e.g., `final_grade_scale`)
   - GT value: `true` (boolean) or `""` (empty string)
   - `true` means the field exists in the syllabus
   - `""` means the field doesn't exist
   - Comparison: Uses `compare_boolean_presence()`
     - If GT is `true` → detector should return non-empty content
     - If GT is `""` → detector should return empty content
   - The detector still returns `{"found": bool, "content": str}` format

## Testing Your Detector

Once your detector is in the `detectors/` folder:

```bash
python test_runner.py
```

The test runner will:
1. Automatically import your detector
2. Run it on all syllabi in `ground_truth_syllabus/`
3. Compare results with `ground_truth.json`
4. Display accuracy statistics
5. Save detailed results to `test_results.json`

## Fields Currently Tested

- modality
- SLOs
- email
- credit_hour
- workload
- instructor_name
- instructor_title
- instructor_department
- office_address
- office_hours
- office_phone
- assignment_types_title
- grading_procedures_title
- deadline_expectations_title
- preferred_contact_method
- response_time
- class_location
- assignment_delivery
- final_grade_scale

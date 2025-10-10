#!/usr/bin/env python3
"""
Automated testing for syllabus field detection
Uses detectors + ground_truth.json
- Lenient matching:
  * If GT is "Not found"/empty and prediction is empty => match True
  * Fuzzy text match for near-equal strings
  * Modality normalization (online / hybrid / in-person)
Prints results to terminal and saves to test_results.json
Now also captures SLO text and writes it to JSON only (no terminal SLO prints), including both GT and predicted SLOs in the per-file details.
Includes support for assignment_types_title, grading_procedures_title, and deadline_expectations_title fields.
"""
import os
import sys
import json
import argparse
from collections import defaultdict
from difflib import SequenceMatcher

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (REPO_ROOT, PARENT):
    if p not in sys.path:
        sys.path.append(p)

from document_processing import extract_text_from_pdf, extract_text_from_docx

# ------------------ Detector Imports ------------------
try:
    from detectors.online_detection import detect_modality
    MODALITY_AVAILABLE = True
except Exception:
    MODALITY_AVAILABLE = False
    print("⚠️ Modality detector not available")

try:
    from detectors.slo_detector import SLODetector
    SLO_AVAILABLE = True
except Exception:
    SLO_AVAILABLE = False
    print("⚠️ SLO detector not available")

try:
    from detectors.email_detector import emailDetector
    EMAIL_AVAILABLE = True
except Exception:
    EMAIL_AVAILABLE = False
    print("⚠️ Email detector not available")

try:
    from detectors.credit_hours_detection import CreditHoursDetector
    CREDIT_HOURS_AVAILABLE = True
except Exception:
    CREDIT_HOURS_AVAILABLE = False
    print("⚠️ Credit hours detector not available")

try:
    from detectors.workload_detection import WorkloadDetector
    WORKLOAD_AVAILABLE = True
except Exception:
    WORKLOAD_AVAILABLE = False
    print("⚠️ Workload detector not available")

try:
    from detectors.instructor_detector import InstructorDetector
    INSTRUCTOR_AVAILABLE = True
except Exception:
    INSTRUCTOR_AVAILABLE = False
    print("⚠️ Instructor detector not available")

try:
    from detectors.office_information_detection import OfficeInformationDetector
    OFFICE_INFO_AVAILABLE = True
except Exception:
    OFFICE_INFO_AVAILABLE = False
    print("⚠️ Office information detector not available")

try:
    from detectors.assignment_types_detection import AssignmentTypesDetector
    ASSIGNMENT_TYPES_AVAILABLE = True
except Exception:
    ASSIGNMENT_TYPES_AVAILABLE = False
    print("⚠️ Assignment types detector not available")

try:
    from detectors.grading_procedures_detection import GradingProceduresDetector
    GRADING_PROCEDURES_AVAILABLE = True
except Exception:
    GRADING_PROCEDURES_AVAILABLE = False
    print("⚠️ Grading procedures detector not available")

try:
    from detectors.deadline_expectations_detection import DeadlineExpectationsDetector
    DEADLINE_EXPECTATIONS_AVAILABLE = True
except Exception:
    DEADLINE_EXPECTATIONS_AVAILABLE = False
    print("⚠️ Deadline expectations detector not available")

try:
    from detectors.assignment_delivery_detection import AssignmentDeliveryDetector
    ASSIGNMENT_DELIVERY_AVAILABLE = True
except Exception:
    ASSIGNMENT_DELIVERY_AVAILABLE = False
    print("⚠️ Assignment delivery detector not available")

try:
    from detectors.final_grade_scale_detection import FinalGradeScaleDetector
    FINAL_GRADE_SCALE_AVAILABLE = True
except Exception:
    FINAL_GRADE_SCALE_AVAILABLE = False
    print("⚠️ Final grade scale detector not available")

# ======================================================================
# COMPARISON HELPERS
# ======================================================================

def norm(s):
    if s is None:
        return ""
    return " ".join(str(s).strip().lower().split())

def fuzzy_match(a, b, threshold=0.80):
    a, b = norm(a), norm(b)
    if not a and not b:
        return True
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold

def loose_compare(gt, pred):
    """GT 'not found'/empty vs pred empty => True; otherwise fuzzy."""
    g = norm(gt)
    p = norm(pred)
    if g in ("", "not found") and p == "":
        return True
    return fuzzy_match(g, p)

def compare_modality(gt, pred):
    """Normalize to buckets before compare."""
    def core(s):
        s = norm(s)
        if "hybrid" in s or "blended" in s or "hy-flex" in s or "hyflex" in s:
            return "hybrid"
        if any(x in s for x in ("online", "remote", "asynchronous", "synchronous online")):
            return "online"
        if "in-person" in s or "in person" in s or "on campus" in s:
            return "in-person"
        return s
    return core(gt) == core(pred)

def compare_boolean_presence(gt, pred):
    """
    Compare boolean presence field (GT: true or "") with detector output (string).
    GT true means field should be found (pred non-empty).
    GT "" means field should not be found (pred empty).
    """
    p = norm(pred)
    if gt is True or gt == True:
        # GT says field exists -> pred should be non-empty
        return bool(p)
    elif gt == "" or gt is None:
        # GT says field doesn't exist -> pred should be empty
        return not bool(p)
    else:
        # Fallback for unexpected GT values
        return False

# ======================================================================
# DETECTOR WRAPPERS
# ======================================================================

def detect_all_fields(text: str) -> dict:
    preds = {}

    # Modality
    if MODALITY_AVAILABLE:
        label, _ = detect_modality(text)
        preds["modality"] = label
    else:
        preds["modality"] = "Unknown"

    # SLOs (capture flag + text)
    if SLO_AVAILABLE:
        slo = SLODetector().detect(text)
        preds["has_slos"] = bool(slo.get("found"))
        content = slo.get("content")
        if isinstance(content, list):
            preds["slos_text"] = "\n".join(map(str, content))
        else:
            preds["slos_text"] = content or ""
    else:
        preds["has_slos"] = False
        preds["slos_text"] = ""

    # Email
    if EMAIL_AVAILABLE:
        e = emailDetector().detect(text)
        content = e.get("content")
        if isinstance(content, list) and content:
            preds["email"] = content[0]
        else:
            preds["email"] = content or ""
    else:
        preds["email"] = ""

    # Credit Hours
    if CREDIT_HOURS_AVAILABLE:
        c = CreditHoursDetector().detect(text)
        preds["credit_hour"] = c.get("content", "") if c.get("found") else ""
    else:
        preds["credit_hour"] = ""

    # Workload
    if WORKLOAD_AVAILABLE:
        w = WorkloadDetector().detect(text)
        preds["workload"] = w.get("content", "") if w.get("found") else ""
    else:
        preds["workload"] = ""

    # Instructor
    if INSTRUCTOR_AVAILABLE:
        i = InstructorDetector().detect(text)
        print(f"[INSTRUCTOR DETECTOR OUTPUT] {i}")
        preds["instructor_name"] = i.get("name", "")
        preds["instructor_title"] = i.get("title", "")
        preds["instructor_department"] = i.get("department", "")
    else:
        preds["instructor_name"] = ""
        preds["instructor_title"] = ""
        preds["instructor_department"] = ""

    # Office Information
    if OFFICE_INFO_AVAILABLE:
        o = OfficeInformationDetector().detect(text)
        preds["office_address"] = o.get("office_location", {}).get("content", "") if o.get("office_location", {}).get("found") else ""
        preds["office_hours"] = o.get("office_hours", {}).get("content", "") if o.get("office_hours", {}).get("found") else ""
        preds["office_phone"] = o.get("phone", {}).get("content", "") if o.get("phone", {}).get("found") else ""
    else:
        preds["office_address"] = ""
        preds["office_hours"] = ""
        preds["office_phone"] = ""

    # Assignment Types
    if ASSIGNMENT_TYPES_AVAILABLE:
        a = AssignmentTypesDetector().detect(text)
        preds["assignment_types_title"] = a.get("content", "") if a.get("found") else ""
    else:
        preds["assignment_types_title"] = ""

    # Grading Procedures
    if GRADING_PROCEDURES_AVAILABLE:
        g = GradingProceduresDetector().detect(text)
        preds["grading_procedures_title"] = g.get("content", "") if g.get("found") else ""
    else:
        preds["grading_procedures_title"] = ""

    # Deadline Expectations
    if DEADLINE_EXPECTATIONS_AVAILABLE:
        d = DeadlineExpectationsDetector().detect(text)
        preds["deadline_expectations_title"] = d.get("content", "") if d.get("found") else ""
    else:
        preds["deadline_expectations_title"] = ""

    # Assignment Delivery
    if ASSIGNMENT_DELIVERY_AVAILABLE:
        a = AssignmentDeliveryDetector().detect(text)
        preds["assignment_delivery"] = a.get("content", "") if a.get("found") else ""
    else:
        preds["assignment_delivery"] = ""

    # Final Grade Scale
    if FINAL_GRADE_SCALE_AVAILABLE:
        f = FinalGradeScaleDetector().detect(text)
        preds["final_grade_scale"] = f.get("content", "") if f.get("found") else ""
    else:
        preds["final_grade_scale"] = ""

    return preds

# ======================================================================
# MAIN
# ======================================================================

def main():
    ap = argparse.ArgumentParser(description="Run detectors vs ground_truth.json")
    ap.add_argument("--syllabi", default="ground_truth_syllabus", help="Folder with PDFs/DOCX")
    ap.add_argument("--ground_truth", default="ground_truth.json", help="Ground truth JSON")
    ap.add_argument("--output", default="test_results.json", help="Output JSON file")
    args = ap.parse_args()

    print(f"\n📂 Folder: {os.path.abspath(args.syllabi)}")
    print(f"📘 Ground truth: {os.path.abspath(args.ground_truth)}")

    if not os.path.exists(args.syllabi) or not os.path.exists(args.ground_truth):
        print("❌ Missing folder or JSON.")
        sys.exit(1)

    with open(args.ground_truth, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    print(f"\nFound {len(gt_data)} records in ground truth.")

    field_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    details = []

    for i, record in enumerate(gt_data, 1):
        fname = record.get("filename", "")
        fpath = os.path.join(args.syllabi, fname)
        if not os.path.exists(fpath):
            print(f"[{i}] ❌ Missing file: {fname}")
            continue

        # Extract text
        try:
            if fpath.lower().endswith(".pdf"):
                text = extract_text_from_pdf(fpath) or ""
            else:
                text = extract_text_from_docx(fpath) or ""
        except Exception as e:
            print(f"[{i}] Error reading {fname}: {e}")
            continue

        preds = detect_all_fields(text)
        result = {"filename": fname}

        # Modality
        if "modality" in record:
            match = compare_modality(record["modality"], preds.get("modality", ""))
            field_stats["modality"]["total"] += 1
            field_stats["modality"]["correct"] += int(match)
            result["modality"] = {"gt": record["modality"], "pred": preds.get("modality", ""), "match": match}
        # SLOs: compare presence, store texts (JSON only)
        if "SLOs" in record:
            gt_text = str(record.get("SLOs", "") or "").strip()
            gt_has = bool(norm(gt_text))
            pred_has = bool(preds.get("has_slos"))
            match = (gt_has == pred_has)

            field_stats["SLOs"]["total"] += 1
            field_stats["SLOs"]["correct"] += int(match)

            result["slos"] = {
                "gt_present": gt_has,
                "pred_present": pred_has,
                "match": match,
                "gt_text": gt_text,
                "pred_text": preds.get("slos_text", "")
            }

        # Email
        if "email" in record:
            match = loose_compare(record["email"], preds.get("email", ""))
            field_stats["email"]["total"] += 1
            field_stats["email"]["correct"] += int(match)
            result["email"] = {"gt": record["email"], "pred": preds.get("email", ""), "match": match}

        # Credit hour
        if "credit_hour" in record:
            match = loose_compare(record["credit_hour"], preds.get("credit_hour", ""))
            field_stats["credit_hour"]["total"] += 1
            field_stats["credit_hour"]["correct"] += int(match)
            result["credit_hour"] = {"gt": record["credit_hour"], "pred": preds.get("credit_hour", ""), "match": match}

        # Workload
        if "workload" in record:
            match = loose_compare(record["workload"], preds.get("workload", ""))
            field_stats["workload"]["total"] += 1
            field_stats["workload"]["correct"] += int(match)
            result["workload"] = {"gt": record["workload"], "pred": preds.get("workload", ""), "match": match}

        # Instructor Name
        if "instructor_name" in record:
            match = loose_compare(record["instructor_name"], preds.get("instructor_name", ""))
            field_stats["instructor_name"]["total"] += 1
            field_stats["instructor_name"]["correct"] += int(match)
            result["instructor_name"] = {"gt": record["instructor_name"], "pred": preds.get("instructor_name", ""), "match": match}

        # Instructor Title
        if "instructor_title" in record:
            match = loose_compare(record["instructor_title"], preds.get("instructor_title", ""))
            field_stats["instructor_title"]["total"] += 1
            field_stats["instructor_title"]["correct"] += int(match)
            result["instructor_title"] = {"gt": record["instructor_title"], "pred": preds.get("instructor_title", ""), "match": match}

        # Instructor Department
        if "instructor_department" in record:
            match = loose_compare(record["instructor_department"], preds.get("instructor_department", ""))
            field_stats["instructor_department"]["total"] += 1
            field_stats["instructor_department"]["correct"] += int(match)
            result["instructor_department"] = {"gt": record["instructor_department"], "pred": preds.get("instructor_department", ""), "match": match}

        # Office Address
        if "office_address" in record:
            match = loose_compare(record["office_address"], preds.get("office_address", ""))
            field_stats["office_address"]["total"] += 1
            field_stats["office_address"]["correct"] += int(match)
            result["office_address"] = {"gt": record["office_address"], "pred": preds.get("office_address", ""), "match": match}

        # Office Hours
        if "office_hours" in record:
            match = loose_compare(record["office_hours"], preds.get("office_hours", ""))
            field_stats["office_hours"]["total"] += 1
            field_stats["office_hours"]["correct"] += int(match)
            result["office_hours"] = {"gt": record["office_hours"], "pred": preds.get("office_hours", ""), "match": match}

        # Office Phone
        if "office_phone" in record:
            match = loose_compare(record["office_phone"], preds.get("office_phone", ""))
            field_stats["office_phone"]["total"] += 1
            field_stats["office_phone"]["correct"] += int(match)
            result["office_phone"] = {"gt": record["office_phone"], "pred": preds.get("office_phone", ""), "match": match}

        # Assignment Types Title
        if "assignment_types_title" in record:
            match = loose_compare(record["assignment_types_title"], preds.get("assignment_types_title", ""))
            field_stats["assignment_types_title"]["total"] += 1
            field_stats["assignment_types_title"]["correct"] += int(match)
            result["assignment_types_title"] = {"gt": record["assignment_types_title"], "pred": preds.get("assignment_types_title", ""), "match": match}

        # Grading Procedures Title
        if "grading_procedures_title" in record:
            match = loose_compare(record["grading_procedures_title"], preds.get("grading_procedures_title", ""))
            field_stats["grading_procedures_title"]["total"] += 1
            field_stats["grading_procedures_title"]["correct"] += int(match)
            result["grading_procedures_title"] = {"gt": record["grading_procedures_title"], "pred": preds.get("grading_procedures_title", ""), "match": match}

        # Deadline Expectations Title
        if "deadline_expectations_title" in record:
            match = loose_compare(record["deadline_expectations_title"], preds.get("deadline_expectations_title", ""))
            field_stats["deadline_expectations_title"]["total"] += 1
            field_stats["deadline_expectations_title"]["correct"] += int(match)
            result["deadline_expectations_title"] = {"gt": record["deadline_expectations_title"], "pred": preds.get("deadline_expectations_title", ""), "match": match}

        # Assignment Delivery
        if "assignment_delivery" in record:
            match = loose_compare(record["assignment_delivery"], preds.get("assignment_delivery", ""))
            field_stats["assignment_delivery"]["total"] += 1
            field_stats["assignment_delivery"]["correct"] += int(match)
            result["assignment_delivery"] = {"gt": record["assignment_delivery"], "pred": preds.get("assignment_delivery", ""), "match": match}

        # Final Grade Scale (boolean presence field)
        if "final_grade_scale" in record:
            match = compare_boolean_presence(record["final_grade_scale"], preds.get("final_grade_scale", ""))
            field_stats["final_grade_scale"]["total"] += 1
            field_stats["final_grade_scale"]["correct"] += int(match)
            result["final_grade_scale"] = {"gt": record["final_grade_scale"], "pred": preds.get("final_grade_scale", ""), "match": match}

        details.append(result)

    # Calculate summary statistics
    summary = {}
    total_correct = total_tests = 0
    for field in ("modality", "SLOs", "email", "credit_hour", "workload", "instructor_name", "instructor_title", "instructor_department", "office_address", "office_hours", "office_phone", "assignment_types_title", "grading_procedures_title", "deadline_expectations_title", "assignment_delivery", "final_grade_scale"):
        stats = field_stats[field]
        acc = (stats["correct"] / stats["total"]) if stats["total"] else 0.0
        summary[field] = {
            "accuracy": round(acc, 4),
            "correct": stats["correct"],
            "total": stats["total"]
        }
        total_correct += stats["correct"]
        total_tests += stats["total"]

    overall = (total_correct / total_tests) if total_tests else 0.0

    # Print summary to terminal
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Field':<30} {'Accuracy':<10} {'Correct/Total'}")
    print("-" * 70)

    for field in ("modality", "SLOs", "email", "credit_hour", "workload", "instructor_name", "instructor_title", "instructor_department", "office_address", "office_hours", "office_phone", "assignment_types_title", "grading_procedures_title", "deadline_expectations_title", "assignment_delivery", "final_grade_scale"):
        stats = summary[field]
        print(f"{field:<30} {stats['accuracy']:>6.1%}      {stats['correct']:>3}/{stats['total']:<3}")

    print("-" * 70)
    print(f"{'OVERALL':<30} {overall:>6.1%}      {total_correct}/{total_tests}")
    print("=" * 70)

    # Save results to JSON
    output_data = {
        "summary": summary,
        "overall": {
            "accuracy": round(overall, 4),
            "correct": total_correct,
            "total": total_tests
        },
        "details": details
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to {args.output}")

if __name__ == "__main__":
    main()

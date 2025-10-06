#!/usr/bin/env python3
"""
Automated testing for syllabus field detection
Uses detectors + ground_truth.json (lenient matching)
"""

import os
import sys
import json
import argparse
from collections import defaultdict
from difflib import SequenceMatcher

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from document_processing import extract_text_from_pdf, extract_text_from_docx

# ------------------ Detector Imports ------------------
try:
    from detectors.online_detection import detect_modality
    MODALITY_AVAILABLE = True
except:
    MODALITY_AVAILABLE = False
    print("⚠️ Modality detector not available")

try:
    from detectors.slo_detector import SLODetector
    SLO_AVAILABLE = True
except:
    SLO_AVAILABLE = False
    print("⚠️ SLO detector not available")

try:
    from detectors.email_detection import emailDetector
    EMAIL_AVAILABLE = True
except:
    EMAIL_AVAILABLE = False
    print("⚠️ Email detector not available")

try:
    from detectors.credit_hours_detection import CreditHoursDetector
    CREDIT_HOURS_AVAILABLE = True
except:
    CREDIT_HOURS_AVAILABLE = False
    print("⚠️ Credit hours detector not available")

try:
    from detectors.workload_detection import WorkloadDetector
    WORKLOAD_AVAILABLE = True
except:
    WORKLOAD_AVAILABLE = False
    print("⚠️ Workload detector not available")

# ======================================================================
# COMPARISON HELPERS
# ======================================================================

def normalize_text(s: str) -> str:
    if not s:
        return ""
    return " ".join(str(s).lower().strip().split())

def loose_compare(gt, pred) -> bool:
    """More lenient match: fuzzy + blank handling"""
    g = normalize_text(gt)
    p = normalize_text(pred)

    # Both missing or "not found"
    if (not g or g in ["not found"]) and (not p or p in ["not found"]):
        return True

    # If either missing, mark false (unless both blank)
    if not g or not p:
        return False

    # Exact or substring
    if g == p or g in p or p in g:
        return True

    # Fuzzy ratio >= 0.8 counts as match
    ratio = SequenceMatcher(None, g, p).ratio()
    return ratio >= 0.8


def compare_modality(gt, pred) -> bool:
    """Simplified modality comparison"""
    def core(s):
        s = normalize_text(s)
        if 'hybrid' in s or 'blended' in s:
            return "hybrid"
        if any(x in s for x in ["online", "remote", "asynchronous"]):
            return "online"
        if "in-person" in s or "in person" in s or "on campus" in s:
            return "in-person"
        return s
    return core(gt) == core(pred)


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

    # SLOs
    if SLO_AVAILABLE:
        slo = SLODetector().detect(text)
        preds["has_slos"] = bool(slo.get("found"))
    else:
        preds["has_slos"] = False

    # Email
    if EMAIL_AVAILABLE:
        e = emailDetector().detect(text)
        preds["email"] = (
            e.get("content")[0] if isinstance(e.get("content"), list) and e.get("content") else e.get("content", "")
        )
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

    return preds


# ======================================================================
# MAIN SCRIPT
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Run syllabus field detectors vs. ground truth")
    parser.add_argument("--syllabi", default="Ground_truth_syllabus", help="Folder with syllabi")
    parser.add_argument("--ground_truth", default="ground_truth.json", help="Ground truth JSON")
    args = parser.parse_args()

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
        text = extract_text_from_pdf(fpath) if fpath.endswith(".pdf") else extract_text_from_docx(fpath)
        preds = detect_all_fields(text)
        result = {"filename": fname}

        # === Compare fields ===
        for field in ["modality", "SLOs", "email", "credit_hour", "workload"]:
            gt_val = record.get(field, "")
            pred_val = preds.get(field.lower(), "" if field != "SLOs" else preds.get("has_slos"))
            match = False

            if field == "modality":
                match = compare_modality(gt_val, pred_val)
            elif field == "SLOs":
                match = bool(gt_val) == bool(pred_val)
            else:
                match = loose_compare(gt_val, pred_val)

            field_stats[field]["total"] += 1
            if match:
                field_stats[field]["correct"] += 1

            result[field] = {"gt": gt_val, "pred": pred_val, "match": match}

        details.append(result)

    # === Print Summary ===
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Field':<20} {'Accuracy':<10} {'Correct/Total'}")
    print("-" * 50)

    total_correct = total_tests = 0
    for field, stats in field_stats.items():
        acc = stats["correct"] / stats["total"] if stats["total"] else 0
        print(f"{field:<20} {acc:>6.1%}      {stats['correct']:>3}/{stats['total']}")
        total_correct += stats["correct"]
        total_tests += stats["total"]

    overall = total_correct / total_tests if total_tests else 0
    print("-" * 50)
    print(f"{'OVERALL':<20} {overall:>6.1%}      {total_correct}/{total_tests}")
    print("=" * 70)

if __name__ == "__main__":
    main()

# detectors/online_detection.py
# Rule-based detector for course delivery: Online / Hybrid / In-Person
from __future__ import annotations
import re
import unicodedata
from typing import Dict, List

# ----------------------------
# Normalize & helpers
# ----------------------------

def normalize_syllabus_text(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = (t.replace("•", "- ").replace("▪", "- ").replace("‣", "- ").replace("◦", "- ").replace("\u2022", "- "))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
INSTRUCTOR_LINE_RE = re.compile(r"(?i)\b(Instructor|Professor|Prof\.?)\s*[:\-]\s*(.+)$")
COURSE_LINE_RE = re.compile(r"(?i)^([A-Z]{2,6}\s?\d{3,4}[A-Z]?(?:\s*\([^)]+\))?)\s*[:\-–]\s*(.+)$")

def _truncate(s: str, n: int = 160) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return (s[: n - 1] + "…") if len(s) > n else s

def quick_course_metadata(text: str) -> Dict[str, str]:
    """Best-effort Course / Instructor / Email for the header."""
    t = normalize_syllabus_text(text)
    meta = {"course": "", "instructor": "", "email": ""}

    m = EMAIL_RE.search(t)
    if m:
        meta["email"] = m.group(0)

    for ln in t.splitlines()[:80]:
        m = INSTRUCTOR_LINE_RE.search(ln.strip())
        if m:
            meta["instructor"] = m.group(2).strip()
            break

    for ln in t.splitlines()[:60]:
        m = COURSE_LINE_RE.search(ln.strip())
        if m:
            meta["course"] = f"{m.group(1).strip()} — {m.group(2).strip()}"
            break

    if not meta["course"]:
        # fallback to first non-empty line
        for ln in t.splitlines():
            if ln.strip():
                meta["course"] = ln.strip()
                break

    return meta

# ----------------------------
# Keyword banks
# ----------------------------

ONLINE_STRONG = [
    "online, synchronous", "online synchronous", "synchronous online",
    "online, asynchronous", "online asynchronous", "asynchronous online",
    "delivered online", "fully online", "online course",
    "virtual meeting", "meets on zoom", "meet on zoom", "via zoom", "on zoom",
    "teams meeting", "meets on teams", "webex meeting",
    "remote only", "remote instruction", "distance learning", "live online",
]
ONLINE_SUPPORT = ["canvas course site", "posted to canvas", "available on canvas", "lms", "blackboard", "moodle", "online platform"]

HYBRID_STRONG = [
    "hybrid", "hy-flex", "hyflex", "combination of in-person and online",
    "blend of in-person and online", "meets both online and in person",
]

INPERSON_STRONG = [
    "in person", "in-person", "classroom", "lecture hall", "lab room",
    "on campus only", "meet in room", "meets in room", "meet in", "meets in",
    "building", "hall room", "room",
]

# Override: if syllabus is in-person but occasionally uses Zoom, keep In-Person.
OCCASIONAL_ONLINE = [
    "may meet on zoom", "occasionally online", "some sessions may be online",
    "if needed we will meet on zoom", "in case of weather we will meet on zoom",
    "virtual option may be used occasionally",
]

def _hits(text: str, phrases: List[str]) -> List[str]:
    t = text.lower()
    out: List[str] = []
    for p in phrases:
        if p in t:
            i = t.find(p)
            start = max(0, i - 100)
            end = min(len(text), i + len(p) + 100)
            out.append(_truncate(text[start:end]))
    return out

# ----------------------------
# Core detection
# ----------------------------

def detect_course_delivery(text: str) -> Dict[str, object]:
    """
    Returns:
      {
        "modality": "Online"|"Hybrid"|"In-Person"|"Unknown",
        "confidence": float (0..1),
        "evidence": [str, ...]
      }
    """
    t = normalize_syllabus_text(text)

    ev_online = _hits(t, ONLINE_STRONG)
    ev_hybrid = _hits(t, HYBRID_STRONG)
    ev_inperson = _hits(t, INPERSON_STRONG)
    ev_occ = _hits(t, OCCASIONAL_ONLINE)
    online_support_ct = len(_hits(t, ONLINE_SUPPORT))

    score_online = 1.00 * len(ev_online) + 0.25 * online_support_ct
    score_hybrid = 1.00 * len(ev_hybrid) + 0.50 * bool(ev_online) + 0.50 * bool(ev_inperson)
    score_inperson = 1.00 * len(ev_inperson)

    # pick label
    if score_hybrid >= max(score_online, score_inperson) and score_hybrid > 0:
        label = "Hybrid"
        evidence = (ev_hybrid or [])[:2]
        if ev_online:   evidence.append(ev_online[0])
        if ev_inperson: evidence.append(ev_inperson[0])
    elif score_online > score_inperson and score_online > 0:
        label = "Online"
        evidence = (ev_online or [])[:3]
    elif score_inperson > 0:
        label = "In-Person"
        evidence = (ev_inperson or [])[:3]
    else:
        label = "Unknown"
        evidence = []

    # Override: in-person + only occasional-online ⇒ In-Person
    if label in ("Hybrid", "Online") and ev_inperson and ev_occ:
        label = "In-Person"
        evidence = [ev_inperson[0], ev_occ[0]]

    # confidence (no %)
    scores = [score_online, score_hybrid, score_inperson]
    top = max(scores)
    total = sum(scores) or 1.0
    conf = round(top / total, 2) if top > 0 else 0.0
    if conf < 0.55 and top > 0:  # floor a bit so borderline reads reasonable
        conf = 0.55

    return {"modality": label, "confidence": conf, "evidence": evidence[:4]}

# ----------------------------
# UI formatting
# ----------------------------

def format_modality_card(result: Dict[str, object], meta: Dict[str, str] | None = None) -> Dict[str, object]:
    """
    Build a UI-friendly dict that your front-end prints directly, matching:
        Result: PASS
        Hybrid modality detected
        <Course line>
        Instructor: <name>  (<email if any>)
        Label: Hybrid
        Confidence: 0.8
        - evidence...
        - evidence...
    """
    meta = meta or {"course": "", "instructor": "", "email": ""}
    modality = str(result.get("modality", "Unknown"))
    conf = float(result.get("confidence", 0.0))
    evidence = result.get("evidence", []) or []

    status = "PASS" if modality in ("Online", "Hybrid", "In-Person") else "FAIL"

    msg = f"{modality} modality detected" if modality != "Unknown" else "Detected delivery"
    header_lines: List[str] = []

    if meta.get("course"):
        header_lines.append(meta["course"])
    if meta.get("instructor") or meta.get("email"):
        ins = meta.get("instructor", "")
        eml = meta.get("email", "")
        if ins and eml:
            header_lines.append(f"Instructor: {ins}  ({eml})")
        elif ins:
            header_lines.append(f"Instructor: {ins}")
        else:
            header_lines.append(f"Email: {eml}")

    # Return card fields the UI can show line-by-line
    return {
        "status": status,                 # "PASS" / "FAIL"
        "heading": "Course Delivery",
        "message": msg,                   # e.g., "Hybrid modality detected"
        "label": modality,                # explicit label line
        "confidence": conf,               # decimal (no %)
        "header": header_lines,           # list of 0-2 lines (course/instructor/email)
        "evidence": evidence,             # short bullets
    }


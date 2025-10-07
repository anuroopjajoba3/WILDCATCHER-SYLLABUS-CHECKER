# detectors/online_detection.py
# Rule-based detector for course delivery: Online / Hybrid / In-Person
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Tuple

__all__ = [
    "detect_course_delivery",
    "detect_modality",
    "format_modality_card",
    "quick_course_metadata",
]

# ----------------------------
# Normalize & helpers
# ----------------------------

def normalize_syllabus_text(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    # normalize bullets and whitespace
    t = (
        t.replace("•", "- ")
        .replace("▪", "- ")
        .replace("‣", "- ")
        .replace("◦", "- ")
        .replace("\u2022", "- ")
    )
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ----------------------------
# Enhanced detection patterns
# ----------------------------

# include abbreviations and variants (Rm./Bldg.), keep Pandra/Pandora
BUILDING_WORDS = r"(?:rm\.?|room|hall|bldg\.?|building|lab|laboratory|lecture hall|classroom|pandra|pandora)"

# Day/time tokens to detect class schedules (e.g., TR 9:10–10:00 AM)
DAYS_TOKEN = r"(?:m/w|mw|t/th|tth|tr|mon(?:day)?|tue(?:s)?(?:day)?|wed(?:nesday)?|thu(?:rs)?(?:day)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
TIME_TOKEN = r"(?:\b\d{1,2}:\d{2}\s?(?:am|pm)?\b|\b\d{1,2}\s?(?:am|pm)\b)"

def _find_class_location_section(text: str) -> str:
    """Extract a likely 'class location / meets / meeting info' section (not office hours)."""
    lines = text.split("\n")

    # no ^ anchor; include 'schedule' as a cue
    location_patterns = [
        r"(?i)(?:class|course)\s+(?:location|meets?|meeting|time)",
        r"(?i)(?:meeting\s+)?(?:location|place|where)",
        r"(?i)(?:time\s+and\s+)?location",
        r"(?i)(?:class|course)\s+delivery",
        r"(?i)delivery\s+(?:method|format|mode)",
        r"(?i)modality",
        r"(?i)schedule",
    ]

    for i, line in enumerate(lines[:300]):
        for pat in location_patterns:
            if re.search(pat, line):
                start = max(0, i - 1)
                end = min(i + 6, len(lines))
                return "\n".join(lines[start:end]).lower()
    return ""


def _find_office_hours_section(text: str) -> str:
    """Extract office hours section for disambiguation."""
    lines = text.split("\n")
    for i, line in enumerate(lines[:400]):
        if re.search(r"(?i)\boffice\s+hours?\b", line):
            start = max(0, i - 1)
            end = min(i + 6, len(lines))
            return "\n".join(lines[start:end]).lower()
    return ""


def _has_zoom_class_phrase(s: str) -> bool:
    """Zoom/Teams/Webex in a class meeting context (avoid office hours)."""
    if not s:
        return False
    return bool(
        re.search(r"(?i)\b(meets?|meeting|class|delivered|offered)\b.*\b(zoom|microsoft\s*teams|teams|webex)\b", s)
    )


def _has_physical_room_phrase(s: str) -> bool:
    """Physical location cues in class context."""
    if not s:
        return False
    if re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", s):
        return True
    if re.search(rf"(?i)\b(meets?|meeting)\s+in\b.*\b({BUILDING_WORDS})\b", s):
        return True
    return False


def detect_course_delivery(text: str) -> Dict[str, object]:
    """
    Multi-phase rule detector for course modality with context guards
    to avoid office-hours false positives and catch synchronous/asynchronous phrasing.
    """
    if not text:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": []}

    t = normalize_syllabus_text(text)
    t_lower = t.lower()

    class_section = _find_class_location_section(t)
    office_section = _find_office_hours_section(t)
    evidence = []

    # === PHASE 1: Explicit definitive statements ===
    online_definitive = [
        "100% online",
        "fully online",
        "completely online",
        "entirely online",
        "online only",
        "course is online",
        "this course is online",
        "delivered entirely online",
        "offered online",
        "synchronous online",
        "meets online",
        "meets on zoom",
        "meets via zoom",
        "asynchronous online",
        "fully asynchronous",
        "entirely asynchronous",
        "this course meets synchronously online",
        "course meets synchronously online",
        "no scheduled class times",
        "no scheduled class meeting times",
        "there are no scheduled class times",
        "there are no scheduled meeting times",
    ]
    for phrase in online_definitive:
        if phrase in t_lower:
            return {"modality": "Online", "confidence": 0.95, "evidence": [phrase]}

    # "Time/Location: ... Online" in header
    if re.search(r"(?i)(?:time\s+and\s+)?location[:\s]+.*\bonline\b", t_lower[:800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["location states online"]}

    # Day/time followed by online in header
    if re.search(r"(?i)(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*[,\s]+\d{1,2}:\d{2}.*\bonline\b", t_lower[:800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["class time shows online"]}

    hybrid_definitive = [
        "hybrid course",
        "hy-flex",
        "hyflex",
        "blended course",
        "hybrid format",
        "blended format",
        "face-to-face and online",
        "in-person and online",
    ]
    for phrase in hybrid_definitive:
        if phrase in t_lower:
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": [phrase]}

    if re.search(r"(?i)face[-\s]?to[-\s]?face\s+(?:weekly|sessions?).*(?:async|online)", t_lower):
        return {"modality": "Hybrid", "confidence": 0.92, "evidence": ["face-to-face + async/online components"]}

    # === PHASE 2: Class location section takes precedence over office hours ===
    if class_section:
        if _has_zoom_class_phrase(class_section):
            return {"modality": "Online", "confidence": 0.90, "evidence": ["class meets on Zoom/Teams/Webex"]}
        if _has_physical_room_phrase(class_section):
            return {"modality": "In-Person", "confidence": 0.90, "evidence": ["class meets in physical room"]}

    # Explicit delivery method lines near top
    header_1000 = t_lower[:1000]
    if re.search(r"(?i)(?:delivery|modality|format|mode)\s*[:\-]?\s*(?:online|asynchronous|synchronous online)", header_1000):
        return {"modality": "Online", "confidence": 0.92, "evidence": ["delivery method states online"]}

    # Header "meets in Room/Lab/Pandora …" is strong in-person
    header_500 = t_lower[:600]
    m = re.search(rf"(?i)\b(meets?|meeting)\b.*\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", header_500)
    if m:
        office_in_header = "office" in header_500[max(0, m.start() - 50) : m.end() + 150]
        if not office_in_header:
            return {"modality": "In-Person", "confidence": 0.92, "evidence": ["header shows physical meeting room"]}

    # NEW early in-person catches
    if re.search(r"(?i)\bin[ -]?person\b", header_500) and "office" not in header_500:
        return {"modality": "In-Person", "confidence": 0.90, "evidence": ["header says in person"]}

    non_office = t_lower.replace(office_section, "") if office_section else t_lower

    if re.search(rf"\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", non_office):
        return {"modality": "In-Person", "confidence": 0.90, "evidence": ["physical room outside office hours"]}

    if re.search(DAYS_TOKEN, non_office) and re.search(TIME_TOKEN, non_office) and not re.search(
        r"\b(online|zoom|microsoft\s*teams|webex|remote)\b",
        non_office,
    ):
        return {"modality": "In-Person", "confidence": 0.86, "evidence": ["day/time schedule with no online cues"]}

    # === PHASE 3: Asynchronous (guard against office hours / tutoring) ===
    if "asynchronous" in t_lower:
        i = t_lower.find("asynchronous")
        snippet = t_lower[max(0, i - 220) : i + 220]
        bad_context = [
            "tutoring",
            "writing lab",
            "writing center",
            "owl",
            "support service",
            "recorded lectures",
            "temporary",
            "accommodations",
            "miss class",
        ]
        if not any(b in snippet for b in bad_context):
            if any(w in snippet for w in [
                "online",
                "remote",
                "delivered",
                "format",
                "course is",
                "meets online",
                "delivery",
            ]):
                if not any(w in snippet for w in ["meets in", "classroom", "in person", "on campus"]):
                    return {"modality": "Online", "confidence": 0.88, "evidence": ["asynchronous online delivery"]}

    # === PHASE 4: Scoring (soft signals) ===
    score_online = 0.0
    score_hybrid = 0.0
    score_inperson = 0.0

    online_patterns = [
        (r"(?i)\bcourse\s+(?:is\s+)?(?:delivered|offered|taught)\s+online\b", 3.5),
        (r"(?i)\bonline\s+(?:course|format|delivery|instruction)\b", 3.0),
        (r"(?i)\bsynchronous\s+online\b", 3.2),
        (r"(?i)\basynchronous\s+(?:course|format|delivery)\b", 3.2),
        (r"(?i)\bremote\s+(?:course|instruction|learning)\b", 2.5),
        (r"(?i)\bvirtual\s+course\b", 2.5),
        (r"(?i)\bclass\s+meets?\s+(?:on|via)\s+(?:zoom|microsoft\s*teams|teams|webex)\b", 3.5),
        (r"(?i)\bdelivered\s+(?:entirely\s+)?(?:online|remotely|asynchronously)\b", 3.5),
    ]
    for pat, w in online_patterns:
        if re.search(pat, t_lower):
            score_online += w
            evidence.append("online_pattern_match")

    first_1500 = t_lower[:1500]
    zpos = first_1500.find("zoom")
    if zpos != -1:
        near = first_1500[max(0, zpos - 60) : zpos + 60]
        if "office" not in near:
            score_online += 2.0

    inperson_patterns = [
        (rf"(?i)\b(?:class|course|lecture)\s+(?:meets?|is held|location).*(?:{BUILDING_WORDS})\b", 3.0),
        (rf"(?i)\b(?:location|where)\b.*\b(?:{BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", 2.7),
        (r"(?i)\bin[-\s]?person\s+(?:class|course|instruction)\b", 2.5),
        (r"(?i)\bon\s+campus\s+(?:course|class)\b", 2.0),
        (r"(?i)\bclassroom\s+instruction\b", 2.0),
        (rf"(?i)\b[A-Z][a-zA-Z]+(?:\s+(?:Hall|Building|Lab))?\s+[A-Za-z]?\d{{2,4}}\b", 2.1),
        (r"(?i)\btaking\s+attendance\b", 1.5),
        (r"(?i)\barrive\s+late\s+to\s+class\b", 1.3),
        (r"(?i)\bleave\s+early\s+from\s+class\b", 1.3),
        (r"(?i)\bneed\s+to\s+be\s+here\b", 1.5),
        # NEW soft in-person signals
        (r"(?i)\bin[ -]?person\b", 2.0),
        (r"(?i)\bon[- ]site\b", 1.8),
        (r"(?i)face[- ]to[- ]face\b", 2.0),
        (r"(?i)\b(outdoor|field)\s+(meetings?|sessions?|labs?)\b", 2.0),
    ]
    for pat, w in inperson_patterns:
        if re.search(pat, t_lower):
            score_inperson += w
            evidence.append("inperson_pattern_match")

    if score_online > 1.3 and score_inperson > 1.3:
        score_hybrid = max(score_hybrid, (score_online + score_inperson) * 0.55)

    if office_section and score_inperson > 0:
        room_in_class = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", class_section))
        room_in_office = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", office_section))
        if room_in_office and not room_in_class:
            score_inperson = max(0.0, score_inperson - 4.0)
            evidence.append("reduced_inperson_office_hours_only")
            if score_online > 1.0:
                score_online += 2.0
                evidence.append("boosted_online_no_class_location")

    scores = {"Online": score_online, "Hybrid": score_hybrid, "In-Person": score_inperson}
    max_score = max(scores.values())
    if max_score <= 0:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["no clear modality indicators"]}

    modality = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(max_score / total, 2) if total > 0 else 0.6
    confidence = max(confidence, 0.60)

    return {
        "modality": modality,
        "confidence": confidence,
        "evidence": evidence[:4] if evidence else [f"{modality.lower()} indicators found"],
    }

# ----------------------------
# Helpers expected by the API layer
# ----------------------------

def quick_course_metadata(text: str) -> Dict[str, str]:
    """Return a light-weight course/instructor/email dict for UI headers.
    Best-effort extraction; empty strings if not found.
    """
    t = normalize_syllabus_text(text)
    t_lower = t.lower()

    # Email
    m_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    email = m_email.group(0) if m_email else ""

    # Instructor: take the line after an Instructor/Professor label; else first "By <Name>"; else empty
    m_instr = re.search(r"(?im)^(?:instructor|professor|lecturer)[:\s-]+(.{3,80})$", t)
    instructor = (m_instr.group(1).strip() if m_instr else "")
    if not instructor:
        m_by = re.search(r"(?im)^(?:by)[:\s-]+(.{3,80})$", t)
        instructor = m_by.group(1).strip() if m_by else ""

    # Course line: try Course Title/Name/Code labels; else first code-like token in header
    m_course = re.search(r"(?im)^(?:course|class)\s*(?:title|name|code)?[:\s-]+(.{3,80})$", t)
    course = (m_course.group(1).strip() if m_course else "")
    if not course:
        m_code = re.search(r"\b[A-Z]{2,}\s?\d{3,}[A-Z-]*\b", t[:400])
        course = m_code.group(0) if m_code else ""

    return {"course": course, "instructor": instructor, "email": email}


def format_modality_card(result: Dict[str, object], meta: Dict[str, str] | None = None) -> Dict[str, object]:
    """Shape detect_course_delivery() output into a card for the API/UI layer.
    Keeps keys that the API expects.
    """
    meta = meta or {}
    label = str(result.get("modality", "Unknown"))
    conf = float(result.get("confidence") or 0.0)
    evidence = result.get("evidence") or []

    status = "PASS" if label != "Unknown" else "FAIL"
    message = f"{label} modality detected" if label != "Unknown" else "Detected delivery"

    return {
        "status": status,
        "heading": "Course Delivery",
        "message": message,
        "label": label,
        "confidence": round(conf, 2),  # 0–1 decimal
        "evidence": list(evidence)[:5],
        # meta is not inserted here; API will add course/instructor/email via _massage_modality_card
    }

# ----------------------------
# Back-compat helper for your test runner
# ----------------------------

def detect_modality(text: str) -> Tuple[str, str]:
    """Return (label, evidence_str) for compatibility with test runner."""
    res = detect_course_delivery(text)
    label = res.get("modality", "Unknown")
    ev = res.get("evidence") or []
    return label, " | ".join(ev[:3])


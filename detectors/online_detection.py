# detectors/online_detection.py
# Rule-based detector for course delivery: Online / Hybrid / In-Person
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Tuple, Optional

__all__ = [
    "detect_course_delivery",
    "detect_modality",
    "format_modality_card",
    "quick_course_metadata",
]

# Detection Configuration Constants
MAX_LINES_LOCATION_SEARCH = 300
MAX_LINES_OFFICE_SEARCH = 400
HEADER_SEARCH_LIMIT_800 = 800
HEADER_SEARCH_LIMIT_1000 = 1000
HEADER_SEARCH_LIMIT_500 = 500
HEADER_SEARCH_LIMIT_600 = 600
HEADER_SEARCH_LIMIT_1500 = 1500
HEADER_SEARCH_LIMIT_400 = 400
CONTEXT_WINDOW_BEFORE = 1
CONTEXT_WINDOW_AFTER = 6
CONTEXT_OFFSET_50 = 50
CONTEXT_OFFSET_60 = 60
CONTEXT_OFFSET_150 = 150
CONTEXT_OFFSET_220 = 220
MIN_CONFIDENCE_THRESHOLD = 0.60
HYBRID_SCORE_MULTIPLIER = 0.55
INPERSON_PENALTY = 4.0
ONLINE_BOOST = 2.0
MIN_SCORE_THRESHOLD_ONLINE = 1.3
MIN_SCORE_THRESHOLD_INPERSON = 1.3
MIN_SCORE_THRESHOLD_ONLINE_BOOST = 1.0

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

    for i, line in enumerate(lines[:MAX_LINES_LOCATION_SEARCH]):
        for pat in location_patterns:
            if re.search(pat, line):
                start = max(0, i - CONTEXT_WINDOW_BEFORE)
                end = min(i + CONTEXT_WINDOW_AFTER, len(lines))
                return "\n".join(lines[start:end]).lower()
    return ""


def _find_office_hours_section(text: str) -> str:
    """Extract office hours section for disambiguation."""
    lines = text.split("\n")
    for i, line in enumerate(lines[:MAX_LINES_OFFICE_SEARCH]):
        if re.search(r"(?i)\boffice\s+hours?\b", line):
            start = max(0, i - CONTEXT_WINDOW_BEFORE)
            end = min(i + CONTEXT_WINDOW_AFTER, len(lines))
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
    """Physical location cues in class context. Filter out support services."""
    if not s:
        return False

    # Filter out support service contexts - these are NOT class locations
    support_contexts = [
        "accessibility services", "student accessibility", "counseling services",
        "tutoring", "writing center", "library", "financial aid", "registrar",
        "dean's office", "advisement", "student services"
    ]
    s_lower = s.lower()
    if any(ctx in s_lower for ctx in support_contexts):
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

    # === HYBRID CHECKS FIRST (before online-only checks) ===
    hybrid_definitive = [
        "hybrid course",
        "hy-flex",
        "hyflex",
        "blended course",
        "hybrid format",
        "blended format",
        "hybrid delivery",
        # Removed "in-person and online" and "face-to-face and online" - too often refers to
        # tutoring services, learning activities, or resources rather than course modality
    ]
    for phrase in hybrid_definitive:
        if phrase in t_lower:
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": [phrase]}

    # CRITICAL: Check for hybrid patterns BEFORE "location: online" check
    # Pattern: "online AND also in room X" or "zoom and also in"
    if re.search(r"(?i)\b(online|zoom|teams|webex).*\b(and also in|also in)\b.*\b(room|rm\.?|pandora|pandra|hall|building)\b", t_lower[:HEADER_SEARCH_LIMIT_1000]):
        return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["online and also in physical location"]}

    if re.search(r"(?i)\blocation.*:.*\bonline\b.*\band\b.*\b(room|rm\.?|pandora|pandra)\b", t_lower[:HEADER_SEARCH_LIMIT_1000]):
        return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["location shows both online and room"]}

    # NOW check for online-only patterns
    # "Time/Location: ... Online" in header (but NOT if it also mentions room/building)
    location_online_match = re.search(r"(?i)(?:time\s+and\s+)?location[:\s]+.*\bonline\b", t_lower[:HEADER_SEARCH_LIMIT_800])
    if location_online_match:
        # Check if it also mentions a room/building (would be hybrid)
        location_text = t_lower[location_online_match.start():min(location_online_match.end() + 100, len(t_lower))]
        if not any(word in location_text for word in ["room", "rm", "hall", "building", "pandora", "pandra"]):
            return {"modality": "Online", "confidence": 0.93, "evidence": ["location states online"]}

    # Day/time followed by online in header
    if re.search(r"(?i)(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*[,\s]+\d{1,2}:\d{2}.*\bonline\b", t_lower[:HEADER_SEARCH_LIMIT_800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["class time shows online"]}

    if re.search(r"(?i)face[-\s]?to[-\s]?face\s+(?:weekly|sessions?).*(?:async|online)", t_lower):
        return {"modality": "Hybrid", "confidence": 0.92, "evidence": ["face-to-face + async/online components"]}

    # === PHASE 2: Class location section takes precedence over office hours ===
    # BUT: Check for "hybrid" keyword in header FIRST before assuming in-person
    header_1500 = t_lower[:HEADER_SEARCH_LIMIT_1500]
    if "hybrid" in header_1500:
        # Check if it's actually referring to class modality (not just course content)
        if any(word in header_1500 for word in ["hybrid delivery", "hybrid course", "hybrid format", "hybrid modality", "online with some campus"]):
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["header explicitly states hybrid"]}

    if class_section:
        if _has_zoom_class_phrase(class_section):
            return {"modality": "Online", "confidence": 0.90, "evidence": ["class meets on Zoom/Teams/Webex"]}
        if _has_physical_room_phrase(class_section):
            return {"modality": "In-Person", "confidence": 0.90, "evidence": ["class meets in physical room"]}

    # Explicit delivery method lines near top
    header_1000 = t_lower[:HEADER_SEARCH_LIMIT_1000]
    if re.search(r"(?i)(?:delivery|modality|format|mode)\s*[:\-]?\s*(?:online|asynchronous|synchronous online)", header_1000):
        return {"modality": "Online", "confidence": 0.92, "evidence": ["delivery method states online"]}

    # Header "meets in Room/Lab/Pandora …" is strong in-person
    header_600 = t_lower[:HEADER_SEARCH_LIMIT_600]
    meeting_match = re.search(rf"(?i)\b(meets?|meeting)\b.*\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", header_600)
    if meeting_match:
        office_in_header = "office" in header_600[max(0, meeting_match.start() - CONTEXT_OFFSET_50) : meeting_match.end() + CONTEXT_OFFSET_150]
        # Also check for hybrid before assuming in-person
        if not office_in_header and "hybrid" not in header_1500:
            return {"modality": "In-Person", "confidence": 0.92, "evidence": ["header shows physical meeting room"]}

    # NEW early in-person catches
    # But ONLY if "hybrid" is not mentioned in header
    if re.search(r"(?i)\bin[ -]?person\b", header_600) and "office" not in header_600 and "hybrid" not in header_1500:
        return {"modality": "In-Person", "confidence": 0.90, "evidence": ["header says in person"]}

    non_office = t_lower.replace(office_section, "") if office_section else t_lower

    # Check for hybrid again before returning in-person for physical room
    if re.search(rf"\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", non_office) and "hybrid" not in header_1500:
        return {"modality": "In-Person", "confidence": 0.90, "evidence": ["physical room outside office hours"]}

    if re.search(DAYS_TOKEN, non_office) and re.search(TIME_TOKEN, non_office) and not re.search(
        r"\b(online|zoom|microsoft\s*teams|webex|remote)\b",
        non_office,
    ) and "hybrid" not in header_1500:
        return {"modality": "In-Person", "confidence": 0.86, "evidence": ["day/time schedule with no online cues"]}

    # === PHASE 3: Asynchronous (guard against office hours / tutoring) ===
    if "asynchronous" in t_lower:
        async_position = t_lower.find("asynchronous")
        snippet = t_lower[max(0, async_position - CONTEXT_OFFSET_220) : async_position + CONTEXT_OFFSET_220]
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
        (r"(?i)\bonline\s+(?:course|format|delivery|instruction|modality)\b", 3.0),
        (r"(?i)\bsynchronous\s+online\b", 3.2),
        (r"(?i)\basynchronous\s+(?:course|format|delivery)\b", 3.2),
        (r"(?i)\bremote\s+(?:course|instruction|learning)\b", 2.5),
        (r"(?i)\bvirtual\s+course\b", 2.5),
        (r"(?i)\bclass\s+meets?\s+(?:on|via)\s+(?:zoom|microsoft\s*teams|teams|webex)\b", 3.5),
        (r"(?i)\bdelivered\s+(?:entirely\s+)?(?:online|remotely|asynchronously)\b", 3.5),
    ]

    # Avoid counting "online" in irrelevant contexts (textbook, materials, resources)
    irrelevant_online_contexts = [
        "textbook online", "materials online", "resources online",
        "available online", "posted online", "submit online", "canvas online"
    ]

    for pat, w in online_patterns:
        match = re.search(pat, t_lower)
        if match:
            # Check if this match is in an irrelevant context
            match_start = match.start()
            match_context = t_lower[max(0, match_start - 30):match.end() + 30]
            if not any(ctx in match_context for ctx in irrelevant_online_contexts):
                score_online += w
                evidence.append("online_pattern_match")

    first_1500 = t_lower[:HEADER_SEARCH_LIMIT_1500]
    zoom_position = first_1500.find("zoom")
    if zoom_position != -1:
        near = first_1500[max(0, zoom_position - CONTEXT_OFFSET_60) : zoom_position + CONTEXT_OFFSET_60]
        # Only count zoom if it's about class meetings, not office hours or support services
        if "office" not in near and "counseling" not in near and "support" not in near:
            if any(ctx in near for ctx in ["meet", "class", "course", "location", "delivery"]):
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
        # Soft in-person signals
        (r"(?i)\bin[ -]?person\b", 2.0),
        (r"(?i)\bon[- ]site\b", 1.8),
        (r"(?i)face[- ]to[- ]face\b", 2.0),
        (r"(?i)\b(outdoor|field)\s+(meetings?|sessions?|labs?)\b", 2.0),
    ]

    # Support service contexts to filter out
    support_service_contexts = [
        "accessibility", "counseling", "tutoring", "writing center",
        "library", "financial aid", "registrar", "advisement", "student services",
        "wellness", "health services"
    ]

    # Course code patterns to filter out (these are NOT buildings)
    course_code_patterns = [
        r"\bcomp\s*\d",  # COMP 405, COMP405
        r"\bmath\s*\d",  # MATH 418
        r"\bbms\s*\d",   # BMS 508
        r"\bphys\s*\d",  # PHYS 401
        r"\banth\s*\d",  # ANTH 411
        r"\bpsyc\s*\d",  # PSYC 401
        r"\bbiol\s*\d",  # BIOL 414
        r"\bcmn\s*\d",   # CMN 455
        r"\bnsia\s*\d",  # NSIA 850
        r"\bcredit",     # "4 credits"
        r"\bcrn\s*:",    # CRN: 12143
    ]

    for pat, w in inperson_patterns:
        match = re.search(pat, t_lower)
        if match:
            # Check if this match is in a support service context
            match_start = match.start()
            match_context = t_lower[max(0, match_start - 50):match.end() + 50]

            # Also check if it's a course code pattern
            is_course_code = any(re.search(code_pat, match_context) for code_pat in course_code_patterns)

            if not any(ctx in match_context for ctx in support_service_contexts) and not is_course_code:
                score_inperson += w
                evidence.append("inperson_pattern_match")

    if score_online > MIN_SCORE_THRESHOLD_ONLINE and score_inperson > MIN_SCORE_THRESHOLD_INPERSON:
        score_hybrid = max(score_hybrid, (score_online + score_inperson) * HYBRID_SCORE_MULTIPLIER)

    if office_section and score_inperson > 0:
        room_in_class = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", class_section))
        room_in_office = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", office_section))
        if room_in_office and not room_in_class:
            score_inperson = max(0.0, score_inperson - INPERSON_PENALTY)
            evidence.append("reduced_inperson_office_hours_only")
            if score_online > MIN_SCORE_THRESHOLD_ONLINE_BOOST:
                score_online += ONLINE_BOOST
                evidence.append("boosted_online_no_class_location")

    scores = {"Online": score_online, "Hybrid": score_hybrid, "In-Person": score_inperson}
    max_score = max(scores.values())

    # Return Unknown if no significant evidence found
    # Require at least 2.0 score (lowered from 3.5 to improve recall)
    if max_score < 2.0:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["no clear modality indicators"]}

    modality = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(max_score / total, 2) if total > 0 else MIN_CONFIDENCE_THRESHOLD
    confidence = max(confidence, MIN_CONFIDENCE_THRESHOLD)

    # Also return Unknown if confidence is too low (ambiguous/weak signals)
    # Lowered from 0.70 to 0.60 to improve recall
    if confidence < 0.60:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["weak or ambiguous modality signals"]}

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
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    email = email_match.group(0) if email_match else ""

    # Instructor: take the line after an Instructor/Professor label; else first "By <Name>"; else empty
    instructor_match = re.search(r"(?im)^(?:instructor|professor|lecturer)[:\s-]+(.{3,80})$", t)
    instructor = (instructor_match.group(1).strip() if instructor_match else "")
    if not instructor:
        by_match = re.search(r"(?im)^(?:by)[:\s-]+(.{3,80})$", t)
        instructor = by_match.group(1).strip() if by_match else ""

    # Course line: try Course Title/Name/Code labels; else first code-like token in header
    course_match = re.search(r"(?im)^(?:course|class)\s*(?:title|name|code)?[:\s-]+(.{3,80})$", t)
    course = (course_match.group(1).strip() if course_match else "")
    if not course:
        code_match = re.search(r"\b[A-Z]{2,}\s?\d{3,}[A-Z-]*\b", t[:HEADER_SEARCH_LIMIT_400])
        course = code_match.group(0) if code_match else ""

    return {"course": course, "instructor": instructor, "email": email}


def format_modality_card(result: Dict[str, object], meta: Optional[Dict[str, str]] = None) -> Dict[str, object]:
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


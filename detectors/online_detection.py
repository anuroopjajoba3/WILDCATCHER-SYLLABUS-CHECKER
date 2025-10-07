# detectors/online_detection.py
# Rule-based detector for course delivery: Online / Hybrid / In-Person
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Tuple

# ----------------------------
# Normalize & helpers
# ----------------------------

def normalize_syllabus_text(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    # normalize bullets and whitespace
    t = (t.replace("•", "- ")
           .replace("▪", "- ")
           .replace("‣", "- ")
           .replace("◦", "- ")
           .replace("\u2022", "- "))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ----------------------------
# Enhanced detection patterns
# ----------------------------

# include both spellings and common room tokens
BUILDING_WORDS = r"(?:room|hall|building|lab|pandra|pandora|lecture hall|classroom)"

def _find_class_location_section(text: str) -> str:
    """Extract a likely 'class location / meets / meeting info' section (not office hours)."""
    lines = text.split("\n")

    location_patterns = [
        r"(?i)^(?:class|course)\s+(?:location|meets?|meeting|time)",
        r"(?i)^(?:meeting\s+)?(?:location|place|where)",
        r"(?i)^(?:time\s+and\s+)?location",
        r"(?i)^(?:class|course)\s+delivery",
        r"(?i)^delivery\s+(?:method|format|mode)",
        r"(?i)^modality",
    ]

    for i, line in enumerate(lines[:300]):
        for pat in location_patterns:
            if re.search(pat, line):
                # take a small window around it
                start = max(0, i-1)
                end = min(i+6, len(lines))
                return "\n".join(lines[start:end]).lower()
    return ""

def _find_office_hours_section(text: str) -> str:
    """Extract office hours section for disambiguation."""
    lines = text.split("\n")
    for i, line in enumerate(lines[:400]):
        if re.search(r"(?i)\boffice\s+hours?\b", line):
            start = max(0, i-1)
            end = min(i+6, len(lines))
            return "\n".join(lines[start:end]).lower()
    return ""

def _has_zoom_class_phrase(s: str) -> bool:
    """Zoom/Teams/Webex in a class meeting context (avoid office hours)."""
    if not s:
        return False
    # examples: "class meets on Zoom", "meets via Zoom", "meeting on Teams"
    return bool(re.search(r"(?i)\b(meets?|meeting|class|delivered|offered)\b.*\b(zoom|microsoft\s*teams|teams|webex)\b", s))

def _has_physical_room_phrase(s: str) -> bool:
    """Physical location cues in class context."""
    if not s:
        return False
    # Room tokens with numbers
    if re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", s):
        return True
    # "meets in <building/room>"
    if re.search(rf"(?i)\b(meets?|meeting)\s+in\b.*\b({BUILDING_WORDS})\b", s):
        return True
    return False

def detect_course_delivery(text: str) -> Dict[str, object]:
    """
    Multi-phase rule detector for course modality with context guards
    to avoid office-hours false positives and catch synchronous online phrasing.
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
        "100% online", "fully online", "completely online", "entirely online",
        "online only", "course is online", "this course is online",
        "delivered entirely online", "offered online",
        "synchronous online", "meets online", "meets on zoom", "meets via zoom",
        "asynchronous online", "fully asynchronous", "entirely asynchronous",
        "this course meets synchronously online", "course meets synchronously online",
        "no scheduled class times", "no scheduled class meeting times",
        "there are no scheduled class times", "there are no scheduled meeting times"
    ]
    for phrase in online_definitive:
        if phrase in t_lower:
            return {"modality": "Online", "confidence": 0.95, "evidence": [phrase]}
    
    # Check for "Time/Location: ... Online" pattern (common in headers)
    if re.search(r"(?i)(?:time\s+and\s+)?location[:\s]+.*\bonline\b", t_lower[:800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["location states online"]}
    
    # Check for day/time followed by "online" in first 800 chars
    if re.search(r"(?i)(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*[,\s]+\d{1,2}:\d{2}.*\bonline\b", t_lower[:800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["class time shows online"]}

    hybrid_definitive = [
        "hybrid course", "hy-flex", "hyflex", "blended course",
        "hybrid format", "blended format",
        "face-to-face and online", "in-person and online"
    ]
    for phrase in hybrid_definitive:
        if phrase in t_lower:
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": [phrase]}

    # face-to-face weekly + async/online mention
    if re.search(r"(?i)face[-\s]?to[-\s]?face\s+(?:weekly|sessions?).*(?:async|online)", t_lower):
        return {"modality": "Hybrid", "confidence": 0.92, "evidence": ["face-to-face + async/online components"]}

    # === PHASE 2: Class location section takes precedence over office hours ===
    if class_section:
        if _has_zoom_class_phrase(class_section):
            return {"modality": "Online", "confidence": 0.90, "evidence": ["class meets on Zoom/Teams/Webex"]}

        if _has_physical_room_phrase(class_section):
            return {"modality": "In-Person", "confidence": 0.90, "evidence": ["class meets in physical room"]}

    # Check for explicit "Delivery Method: Online" or similar in first 1000 chars
    header_1000 = t_lower[:1000]
    if re.search(r"(?i)(?:delivery|modality|format|mode)\s*[:\-]?\s*(?:online|asynchronous|synchronous online)", header_1000):
        return {"modality": "Online", "confidence": 0.92, "evidence": ["delivery method states online"]}

    # A header "meets in Room/Lab/Pandra/Pandora …" in the very top section is strong in-person
    header_500 = t_lower[:600]
    if re.search(rf"(?i)\b(meets?|meeting)\b.*\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", header_500):
        # But check it's not in office hours context
        office_in_header = "office" in header_500[max(0, header_500.find("meets")-50):header_500.find("meets")+150] if "meets" in header_500 else False
        if not office_in_header:
            return {"modality": "In-Person", "confidence": 0.92, "evidence": ["header shows physical meeting room"]}

    # === PHASE 3: Asynchronous (guard against office hours / tutoring) ===
    if "asynchronous" in t_lower:
        i = t_lower.find("asynchronous")
        snippet = t_lower[max(0, i-220): i+220]
        # ignore support-service/non-modality contexts
        bad_context = ["tutoring", "writing lab", "writing center", "owl", "support service",
                       "recorded lectures", "temporary", "accommodations", "miss class"]
        # Don't exclude "office hours" here - that's already handled separately
        if not any(b in snippet for b in bad_context):
            # online context nearby
            if any(w in snippet for w in ["online", "remote", "delivered", "format", "course is", "meets online", "delivery"]):
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
            evidence.append(f"online_pattern_match")

    # shallow section for early Zoom mentions (avoid office context)
    first_1500 = t_lower[:1500]
    zpos = first_1500.find("zoom")
    if zpos != -1:
        # if "office" not close to zoom mention, treat as course cue
        near = first_1500[max(0, zpos-60): zpos+60]
        if "office" not in near:
            score_online += 2.0

    inperson_patterns = [
        (rf"(?i)\b(?:class|course|lecture)\s+(?:meets?|is held|location).*(?:{BUILDING_WORDS})\b", 3.0),
        (rf"(?i)\b(?:location|where)\b.*\b(?:{BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", 2.7),
        (r"(?i)\bin[-\s]?person\s+(?:class|course|instruction)\b", 2.5),
        (r"(?i)\bon\s+campus\s+(?:course|class)\b", 2.0),
        (r"(?i)\bclassroom\s+instruction\b", 2.0),
        (rf"(?i)\b[A-Z][a-zA-Z]+(?:\s+(?:Hall|Building|Lab))?\s+[A-Za-z]?\d{{2,4}}\b", 2.1),
        # class management phrases that usually imply being in a room
        (r"(?i)\btaking\s+attendance\b", 1.5),
        (r"(?i)\barrive\s+late\s+to\s+class\b", 1.3),
        (r"(?i)\bleave\s+early\s+from\s+class\b", 1.3),
        (r"(?i)\bneed\s+to\s+be\s+here\b", 1.5),
    ]
    for pat, w in inperson_patterns:
        if re.search(pat, t_lower):
            score_inperson += w
            evidence.append(f"inperson_pattern_match")

    # hybrid: presence of both online and in-person cues
    if score_online > 1.3 and score_inperson > 1.3:
        score_hybrid = max(score_hybrid, (score_online + score_inperson) * 0.55)

    # Office-hours disambiguation: if rooms only appear in office hours, reduce in-person scoring
    if office_section and score_inperson > 0:
        room_in_class = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", class_section))
        room_in_office = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", office_section))
        
        if room_in_office and not room_in_class:
            # Rooms only in office hours - heavily reduce in-person score
            score_inperson = max(0.0, score_inperson - 4.0)
            evidence.append("reduced_inperson_office_hours_only")
            
            # If we have ANY online signals (even weak ones), favor online
            if score_online > 1.0:
                score_online += 2.0  # Boost online instead of just reducing in-person
                evidence.append("boosted_online_no_class_location")

    scores = {"Online": score_online, "Hybrid": score_hybrid, "In-Person": score_inperson}
    max_score = max(scores.values())

    if max_score <= 0:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["no clear modality indicators"]}

    modality = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(max_score / total, 2) if total > 0 else 0.6
    confidence = max(confidence, 0.60)  # floor

    return {
        "modality": modality,
        "confidence": confidence,
        "evidence": evidence[:4] if evidence else [f"{modality.lower()} indicators found"],
    }

# ----------------------------
# Helper for test_runner.py
# ----------------------------

def detect_modality(text: str) -> Tuple[str, str]:
    """Return (label, evidence_str) for compatibility with test runner."""
    res = detect_course_delivery(text)
    label = res.get("modality", "Unknown")
    ev = res.get("evidence") or []
    return label, " | ".join(ev[:3])
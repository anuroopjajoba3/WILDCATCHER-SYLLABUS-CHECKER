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
    t = (t.replace("•", "- ").replace("▪", "- ").replace("‣", "- ").replace("◦", "- ").replace("\u2022", "- "))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ----------------------------
# Enhanced detection patterns
# ----------------------------

BUILDING_WORDS = r"(?:room|hall|building|lab|pandra|pandora)"

def _find_class_location_section(text: str) -> str:
    """Extract the class/course location section (not office hours)"""
    lines = text.split('\n')
    
    location_patterns = [
        r'(?i)^(?:class|course)\s+(?:location|meets?|time)',
        r'(?i)^(?:meeting\s+)?(?:location|place|where)',
        r'(?i)^(?:time\s+and\s+)?location',
    ]
    
    for i, line in enumerate(lines[:200]):  # Check first 200 lines
        for pattern in location_patterns:
            if re.search(pattern, line):
                context = '\n'.join(lines[i:min(i+5, len(lines))])
                return context.lower()
    
    return ""

def _find_office_hours_section(text: str) -> str:
    """Extract office hours section"""
    lines = text.split('\n')
    
    for i, line in enumerate(lines[:300]):
        if re.search(r'(?i)office\s+hours?', line):
            context = '\n'.join(lines[max(0, i-1):min(i+5, len(lines))])
            return context.lower()
    
    return ""

def detect_course_delivery(text: str) -> Dict[str, object]:
    """
    Enhanced detection with improved context awareness
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
    ]
    for phrase in online_definitive:
        if phrase in t_lower:
            return {"modality": "Online", "confidence": 0.95, "evidence": [phrase]}
    
    hybrid_definitive = [
        "hybrid course", "hy-flex", "hyflex", "blended course",
        "hybrid format", "blended format",
    ]
    for phrase in hybrid_definitive:
        if phrase in t_lower:
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": [phrase]}
    
    if re.search(r'face-to-face\s+(?:weekly|sessions?).*(?:async|online)', t_lower):
        return {"modality": "Hybrid", "confidence": 0.92, "evidence": ["face-to-face + async/online components"]}
    
    # === PHASE 2: Class location section ===
    # Check for explicit meeting location in first 500 chars
    header_section = t_lower[:500]
    meeting_match = re.search(r'(?:meetings?|class\s+meets?|meets\s+in).*?(?:room|lab|hall|building|pandora|pandra)\s+[A-Za-z]?\d{2,4}', header_section)
    if meeting_match:
        return {"modality": "In-Person", "confidence": 0.92, "evidence": ["class meets in physical location"]}
    
    if class_section:
        if any(word in class_section for word in ["zoom", "microsoft teams", "webex"]):
            if not any(word in class_section for word in ["may", "occasionally", "if needed", "weather"]):
                return {"modality": "Online", "confidence": 0.88, "evidence": ["class meets via zoom/teams"]}
        
        if re.search(rf"{BUILDING_WORDS}\s+[A-Za-z]?\d{{2,4}}", class_section):
            return {"modality": "In-Person", "confidence": 0.88, "evidence": ["class meets in physical room"]}
    
    # === PHASE 3: Asynchronous context ===
    if "asynchronous" in t_lower:
        idx = t_lower.find("asynchronous")
        snippet = t_lower[max(0, idx-200):min(len(t_lower), idx+200)]
        
        # Skip if it's about support services (tutoring, writing lab, etc.) or temporary accommodations
        if any(word in snippet for word in ["tutoring", "writing lab", "writing center", "owl", "support service", "recorded lectures", "temporary", "accommodations", "if you are required to miss"]):
            pass  # Not about course modality
        elif any(word in snippet for word in ["online", "remote", "delivered", "format", "course is"]):
            if not any(word in snippet for word in ["meets in", "classroom", "in person"]):
                return {"modality": "Online", "confidence": 0.82, "evidence": ["asynchronous online delivery"]}
    
    # === PHASE 4: Pattern-based scoring ===
    score_online = 0.0
    score_hybrid = 0.0
    score_inperson = 0.0
    
    online_patterns = [
        (r'(?i)course\s+(?:is\s+)?(?:delivered|offered|taught)\s+online', 3.0),
        (r'(?i)online\s+(?:course|format|delivery|instruction)', 2.5),
        (r'(?i)synchronous\s+online', 2.5),
        (r'(?i)remote\s+(?:course|instruction|learning)', 2.0),
        (r'(?i)virtual\s+course', 2.0),
    ]
    for pattern, weight in online_patterns:
        if re.search(pattern, t_lower):
            score_online += weight
            evidence.append(f"found: {pattern}")
    
    first_section = t_lower[:1500]
    if "zoom" in first_section and "office" not in first_section[:first_section.find("zoom")+50]:
        score_online += 1.5
    
    inperson_patterns = [
        (rf"(?i)(?:class|course|lecture)\s+(?:meets?|held|location).*{BUILDING_WORDS}", 3.0),
        (rf"(?i)(?:location|where).*(?:{BUILDING_WORDS})\s+[A-Za-z]?\d{{2,4}}", 2.7),
        (r"(?i)in[-\s]?person\s+(?:class|course|instruction)", 2.5),
        (r"(?i)on\s+campus\s+(?:course|class)", 2.0),
        (r"(?i)classroom\s+instruction", 2.0),
        (rf"(?i)\b[A-Z][a-zA-Z]+(?:\s+(?:Hall|Building|Lab))?\s+[A-Za-z]?\d{{2,4}}\b", 2.3),
        (r"(?i)(?:taking|keep)\s+attendance\s+(?:every|each)\s+(?:day|class)", 2.5),
        (r"(?i)(?:come|arrive)\s+(?:in\s+)?late\s+to\s+class", 2.0),
        (r"(?i)leave\s+early\s+from\s+class", 2.0),
        (r"(?i)need\s+to\s+be\s+here\s+on\s+a\s+consistent\s+basis", 2.5),
        (r"(?i)removal\s+from\s+(?:this\s+)?class", 1.8),
    ]
    for pattern, weight in inperson_patterns:
        if re.search(pattern, t_lower):
            score_inperson += weight
            evidence.append(f"found: {pattern}")
    
    if re.search(r"(?i)(?:course|class)\s+meets\s+in\s+(?!zoom)", t_lower):
        score_inperson += 2.0
    
    if re.search(r'(?i)(?:some|portion|part).*(?:online|remote)', t_lower) and \
       re.search(r'(?i)(?:some|portion|part).*(?:in.?person|on.?campus)', t_lower):
        score_hybrid = 3.0
    
    if score_online > 1.5 and score_inperson > 1.5:
        score_hybrid = max(score_hybrid, (score_online + score_inperson) * 0.6)
    
    if office_section and score_inperson > 0:
        room_in_class = bool(re.search(r'room\s+\d+', class_section))
        room_in_office = bool(re.search(r'room\s+\d+', office_section))
        if room_in_office and not room_in_class:
            score_inperson = max(0, score_inperson - 2.0)
    
    scores = {"Online": score_online, "Hybrid": score_hybrid, "In-Person": score_inperson}
    max_score = max(scores.values())
    
    if max_score == 0:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["no clear modality indicators found"]}
    
    modality = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(max_score / total, 2) if total > 0 else 0.5
    if confidence < 0.60:
        confidence = 0.60
    
    return {"modality": modality, "confidence": confidence, "evidence": evidence[:4] if evidence else [f"{modality.lower()} indicators found"]}

# ----------------------------
# Helper function for test_runner.py
# ----------------------------

def detect_modality(text: str) -> Tuple[str, str]:
    """Simple wrapper that returns modality and empty evidence string"""
    result = detect_course_delivery(text)
    label = result.get("modality", "Unknown")
    # Return empty evidence string since you don't need it
    return label, ""

# Alias for backwards compatibility
extract_modality_improved = detect_modality

# ----------------------------
# Metadata extraction for UI
# ----------------------------

def quick_course_metadata(text: str) -> Dict[str, str]:
    """Extract course name, instructor, and email for display"""
    if not text:
        return {"course": "", "instructor": "", "email": ""}
    
    t = normalize_syllabus_text(text)
    meta = {"course": "", "instructor": "", "email": ""}
    
    # Extract email
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", t)
    if email_match:
        meta["email"] = email_match.group(0)
    
    # Extract instructor
    for line in t.splitlines()[:80]:
        instructor_match = re.search(r"(?i)\b(Instructor|Professor|Prof\.?)\s*[:\-]\s*(.+)$", line.strip())
        if instructor_match:
            meta["instructor"] = instructor_match.group(2).strip()
            break
    
    # Extract course name
    for line in t.splitlines()[:60]:
        course_match = re.search(r"(?i)^([A-Z]{2,6}\s?\d{3,4}[A-Z]?(?:\s*\([^)]+\))?)\s*[:\-–]\s*(.+)$", line.strip())
        if course_match:
            meta["course"] = f"{course_match.group(1).strip()} — {course_match.group(2).strip()}"
            break
    
    if not meta["course"]:
        for line in t.splitlines():
            if line.strip():
                meta["course"] = line.strip()
                break
    
    return meta

def format_modality_card(result: Dict[str, object], meta: Dict[str, str] = None) -> Dict[str, object]:
    """Format modality detection result as a card for the UI"""
    meta = meta or {"course": "", "instructor": "", "email": ""}
    modality = str(result.get("modality", "Unknown"))
    conf = float(result.get("confidence", 0.0))
    evidence = result.get("evidence", []) or []
    
    status = "PASS" if modality in ("Online", "Hybrid", "In-Person") else "FAIL"
    msg = f"{modality} modality detected" if modality != "Unknown" else "Detected delivery"
    
    header_lines = []
    if meta.get("course"):
        header_lines.append(meta["course"])
    if meta.get("instructor") or meta.get("email"):
        ins = meta.get("instructor", "")
        eml = meta.get("email", "")
        if ins and eml:
            header_lines.append(f"{ins} — {eml}")
        elif ins:
            header_lines.append(f"Instructor: {ins}")
        else:
            header_lines.append(f"Email: {eml}")
    
    return {
        "status": status,
        "heading": "Course Delivery",
        "message": msg,
        "label": modality,
        "confidence": conf,
        "header": header_lines,
        "evidence": evidence,
    }
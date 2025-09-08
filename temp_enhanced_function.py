async def extract_course_information(text, llm):
    """
    Extracts course information from the provided text using an LLM.
    Enhanced version with better field detection.
    """
    # Keep existing text limiting logic
    if len(text) > 60000:
        limited_text = text[:30000] + "\n\n[... middle content omitted ...]\n\n" + text[-10000:]
    else:
        limited_text = text.strip()

    # Generate a hash of the limited text for caching
    text_hash = hashlib.md5(limited_text.encode()).hexdigest()

    # Check if already processed
    existing_doc = session.query(DocumentInfo).filter_by(doc_hash=text_hash).first()
    if existing_doc:
        print("Using cached document info.")
        return json.loads(existing_doc.extracted_info)

    # Enhanced prompt with better instructions
    prompt = f"""
    You are an expert at extracting course information from syllabi. Your task is to find and extract ALL available course information, regardless of formatting or structure.

    CRITICAL INSTRUCTIONS:
    1. Search the ENTIRE text for each field - information may be scattered throughout
    2. Look for variations, synonyms, and contextual clues
    3. Extract partial information if complete info isn't available
    4. ONLY omit a field if there's absolutely no relevant information
    5. Check tables, lists, paragraphs, headers - everywhere
    6. Information may be embedded in sentences rather than labeled

    FIELD DETECTION PATTERNS (use ALL variations):

    **Course ID**: Look for patterns like "COMP 690", "NSIA 850", "CPRM ###", course codes, numbers
    - May appear as: "Course:", "Course Number:", "Course Code:", or just at the top

    **Credits**: 
    - Look for: "Credits:", "Credit Hours:", "# credits", "units"
    - Patterns: "3 credits", "Credits: 3", "3-credit course", "(3 cr)"
    - May be in parentheses after course name

    **Term/Semester**:
    - Patterns: "Summer 2025", "Fall Term", "Spring Semester"
    - Date ranges: "(05/27/2025 – 07/18/2025)", "May 19 - Aug 8"
    - "Term 5", "8-week course", "Session A/B"

    **Instructor Info**:
    - Name: Look after "Instructor:", "Professor:", "Dr.", "Prof."
    - Title: "Assistant Professor", "Adjunct", "Lecturer", "Clinical Professor"
    - Department: Text after title, "of [Department]", "in [Program]"
    - Email: Any @unh.edu or @[domain] address
    - Phone: (###) ###-####, ###-###-####, ###.###.####, "ext.", "x####"
    - Response time: "within 24 hours", "responds in", "1-2 business days"

    **Office Hours**:
    - "Office hours:", "Available:", "Meeting times:"
    - "By appointment", "Mondays 2-4pm", "scheduled via email"
    - May be in multiple places or formats

    **Department/Program**:
    - "College of", "School of", "Department of", "Program in"
    - May appear in header, after instructor info, or course description

    **Prerequisites**:
    - "Prerequisites:", "Prereq:", "Required:", "Must have completed"
    - "None", "N/A", "Faculty permission"
    - Course codes like "COMP 401" or descriptions

    **Learning Outcomes/Objectives**:
    - "Learning Outcomes", "Objectives", "Students will be able to"
    - "Upon completion", "By the end of this course"
    - Bullet points starting with action verbs

    **Grading**:
    - Look for percentages that sum to 100
    - "Assessment", "Evaluation", "Grade breakdown"
    - Letter grades with percentages: "A: 93-100%"
    - Assignment weights: "Exams 40%", "Participation 20%"

    **Attendance Policy**:
    - "Attendance", "Absence", "Missing class", "Participation"
    - May be in general policies section

    **Late Policy**:
    - "Late submission", "Late work", "Extensions", "Penalties"
    - "X% deduction per day", "not accepted after"

    **Academic Integrity**:
    - "Academic honesty", "Plagiarism", "Cheating", "Honor code"
    - "AI policy", "ChatGPT", "automated tools"

    **Materials/Textbook**:
    - "Required text", "Textbook", "Readings", "Materials"
    - ISBN numbers, author names, titles in italics
    - "No textbook required", "Provided on Canvas"

    **Technical Requirements**:
    - "Computer", "Software", "Browser", "Internet"
    - "Canvas", "Zoom", "Microsoft Teams"

    **Workload**:
    - "X hours per week", "time commitment", "expected effort"
    - "135 hours total", "3 hours per credit"

    CONTEXT RULES:
    - If you see "See the UNH Credit Hour Policy" after a number, that number is credits
    - "College of Professional Studies" is a department
    - "By appointment" means office hours are available by appointment
    - Date ranges in parentheses indicate the term dates
    - "Adjunct" or "Clinical" before "Professor" is part of the title

    Text to analyze:
    {limited_text}

    Return ONLY a valid JSON object with these fields (omit completely if not found):
    {{
        "Course Id": "",
        "Course Name": "",
        "Credits": "",
        "Modality": "",
        "Term": "",
        "Department": "",
        "Prerequisites": "",
        "Instructor Name": "",
        "Instructor Title/Rank": "",
        "Instructor Department": "",
        "Instructor Email": "",
        "Instructor Response Time": "",
        "Office Location": "",
        "Phone Number": "",
        "Office Hours": "",
        "Teaching Assistant Info": "",
        "Course Format": "",
        "Student Learning Outcomes": "",
        "Course Topics & Dates": "",
        "Sensitive Content": "",
        "Credit Hour Workload Estimate": "",
        "Assignment Types and Delivery": "",
        "Grading Procedures": "",
        "Final Grade Scale": "",
        "Textbook": "",
        "Other Materials": "",
        "Technical Requirements": "",
        "Attendance Policy": "",
        "Late Submission Policy": "",
        "Academic Integrity": "",
        "Program Accreditation Info": ""
    }}
    """

    try:
        # Call the LLM
        response = await llm.ainvoke(prompt)
        raw_text = response.content.strip()

        # Better JSON extraction
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
        
        # Clean up the response
        raw_text = raw_text.strip()
        if not raw_text.startswith("{"):
            start_idx = raw_text.find("{")
            if start_idx != -1:
                raw_text = raw_text[start_idx:]
        if not raw_text.endswith("}"):
            end_idx = raw_text.rfind("}")
            if end_idx != -1:
                raw_text = raw_text[:end_idx + 1]

        # Parse JSON
        extracted_info = json.loads(raw_text)
        
        # Post-process to remove empty fields
        extracted_info = {k: v for k, v in extracted_info.items() if v and v.strip()}
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw text: {raw_text[:500]}")
        extracted_info = {"error": "Failed to parse response"}
    except Exception as e:
        print(f"Extraction error: {e}")
        extracted_info = {"error": str(e)}

    # Cache the result
    try:
        new_doc = DocumentInfo(doc_hash=text_hash, extracted_info=json.dumps(extracted_info))
        session.add(new_doc)
        session.commit()
    except Exception as e:
        session.rollback()
        print("Error inserting document info:", e)
        existing_doc = session.query(DocumentInfo).filter_by(doc_hash=text_hash).first()
        if existing_doc:
            return json.loads(existing_doc.extracted_info)
        else:
            return {"error": "Failed to save document info."}

    return extracted_info
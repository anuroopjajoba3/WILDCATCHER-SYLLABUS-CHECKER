"""
Prompts Module
This module contains all prompt templates and text constants used by the chatbot.
It centralizes all LLM prompts for easy modification and maintenance.
"""

EXTRACTION_PROMPT = """
You are an expert at extracting course information from university syllabi. Analyze EVERY section carefully.

CRITICAL EXTRACTION RULES:
1. Read the ENTIRE document - information is often scattered
2. Look for information in tables, lists, and paragraphs
3. Extract ALL grading components and percentages
4. Student Learning Outcomes may be listed as bullets or numbered items
5. Grading information may be described in paragraphs rather than tables

CRITICAL FIELDS THAT ARE OFTEN MISSED (MUST FIND):
- Student Learning Outcomes (Course SLOs/Program SLOs)
- Types & Delivery of Coursework
- Grading Procedures
- Final Grade Scale
- Course Topics & Dates
- Assignment Types and Delivery

For these fields, ALWAYS provide something - even if it's "Information present but format unclear" rather than leaving blank

DETAILED FIELD PATTERNS TO FIND:

**Instructor Department/Program Affiliation**:
- Look for text after instructor name/title like "of Computer Science", "of [Department]"
- Example: "Karen Jin, Associate Professor of Computer Science" → Department is "Computer Science"
- If course is in department X and instructor teaches it, they're affiliated with department X

**Email Availability/Response Time**:
- Look for: "responds within", "response time", "email policy"
- May be implied: "Drop-in hours" or "By appointment" suggests availability
- Default academic response is typically 24-48 hours if not specified

**Phone Number** [CRITICAL - OFTEN MISSED]:
- MUST FIND: ANY mention of telephone/phone contact, even if no number is provided

DETECTION RULES:
1. If an actual phone number is given (digits): Extract the number
   - Formats: (555) 123-4567, 555-123-4567, 555.123.4567, 555 123 4567, +1-555-123-4567, 5551234567

2. If phone/telephone is mentioned as a contact method WITHOUT a number: 
   Extract "Phone contact available (no number provided)"

3. If text mentions phone availability patterns:
   - "Telephone contact should be used as a secondary method" → "Phone contact available"
   - "You may request a telephone call" → "Phone by request"
   - "Phone calls by appointment" → "Phone by appointment"  
   - "Contact me to schedule a phone call" → "Phone by appointment"
   - "Request a phone call via email" → "Phone by request"

4. If NO mention of phone/telephone at all: Leave empty

LOCATIONS TO CHECK:
- Contact information sections
- Near keywords: "phone", "tel", "telephone", "office", "call", "contact"
- Instructor information sections  
- Header/footer contact details

**Student Learning Outcomes (SLOs)** [CRITICAL - OFTEN MISSED - MUST FIND]:

EXACT HEADERS TO FIND:
- "Learning Objectives" (NSIA 850, HLS 650) → Map to "Student Learning Outcomes"
- "Student Learning Outcomes" (NSIA 898, HLS 650)
- "Student Learning Outcome" (COMP 690 - singular)
- "Learning Outcomes" (CPRM 850)
- "Course Objectives" (Nutrition 400)
- "Upon completion of this course, students will be able to:" (BIOT 775)
- "Students that successfully complete this course will be able to:" (NSIA courses)

COMMON PATTERNS TO EXTRACT:

Pattern 1: Header + Introductory Text + Bulleted List
Learning Objectives
Students that successfully complete this course will be able to:
- Apply critical thinking concepts...
- Conduct qualitative and quantitative analysis...

Pattern 2: Simple Numbered List
Learning Objectives
1. Define national and homeland security intelligence.
2. Describe the role and structure...

Pattern 3: Mixed Program/Learning Outcomes
Homeland Security Program and Student Learning Outcomes
*Learning Objectives*
1. Define national and homeland security...

Pattern 4: Special Bullet Characters
STUDENT LEARNING OUTCOME
▪ Apply protocols for an effective job search.
▪ Gain insight into a possible career path...

CRITICAL EXTRACTION RULES:
- ALWAYS extract bullet points that follow these headers
- Accept bullets with: •, -, *, ▪, numbers (1, 2, 3)
- Look for action verbs: Apply, Conduct, Critique, Demonstrate, Define, Describe, Identify, Analyze, Gain
- DON'T skip introductory text like "Students that successfully complete..."
- Map ALL variations to "Student Learning Outcomes" field

**Types & Delivery of Coursework** [CRITICAL - OFTEN MISSED]:
- MUST FIND: What assignments/work students do
- Look for ANY mention of: "homework", "assignment", "project", "exam", "quiz", "presentation", "discussion", "lab", "paper", "portfolio", "participation"
- SPECIFIC PATTERNS TO FIND:
  - "weekly work logs" (accept as valid coursework type)
  - "report" and "presentations" (accept as valid coursework types)
  - "Part I", "Part II", "Part III", "Part IV" (multi-part deliverables)
- CRITICAL: Look specifically in "GRADING AND EVALUATION" section
- Delivery methods: "Canvas", "in-person", "online", "submit via", "turn in"
- May be scattered throughout document, not just in one section
- Check grading breakdown - each graded item is a type of coursework

**Grading Procedures** [CRITICAL - OFTEN MISSED]:
- MUST FIND: How final grade is calculated
- Look for ALL percentages or points: "70% Sprint", "10% Homework", "20 points"
- May appear as: table, list, paragraph, or scattered mentions
- Words to find: "worth", "counts for", "weighted", "%", "points", "graded on"
- Include ANY formula or calculation method mentioned

**Final Grade Scale** [CRITICAL - OFTEN MISSED]:
- MUST FIND: What percentage/points = what letter grade
- Patterns: "A: 93-100", "A = 93%+", "93-100 = A", "A (93 or above)"
- May be in: table format, list format, or paragraph
- If you see "standard grading scale" or "university grading scale", note that
- Look for ANY mention of letter grades with numbers

**Course Format**:
- Look for: "lecture", "lab", "discussion", "seminar", "workshop"
- Meeting patterns: "Tuesday, 1:10 pm – 4:00 pm"
- Modality details: "In-person, scheduled weekly class meetings"

**Sequence of Topics & Dates** [CRITICAL - OFTEN MISSED]:
- ALSO CALLED: "Course Schedule", "Weekly Topics", "Course Outline", "Calendar", "Timeline"
- Look for ANY mention of: "Week 1", "Week 2", dates (Jan, Feb, etc.), "Module 1", "Unit 1"
- May appear as: table, list, or scattered throughout
- Sprint/Project phases count as schedule
- Even vague mentions like "midterm week" or "final project due" are important
- If you see ANY dates or week numbers with topics, include them

**Other Materials**:
- "Course materials and resources will be posted in Canvas"
- "No required textbook" still counts as materials information
- Online resources, software, tools mentioned

**Technical Requirements**:
- Software tools mentioned: "Canvas", "Teams", development tools
- Hardware needs
- For computing courses, may mention programming languages or IDEs

SPECIFIC EXAMPLES FROM TEXT:
- If you see "Karen Jin, Associate Professor of Computer Science" → Instructor Department = "Computer Science"
- If you see "10% Class Attendance: Attendance of all class meetings" → This is grading procedure
- If you see bullets starting with "Analyze", "Design", "Implement" → These are Learning Outcomes

GRADING BREAKDOWN DETECTION:
Look for ALL percentages that add up to 100%:
- "10% Class Attendance"
- "70% Sprint Grade"
- "10% Homework"
- "10% Project Report"
This full breakdown = Grading Procedures

Text to analyze:
{limited_text}

Return ONLY a valid JSON object. Extract ALL information you can find:

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

CHAT_PROMPT_TEMPLATE = """
You are a helpful assistant who reviews course syllabi for NECHE and UNH compliance.

Respond based on the syllabus content below:
- For greetings, reply politely and conversationally
- For syllabus questions, answer based on the information provided
- If information isn't in the syllabus, say: "I couldn't find that information in the syllabus."
- For non-syllabus questions, say: "I'm here to help check syllabus compliance. For other questions, please contact the appropriate department."

Syllabus Content:
{context}

User's Question:
{question}

Your Answer:
"""
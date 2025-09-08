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

DETAILED FIELD PATTERNS TO FIND:

**Instructor Department/Program Affiliation**:
- Look for text after instructor name/title like "of Computer Science", "of [Department]"
- Example: "Karen Jin, Associate Professor of Computer Science" → Department is "Computer Science"
- If course is in department X and instructor teaches it, they're affiliated with department X

**Email Availability/Response Time**:
- Look for: "responds within", "response time", "email policy"
- May be implied: "Drop-in hours" or "By appointment" suggests availability
- Default academic response is typically 24-48 hours if not specified

**Student Learning Outcomes (SLOs)**:
- Headers: "Student Learning Outcome", "Learning Objectives", "Course Objectives"
- Look for bullet points starting with action verbs: "Analyze", "Design", "Implement", "Evaluate"
- Example: "• Analyze complex computing problems..."
- May be a numbered or bulleted list

**Types & Delivery of Coursework**:
- Look in grading section for assignment types
- Common types: "Homework", "Projects", "Exams", "Presentations", "Reports"
- Delivery: "Canvas", "In-person", "Online submission"
- May be described in grading breakdown

**Grading Procedures**:
- Look for how grades are calculated
- Example: "70% Sprint Grade", "10% Homework", "10% Project Report"
- May include formulas like "Teamwork Multiplier * Team Sprint Grade"
- Check for rubrics or evaluation criteria

**Final Grade Scale**:
- Letter grade percentages: "A: 90-100%", "B: 80-89%"
- May be in a table or list format
- Sometimes stated as "standard UNH grading scale"
- If not explicit, note if there's a reference to university standards

**Course Format**:
- Look for: "lecture", "lab", "discussion", "seminar", "workshop"
- Meeting patterns: "Tuesday, 1:10 pm – 4:00 pm"
- Modality details: "In-person, scheduled weekly class meetings"

**Sequence of Topics & Dates**:
- May be called: "Course Schedule", "Weekly Topics", "Course Outline"
- Sprint/Project phases if mentioned
- Look for any timeline or sequence information

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
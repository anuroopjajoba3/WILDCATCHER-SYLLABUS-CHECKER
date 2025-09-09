"""
File: chatbot.py
Date: 04-23-2025
Enhanced version with improved field detection
"""

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.schema import Document, HumanMessage
from langchain.memory import ConversationBufferMemory
import re
import json
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import time
from docx import Document as DocxDocument
from database import DocumentInfo, Session
import zipfile
import tempfile
import shutil
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("gunicorn.log"),
        logging.StreamHandler()
    ]
)

session = Session()
app = Flask(__name__)

# Helper function to validate extracted information
def validate_extracted_info(info):
    """Validates and cleans extracted information."""
    if not info or not isinstance(info, dict):
        return info
    
    # Check email format
    if "Instructor Email" in info:
        email = info["Instructor Email"]
        if "@" not in email:
            del info["Instructor Email"]
    
    # Check credits is a number
    if "Credits" in info:
        credits = str(info["Credits"])
        # Extract just the number
        match = re.search(r'\d+', credits)
        if match:
            info["Credits"] = match.group()
    
    # Validate phone number format
    if "Phone Number" in info:
        phone = str(info["Phone Number"])
        # Remove non-digits and check length
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 15:
            del info["Phone Number"]
    
    # Remove empty or placeholder values
    keys_to_remove = []
    for key, value in info.items():
        if value in [None, "", "N/A", "Not Specified", "Unknown", "Not Found"]:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del info[key]
    
    return info

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file using pdfplumber."""
    text = []
    try:
        with pdfplumber.open(pdf_path) as pdf_doc:
            for page in pdf_doc.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
                # Also extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        for row in table:
                            if row:
                                text.append(" | ".join([str(cell) if cell else "" for cell in row]))
    except Exception as e:
        logging.error(f"Error extracting PDF {pdf_path}: {e}")
        return None
    
    combined_text = "\n".join(text)
    
    if not combined_text.strip():
        logging.warning(f"No text extracted from {pdf_path}")
        return None
    else:
        logging.info(f"Extracted {len(combined_text)} characters from {pdf_path}")
        return combined_text

def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file using python-docx."""
    full_text = []
    try:
        doc = DocxDocument(docx_path)
        
        # Extract paragraph text
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        
        # Extract table content
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                if any(row_data):
                    full_text.append(" | ".join(row_data))
        
        # Extract from headers and footers if present
        for section in doc.sections:
            header_text = section.header.paragraphs[0].text.strip() if section.header.paragraphs else ""
            footer_text = section.footer.paragraphs[0].text.strip() if section.footer.paragraphs else ""
            if header_text:
                full_text.insert(0, header_text)
            if footer_text:
                full_text.append(footer_text)
                
    except Exception as e:
        logging.error(f"Error extracting DOCX {docx_path}: {e}")
        return None
    
    combined_text = "\n".join(full_text)
    
    if not combined_text.strip():
        logging.warning(f"No text extracted from {docx_path}")
        return None
    else:
        logging.info(f"Extracted {len(combined_text)} characters from {docx_path}")
        return combined_text

async def extract_course_information(text, llm):
    """
    Enhanced extraction with much better field detection patterns.
    """
    if not text:
        return {"error": "No text provided"}
    
    # Smart text limiting - keep beginning and end
    if len(text) > 60000:
        limited_text = text[:35000] + "\n\n[... content trimmed ...]\n\n" + text[-15000:]
    else:
        limited_text = text.strip()
    
    # Generate hash for caching
    text_hash = hashlib.md5(limited_text.encode()).hexdigest()
    
    # Check cache
    existing_doc = session.query(DocumentInfo).filter_by(doc_hash=text_hash).first()
    if existing_doc:
        logging.info("Using cached document info")
        return json.loads(existing_doc.extracted_info)
    
    # Much more detailed prompt
    prompt = f"""
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
    
    try:
        # Call LLM
        response = await llm.ainvoke(prompt)
        raw_text = response.content.strip()
        
        # Extract JSON from response
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
        
        # Clean JSON
        raw_text = raw_text.strip()
        if not raw_text.startswith("{"):
            start_idx = raw_text.find("{")
            if start_idx != -1:
                raw_text = raw_text[start_idx:]
        if not raw_text.endswith("}"):
            end_idx = raw_text.rfind("}")
            if end_idx != -1:
                raw_text = raw_text[:end_idx + 1]
        
        # Parse and validate
        extracted_info = json.loads(raw_text)
        
        # Enhanced post-processing
        extracted_info = enhanced_post_process(extracted_info, limited_text)
        
        # Remove truly empty fields
        extracted_info = {k: v for k, v in extracted_info.items() 
                         if v and str(v).strip() and v not in ["N/A", "Not Found", "Not Specified"]}
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        extracted_info = {"error": "Failed to parse response"}
    except Exception as e:
        logging.error(f"Extraction error: {e}")
        extracted_info = {"error": str(e)}
    
    # Cache result
    try:
        new_doc = DocumentInfo(doc_hash=text_hash, extracted_info=json.dumps(extracted_info))
        session.add(new_doc)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Cache error: {e}")
    
    return extracted_info

def enhanced_post_process(info, original_text):
    """
    Enhanced post-processing with pattern matching for missed fields.
    """
    if not info or not isinstance(info, dict):
        return info
    
    # Check for instructor department in original text if missing
    if "Instructor Department" not in info or not info.get("Instructor Department"):
        # Pattern: "Professor of [Department]"
        dept_pattern = r"Professor of ([^,\n]+)"
        match = re.search(dept_pattern, original_text, re.IGNORECASE)
        if match:
            info["Instructor Department"] = match.group(1).strip()
    
    # Check for SLOs if missing
    if "Student Learning Outcomes" not in info or not info.get("Student Learning Outcomes"):
        # Look for bullet points after "Learning Outcome" header
        slo_pattern = r"Student Learning Outcome[s]?:?\s*\n((?:[\s•\-\*]*[A-Z][^\n]+\n?)+)"
        match = re.search(slo_pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            info["Student Learning Outcomes"] = match.group(1).strip()
    
    # Check for grading breakdown
    if "Grading Procedures" not in info or not info.get("Grading Procedures"):
        # Look for percentages
        grade_pattern = r"(\d+%[^:\n]*:[^\n]+)"
        matches = re.findall(grade_pattern, original_text)
        if matches:
            info["Grading Procedures"] = "; ".join(matches)
    
    # Check for course format
    if "Course Format" not in info or not info.get("Course Format"):
        # Look for meeting pattern
        format_pattern = r"(In-person|Online|Hybrid)[^.]*weekly[^.]*meetings?"
        match = re.search(format_pattern, original_text, re.IGNORECASE)
        if match:
            info["Course Format"] = match.group(0).strip()
    
    # Email response time - only extract if explicitly mentioned (removed auto-fill to prevent false positives)
    # The enhanced post-processing in course_extraction.py handles this properly
    
    # Materials check
    if "Other Materials" not in info:
        if "Canvas" in original_text or "posted in Canvas" in original_text.lower():
            info["Other Materials"] = "Course materials and resources posted in Canvas"
    
    # Technical requirements for computing courses
    if "Technical Requirements" not in info:
        if any(term in original_text.lower() for term in ["canvas", "teams", "scrum", "development"]):
            info["Technical Requirements"] = "Canvas LMS, Microsoft Teams, development tools as specified"
    
    # Assignment types from grading section
    if "Assignment Types and Delivery" not in info:
        types = []
        if "homework" in original_text.lower():
            types.append("Homework")
        if "project" in original_text.lower():
            types.append("Projects")
        if "sprint" in original_text.lower():
            types.append("Sprint deliverables")
        if "report" in original_text.lower():
            types.append("Reports")
        if types:
            info["Assignment Types and Delivery"] = ", ".join(types) + " (via Canvas)"
    
    return info

@app.route('/')
def home():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_file():
    """Handles single file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return jsonify({'error': 'Invalid file type. Please upload PDF or Word document.'}), 400

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # Clean old uploads
    uploaded_files = sorted(os.listdir('uploads'))
    if len(uploaded_files) > 5:
        for old_file in uploaded_files[:-5]:
            old_file_path = os.path.join('uploads', old_file)
            if os.path.isdir(old_file_path):
                shutil.rmtree(old_file_path)
            else:
                os.remove(old_file_path)

    file_path = os.path.join('uploads', file.filename)
    file.save(file_path)
    
    logging.info(f"{request.remote_addr} uploaded file: {file.filename}")

    # Extract text
    if file.filename.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file_path)
    else:
        extracted_text = extract_text_from_docx(file_path)

    if extracted_text is None:
        return jsonify({'error': 'Failed to extract text from document.'}), 400

    # Extract course information
    extracted_info = asyncio.run(extract_course_information(extracted_text, llm))
    
    if extracted_info and isinstance(extracted_info, dict):
        return jsonify({'extracted_information': extracted_info})
    else:
        return jsonify({'error': "No relevant course information found."}), 400

# Initialize files
chat_history_file = 'chat_history.json'
conversation_memory_file = 'conversation_memory.json'

def initialize_chat_history_file():
    """Initialize chat history files."""
    for file_path in [chat_history_file, conversation_memory_file]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                json.dump([], file)

def load_chat_history():
    """Load chat history."""
    if os.path.exists(chat_history_file):
        try:
            with open(chat_history_file, 'r') as file:
                data = json.load(file)
                return data if data else []
        except json.JSONDecodeError:
            return []
    return []

def save_chat_history(chat_history):
    """Save chat history."""
    with open(chat_history_file, 'w') as file:
        json.dump(chat_history, file, indent=4)

def load_conversation_memory():
    """Load conversation memory."""
    if os.path.exists(conversation_memory_file):
        try:
            with open(conversation_memory_file, 'r') as file:
                data = json.load(file)
                return data if data else []
        except json.JSONDecodeError:
            return []
    return []

def save_conversation_memory(memory):
    """Save conversation memory."""
    with open(conversation_memory_file, 'w') as file:
        json.dump(memory, file, indent=4)

# Initialize OpenAI
apikey = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=apikey,
    temperature=0,
    top_p=1
)

# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=apikey)

persist_directory = 'chroma_db'
try:
    if os.path.exists(persist_directory):
        db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    else:
        db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
except Exception as e:
    logging.error(f"Error with vector database: {e}")
    persist_directory = f'chroma_db_new_{int(time.time())}'
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 5})

# Load conversation memory
previous_memory = load_conversation_memory()
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k=3)
for item in previous_memory:
    if "user" in item and "assistant" in item:
        memory.chat_memory.add_user_message(item["user"])
        memory.chat_memory.add_ai_message(item["assistant"])

# Text splitter for documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    separators=["\n\n", "\n", " "]
)

PROMPT_TEMPLATE = """
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

@app.route('/ask', methods=['POST'])
def ask():
    """Handle user questions."""
    try:
        data = request.get_json()
        user_question = data.get('message', '').strip()
        
        if not user_question:
            return jsonify({"response": "Please provide a question."}), 400
        
        # Check for upload instructions
        if "upload" in user_question.lower() or "internship" in user_question.lower():
            return jsonify({"response": "Click the paperclip icon to upload files, or the folder icon to upload folders."})
        
        # Retrieve context
        try:
            relevant_docs = db.similarity_search(user_question, **retriever.search_kwargs)
        except Exception as e:
            logging.error(f"Retrieval error: {e}")
            relevant_docs = []
        
        retrieval_context = [doc.page_content for doc in relevant_docs] if relevant_docs else ["No syllabus content available."]
        
        # Build prompt
        prompt_text = PROMPT_TEMPLATE.format(
            context="\n".join(retrieval_context),
            question=user_question
        )
        
        # Get response
        response = asyncio.run(llm.ainvoke([HumanMessage(content=prompt_text)]))
        answer = response.content if response and hasattr(response, "content") else "I couldn't process that request."
        
        return jsonify({"response": answer})
        
    except Exception as e:
        logging.error(f"Error in ask endpoint: {e}")
        return jsonify({"response": "An error occurred processing your request."}), 500

@app.route('/upload_folder', methods=['POST'])
def upload_folder():
    """Handle folder uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400

    extracted_info_list = []

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    def process_single_file(file):
        filename = file.filename
        if not filename or not (filename.endswith('.pdf') or filename.endswith('.docx')):
            return None

        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)

        if not extracted_text:
            return None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            extracted_info = loop.run_until_complete(extract_course_information(extracted_text, llm))
        finally:
            loop.close()

        return {filename: extracted_info}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_single_file, file) for file in files]
        for future in as_completed(futures):
            result = future.result()
            if result:
                extracted_info_list.append(result)

    if not extracted_info_list:
        return jsonify({'error': 'No valid files processed.'}), 400

    return jsonify({'extracted_information': extracted_info_list})

def process_file(file_path, filename):
    """Process a single file."""
    try:
        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)
            
        if extracted_text:
            extracted_info = asyncio.run(extract_course_information(extracted_text, llm))
            return {filename: extracted_info}
        else:
            return {filename: {"error": "No text extracted"}}
    except Exception as e:
        logging.error(f"Error processing {filename}: {e}")
        return None

@app.route('/upload_zip', methods=['POST'])
def upload_zip():
    """Handle zip file uploads."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    zip_file = request.files['file']
    if zip_file.filename == '' or not zip_file.filename.endswith('.zip'):
        return jsonify({'error': 'Please upload a valid zip file.'}), 400

    temp_dir = tempfile.mkdtemp()

    try:
        zip_path = os.path.join(temp_dir, zip_file.filename)
        zip_file.save(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        extracted_info_list = []
        futures = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            for root, dirs, files in os.walk(temp_dir):
                for filename in files:
                    if filename.endswith('.pdf') or filename.endswith('.docx'):
                        file_path = os.path.join(root, filename)
                        futures.append(executor.submit(process_file, file_path, filename))
                        
            for future in as_completed(futures):
                result = future.result()
                if result:
                    extracted_info_list.append(result)

        if not extracted_info_list:
            return jsonify({'error': 'No valid files processed.'}), 400

        return jsonify({'extracted_information': extracted_info_list})
        
    except Exception as e:
        logging.error(f"Zip processing error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        shutil.rmtree(temp_dir)

@app.route("/email_report", methods=["POST"])
def email_report():
    """Send compliance report via email."""
    data = request.get_json()
    recipient_email = data.get("email")
    report_html = data.get("report_html")

    try:
        sender_email = os.getenv("GMAIL_USER")
        app_password = os.getenv("GMAIL_PASS")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "NECHE Compliance Report"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        msg.attach(MIMEText(report_html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        return jsonify({"success": True})

    except Exception as e:
        logging.error(f"Email error: {e}")
        return jsonify({"success": False, "error": str(e)})

# Initialize on startup
initialize_chat_history_file()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8001, threaded=True)
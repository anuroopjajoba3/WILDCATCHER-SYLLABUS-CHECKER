"""

File: chatbot.py
Date: 04-23-2025

"""

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

#import chatbot
from flask import Flask, request, jsonify, render_template
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document, HumanMessage
from langchain.memory import ConversationBufferMemory
import re
import json
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import asyncio
import hashlib
from docx import Document as DocxDocument
from database import DocumentInfo, Session
import zipfile
import tempfile
import shutil

import logging

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
# Route for rendering the homepage

# function that iterates through pdf file and extracts text
def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using pdfplumber.
    Args:PDF file path.
    Returns: Extracted text as a string.
    """
    text = []
    with pdfplumber.open(pdf_path) as pdf_doc:
        for page in pdf_doc.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    text = "\n".join(text)

    if not text.strip():
        print(f"Warning: No text extracted from {pdf_path}")
    else:
        print(f"Extracted {len(text)} characters from {pdf_path}")
    
    return text if text.strip() else None

def extract_text_from_docx(docx_path):
    """
    Extracts text from a DOCX file using python-docx.
    Args: DOCX file path.
    Returns: Extracted text as a string.
    """
    full_text = []
    doc = DocxDocument(docx_path)

    # Extract paragraph text
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())

    # Extract table content (new addition)
    for table in doc.tables:
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            full_text.append(" | ".join(row_data))

    combined_text = "\n".join(full_text)

    if not combined_text.strip():
        print(f"Warning: No text extracted from {docx_path}")
        return None
    else:
        print(f"Extracted {len(combined_text)} characters from {docx_path}")
        return combined_text

@app.route('/upload_pdf', methods=['POST'])
def upload_file():
    """
    Uploads a PDF or Word document and extracts course information.
    Returns: JSON response with extracted information or error message.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected. Please upload a valid document.'}), 400

    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return jsonify({'error': 'Invalid file type. Please upload a PDF or Word document (.docx).'}), 400

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

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
    
    logging.info(f"{request.remote_addr} uploaded folder file: {file.filename}")

    # Choose extractor based on file type
    if file.filename.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file_path)
    else:
        extracted_text = extract_text_from_docx(file_path)

    if extracted_text is None:
        return jsonify({'error': 'Failed to extract text from the document. Please check the file format.'}), 400

    extracted_info = asyncio.run(extract_course_information(extracted_text, llm))
    print("Extracted Course Information:", extracted_info)

    if extracted_info and isinstance(extracted_info, dict):
        return jsonify({'extracted_information': extracted_info})
    else:
        return jsonify({'error': "No relevant course information found in the document."}), 400

# function that looks for course information 
async def extract_course_information(text, llm):
    """
    Extracts course information from the provided text using an LLM.
    Args:
        text: Text to extract information from.
        llm: Language model instance for processing.
    Returns: Extracted course information as a dictionary.
        """
    # Trim text to first 15000 characters (or adjust as needed)
    limited_text = text[:30000].strip()

    # Initialize extracted_info to ensure it exists even if errors occur
    extracted_info = None

    # Generate a hash of the limited text for caching
    text_hash = hashlib.md5(limited_text.encode()).hexdigest()

    # Check if already processed
    existing_doc = session.query(DocumentInfo).filter_by(doc_hash=text_hash).first()
    if existing_doc:
        print("Using cached document info.")
        return json.loads(existing_doc.extracted_info)
    
    # Define your prompt
    prompt = f"""
    Extract the following course details from this text in a structured JSON format. 
    If a field is missing from the text, **completely omit that field** from the JSON output. 
    Do NOT insert "Not Specified", "N/A", "Unknown", or any placeholder text.
    If details like Modality, Credits, or Assignment Types are embedded in Course Format or Grading Sections, 
    extract them and place them in their respective fields.
    Course id/ course number is the same as course id. 
    Time and Location is the same as modality.
    If there's some thing after the instructor title/rank, it is instructor department. 
    When you see Final Grade, if there are percentages in the following lines, if that sum up to 100, then those are the final grading scale.



    JSON Structure:
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
        "Program Accreditation Info": "",
    }}

    Text:
    {limited_text}

    **Return only the JSON object. No extra text.**
    """

    # Call the LLM asynchronously
    response = await llm.ainvoke(prompt)

    print("\nDEBUG: OpenAI Raw Response:\n", response.content[:500])

    # Try to extract JSON from the response
    raw_text = response.content.strip()

    if not raw_text.startswith("{"):
        raw_text = raw_text[raw_text.find("{"):]
    if not raw_text.endswith("}"):
        raw_text = raw_text[:raw_text.rfind("}") + 1]

    try:
        extracted_info = json.loads(raw_text)
    except json.JSONDecodeError:
        extracted_info = {"error": "Failed to parse OpenAI response"}

    # Save the result in the database for caching
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



@app.route('/')
def home():
    """Renders the homepage."""
    return render_template('index.html')

# File paths for storing chat history and conversation memory
chat_history_file = 'chat_history.json'
conversation_memory_file = 'conversation_memory.json'

# OpenAI API key for accessing embeddings and language models
apikey = os.getenv("OPENAI_API_KEY")
# Initialize the chat history and conversation memory files if they don't exist
def initialize_chat_history_file():
    """Ensures chat history and conversation memory files are available."""
    if not os.path.exists(chat_history_file):
        with open(chat_history_file, 'w') as file:
            json.dump([], file)
    if not os.path.exists(conversation_memory_file):
        with open(conversation_memory_file, 'w') as file:
            json.dump([], file)

# Load general chat history from a JSON file
def load_chat_history():
    """Loads the chat history from a JSON file."""
    if os.path.exists(chat_history_file):
        try:
            with open(chat_history_file, 'r') as file:
                data = json.load(file)
                return data if data else []
        except json.JSONDecodeError:
            return []
    return []

# Save updated chat history to a JSON file
def save_chat_history(chat_history):
    """Writes updated chat history to a JSON file."""
    with open(chat_history_file, 'w') as file:
        json.dump(chat_history, file, indent=4)

# Load conversation memory from a JSON file
def load_conversation_memory():
    """Loads conversation memory for persistent chat context."""
    if os.path.exists(conversation_memory_file):
        try:
            with open(conversation_memory_file, 'r') as file:
                data = json.load(file)
                return data if data else []
        except json.JSONDecodeError:
            return []
    return []

# Save updated conversation memory to a JSON file
def save_conversation_memory(memory):
    """Writes updated conversation memory to a JSON file."""
    with open(conversation_memory_file, 'w') as file:
        json.dump(memory, file, indent=4)

# Generate a hash for a user's question
def get_question_hash(question):
    """Generates a unique hash for the input question to detect duplicates."""
    normalized_question = " ".join(question.lower().split())
    return hashlib.md5(normalized_question.encode()).hexdigest()

# Retrieve cached response for a hashed question
def get_cached_response(question_hash):
    """Checks if a response to the given question hash already exists in history."""
    chat_history = load_chat_history()
    for entry in chat_history:
        if entry.get("question_hash") == question_hash:
            return entry.get("bot_response")
    return None

# Save a user interaction to chat history
def save_interaction_to_json(user_question, bot_response):
    """Stores the user's question and the bot's response in chat history."""
    chat_history = load_chat_history()
    question_hash = get_question_hash(user_question)
    new_chat = {
        "user_question": user_question,
        "bot_response": bot_response,
        "timestamp": datetime.now().isoformat(),
        "question_hash": question_hash
    }
    # Update existing entry or add a new one
    for entry in chat_history:
        if entry.get("question_hash") == question_hash:
            entry.update(new_chat)
            break
    else:
        chat_history.append(new_chat)
    save_chat_history(chat_history)




# Process multiple PDFs from a directory
def extract_texts_from_multiple_pdfs(pdf_directory):
    """Processes all PDFs in a directory and extracts their content."""
    documents = []
    for pdf_file in os.listdir(pdf_directory):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, pdf_file)
            pdf_text = extract_text_from_pdf(pdf_path)
            documents.append(Document(page_content=pdf_text, metadata={"source": pdf_file}))
    return documents


#pdf_directory = r'C:\Users\juana\Internship class\Spring2025-Team-Marvel\data'  # Use raw string to avoid escape character issues

#documents = extract_texts_from_multiple_pdfs(pdf_directory)

# Split documents into chunks for better context management
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    separators=["\n\n", "\n", " "]
)


# Custom document splitting logic based on weekly sections
def custom_split_documents_by_weeks(documents):
    """Splits documents into logical sections by weeks or content."""
    chunks = []
    for doc in documents:
        if "<TABLE_START>" in doc.page_content:
            week_sections = re.split(r"(Week \d+)", doc.page_content)
            current_week = None
            for part in week_sections:
                week_match = re.match(r"Week \d+", part)
                if week_match:
                    current_week = part.strip()
                elif current_week:
                    chunks.append(Document(page_content=f"{current_week}\n{part.strip()}", metadata=doc.metadata))
        else:
            chunked_texts = text_splitter.split_text(doc.page_content)
            for chunk in chunked_texts:
                chunks.append(Document(page_content=chunk, metadata=doc.metadata))
    return chunks

#texts = custom_split_documents_by_weeks(documents)



# Load OpenAI embeddings for vector search
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=apikey)

# Create a Chroma vector store for semantic search
persist_directory = 'db'
if os.path.exists(persist_directory):
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
else:
    # Create empty database - will be populated when documents are uploaded
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

# Configure a retriever for semantic search
retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 5})

# Set up conversation memory and load previous context

previous_memory = load_conversation_memory()
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k=3)
for item in previous_memory:
    memory.chat_memory.add_user_message(item["user"])
    memory.chat_memory.add_ai_message(item["assistant"])



# Initialize the open AI LLM Model
apikey = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    openai_api_key=apikey,
    temperature=0,
    top_p=1
)

# Define the custom prompt template for friendly, conversational tone
PROMPT_TEMPLATE = """
You are a helpful and friendly assistant who reviews course syllabi to determine if they meet NECHE and UNH minimal compliance requirements.

You should respond to questions based on the syllabus content below.

- If the question is a greeting or casual small talk (e.g., "hi", "how are you", "good morning"), reply politely and conversationally.
- If the question is about syllabus content (like instructor name, grading, schedule), answer based on the information provided.
- If the answer is not in the syllabus, respond with: "I'm sorry, I couldn't find that information in the syllabus."
- If the question is unrelated to NECHE or syllabi (e.g., library help, course registration, study rooms), respond with: "I'm here to help check if your uploaded syllabus meets NECHE and minimal compliance requirements. For other questions, please contact the appropriate department."

---

### Syllabus Content:
{context}

### User's Question:
{question}

--- 

Your Answer:
"""


        # (remove all the hardcoded greeting/small talk/filters here)
@app.route('/ask', methods=['POST'])
def ask():
    """Handles user questions and returns the LLM's response.
    Returns: JSON response with the LLM's answer or error message."""
    try: 
        data = request.get_json()
        user_question = data.get('message', '').strip().lower()  # Normalize input
        if not isinstance(user_question, str) or not user_question:
            return jsonify({"response": "Hmm, I didn't quite catch that. Could you try rephrasing?"}), 400

        # Debug user input

        # Quick check for basic command
        if "internship" in user_question or "upload" in user_question:
            return jsonify({"response": (
                "Click on the 📎 icon to upload file,zip file and 📁 icon to upload  folder below. I'll check the compliance for you."
            )})

        # Retrieve context from Chroma
        try:
            relevant_docs = db.similarity_search(user_question, **retriever.search_kwargs)
            print(f" Retrieved {len(relevant_docs)} relevant docs")
        except Exception as retrieval_error:
            print(" Retrieval error:", retrieval_error)
            return jsonify({"response": ":warning: Retrieval system failed. Check vector DB setup."}), 500

        retrieval_context = [doc.page_content for doc in relevant_docs]

        if not retrieval_context:
            return jsonify({"response": "Sorry, I could not find relevant information in the uploaded syllabus."})

        # Build prompt
        prompt_text = PROMPT_TEMPLATE.format(
            context="\n".join(retrieval_context),
            question=user_question
        )
        print("📄 Prompt (preview):\n", prompt_text[:1000])  # Limit print size

        # Run async LLM
        try:
            response = asyncio.run(llm.ainvoke([HumanMessage(content=prompt_text)]))
            if not response or not hasattr(response, "content"):
                raise ValueError("No content returned from LLM.")
            answer = response.content
            print(" LLM Response:", answer[:500])  # Print part of the answer
        except Exception as llm_error:
            print(" LLM Error:", llm_error)
            return jsonify({"response": f":warning: LLM error: {str(llm_error)}"}), 500

        return jsonify({"response": answer})
    
    except Exception as e:
        print(" Server error:", e)
        return jsonify({"response": f":warning: Server error: {str(e)}"}), 500


from concurrent.futures import ThreadPoolExecutor, as_completed

@app.route('/upload_folder', methods=['POST'])
def upload_folder():
    """Handles folder uploads and processes PDF/Word documents in parallel."""
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
        if filename == '' or not (filename.endswith('.pdf') or filename.endswith('.docx')):
            return None

        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)

        if not extracted_text:
            return None

        # Create a new event loop for this thread
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




from concurrent.futures import ThreadPoolExecutor, as_completed

def process_file(file_path, filename):
    """Processes a single file and extracts course information.
    Args:
        file_path: Path to the file.
        filename: Name of the file.
    Returns: Extracted information as a dictionary.
    """
    try:
        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)
        if extracted_text:
            extracted_info = asyncio.run(extract_course_information(extracted_text, llm))
            return {filename: extracted_info}
        else:
            # If no text was extracted, return a special value or None
            return {filename: {"error": "No text extracted"}}
    except Exception as e:
        print(f"Error processing {filename}: {e}")
    return None




@app.route('/upload_zip', methods=['POST'])
def upload_zip():
    """Handles zip file uploads and processes PDF/Word documents within the zip.
    Returns: JSON response with extracted information or error message.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    zip_file = request.files['file']
    if zip_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not zip_file.filename.endswith('.zip'):
        return jsonify({'error': 'Invalid file type. Please upload a zip file.'}), 400

    # Create a temporary directory to extract the zip contents
    temp_dir = tempfile.mkdtemp()

    try:
        zip_path = os.path.join(temp_dir, zip_file.filename)
        zip_file.save(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        extracted_info_list = []
        futures = []
        with ThreadPoolExecutor(max_workers=4) as executor:  # Adjust max_workers as needed
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
        return jsonify({'error': str(e)}), 500
    finally:
        shutil.rmtree(temp_dir)


from flask import request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

@app.route("/email_report", methods=["POST"])
def email_report():
    """Sends the compliance report via email.
    Returns: JSON response indicating success or failure."""
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
        return jsonify({"success": False, "error": str(e)})



initialize_chat_history_file()
    
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8002, threaded=True)
    
    
    
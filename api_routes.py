"""
API Routes Module
This module contains all Flask route handlers for the chatbot application.
It handles file uploads, chat interactions, and email functionality.
"""

import os
import json
import asyncio
import logging
import tempfile
import shutil
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import request, jsonify, render_template
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.schema import HumanMessage

from document_processing import extract_text_from_pdf, extract_text_from_docx
from course_extraction import extract_course_information
from prompts import CHAT_PROMPT_TEMPLATE
from config import Config


def create_routes(app, ai_models, chat_manager):
    """
    Create all Flask routes for the application.
    
    Args:
        app: Flask application instance
        ai_models: AIModels instance
        chat_manager: ChatManager instance
    """
    
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

        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)

        # Clean old uploads
        uploaded_files = sorted(os.listdir(Config.UPLOAD_FOLDER))
        if len(uploaded_files) > Config.MAX_UPLOAD_FILES:
            for old_file in uploaded_files[:-Config.MAX_UPLOAD_FILES]:
                old_file_path = os.path.join(Config.UPLOAD_FOLDER, old_file)
                if os.path.isdir(old_file_path):
                    shutil.rmtree(old_file_path)
                else:
                    os.remove(old_file_path)

        file_path = os.path.join(Config.UPLOAD_FOLDER, file.filename)
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
        extracted_info = asyncio.run(
            extract_course_information(extracted_text, ai_models.get_llm())
        )
        
        if extracted_info and isinstance(extracted_info, dict):
            return jsonify({'extracted_information': extracted_info})
        else:
            return jsonify({'error': "No relevant course information found."}), 400
    
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
                return jsonify({
                    "response": "Click the paperclip icon to upload files, or the folder icon to upload folders."
                })
            
            # Retrieve context
            try:
                relevant_docs = ai_models.get_db().similarity_search(
                    user_question,
                    **ai_models.get_retriever().search_kwargs
                )
            except Exception as e:
                logging.error(f"Retrieval error: {e}")
                relevant_docs = []
            
            retrieval_context = [doc.page_content for doc in relevant_docs] if relevant_docs else ["No syllabus content available."]
            
            # Build prompt
            prompt_text = CHAT_PROMPT_TEMPLATE.format(
                context="\n".join(retrieval_context),
                question=user_question
            )
            
            # Get response
            response = asyncio.run(
                ai_models.get_llm().ainvoke([HumanMessage(content=prompt_text)])
            )
            answer = response.content if response and hasattr(response, "content") else "I couldn't process that request."
            
            # Save to chat history
            chat_manager.add_conversation(user_question, answer)
            
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

        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)

        def process_single_file(file):
            filename = file.filename
            if not filename or not (filename.endswith('.pdf') or filename.endswith('.docx')):
                return None

            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
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
                extracted_info = loop.run_until_complete(
                    extract_course_information(extracted_text, ai_models.get_llm())
                )
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
            
            def process_file(file_path, filename):
                """Process a single file."""
                try:
                    if filename.endswith('.pdf'):
                        extracted_text = extract_text_from_pdf(file_path)
                    else:
                        extracted_text = extract_text_from_docx(file_path)
                        
                    if extracted_text:
                        extracted_info = asyncio.run(
                            extract_course_information(extracted_text, ai_models.get_llm())
                        )
                        return {filename: extracted_info}
                    else:
                        return {filename: {"error": "No text extracted"}}
                except Exception as e:
                    logging.error(f"Error processing {filename}: {e}")
                    return None
            
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
            sender_email = Config.GMAIL_USER
            app_password = Config.GMAIL_PASS

            if not sender_email or not app_password:
                return jsonify({"success": False, "error": "Email configuration missing"}), 500

            msg = MIMEMultipart("alternative")
            msg["Subject"] = "NECHE Compliance Report"
            msg["From"] = sender_email
            msg["To"] = recipient_email

            msg.attach(MIMEText(report_html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, app_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            logging.info(f"Email sent successfully to {recipient_email}")
            return jsonify({"success": True})

        except Exception as e:
            logging.error(f"Email error: {e}")
            return jsonify({"success": False, "error": str(e)})
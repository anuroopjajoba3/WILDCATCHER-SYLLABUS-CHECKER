import os
import sys
import pytest
import chatbot
from flask import Flask, jsonify
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatbot import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_upload_invalid_file(client: FlaskClient): 
    # Path to a non-PDF file for testing
    sample_txt_path = 'C:/Users/Admin/Spring2025-Team-Marvel/testing/sample.txt'
    
    # Ensure the sample text file exists
    assert os.path.exists(sample_txt_path), "Sample text file does not exist."

    # Open the sample text file in binary mode
    with open(sample_txt_path, 'rb') as txt_file:
        data = {
            'file': (txt_file, 'sample.txt')
        }
        # Send a POST request to the /upload_pdf endpoint with the text file
        response = client.post('/upload_pdf', content_type='multipart/form-data', data=data)
        
        # Verify the response status code
        assert response.status_code == 400, "Invalid file type should return 400 status code."

        # Verify the response data
        response_data = response.get_json()
        assert 'error' in response_data, "Error message not found in response."
        assert response_data['error'] == "Invalid file type. Please upload a PDF file.", "Unexpected error message."

def test_uploaded_pdfs(client: FlaskClient):
    # Directory where uploaded PDFs are saved
    upload_dir = 'C:/Users/Admin/Spring2025-Team-Marvel/uploads'
    
    # Ensure the uploads directory exists
    assert os.path.exists(upload_dir), "Uploads directory does not exist."

    # Check if there are any PDF files in the uploads directory
    pdf_files = [f for f in os.listdir(upload_dir) if f.endswith('.pdf')]
    assert len(pdf_files) > 0, "No PDF files found in the uploads directory."

    for pdf_file in pdf_files:
        pdf_path = os.path.join(upload_dir, pdf_file)
        # Ensure each PDF file exists
        assert os.path.exists(pdf_path), f"Uploaded PDF file {pdf_file} does not exist."

        # Verify the content of the PDF file (optional)
        with open(pdf_path, 'rb') as file:
            content = file.read()
            assert content, f"Uploaded PDF file {pdf_file} is empty."

def test_upload_word_document(client: FlaskClient):
    # Path to a Word document file for testing
    sample_docx_path = 'C:/Users/Admin/Spring2025-Team-Marvel/testing/sample.docx'
    
    # Ensure the sample Word document file exists
    assert os.path.exists(sample_docx_path), "Sample Word document file does not exist."

    # Open the sample Word document file in binary mode
    with open(sample_docx_path, 'rb') as docx_file:
        data = {
            'file': (docx_file, 'sample.docx')
        }
        # Send a POST request to the /upload_pdf endpoint with the Word document file
        response = client.post('/upload_pdf', content_type='multipart/form-data', data=data)
        
        # Verify the response status code
        assert response.status_code == 200, "Valid Word document should return 200 status code."

        # Verify the response data
        response_data = response.get_json()
        assert 'extracted_information' in response_data, "Extracted information not found in response."
        assert response_data['extracted_information'], "No extracted information found in response."

def test_uploaded_word_documents(client: FlaskClient):
    # Directory where uploaded Word documents are saved
    upload_dir = 'C:/Users/Admin/Spring2025-Team-Marvel/uploads'
    
    # Ensure the uploads directory exists
    assert os.path.exists(upload_dir), "Uploads directory does not exist."

    # Check if there are any Word document files in the uploads directory
    docx_files = [f for f in os.listdir(upload_dir) if f.endswith('.docx')]
    assert len(docx_files) > 0, "No Word document files found in the uploads directory."

    for docx_file in docx_files:
        docx_path = os.path.join(upload_dir, docx_file)
        # Ensure each Word document file exists
        assert os.path.exists(docx_path), f"Uploaded Word document file {docx_file} does not exist."

        # Verify the content of the Word document file (optional)
        with open(docx_path, 'rb') as file:
            content = file.read()
            assert content, f"Uploaded Word document file {docx_file} is empty."

if __name__ == '__main__':
    pytest.main()
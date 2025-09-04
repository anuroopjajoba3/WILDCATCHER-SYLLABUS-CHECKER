# automated_testing.py
import os
import json
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document, HumanMessage
from langchain.chat_models import ChatOpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Define paths and parameters
pdf_directory = '/Users/admin/Spring2025-Team-Marvel/data'
persist_directory = 'automated_testing_db'
test_data_file = 'test_data.json'
openai_api_key = "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"

# Function to extract texts and tables from multiple PDFs
def extract_texts_from_multiple_pdfs(pdf_directory):
    documents = []
    for pdf_file in os.listdir(pdf_directory):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, pdf_file)
            text = ''
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    text += page_text + "\n"
                    tables = page.extract_table()
                    if tables:
                        text += "\n\n" + "\n".join(
                            ["\t".join([str(cell) if cell is not None else '' for cell in row]) for row in tables if row]
                        ) + "\n"
            documents.append(Document(page_content=text, metadata={"source": pdf_file}))
    return documents

# Extract and prepare document data
documents = extract_texts_from_multiple_pdfs(pdf_directory)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
texts = [Document(page_content=chunk, metadata=doc.metadata) for doc in documents for chunk in text_splitter.split_text(doc.page_content)]

# Initialize embeddings and vector store independently
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
auto_db = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)
retriever = auto_db.as_retriever(search_type="similarity", search_kwargs={"k":10})

# Initialize language model
llm = ChatOpenAI(model="GPT-4o mini", openai_api_key=openai_api_key, temperature=0)

# Generate test data
def generate_test_data(documents, num_questions=10):
    test_data = []
    for document in documents:
        prompt = f"Generate {num_questions} questions and answers based on the following content. Return the output in JSON format as a list of objects with 'question' and 'answer' keys:\n\n{document.page_content[:2000]}"
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # Check if response is in JSON format and handle errors gracefully
        try:
            question_answer_pairs = json.loads(response.content)
            for qa in question_answer_pairs:
                test_data.append({
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "source": document.metadata["source"]
                })
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            print("Response content:", response.content)  # Log content for debugging
            continue  # Skip this response if it's not valid JSON

    # Save generated test data to a file
    with open(test_data_file, 'w') as file:
        json.dump(test_data, file, indent=4)


# Similarity scoring function
def calculate_similarity(answer1, answer2):
    embedding1 = embeddings.embed_query(answer1)
    embedding2 = embeddings.embed_query(answer2)
    return cosine_similarity([embedding1], [embedding2])[0][0]

def automated_testing(threshold=0.8):
    with open(test_data_file, 'r') as file:
        test_data = json.load(file)
    
    results = []
    for item in test_data:
        question = item['question']
        expected_answer = item['answer']
        
        # Simulate a chatbot response independently
        response = ask_chatbot(question)
        actual_answer = response.get("response", "")
        
        # Calculate similarity score
        similarity_score = calculate_similarity(actual_answer, expected_answer)
        
        result = {
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
            "similarity_score": similarity_score,
            "is_correct": bool(similarity_score >= threshold)  # Convert numpy.bool_ to Python bool
        }
        results.append(result)

    # Save results to JSON
    with open('test_results.json', 'w') as result_file:
        json.dump(results, result_file, indent=4)

    correct_answers = sum([1 for r in results if r['is_correct']])
    accuracy = correct_answers / len(results)
    print(f"Accuracy: {accuracy:.2f}")


# Independent function to simulate chatbot response
def ask_chatbot(user_question):
    # Use get_relevant_documents instead of calling retriever directly
    relevant_docs = retriever.get_relevant_documents(user_question)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    prompt_text = f"{user_question}\nContext: {context}"
    
    response = llm.invoke([HumanMessage(content=prompt_text)])
    answer = response.content if response else "No answer found"
    return {"response": answer}


# Run the testing
if __name__ == '__main__':
    # Generate test data (optional: comment this out if test data already exists)
    generate_test_data(documents)
    
    # Run automated testing
    automated_testing()

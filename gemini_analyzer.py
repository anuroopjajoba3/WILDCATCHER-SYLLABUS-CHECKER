"""
Gemini Analyzer Module - RAG Enhanced
Uses ChromaDB retrieved context to ground Gemini responses in real syllabus examples.
"""

import json
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()

from config import Config
from rag_pipeline import get_rag_context

# Initialize Gemini client
client = genai.Client(api_key=Config.GEMINI_API_KEY)


def analyze_compliance_summary(extracted_text: str, detector_results: dict) -> dict:
    """
    Uses Gemini + RAG to generate overall compliance summary.
    Retrieves real compliant syllabus examples from ChromaDB as context.
    """
    detector_summary = []
    checks = [
        ("SLOs", detector_results.get("slos", {}).get("status")),
        ("Grading Scale", "PASS" if detector_results.get("grading_scale", {}).get("found") else "FAIL"),
        ("Instructor Info", "PASS" if detector_results.get("instructor", {}).get("found") else "FAIL"),
        ("Office Information", "PASS" if detector_results.get("office_information", {}).get("found") else "FAIL"),
        ("Email", "PASS" if detector_results.get("email_information", {}).get("found") else "FAIL"),
        ("Credit Hours", "PASS" if detector_results.get("credit_hours", {}).get("found") else "FAIL"),
        ("Course Delivery", detector_results.get("modality_status", "FAIL")),
        ("Late Work Policy", "PASS" if detector_results.get("late_information", {}).get("found") else "FAIL"),
        ("Assignment Types", "PASS" if detector_results.get("assignment_types", {}).get("found") else "FAIL"),
    ]
    for name, status in checks:
        detector_summary.append(f"- {name}: {status or 'FAIL'}")

    # RAG: retrieve examples of compliant syllabi for failed items
    failed_items = [name for name, status in checks if status != "PASS"]
    rag_query = f"NECHE compliance requirements: {', '.join(failed_items)}" if failed_items else "complete NECHE compliant syllabus"
    rag_context = get_rag_context(rag_query, n_results=3)

    rag_section = f"""
Reference examples from compliant syllabi in our database:
{rag_context}
""" if rag_context else ""

    prompt = f"""
You are a university accreditation compliance expert reviewing a course syllabus for NECHE standards.

Automated detection results:
{chr(10).join(detector_summary)}

{rag_section}

Syllabus text (first 2000 characters):
{extracted_text[:2000]}

Based on the detection results and reference examples, provide your assessment.
Return ONLY valid JSON, no markdown, no explanation:
{{
    "overall_status": "PASS" or "FAIL",
    "compliance_score": number between 0 and 100,
    "summary": "2-3 sentence plain English summary",
    "top_issues": ["issue 1", "issue 2", "issue 3"],
    "recommendation": "one specific actionable recommendation"
}}
"""

    try:
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        result = json.loads(text)
        return result

    except json.JSONDecodeError:
        logging.error(f"Gemini returned invalid JSON: {response.text}")
        return {
            "overall_status": "UNKNOWN",
            "compliance_score": 0,
            "summary": "Could not generate AI summary.",
            "top_issues": [],
            "recommendation": "Please review the syllabus manually."
        }
    except Exception as e:
        logging.error(f"Gemini API error in analyze_compliance_summary: {e}")
        return None


def answer_syllabus_question(question: str, extracted_text: str) -> str:
    """
    Uses Gemini + RAG to answer questions about a syllabus.
    Retrieves relevant sections from similar syllabi as reference context.
    """
    # RAG: find relevant sections from compliant syllabi
    rag_context = get_rag_context(question, n_results=3)

    rag_section = f"""
Here are relevant sections from other compliant syllabi for reference:
{rag_context}
""" if rag_context else ""

    prompt = f"""
You are a helpful assistant that answers questions about university syllabi.

Uploaded syllabus content (first 4000 characters):
{extracted_text[:4000]}

{rag_section}

User question: {question}

Answer based primarily on the uploaded syllabus content above.
If the information is not in the uploaded syllabus, say so clearly.
Keep your answer under 150 words.
"""

    try:
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API error in answer_syllabus_question: {e}")
        return "Sorry, I couldn't process your question right now. Please try again."
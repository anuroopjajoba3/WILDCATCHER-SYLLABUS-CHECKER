import unittest
from grading_procedures_detection import GradingProceduresDetector

class TestGradingProceduresDetector(unittest.TestCase):
    def test_real_pdf_file(self):
        # Extract text from the real PDF syllabus file
        import os
        sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if sys_path not in os.sys.path:
            os.sys.path.insert(0, sys_path)
        from document_processing import extract_text_from_pdf
        pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ground_truth_syllabus/557_syllabus.pdf'))
        if not os.path.exists(pdf_path):
            self.skipTest(f"PDF file not found: {pdf_path}")
        text = extract_text_from_pdf(pdf_path)
        result = self.detector.detect(text)
        print("PDF Detected:", result)
        # Optionally, add assertions based on expected content
    def setUp(self):
        self.detector = GradingProceduresDetector()

    def test_detect_grading_section(self):
        sample_text = """
        Grading Procedures:
        - Exams: 50%
        - Homework: 30%
        - Participation: 20%
        """
        result = self.detector.detect(sample_text)
        self.assertTrue(result['found'])
        self.assertIn('Exams', result['content'])

    def test_no_grading_section(self):
        sample_text = "This syllabus does not mention grading."
        result = self.detector.detect(sample_text)
        self.assertFalse(result['found'])
        self.assertIsNone(result['content'])

if __name__ == '__main__':
    unittest.main()

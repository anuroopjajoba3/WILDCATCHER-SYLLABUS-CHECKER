
import logging
from typing import Dict, Any

class GradingProceduresDetector:
    """
    Detector for Grading Procedures/Policy/Breakdown sections.
    Uses robust header/content extraction logic, modeled after SLODetector.
    """

    def __init__(self):
        self.field_name = 'grading_procedures'
        self.logger = logging.getLogger('detector.grading_procedures')
        self.approved_titles = [
            "grading procedures", "grading procedure", "grading policy", "grading policies", "grading",
            "grade evaluation", "assessment", "evaluation criteria", "grade breakdown", "how your grade is calculated",
            "grading system", "grading method", "grading components", "basis for grade", "basis of grade", "grading structure",
            "grading scheme", "grading and evaluation", "assignment and grading details", "assignment and grading", "grading details",
            "grading scale", "grading information", "evaluation of student work", "assignment and evaluation", "course evaluation",
            "course requirements and grading", "final grade calculation", "how grades are determined", "grading breakdown", "grading rubric",
            "grade distribution", "marking scheme", "marks distribution", "weighting of assignments", "weight of assignments", "grade weights",
            "grading format", "grading summary", "grading outline", "grading plan", "grading chart", "grading matrix", "grading structure",
            "grading standards", "grading formula", "grading details", "grading explanation", "grading description", "grading process",
            "grading approach", "grading overview", "grading system and policies", "grading and assignments", "grading and requirements",
            "grading rules", "grading scale", "grading breakdown", "grading weights", "grading percentages", "grading criteria"
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info("Starting grading procedures detection")
        if len(text) > 20000:
            text = text[:20000]
            self.logger.info("Truncated large document to 20,000 characters")
        try:
            found, content = self._simple_title_detection(text)
            if found:
                result = {
                    'field_name': self.field_name,
                    'found': True,
                    'content': content
                }
                self.logger.info(f"FOUND: {self.field_name}")
                self.logger.info("SUCCESS: Found approved grading procedures title")
            else:
                result = {
                    'field_name': self.field_name,
                    'found': False,
                    'content': None
                }
                self.logger.info(f"NOT_FOUND: {self.field_name}")
                self.logger.info("No approved grading procedures titles found")
            self.logger.info(f"Detection complete for {self.field_name}: {'SUCCESS' if found else 'NO_MATCH'}")
            return result
        except Exception as e:
            self.logger.error(f"Error in grading procedures detection: {e}")
            return {
                'field_name': self.field_name,
                'found': False,
                'content': None
            }

    def _simple_title_detection(self, text: str) -> tuple[bool, str]:
        lines = text.split('\n')
        potential_matches = []
        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            line_for_comparison = line_clean.replace(':', '').replace('.', '').strip()
            contains_approved_title = False
            for title in self.approved_titles:
                if title in line_for_comparison:
                    line_words = line_for_comparison.split()
                    title_words = title.split()
                    is_valid_header = False
                    if len(line_words) <= len(title_words) + 2:
                        has_proper_formatting = (
                            ':' in line or
                            line.strip().isupper() or
                            (len(line_words) == len(title_words) and not line_clean.endswith((',', ';', '.', '!', '?')))
                        )
                        if has_proper_formatting:
                            is_valid_header = True
                    elif line_for_comparison.startswith(title):
                        if ':' in line or len(line_words) <= len(title_words) + 4:
                            is_valid_header = True
                    elif line_for_comparison.endswith(title):
                        if len(line_words) <= len(title_words) + 3:
                            is_valid_header = True
                    if is_valid_header:
                        contains_approved_title = True
                        break
            if contains_approved_title:
                score = 0
                starts_with_approved = False
                for title in self.approved_titles:
                    if line_for_comparison.startswith(title):
                        starts_with_approved = True
                        break
                if starts_with_approved:
                    score += 10
                if len(line_for_comparison) < 50:
                    score += 5
                if len(line_for_comparison) > 100:
                    score -= 5
                if ':' in line:
                    score += 3
                if line.strip().isupper():
                    score += 2
                potential_matches.append((score, i, line))
        if potential_matches:
            potential_matches.sort(key=lambda x: x[0], reverse=True)
            best_score, best_i, best_line = potential_matches[0]
            if best_score < 5:
                return False, ""
            title = best_line.strip()
            content_lines = [title]
            content_length = len(title)
            for j in range(best_i + 1, min(best_i + 10, len(lines))):
                if j >= len(lines):
                    break
                next_line = lines[j].strip()
                if not next_line:
                    continue
                if any(section in next_line.lower() for section in [
                    'course description', 'course objectives', 'course goals', 'prerequisites', 'textbook', 'grading', 'schedule',
                    'attendance', 'office hours', 'contact', 'instructor', 'modality', 'workload', 'email', 'credit hours',
                    'academic integrity', 'support', 'conduct', 'communication', 'library', 'tutoring', 'final project', 'presentation', 'make-up', 'confidentiality', 'reporting', 'wellness', 'policy', 'plagiarism', 'integrity', 'resources', 'support', 'requirements', 'structure', 'navigation', 'syllabus', 'modules', 'home page']):
                    break
                content_lines.append(next_line)
                content_length += len(next_line)
                if content_length > 500:
                    break
            content = '\n'.join(content_lines)
            return True, content
        print("[DEBUG] No grading section header found.")
        return False, ""

# database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class DocumentInfo(Base):
    __tablename__ = 'document_info'   # This line is critical!
    id = Column(Integer, primary_key=True)
    doc_hash = Column(String(64), unique=True, nullable=False)
    extracted_info = Column(Text, nullable=False)  # Store JSON as text
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Create the engine and session maker
engine = create_engine('sqlite:///documents.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class NormalizedInfo(Base):
    __tablename__ = 'normalized_info'

    id = Column(Integer, primary_key=True)
    course_id = Column(String)
    course_name = Column(String)
    term = Column(String)
    department = Column(String)
    prerequisites = Column(Text)
    instructor_name = Column(String)
    instructor_title = Column(String)
    instructor_department = Column(String)
    instructor_email = Column(String)
    instructor_response_time = Column(Text)
    office_hours = Column(Text)
    course_format = Column(String)
    student_learning_outcomes = Column(Text)
    final_grade_scale = Column(Text)
    assignment_types = Column(Text)
    grading_procedures = Column(Text)
    technical_requirements = Column(Text)
    attendance_policy = Column(Text)
    late_submission_policy = Column(Text)
    academic_integrity = Column(Text)
    extracted_at = Column(DateTime)


from database import Base, engine
Base.metadata.create_all(engine)

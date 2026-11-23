import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime, ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base

class Department(Base):
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    subjects = relationship('CourseSubject', back_populates='department', cascade='all, delete-orphan')
    students = relationship('Student', back_populates='department', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'student_count': len(self.students),
            'subject_count': len(self.subjects)
        }

class CourseSubject(Base):
    __tablename__ = 'course_subjects'

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    code = Column(String(30), nullable=False, unique=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    semester = Column(Integer, nullable=False, default=1)
    credits = Column(Integer, default=3)
    teacher_name = Column(String(100), default='Faculty')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    department = relationship('Department', back_populates='subjects')
    sessions = relationship('AttendanceSession', back_populates='subject', cascade='all, delete-orphan')
    marks = relationship('StudentMark', back_populates='subject', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else '',
            'semester': self.semester,
            'credits': self.credits,
            'teacher_name': self.teacher_name,
            'total_sessions': len(self.sessions)
        }

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    roll_no = Column(String(50), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(120), nullable=False)
    parent_email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    semester = Column(Integer, nullable=False, default=1)
    section = Column(String(10), nullable=False, default='A')
    status = Column(String(20), default='Active')  # Active, Inactive, Suspended
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    department = relationship('Department', back_populates='students')
    attendance_records = relationship('AttendanceRecord', back_populates='student', cascade='all, delete-orphan')
    notifications = relationship('NotificationLog', back_populates='student', cascade='all, delete-orphan')
    marks = relationship('StudentMark', back_populates='student', cascade='all, delete-orphan')

    def calculate_attendance(self, subject_id=None):
        """Calculate attendance stats for this student across all or specific subject"""
        records = [r for r in self.attendance_records if r.session is not None]
        if subject_id:
            records = [r for r in records if r.session.subject_id == subject_id]
        
        total = len(records)
        if total == 0:
            return {'total': 0, 'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'percentage': 100.0, 'status': 'No Sessions'}
        
        present = sum(1 for r in records if r.status == 'PRESENT')
        absent = sum(1 for r in records if r.status == 'ABSENT')
        late = sum(1 for r in records if r.status == 'LATE')
        bypass = sum(1 for r in records if r.status in ('BYPASS', 'EXCUSED'))
        
        # Late is given 0.5 or 1 weight; standard university rule: Late counts as 0.75 or 1.0, Excused doesn't count against
        effective_present = present + bypass
        percentage = round((effective_present / total) * 100, 1)
        
        if percentage >= 85.0:
            status = 'Excellent'
        elif percentage >= 75.0:
            status = 'Good'
        elif percentage >= 65.0:
            status = 'Warning'
        else:
            status = 'Critical'
            
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': bypass,
            'bypass': bypass,
            'percentage': percentage,
            'status': status
        }

    def to_dict(self):
        stats = self.calculate_attendance()
        return {
            'id': self.id,
            'roll_no': self.roll_no,
            'full_name': self.full_name,
            'email': self.email,
            'parent_email': self.parent_email,
            'phone': self.phone,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else '',
            'department_code': self.department.code if self.department else '',
            'semester': self.semester,
            'section': self.section,
            'status': self.status,
            'attendance_percentage': stats['percentage'],
            'attendance_status': stats['status'],
            'total_sessions': stats['total'],
            'absent_count': stats['absent']
        }

class AttendanceSession(Base):
    __tablename__ = 'attendance_sessions'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('course_subjects.id'), nullable=False)
    date = Column(Date, nullable=False, default=datetime.date.today)
    start_time = Column(String(20), default='09:00 AM')
    end_time = Column(String(20), default='10:00 AM')
    semester = Column(Integer, nullable=False)
    section = Column(String(10), nullable=False, default='A')
    topic_covered = Column(String(255), nullable=True)
    created_by = Column(String(100), default='Faculty')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    subject = relationship('CourseSubject', back_populates='sessions')
    records = relationship('AttendanceRecord', back_populates='session', cascade='all, delete-orphan')

    def get_summary(self):
        total = len(self.records)
        if total == 0:
            return {'total': 0, 'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'percentage': 0.0}
        present = sum(1 for r in self.records if r.status == 'PRESENT')
        absent = sum(1 for r in self.records if r.status == 'ABSENT')
        late = sum(1 for r in self.records if r.status == 'LATE')
        bypass = sum(1 for r in self.records if r.status in ('BYPASS', 'EXCUSED'))
        percentage = round(((present + bypass) / total) * 100, 1)
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': bypass,
            'bypass': bypass,
            'percentage': percentage
        }

class StudentMark(Base):
    __tablename__ = 'student_marks'
    __table_args__ = (UniqueConstraint('student_id', 'subject_id', name='uq_student_subject_marks'),)

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('course_subjects.id'), nullable=False)
    mid_sem_marks = Column(Float, nullable=True)
    final_sem_marks = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    student = relationship('Student', back_populates='marks')
    subject = relationship('CourseSubject', back_populates='marks')

class AttendanceRecord(Base):
    __tablename__ = 'attendance_records'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('attendance_sessions.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    status = Column(String(20), nullable=False, default='PRESENT')  # PRESENT, ABSENT, BYPASS
    remarks = Column(String(255), nullable=True)
    marked_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    session = relationship('AttendanceSession', back_populates='records')
    student = relationship('Student', back_populates='attendance_records')

class NotificationLog(Base):
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=True)
    recipient_email = Column(String(120), nullable=False)
    recipient_role = Column(String(20), default='STUDENT')  # STUDENT, PARENT, BOTH
    notification_type = Column(String(50), nullable=False)  # ABSENTEE_ALERT, LOW_ATTENDANCE_WARNING, GENERAL
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    status = Column(String(20), default='SENT')  # SENT, SIMULATED, FAILED
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    student = relationship('Student', back_populates='notifications')

class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)

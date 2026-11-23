import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
from sqlalchemy import func
from database import db_session
from models import (
    Student, Department, CourseSubject, AttendanceSession, StudentMark,
    AttendanceRecord, NotificationLog, SystemSetting
)
from services.notification_service import dispatch_session_absentee_notifications, get_setting

def get_attendance_threshold():
    val = get_setting('attendance_threshold', '75.0')
    try:
        return float(val)
    except (ValueError, TypeError):
        return 75.0

def get_dashboard_metrics():
    """Returns high-level statistics for the main dashboard"""
    total_students = db_session.query(Student).filter_by(status='Active').count()
    total_departments = db_session.query(Department).count()
    total_subjects = db_session.query(CourseSubject).count()
    total_sessions = db_session.query(AttendanceSession).count()
    
    # Today's attendance
    today = datetime.date.today()
    today_sessions = db_session.query(AttendanceSession).filter(AttendanceSession.date == today).all()
    today_records = []
    for s in today_sessions:
        today_records.extend(s.records)
    
    if today_records:
        today_present = sum(1 for r in today_records if r.status in ['PRESENT', 'BYPASS', 'EXCUSED'])
        today_pct = round((today_present / len(today_records)) * 100, 1)
    else:
        # If no session recorded today, calculate past 7 days average
        past_week = today - datetime.timedelta(days=7)
        recent_records = db_session.query(AttendanceRecord).join(AttendanceSession).filter(AttendanceSession.date >= past_week).all()
        if recent_records:
            present_cnt = sum(1 for r in recent_records if r.status in ['PRESENT', 'BYPASS', 'EXCUSED'])
            today_pct = round((present_cnt / len(recent_records)) * 100, 1)
        else:
            today_pct = 0.0

    # Defaulters (< 75%)
    threshold = get_attendance_threshold()
    all_students = db_session.query(Student).filter_by(status='Active').all()
    defaulters = []
    
    for st in all_students:
        stats = st.calculate_attendance()
        if stats['total'] > 0 and stats['percentage'] < threshold:
            defaulters.append({
                'student': st,
                'stats': stats
            })

    # Sort defaulters by lowest percentage first
    defaulters.sort(key=lambda x: x['stats']['percentage'])

    # Recent sessions
    recent_sessions = (
        db_session.query(AttendanceSession)
        .order_by(AttendanceSession.date.desc(), AttendanceSession.id.desc())
        .limit(6)
        .all()
    )

    # Recent notification logs
    recent_notifications = (
        db_session.query(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(5)
        .all()
    )

    return {
        'total_students': total_students,
        'total_departments': total_departments,
        'total_subjects': total_subjects,
        'total_sessions': total_sessions,
        'today_percentage': today_pct,
        'today_sessions_count': len(today_sessions),
        'defaulter_count': len(defaulters),
        'threshold': threshold,
        'defaulters_preview': defaulters[:5],
        'recent_sessions': recent_sessions,
        'recent_notifications': recent_notifications
    }

def get_defaulters_list(threshold=None, department_id=None, semester=None, section=None):
    if threshold is None:
        threshold = get_attendance_threshold()
    else:
        threshold = float(threshold)

    query = db_session.query(Student).filter_by(status='Active')
    if department_id:
        query = query.filter(Student.department_id == int(department_id))
    if semester:
        query = query.filter(Student.semester == int(semester))
    if section:
        query = query.filter(Student.section == section)

    students = query.all()
    defaulters = []

    for st in students:
        stats = st.calculate_attendance()
        if stats['total'] > 0 and stats['percentage'] < threshold:
            defaulters.append({
                'student': st,
                'stats': stats,
                'classes_needed': max(0, int(((threshold * stats['total']) - (stats['present'] * 100)) / (100 - threshold)) + 1)
            })

    defaulters.sort(key=lambda x: x['stats']['percentage'])
    return defaulters

def get_attendance_trends(days=14):
    """Calculates daily attendance percentages for the last N days"""
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)
    
    sessions = (
        db_session.query(AttendanceSession)
        .filter(AttendanceSession.date >= start_date, AttendanceSession.date <= end_date)
        .order_by(AttendanceSession.date.asc())
        .all()
    )
    
    # Group by date
    daily_data = {}
    current = start_date
    while current <= end_date:
        daily_data[current] = {'present': 0, 'total': 0}
        current += datetime.timedelta(days=1)
        
    for s in sessions:
        if s.date in daily_data:
            for r in s.records:
                daily_data[s.date]['total'] += 1
                if r.status in ['PRESENT', 'BYPASS', 'EXCUSED']:
                    daily_data[s.date]['present'] += 1

    labels = []
    data_points = []
    
    for d in sorted(daily_data.keys()):
        labels.append(d.strftime('%b %d'))
        tot = daily_data[d]['total']
        if tot > 0:
            pct = round((daily_data[d]['present'] / tot) * 100, 1)
        else:
            pct = None
        data_points.append(pct)
        
    return {'labels': labels, 'data': data_points}

def get_subject_breakdown():
    """Calculates average attendance percentage for all subjects"""
    subjects = db_session.query(CourseSubject).all()
    breakdown = []
    
    for subj in subjects:
        records = (
            db_session.query(AttendanceRecord)
            .join(AttendanceSession)
            .filter(AttendanceSession.subject_id == subj.id)
            .all()
        )
        total = len(records)
        if total > 0:
            present = sum(1 for r in records if r.status in ['PRESENT', 'BYPASS', 'EXCUSED'])
            pct = round((present / total) * 100, 1)
        else:
            pct = 0.0
            
        breakdown.append({
            'id': subj.id,
            'code': subj.code,
            'name': subj.name,
            'teacher': subj.teacher_name,
            'sessions_count': len(subj.sessions),
            'percentage': pct
        })
        
    return breakdown

def record_new_session(subject_id, session_date, start_time, end_time, semester, section, topic_covered, records_data, auto_notify=True, faculty_name="Faculty"):
    """
    Saves an attendance session and student records.
    records_data: list of dicts [{'student_id': 1, 'status': 'PRESENT', 'remarks': ''}]
    """
    if isinstance(session_date, str):
        session_date = datetime.datetime.strptime(session_date, '%Y-%m-%d').date()

    new_session = AttendanceSession(
        subject_id=int(subject_id),
        date=session_date,
        start_time=start_time,
        end_time=end_time,
        semester=int(semester),
        section=section,
        topic_covered=topic_covered,
        created_by=faculty_name,
        created_at=datetime.datetime.utcnow()
    )
    db_session.add(new_session)
    db_session.flush()  # to get new_session.id

    for item in records_data:
        rec = AttendanceRecord(
            session_id=new_session.id,
            student_id=int(item['student_id']),
            status=item.get('status', 'PRESENT').upper(),
            remarks=item.get('remarks', ''),
            marked_at=datetime.datetime.utcnow()
        )
        db_session.add(rec)

    db_session.commit()

    # Dispatch alerts if requested
    alerts_result = None
    if auto_notify:
        alerts_result = dispatch_session_absentee_notifications(new_session.id)

    return {
        'session_id': new_session.id,
        'alerts_result': alerts_result
    }

def get_student_full_profile(student_id):
    student = db_session.query(Student).get(student_id)
    if not student:
        return None

    overall_stats = student.calculate_attendance()
    
    # Subject wise stats
    all_subjects = db_session.query(CourseSubject).filter(
        CourseSubject.department_id == student.department_id,
        CourseSubject.semester == student.semester
    ).all()

    subject_breakdowns = []
    for subj in all_subjects:
        stats = student.calculate_attendance(subject_id=subj.id)
        subject_breakdowns.append({
            'subject': subj,
            'stats': stats
        })

    # Historical session records sorted desc
    records = (
        db_session.query(AttendanceRecord)
        .join(AttendanceSession)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceSession.date.desc(), AttendanceSession.id.desc())
        .all()
    )

    # Notifications history
    notifications = (
        db_session.query(NotificationLog)
        .filter(NotificationLog.student_id == student.id)
        .order_by(NotificationLog.sent_at.desc())
        .all()
    )

    marks = db_session.query(StudentMark).filter_by(student_id=student.id).all()
    marks_by_subject = {mark.subject_id: mark for mark in marks}

    return {
        'student': student,
        'overall_stats': overall_stats,
        'subject_breakdowns': subject_breakdowns,
        'records': records,
        'notifications': notifications,
        'marks_by_subject': marks_by_subject
    }

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import db_session
from models import NotificationLog, SystemSetting, Student, AttendanceSession
from config import Config

def get_setting(key, default_value=None):
    setting = db_session.query(SystemSetting).filter_by(key=key).first()
    return setting.value if setting else default_value

def get_smtp_config():
    return {
        'server': get_setting('smtp_server', Config.MAIL_SERVER),
        'port': int(get_setting('smtp_port', Config.MAIL_PORT)),
        'use_tls': get_setting('smtp_use_tls', 'true').lower() in ['true', '1', 'on'],
        'username': get_setting('smtp_username', Config.MAIL_USERNAME),
        'password': get_setting('smtp_password', Config.MAIL_PASSWORD),
        'sender': get_setting('mail_sender', Config.MAIL_DEFAULT_SENDER),
        'simulation_mode': get_setting('simulation_mode', 'true').lower() in ['true', '1', 'on']
    }

def send_email_message(to_email, subject, html_content, student_id=None, role='STUDENT', notification_type='GENERAL'):
    """Sends an email via SMTP or records it in simulation mode."""
    if not to_email:
        return {'success': False, 'error': 'No recipient email provided'}

    cfg = get_smtp_config()
    status = 'SIMULATED'
    error_msg = None

    if not cfg['simulation_mode'] and cfg['username'] and cfg['password']:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = cfg['sender']
            msg['To'] = to_email
            
            part = MIMEText(html_content, 'html')
            msg.attach(part)

            server = smtplib.SMTP(cfg['server'], cfg['port'], timeout=10)
            if cfg['use_tls']:
                server.starttls()
            server.login(cfg['username'], cfg['password'])
            server.sendmail(cfg['sender'], [to_email], msg.as_string())
            server.quit()
            status = 'SENT'
        except Exception as e:
            status = 'FAILED'
            error_msg = str(e)
    else:
        # Simulation Mode: Active
        status = 'SIMULATED'

    # Record notification in log
    log_entry = NotificationLog(
        student_id=student_id,
        recipient_email=to_email,
        recipient_role=role,
        notification_type=notification_type,
        subject=subject,
        body_html=html_content,
        status=status,
        error_message=error_msg,
        sent_at=datetime.datetime.utcnow()
    )
    db_session.add(log_entry)
    db_session.commit()

    return {
        'success': status in ['SENT', 'SIMULATED'],
        'status': status,
        'error': error_msg,
        'log_id': log_entry.id
    }

def generate_absentee_email_html(student, session, remarks=""):
    date_str = session.date.strftime('%B %d, %Y') if isinstance(session.date, (datetime.date, datetime.datetime)) else str(session.date)
    subject_name = session.subject.name if session.subject else "Class Session"
    subject_code = session.subject.code if session.subject else "N/A"
    
    stats = student.calculate_attendance()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #1e293b; }}
        .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .header {{ background: linear-gradient(135deg, #e11d48, #be123c); padding: 25px; color: #ffffff; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }}
        .content {{ padding: 30px; }}
        .badge-alert {{ display: inline-block; background: #ffe4e6; color: #9f1239; font-weight: 600; padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-bottom: 15px; }}
        .details-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin: 20px 0; }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; font-size: 14px; }}
        .detail-row:last-child {{ border-bottom: none; }}
        .detail-label {{ color: #64748b; font-weight: 500; }}
        .detail-val {{ font-weight: 600; color: #0f172a; }}
        .stat-banner {{ display: flex; justify-content: space-around; background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
        .stat-num {{ font-size: 20px; font-weight: 700; color: {'#e11d48' if stats['percentage'] < 75 else '#059669'}; }}
        .stat-label {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
        .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>⚠️ Student Absence Notification</h1>
          <p>Official Attendance Management Alert</p>
        </div>
        <div class="content">
          <span class="badge-alert">Status: Unexcused Absence</span>
          <p>Dear <strong>{student.full_name}</strong> (and Parent/Guardian),</p>
          <p>This automated message is to notify you that the student was marked <strong>ABSENT</strong> for the following scheduled academic session:</p>
          
          <div class="details-box">
            <div class="detail-row"><span class="detail-label">Roll Number:</span><span class="detail-val">{student.roll_no}</span></div>
            <div class="detail-row"><span class="detail-label">Subject:</span><span class="detail-val">{subject_name} ({subject_code})</span></div>
            <div class="detail-row"><span class="detail-label">Date & Time:</span><span class="detail-val">{date_str} | {session.start_time} - {session.end_time}</span></div>
            <div class="detail-row"><span class="detail-label">Semester & Section:</span><span class="detail-val">Sem {session.semester} - Sec {session.section}</span></div>
            <div class="detail-row"><span class="detail-label">Topic Covered:</span><span class="detail-val">{session.topic_covered or 'Regular Lecture'}</span></div>
            {f'<div class="detail-row"><span class="detail-label">Remarks:</span><span class="detail-val">{remarks}</span></div>' if remarks else ''}
          </div>

          <div class="stat-banner">
            <div>
              <div class="stat-num">{stats['percentage']}%</div>
              <div class="stat-label">Current Overall Attendance</div>
            </div>
            <div>
              <div class="stat-num">{stats['absent']}</div>
              <div class="stat-label">Total Absences</div>
            </div>
            <div>
              <div class="stat-num">{stats['status']}</div>
              <div class="stat-label">Academic Standing</div>
            </div>
          </div>

          <p style="font-size: 13px; color: #475569; line-height: 1.6;">
            Regular attendance is mandatory for academic compliance and semester eligibility. If you believe this absence was recorded in error, or if you have an official medical excuse, please submit a written request to your course instructor or department head within 48 hours.
          </p>
        </div>
        <div class="footer">
          University Attendance Portal &bull; Automated System Notice &bull; Do not reply directly to this email
        </div>
      </div>
    </body>
    </html>
    """
    return html

def generate_low_attendance_email_html(student, threshold=75.0):
    stats = student.calculate_attendance()
    dept_name = student.department.name if student.department else "Academic Dept"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #1e293b; }}
        .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .header {{ background: linear-gradient(135deg, #d97706, #b45309); padding: 25px; color: #ffffff; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
        .content {{ padding: 30px; }}
        .warning-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px; margin: 15px 0; font-size: 14px; color: #92400e; }}
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }}
        .stat-item {{ background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center; }}
        .stat-val {{ font-size: 20px; font-weight: bold; color: #dc2626; }}
        .stat-lbl {{ font-size: 12px; color: #64748b; }}
        .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>⚠️ Academic Warning: Low Attendance</h1>
          <p>Department of {dept_name}</p>
        </div>
        <div class="content">
          <p>Dear <strong>{student.full_name}</strong> (Roll No: <strong>{student.roll_no}</strong>),</p>
          
          <div class="warning-box">
            <strong>CRITICAL DEFICIT DETECTED:</strong> Your current overall attendance is <strong>{stats['percentage']}%</strong>, which is below the mandatory institutional minimum threshold of <strong>{threshold}%</strong>.
          </div>

          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-val">{stats['percentage']}%</div>
              <div class="stat-lbl">Your Attendance</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{threshold}%</div>
              <div class="stat-lbl">Required Threshold</div>
            </div>
            <div class="stat-item">
              <div class="stat-val" style="color:#0f172a;">{stats['present']}/{stats['total']}</div>
              <div class="stat-lbl">Classes Attended</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{stats['absent']}</div>
              <div class="stat-lbl">Classes Missed</div>
            </div>
          </div>

          <p style="font-size: 14px; line-height: 1.6;">
            Falling below the required {threshold}% threshold may lead to <strong>debarment from final semester examinations</strong> according to university academic regulations.
          </p>
          
          <p style="font-size: 14px; line-height: 1.6;">
            <strong>Required Action:</strong> Please contact your Class Advisor and Department Head immediately to review your attendance deficit and establish an attendance recovery plan.
          </p>
        </div>
        <div class="footer">
          Academic Affairs &bull; Automated Defaulter Tracking System &bull; University Administration
        </div>
      </div>
    </body>
    </html>
    """
    return html

def dispatch_session_absentee_notifications(session_id):
    """Sends absentee alerts to all absent students of a session and their parents"""
    session = db_session.query(AttendanceSession).get(session_id)
    if not session:
        return {'success': False, 'message': 'Session not found'}

    sent_count = 0
    absent_records = [r for r in session.records if r.status == 'ABSENT']
    
    for rec in absent_records:
        student = rec.student
        if not student:
            continue
            
        email_html = generate_absentee_email_html(student, session, rec.remarks)
        subj = f"⚠️ Attendance Alert: Absence recorded for {student.full_name} ({student.roll_no})"

        # Send to student
        if student.email:
            send_email_message(
                to_email=student.email,
                subject=subj,
                html_content=email_html,
                student_id=student.id,
                role='STUDENT',
                notification_type='ABSENTEE_ALERT'
            )
            sent_count += 1
            
        # Send to parent if available
        if student.parent_email:
            send_email_message(
                to_email=student.parent_email,
                subject=f"⚠️ Parent Notice: Absence of {student.full_name} in {session.subject.name if session.subject else 'Class'}",
                html_content=email_html,
                student_id=student.id,
                role='PARENT',
                notification_type='ABSENTEE_ALERT'
            )
            sent_count += 1

    return {'success': True, 'alerts_dispatched': sent_count, 'students_count': len(absent_records)}

def dispatch_low_attendance_warnings(student_ids, threshold=75.0):
    """Dispatches low attendance warnings to specified students"""
    sent_count = 0
    for s_id in student_ids:
        student = db_session.query(Student).get(s_id)
        if not student:
            continue
            
        stats = student.calculate_attendance()
        email_html = generate_low_attendance_email_html(student, threshold)
        subj = f"🚨 URGENT: Low Attendance Warning for {student.full_name} ({stats['percentage']}%)"
        
        if student.email:
            send_email_message(
                to_email=student.email,
                subject=subj,
                html_content=email_html,
                student_id=student.id,
                role='STUDENT',
                notification_type='LOW_ATTENDANCE_WARNING'
            )
            sent_count += 1
            
        if student.parent_email:
            send_email_message(
                to_email=student.parent_email,
                subject=f"🚨 URGENT Parent Notice: Low Attendance Alert for {student.full_name}",
                html_content=email_html,
                student_id=student.id,
                role='PARENT',
                notification_type='LOW_ATTENDANCE_WARNING'
            )
            sent_count += 1

    return {'success': True, 'alerts_sent': sent_count}

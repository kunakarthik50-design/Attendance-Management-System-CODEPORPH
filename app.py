import os
import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, send_file, Response, abort
)
from database import db_session, init_db

def get_or_404(model, item_id):
    item = db_session.query(model).get(item_id)
    if not item:
        abort(404)
    return item
from models import (
    Department, CourseSubject, Student, AttendanceSession, 
    AttendanceRecord, StudentMark, NotificationLog, SystemSetting
)
from services.attendance_service import (
    get_dashboard_metrics, get_defaulters_list, get_attendance_trends,
    get_subject_breakdown, record_new_session, get_student_full_profile,
    get_attendance_threshold
)
from services.notification_service import (
    dispatch_session_absentee_notifications, dispatch_low_attendance_warnings,
    send_email_message, get_smtp_config, get_setting
)
from services.import_export import (
    generate_sample_csv_text, process_student_csv_import,
    generate_attendance_excel_report
)
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# Initialize DB on first run if needed
with app.app_context():
    init_db()

# Global context processor for template helpers
@app.context_processor
def inject_global_vars():
    threshold = get_attendance_threshold()
    unread_logs_count = db_session.query(NotificationLog).count()
    return {
        'current_year': datetime.datetime.now().year,
        'global_threshold': threshold,
        'total_notifications_count': unread_logs_count
    }

# ==========================================
# DASHBOARD
# ==========================================
@app.route('/')
def dashboard():
    metrics = get_dashboard_metrics()
    return render_template('dashboard.html', metrics=metrics)

# ==========================================
# ATTENDANCE MANAGEMENT
# ==========================================
@app.route('/attendance/mark', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        session_date = request.form.get('session_date', str(datetime.date.today()))
        start_time = request.form.get('start_time', '09:00 AM')
        end_time = request.form.get('end_time', '10:00 AM')
        semester = request.form.get('semester', 1)
        section = request.form.get('section', 'A')
        topic_covered = request.form.get('topic_covered', '')
        faculty_name = request.form.get('faculty_name', 'Faculty')
        auto_notify = request.form.get('auto_notify') == 'on'

        # Extract student records from form
        raw_student_ids = request.form.getlist('student_ids[]') or request.form.getlist('student_ids')
        clean_student_ids = []
        for raw_id in raw_student_ids:
            if isinstance(raw_id, str) and (raw_id.startswith('[') or ',' in raw_id):
                import ast
                try:
                    parsed = ast.literal_eval(raw_id)
                    if isinstance(parsed, list):
                        clean_student_ids.extend([str(x) for x in parsed])
                        continue
                except Exception:
                    pass
                for part in raw_id.strip('[]').split(','):
                    part = part.strip().strip("'\"")
                    if part:
                        clean_student_ids.append(part)
            else:
                clean_student_ids.append(str(raw_id))

        records_data = []
        for s_id in clean_student_ids:
            status = request.form.get(f'status_{s_id}', 'PRESENT')
            remarks = request.form.get(f'remarks_{s_id}', '')
            records_data.append({
                'student_id': s_id,
                'status': status,
                'remarks': remarks
            })

        if not records_data:
            flash('No students selected to mark attendance.', 'warning')
            return redirect(url_for('mark_attendance'))

        result = record_new_session(
            subject_id=subject_id,
            session_date=session_date,
            start_time=start_time,
            end_time=end_time,
            semester=semester,
            section=section,
            topic_covered=topic_covered,
            records_data=records_data,
            auto_notify=auto_notify,
            faculty_name=faculty_name
        )

        flash(f'Attendance recorded successfully for {len(records_data)} students!', 'success')
        if auto_notify and result.get('alerts_result'):
            alerts = result['alerts_result']
            flash(f"Dispatched {alerts.get('alerts_dispatched', 0)} absentee email notifications.", 'info')

        return redirect(url_for('view_session', session_id=result['session_id']))

    # GET: Prepare filters and options
    departments = db_session.query(Department).order_by(Department.name).all()
    subjects = db_session.query(CourseSubject).order_by(CourseSubject.name).all()
    
    # Query parameters for pre-selected filters
    selected_dept = request.args.get('department_id', type=int)
    selected_sem = request.args.get('semester', default=4, type=int)
    selected_sec = request.args.get('section', default='A')
    selected_subject = request.args.get('subject_id', type=int)

    # Fetch matching students
    query = db_session.query(Student).filter_by(status='Active')
    if selected_dept:
        query = query.filter(Student.department_id == selected_dept)
    if selected_sem:
        query = query.filter(Student.semester == selected_sem)
    if selected_sec:
        query = query.filter(Student.section == selected_sec)

    students = query.order_by(Student.roll_no).all()

    return render_template(
        'attendance/mark.html',
        departments=departments,
        subjects=subjects,
        students=students,
        selected_dept=selected_dept,
        selected_sem=selected_sem,
        selected_sec=selected_sec,
        selected_subject=selected_subject,
        today_date=str(datetime.date.today())
    )

@app.route('/attendance/history')
def attendance_history():
    subject_id = request.args.get('subject_id', type=int)
    semester = request.args.get('semester', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = db_session.query(AttendanceSession).order_by(AttendanceSession.date.desc(), AttendanceSession.id.desc())
    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    if semester:
        query = query.filter(AttendanceSession.semester == semester)
    if date_from:
        try:
            d_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(AttendanceSession.date >= d_from)
        except ValueError:
            pass
    if date_to:
        try:
            d_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(AttendanceSession.date <= d_to)
        except ValueError:
            pass

    sessions = query.all()
    subjects = db_session.query(CourseSubject).order_by(CourseSubject.name).all()

    return render_template(
        'attendance/history.html',
        sessions=sessions,
        subjects=subjects,
        selected_subject=subject_id,
        selected_sem=semester,
        date_from=date_from,
        date_to=date_to
    )

@app.route('/attendance/session/<int:session_id>')
def view_session(session_id):
    session = get_or_404(AttendanceSession, session_id)
    summary = session.get_summary()
    return render_template('attendance/view_session.html', session=session, summary=summary)

@app.route('/attendance/session/<int:session_id>/update', methods=['POST'])
def update_session(session_id):
    session = get_or_404(AttendanceSession, session_id)
    session.topic_covered = request.form.get('topic_covered', session.topic_covered)
    
    # Update individual records
    for rec in session.records:
        status_key = f"status_{rec.student_id}"
        remarks_key = f"remarks_{rec.student_id}"
        if status_key in request.form:
            rec.status = request.form[status_key].upper()
        if remarks_key in request.form:
            rec.remarks = request.form[remarks_key]

    db_session.commit()
    flash('Attendance session updated successfully!', 'success')
    return redirect(url_for('view_session', session_id=session.id))

@app.route('/attendance/session/<int:session_id>/notify-absentees', methods=['POST'])
def notify_session_absentees(session_id):
    result = dispatch_session_absentee_notifications(session_id)
    if result['success']:
        flash(f"Dispatched {result['alerts_dispatched']} absentee email alerts to students and parents!", 'success')
    else:
        flash(f"Error: {result.get('message', 'Failed to dispatch alerts')}", 'danger')
    return redirect(url_for('view_session', session_id=session_id))

@app.route('/attendance/session/<int:session_id>/delete', methods=['POST'])
def delete_session(session_id):
    session = get_or_404(AttendanceSession, session_id)
    db_session.delete(session)
    db_session.commit()
    flash('Attendance session deleted.', 'info')
    return redirect(url_for('attendance_history'))

# ==========================================
# STUDENT MANAGEMENT
# ==========================================
@app.route('/marks', methods=['GET', 'POST'])
def marks_management():
    selected_semester = request.values.get('semester', default=4, type=int)
    selected_section = request.values.get('section', default='A').strip().upper()
    selected_subject = request.values.get('subject_id', type=int)

    if request.method == 'POST':
        if not selected_subject:
            flash('Select a subject before saving marks.', 'warning')
            return redirect(url_for('marks_management', semester=selected_semester, section=selected_section))

        students = db_session.query(Student).filter_by(
            semester=selected_semester, section=selected_section, status='Active'
        ).order_by(Student.roll_no).all()
        saved_count = 0
        for student in students:
            mid_value = request.form.get(f'mid_{student.id}', '').strip()
            final_value = request.form.get(f'final_{student.id}', '').strip()
            if not mid_value and not final_value:
                continue
            try:
                mid_marks = float(mid_value) if mid_value else None
                final_marks = float(final_value) if final_value else None
                if any(value is not None and not 0 <= value <= 100 for value in (mid_marks, final_marks)):
                    raise ValueError
            except ValueError:
                flash(f'Marks for {student.full_name} must be between 0 and 100.', 'danger')
                return redirect(url_for('marks_management', semester=selected_semester, section=selected_section, subject_id=selected_subject))

            mark = db_session.query(StudentMark).filter_by(
                student_id=student.id, subject_id=selected_subject
            ).first()
            if not mark:
                mark = StudentMark(student_id=student.id, subject_id=selected_subject)
                db_session.add(mark)
            mark.mid_sem_marks = mid_marks
            mark.final_sem_marks = final_marks
            saved_count += 1

        db_session.commit()
        flash(f'Marks saved for {saved_count} students.', 'success')
        return redirect(url_for('marks_management', semester=selected_semester, section=selected_section, subject_id=selected_subject))

    subjects = db_session.query(CourseSubject).filter_by(semester=selected_semester).order_by(CourseSubject.code).all()
    students = db_session.query(Student).filter_by(
        semester=selected_semester, section=selected_section, status='Active'
    ).order_by(Student.roll_no).all()
    marks = {}
    if selected_subject:
        marks = {mark.student_id: mark for mark in db_session.query(StudentMark).filter_by(subject_id=selected_subject).all()}

    return render_template(
        'marks/list.html', subjects=subjects, students=students, marks=marks,
        selected_semester=selected_semester, selected_section=selected_section,
        selected_subject=selected_subject
    )

@app.route('/students')
def student_list():
    department_id = request.args.get('department_id', type=int)
    semester = request.args.get('semester', type=int)
    section = request.args.get('section')
    search_query = request.args.get('q', '').strip()

    query = db_session.query(Student)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if semester:
        query = query.filter(Student.semester == semester)
    if section:
        query = query.filter(Student.section == section)
    if search_query:
        query = query.filter(
            (Student.roll_no.ilike(f'%{search_query}%')) |
            (Student.full_name.ilike(f'%{search_query}%')) |
            (Student.email.ilike(f'%{search_query}%'))
        )

    students = query.order_by(Student.roll_no).all()
    departments = db_session.query(Department).order_by(Department.name).all()

    return render_template(
        'students/list.html',
        students=students,
        departments=departments,
        selected_dept=department_id,
        selected_sem=semester,
        selected_sec=section,
        search_query=search_query
    )

@app.route('/students/new', methods=['POST'])
def create_student():
    roll_no = request.form.get('roll_no', '').strip().upper()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    parent_email = request.form.get('parent_email', '').strip()
    phone = request.form.get('phone', '').strip()
    department_id = request.form.get('department_id', type=int)
    semester = request.form.get('semester', default=1, type=int)
    section = request.form.get('section', default='A').strip().upper()

    if not roll_no or not full_name or not email or not department_id:
        flash('Roll No, Name, Email, and Department are mandatory.', 'danger')
        return redirect(url_for('student_list'))

    existing = db_session.query(Student).filter_by(roll_no=roll_no).first()
    if existing:
        flash(f'Student with Roll No {roll_no} already exists.', 'warning')
        return redirect(url_for('student_list'))

    student = Student(
        roll_no=roll_no,
        full_name=full_name,
        email=email,
        parent_email=parent_email,
        phone=phone,
        department_id=department_id,
        semester=semester,
        section=section,
        status='Active'
    )
    db_session.add(student)
    db_session.commit()

    flash(f'Student {full_name} ({roll_no}) enrolled successfully!', 'success')
    return redirect(url_for('student_list'))

@app.route('/students/<int:student_id>')
def student_profile(student_id):
    profile = get_student_full_profile(student_id)
    if not profile:
        flash('Student not found.', 'danger')
        return redirect(url_for('student_list'))
    departments = db_session.query(Department).all()
    return render_template('students/profile.html', profile=profile, departments=departments)

@app.route('/students/<int:student_id>/edit', methods=['POST'])
def edit_student(student_id):
    student = get_or_404(Student, student_id)
    student.full_name = request.form.get('full_name', student.full_name)
    student.email = request.form.get('email', student.email)
    student.parent_email = request.form.get('parent_email', student.parent_email)
    student.phone = request.form.get('phone', student.phone)
    student.department_id = request.form.get('department_id', student.department_id, type=int)
    student.semester = request.form.get('semester', student.semester, type=int)
    student.section = request.form.get('section', student.section).upper()
    student.status = request.form.get('status', student.status)

    db_session.commit()
    flash(f'Student profile for {student.full_name} updated.', 'success')
    return redirect(url_for('student_profile', student_id=student.id))

@app.route('/students/<int:student_id>/send-warning', methods=['POST'])
def send_student_warning(student_id):
    threshold = get_attendance_threshold()
    result = dispatch_low_attendance_warnings([student_id], threshold=threshold)
    if result['success']:
        flash('Attendance warning notification dispatched to student and parent!', 'success')
    else:
        flash('Failed to send warning alert.', 'danger')
    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/students/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    student = get_or_404(Student, student_id)
    name = student.full_name
    db_session.delete(student)
    db_session.commit()
    flash(f'Student {name} deleted successfully.', 'info')
    return redirect(url_for('student_list'))

# ==========================================
# BULK CSV IMPORT & EXPORT
# ==========================================
@app.route('/students/import', methods=['GET', 'POST'])
def import_students():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected.', 'warning')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file chosen.', 'warning')
            return redirect(request.url)

        if not file.filename.lower().endswith('.csv'):
            flash('Only .csv files are supported for bulk student import.', 'danger')
            return redirect(request.url)

        content = file.read()
        results = process_student_csv_import(content)

        flash(f"Bulk Import Completed: {results['imported']} new students created, {results['updated']} updated.", 'success')
        if results['errors']:
            for err in results['errors'][:5]:
                flash(err, 'warning')
            if len(results['errors']) > 5:
                flash(f"...and {len(results['errors']) - 5} more errors.", 'warning')

        return redirect(url_for('student_list'))

    return render_template('students/import_csv.html')

@app.route('/students/sample-csv')
def download_sample_csv():
    csv_data = generate_sample_csv_text()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=students_import_template.csv"}
    )

# ==========================================
# REPORTS & DEFAULTERS
# ==========================================
@app.route('/reports/defaulters')
def defaulters_report():
    threshold = request.args.get('threshold', default=get_attendance_threshold(), type=float)
    department_id = request.args.get('department_id', type=int)
    semester = request.args.get('semester', type=int)
    section = request.args.get('section')

    defaulters = get_defaulters_list(
        threshold=threshold,
        department_id=department_id,
        semester=semester,
        section=section
    )
    departments = db_session.query(Department).order_by(Department.name).all()

    return render_template(
        'reports/defaulters.html',
        defaulters=defaulters,
        threshold=threshold,
        departments=departments,
        selected_dept=department_id,
        selected_sem=semester,
        selected_sec=section
    )

@app.route('/reports/defaulters/send-batch-alerts', methods=['POST'])
def send_batch_defaulters_alert():
    student_ids = request.form.getlist('selected_students[]')
    threshold = request.form.get('threshold', default=get_attendance_threshold(), type=float)

    if not student_ids:
        flash('No defaulter students selected.', 'warning')
        return redirect(url_for('defaulters_report', threshold=threshold))

    student_int_ids = [int(s) for s in student_ids]
    result = dispatch_low_attendance_warnings(student_int_ids, threshold=threshold)
    
    flash(f"Batch warning alerts dispatched successfully! Sent {result.get('alerts_sent', 0)} notifications to students and parents.", 'success')
    return redirect(url_for('defaulters_report', threshold=threshold))

@app.route('/reports/analytics')
def analytics_report():
    metrics = get_dashboard_metrics()
    subjects_stats = get_subject_breakdown()
    return render_template('reports/analytics.html', metrics=metrics, subjects_stats=subjects_stats)

@app.route('/reports/export-excel')
def export_excel():
    department_id = request.args.get('department_id', type=int)
    semester = request.args.get('semester', type=int)

    excel_bytes = generate_attendance_excel_report(department_id=department_id, semester=semester)
    return Response(
        excel_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": "attachment; filename=attendance_master_report.xlsx"}
    )

# ==========================================
# COURSES & DEPARTMENTS
# ==========================================
@app.route('/courses')
def course_list():
    departments = db_session.query(Department).order_by(Department.name).all()
    subjects = db_session.query(CourseSubject).order_by(CourseSubject.semester, CourseSubject.code).all()
    return render_template('courses/list.html', departments=departments, subjects=subjects)

@app.route('/courses/new-subject', methods=['POST'])
def create_subject():
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()
    department_id = request.form.get('department_id', type=int)
    semester = request.form.get('semester', type=int)
    credits = request.form.get('credits', default=3, type=int)
    teacher_name = request.form.get('teacher_name', 'Faculty').strip()

    if not name or not code or not department_id:
        flash('Subject Name, Code, and Department are required.', 'danger')
        return redirect(url_for('course_list'))

    subject = CourseSubject(
        name=name,
        code=code,
        department_id=department_id,
        semester=semester,
        credits=credits,
        teacher_name=teacher_name
    )
    db_session.add(subject)
    db_session.commit()

    flash(f'Subject {code}: {name} added successfully!', 'success')
    return redirect(url_for('course_list'))

@app.route('/courses/new-department', methods=['POST'])
def create_department():
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()

    if not name or not code:
        flash('Department Name and Code are required.', 'danger')
        return redirect(url_for('course_list'))

    dept = Department(name=name, code=code)
    db_session.add(dept)
    db_session.commit()

    flash(f'Department {name} ({code}) created.', 'success')
    return redirect(url_for('course_list'))

# ==========================================
# NOTIFICATIONS & SETTINGS
# ==========================================
@app.route('/notifications')
def notification_logs():
    notif_type = request.args.get('type')
    status = request.args.get('status')
    
    query = db_session.query(NotificationLog).order_by(NotificationLog.sent_at.desc())
    if notif_type:
        query = query.filter(NotificationLog.notification_type == notif_type)
    if status:
        query = query.filter(NotificationLog.status == status)

    logs = query.limit(100).all()
    return render_template('notifications/logs.html', logs=logs, selected_type=notif_type, selected_status=status)

@app.route('/notifications/<int:log_id>/preview')
def preview_notification(log_id):
    log = get_or_404(NotificationLog, log_id)
    return log.body_html

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        keys = ['attendance_threshold', 'simulation_mode', 'smtp_server', 'smtp_port', 'smtp_use_tls', 'smtp_username', 'smtp_password', 'mail_sender']
        for k in keys:
            val = request.form.get(k, '')
            setting = db_session.query(SystemSetting).filter_by(key=k).first()
            if setting:
                setting.value = val
            else:
                setting = SystemSetting(key=k, value=val)
                db_session.add(setting)

        db_session.commit()
        flash('System & Email configuration saved successfully!', 'success')
        return redirect(url_for('settings'))

    smtp_cfg = get_smtp_config()
    threshold = get_attendance_threshold()
    return render_template('notifications/settings.html', config=smtp_cfg, threshold=threshold)

@app.route('/settings/test-email', methods=['POST'])
def test_email():
    recipient = request.form.get('test_recipient')
    if not recipient:
        flash('Please enter a test email address.', 'warning')
        return redirect(url_for('settings'))

    result = send_email_message(
        to_email=recipient,
        subject="✅ University Attendance Portal - Test Connection Email",
        html_content="""
        <div style="font-family:sans-serif; padding:20px; border:1px solid #e2e8f0; border-radius:8px;">
          <h2 style="color:#0284c7;">SMTP System Test Successful</h2>
          <p>This is a verification email from your <strong>Student Attendance Management Portal</strong>.</p>
          <p>Email delivery and template rendering systems are functioning properly.</p>
        </div>
        """,
        role='STUDENT',
        notification_type='TEST_MESSAGE'
    )

    if result['status'] == 'SENT':
        flash(f"Test email successfully dispatched via SMTP to {recipient}!", 'success')
    elif result['status'] == 'SIMULATED':
        flash(f"Simulation Mode Active: Test email recorded in Notification Hub for {recipient}!", 'info')
    else:
        flash(f"Failed to send email: {result.get('error')}", 'danger')

    return redirect(url_for('settings'))

# ==========================================
# AJAX API ENDPOINTS
# ==========================================
@app.route('/api/students/by-class')
def api_students_by_class():
    dept_id = request.args.get('department_id', type=int)
    semester = request.args.get('semester', type=int)
    section = request.args.get('section', 'A')

    query = db_session.query(Student).filter_by(status='Active')
    if dept_id:
        query = query.filter(Student.department_id == dept_id)
    if semester:
        query = query.filter(Student.semester == semester)
    if section:
        query = query.filter(Student.section == section)

    students = query.order_by(Student.roll_no).all()
    return jsonify([s.to_dict() for s in students])

@app.route('/api/charts/trends')
def api_trends():
    days = request.args.get('days', default=14, type=int)
    data = get_attendance_trends(days=days)
    return jsonify(data)

@app.route('/api/charts/subjects')
def api_subjects_chart():
    data = get_subject_breakdown()
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[START] Starting Attendance Portal at http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)

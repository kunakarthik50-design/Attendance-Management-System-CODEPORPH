import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import io
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from database import db_session
from models import Student, Department, CourseSubject, AttendanceSession, AttendanceRecord
from services.attendance_service import get_defaulters_list, get_attendance_threshold

def generate_sample_csv_text():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['roll_no', 'full_name', 'email', 'parent_email', 'phone', 'department_code', 'semester', 'section'])
    writer.writerow(['CS2026001', 'Alex Johnson', 'alex.j@student.edu', 'parent.johnson@gmail.com', '+1-555-0101', 'CSE', '4', 'A'])
    writer.writerow(['CS2026002', 'Sophia Chen', 'sophia.c@student.edu', 'parent.chen@gmail.com', '+1-555-0102', 'CSE', '4', 'A'])
    writer.writerow(['CS2026003', 'Marcus Vance', 'marcus.v@student.edu', 'parent.vance@gmail.com', '+1-555-0103', 'CSE', '4', 'A'])
    writer.writerow(['IT2026010', 'Priya Sharma', 'priya.s@student.edu', 'parent.sharma@gmail.com', '+1-555-0104', 'IT', '4', 'B'])
    writer.writerow(['EC2026021', 'Liam O\'Connor', 'liam.o@student.edu', 'parent.oconnor@gmail.com', '+1-555-0105', 'ECE', '4', 'A'])
    return output.getvalue()

def process_student_csv_import(file_content):
    """
    Parses CSV text/file and bulk inserts/updates students.
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8-sig', errors='ignore')
        
    reader = csv.DictReader(io.StringIO(file_content))
    
    imported_count = 0
    updated_count = 0
    errors = []
    
    # Pre-fetch departments map {code: dept_object}
    depts = {d.code.upper(): d for d in db_session.query(Department).all()}
    
    row_num = 1
    for row in reader:
        row_num += 1
        roll_no = row.get('roll_no', '').strip()
        full_name = row.get('full_name', '').strip()
        email = row.get('email', '').strip()
        parent_email = row.get('parent_email', '').strip()
        phone = row.get('phone', '').strip()
        dept_code = row.get('department_code', '').strip().upper()
        sem_str = row.get('semester', '1').strip()
        section = row.get('section', 'A').strip().upper()

        if not roll_no or not full_name or not email or not dept_code:
            errors.append(f"Row {row_num}: Missing required fields (roll_no, full_name, email, department_code).")
            continue

        try:
            semester = int(sem_str)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid semester '{sem_str}', defaulting to 1.")
            semester = 1

        # Check department
        dept = depts.get(dept_code)
        if not dept:
            # Create department if not present
            dept = Department(name=f"Dept of {dept_code}", code=dept_code)
            db_session.add(dept)
            db_session.flush()
            depts[dept_code] = dept

        # Check existing student by roll_no
        existing_student = db_session.query(Student).filter_by(roll_no=roll_no).first()
        if existing_student:
            existing_student.full_name = full_name
            existing_student.email = email
            existing_student.parent_email = parent_email
            existing_student.phone = phone
            existing_student.department_id = dept.id
            existing_student.semester = semester
            existing_student.section = section
            updated_count += 1
        else:
            new_student = Student(
                roll_no=roll_no,
                full_name=full_name,
                email=email,
                parent_email=parent_email,
                phone=phone,
                department_id=dept.id,
                semester=semester,
                section=section,
                status='Active'
            )
            db_session.add(new_student)
            imported_count += 1

    db_session.commit()
    return {
        'imported': imported_count,
        'updated': updated_count,
        'errors': errors
    }

def generate_attendance_excel_report(department_id=None, semester=None):
    wb = openpyxl.Workbook()
    ws_master = wb.active
    ws_master.title = "Master Attendance"

    # Styles
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    defaulter_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    good_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Sheet 1: Master Attendance
    headers = ["Roll No", "Full Name", "Department", "Semester", "Section", "Total Sessions", "Present", "Absent", "Late", "Attendance %", "Academic Status"]
    ws_master.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws_master.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    query = db_session.query(Student).filter_by(status='Active')
    if department_id:
        query = query.filter(Student.department_id == int(department_id))
    if semester:
        query = query.filter(Student.semester == int(semester))

    students = query.order_by(Student.roll_no).all()
    
    for row_idx, s in enumerate(students, start=2):
        stats = s.calculate_attendance()
        dept_code = s.department.code if s.department else "GEN"
        
        row_data = [
            s.roll_no,
            s.full_name,
            dept_code,
            s.semester,
            s.section,
            stats['total'],
            stats['present'],
            stats['absent'],
            stats['late'],
            f"{stats['percentage']}%",
            stats['status']
        ]
        ws_master.append(row_data)

        # Style data row
        for col_num in range(1, len(headers) + 1):
            c = ws_master.cell(row=row_idx, column=col_num)
            c.border = thin_border
            if col_num in [1, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
                c.alignment = Alignment(horizontal="center")
            if col_num == 10:
                if stats['percentage'] < 75.0 and stats['total'] > 0:
                    c.fill = defaulter_fill
                    c.font = Font(color="991B1B", bold=True)
                elif stats['percentage'] >= 85.0:
                    c.fill = good_fill
                    c.font = Font(color="166534")

    # Sheet 2: Defaulters Report
    ws_defaulters = wb.create_sheet(title="Defaulters (<75%)")
    def_headers = ["Roll No", "Full Name", "Dept", "Sem-Sec", "Attendance %", "Missed Classes", "Student Email", "Parent Email", "Phone"]
    ws_defaulters.append(def_headers)

    for col_num in range(1, len(def_headers) + 1):
        cell = ws_defaulters.cell(row=1, column=col_num)
        cell.fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    defaulters = get_defaulters_list(threshold=75.0, department_id=department_id, semester=semester)
    for row_idx, item in enumerate(defaulters, start=2):
        st = item['student']
        stats = item['stats']
        dept_code = st.department.code if st.department else "GEN"
        
        row_data = [
            st.roll_no,
            st.full_name,
            dept_code,
            f"Sem {st.semester}-{st.section}",
            f"{stats['percentage']}%",
            stats['absent'],
            st.email,
            st.parent_email or 'N/A',
            st.phone or 'N/A'
        ]
        ws_defaulters.append(row_data)
        for col_num in range(1, len(def_headers) + 1):
            c = ws_defaulters.cell(row=row_idx, column=col_num)
            c.border = thin_border
            if col_num == 5:
                c.fill = defaulter_fill
                c.font = Font(color="991B1B", bold=True)

    # Auto-adjust column widths for both sheets
    for ws in [ws_master, ws_defaulters]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

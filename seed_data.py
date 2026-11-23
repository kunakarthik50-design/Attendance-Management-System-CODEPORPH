import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
import random
from database import db_session, init_db
from models import Department, CourseSubject, Student, AttendanceSession, AttendanceRecord, SystemSetting, NotificationLog

def seed_database():
    init_db()

    # Check if already seeded
    if db_session.query(Department).count() > 0:
        print("Database already contains data. Skipping seed.")
        return

    print("Seeding fresh database with rich academic dataset...")

    # 1. System Settings
    settings = [
        SystemSetting(key='attendance_threshold', value='75.0', description='Minimum attendance percentage required to be in good standing'),
        SystemSetting(key='simulation_mode', value='true', description='When true, emails are simulated and logged in DB without requiring SMTP credentials'),
        SystemSetting(key='smtp_server', value='smtp.gmail.com', description='SMTP Host Server'),
        SystemSetting(key='smtp_port', value='587', description='SMTP Port (587 for TLS)'),
        SystemSetting(key='smtp_use_tls', value='true', description='Use STARTTLS encryption'),
        SystemSetting(key='smtp_username', value='', description='SMTP Username / Email address'),
        SystemSetting(key='smtp_password', value='', description='SMTP Password / App Password'),
        SystemSetting(key='mail_sender', value='attendance-alerts@university.edu', description='Default Sender Email Address')
    ]
    db_session.add_all(settings)
    db_session.flush()

    # 2. Departments
    cse = Department(name="Computer Science & Engineering", code="CSE")
    it = Department(name="Information Technology", code="IT")
    ece = Department(name="Electronics & Communication", code="ECE")
    mech = Department(name="Mechanical Engineering", code="MECH")
    
    db_session.add_all([cse, it, ece, mech])
    db_session.flush()

    # 3. Course Subjects
    subjects = [
        CourseSubject(name="Data Structures & Algorithms", code="CS401", department_id=cse.id, semester=4, credits=4, teacher_name="Dr. Alan Turing"),
        CourseSubject(name="Database Management Systems", code="CS402", department_id=cse.id, semester=4, credits=3, teacher_name="Prof. Grace Hopper"),
        CourseSubject(name="Operating Systems", code="CS403", department_id=cse.id, semester=4, credits=3, teacher_name="Dr. Linus Torvalds"),
        CourseSubject(name="Computer Networks", code="CS404", department_id=cse.id, semester=4, credits=3, teacher_name="Prof. Vint Cerf"),
        CourseSubject(name="Machine Learning & AI", code="CS601", department_id=cse.id, semester=6, credits=4, teacher_name="Dr. Geoffrey Hinton"),
        CourseSubject(name="Web Technologies & Cloud", code="IT401", department_id=it.id, semester=4, credits=3, teacher_name="Prof. Tim Berners-Lee"),
        CourseSubject(name="Digital Signal Processing", code="EC401", department_id=ece.id, semester=4, credits=4, teacher_name="Dr. Claude Shannon"),
    ]
    db_session.add_all(subjects)
    db_session.flush()

    # 4. Students (CSE Semester 4, Section A & B)
    student_data = [
        ("CS2026001", "Alex Rivera", "alex.rivera@student.edu", "p.rivera@gmail.com", "+1-555-0101", cse.id, 4, "A", 0.95),
        ("CS2026002", "Sophia Chen", "sophia.chen@student.edu", "parent.chen@gmail.com", "+1-555-0102", cse.id, 4, "A", 0.92),
        ("CS2026003", "Marcus Vance", "marcus.vance@student.edu", "vance.family@yahoo.com", "+1-555-0103", cse.id, 4, "A", 0.60), # Defaulter (<75%)
        ("CS2026004", "Emma Watson", "emma.watson@student.edu", "watson.guardians@gmail.com", "+1-555-0104", cse.id, 4, "A", 0.88),
        ("CS2026005", "David Kim", "david.kim@student.edu", "kim.parents@outlook.com", "+1-555-0105", cse.id, 4, "A", 0.90),
        ("CS2026006", "Aria Stark", "aria.stark@student.edu", "stark.house@gmail.com", "+1-555-0106", cse.id, 4, "A", 0.58), # Defaulter (<75%)
        ("CS2026007", "Rohan Mehta", "rohan.mehta@student.edu", "mehta.family@gmail.com", "+1-555-0107", cse.id, 4, "A", 0.85),
        ("CS2026008", "Elena Rostova", "elena.rostova@student.edu", "rostov.parent@gmail.com", "+1-555-0108", cse.id, 4, "A", 0.78),
        ("CS2026009", "Lucas Silva", "lucas.silva@student.edu", "silva.p@gmail.com", "+1-555-0109", cse.id, 4, "A", 0.68), # Defaulter (<75%)
        ("CS2026010", "Zoe Saldana", "zoe.s@student.edu", "saldana.p@gmail.com", "+1-555-0110", cse.id, 4, "A", 0.94),
        ("CS2026011", "James Wilson", "james.w@student.edu", "wilson.dad@gmail.com", "+1-555-0111", cse.id, 4, "A", 0.91),
        ("CS2026012", "Chloe Bennet", "chloe.b@student.edu", "bennet.p@gmail.com", "+1-555-0112", cse.id, 4, "A", 0.86),
        # IT Students
        ("IT2026001", "Priya Sharma", "priya.sharma@student.edu", "sharma.p@gmail.com", "+1-555-0201", it.id, 4, "A", 0.93),
        ("IT2026002", "Daniel Craig", "daniel.c@student.edu", "craig.parent@gmail.com", "+1-555-0202", it.id, 4, "A", 0.62), # Defaulter
        ("IT2026003", "Ananya Reddy", "ananya.r@student.edu", "reddy.p@gmail.com", "+1-555-0203", it.id, 4, "A", 0.89),
        # ECE Students
        ("EC2026001", "Liam O'Connor", "liam.oc@student.edu", "oconnor.family@gmail.com", "+1-555-0301", ece.id, 4, "A", 0.91),
        ("EC2026002", "Mia Khalifa", "mia.k@student.edu", "khalifa.p@gmail.com", "+1-555-0302", ece.id, 4, "A", 0.88),
    ]

    students = []
    attendance_weights = {}

    for roll, name, email, p_email, phone, d_id, sem, sec, prob in student_data:
        st = Student(
            roll_no=roll,
            full_name=name,
            email=email,
            parent_email=p_email,
            phone=phone,
            department_id=d_id,
            semester=sem,
            section=sec,
            status='Active'
        )
        db_session.add(st)
        students.append(st)
        attendance_weights[roll] = prob

    db_session.flush()

    # 5. Generate Past 14 Days Attendance Sessions & Records
    today = datetime.date.today()
    cse_students_secA = [s for s in students if s.department_id == cse.id and s.semester == 4 and s.section == 'A']
    cse_subjects = [s for s in subjects if s.department_id == cse.id and s.semester == 4]

    topics = [
        "Binary Search Trees & AVL Rotations",
        "Relational Algebra & SQL Joins",
        "Process Scheduling & CPU Algorithms",
        "TCP vs UDP & Transport Layer Protocols",
        "Graph Traversal: BFS & DFS Implementation",
        "Database Normalization: 1NF to BCNF",
        "Virtual Memory & Page Replacement Strategies",
        "Routing Algorithms: Dijkstra & Bellman-Ford",
        "Dynamic Programming: Knapsack & Matrix Chain",
        "Transaction Management & ACID Properties"
    ]

    session_count = 0
    for day_offset in range(12, -1, -1):
        sess_date = today - datetime.timedelta(days=day_offset)
        # Skip Sundays
        if sess_date.weekday() == 6:
            continue

        # Conduct 2 sessions per day for CSE
        for subj_idx, subj in enumerate(cse_subjects[:2]):
            time_slots = [("09:00 AM", "10:00 AM"), ("11:15 AM", "12:15 PM"), ("02:00 PM", "03:00 PM")]
            slot = time_slots[subj_idx % len(time_slots)]
            
            topic = topics[(day_offset * 2 + subj_idx) % len(topics)]
            sess = AttendanceSession(
                subject_id=subj.id,
                date=sess_date,
                start_time=slot[0],
                end_time=slot[1],
                semester=4,
                section="A",
                topic_covered=topic,
                created_by=subj.teacher_name,
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=day_offset)
            )
            db_session.add(sess)
            db_session.flush()
            session_count += 1

            for st in cse_students_secA:
                p_prob = attendance_weights.get(st.roll_no, 0.85)
                rnd = random.random()
                
                if rnd < p_prob:
                    status = 'PRESENT'
                    remarks = ''
                elif rnd < p_prob + 0.05:
                    status = 'LATE'
                    remarks = 'Arrived 15 mins late'
                else:
                    status = 'ABSENT'
                    remarks = 'Unexcused absence'

                rec = AttendanceRecord(
                    session_id=sess.id,
                    student_id=st.id,
                    status=status,
                    remarks=remarks,
                    marked_at=datetime.datetime.utcnow() - datetime.timedelta(days=day_offset)
                )
                db_session.add(rec)

    # 6. Sample Initial Notification Logs for Absent alerts
    absent_sample = db_session.query(AttendanceRecord).filter_by(status='ABSENT').limit(4).all()
    for rec in absent_sample:
        st = rec.student
        sess = rec.session
        log = NotificationLog(
            student_id=st.id,
            recipient_email=st.email,
            recipient_role='STUDENT',
            notification_type='ABSENTEE_ALERT',
            subject=f"⚠️ Attendance Alert: Absence recorded for {st.full_name} ({st.roll_no})",
            body_html=f"<p>Automated Absentee notification for {st.full_name} in {sess.subject.name} on {sess.date}.</p>",
            status='SIMULATED',
            sent_at=sess.created_at
        )
        db_session.add(log)

    db_session.commit()
    print(f"[SUCCESS] Successfully seeded database with {len(students)} students, {len(subjects)} subjects, and {session_count} sessions.")

if __name__ == '__main__':
    seed_database()

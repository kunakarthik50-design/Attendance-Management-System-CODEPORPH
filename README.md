# 🎓 Student Attendance Management System (AttendTrack)
### Python Capstone Project

A full-stack, production-grade **Student Attendance Management System** built with **Python (Flask + SQLAlchemy ORM)**, featuring an interactive classroom attendance marking grid, automated absentee & low-attendance email notifications, real-time analytics dashboards, and bulk CSV/Excel data management.

---

## 🌟 Key Features

1. **Interactive Attendance Marking Matrix**:
   - **One-Click Toggles**: Quick status selection (`Present`, `Absent`, `Bypass`) for each enrolled student.
   - **Real-Time Live Progress Gauge**: Dynamically calculates the live attendance percentage of the session as statuses are clicked.
   - **Classroom Shortcuts**: "Mark All Present" & "Mark All Absent" 1-click bulk buttons.
   - **Custom Lecture Notes**: Record topic covered, time slot, and individual remarks (e.g. medical leave, official duty).

2. **Automated Absentee & Defaulter Email Alerts**:
   - **Instant Absence Alert**: Automatically generates and dispatches official formatted HTML email notices to absent students and their parents.
   - **Defaulter Warning Engine**: Identifies students falling below the mandatory threshold (e.g., `< 75%`) and provides 1-click batch warning email dispatch.
   - **Built-in SMTP + Simulation Hub**: Operates seamlessly with real SMTP (Gmail, Outlook, custom mail servers) as well as an offline **Simulation Mode** that logs and renders emails in the browser without requiring credentials.

3. **Analytics & Performance Dashboards**:
   - **Executive KPI Cards**: Total students, Today's overall attendance rate, At-risk defaulter count, Total sessions.
   - **Interactive Chart.js Visuals**: 14-day daily attendance trends with smooth gradient lines & course-by-course performance comparison bars.
   - **Defaulter Watchlist**: Instant alerts on students requiring immediate academic intervention.

4. **Student & Course Management**:
   - Comprehensive Student Profiles with overall attendance gauges, subject-by-subject progress bars, and chronological history logs.
   - Multi-department, semester, and section support.
   - Course catalog with instructor assignment and credit tracking.
   - Mid-semester and final-semester marks entry by subject, semester, and section.

5. **Bulk CSV / Excel Operations**:
   - **Bulk CSV Roster Import**: Enroll and update dozens of students in a single click.
   - **Excel Master Report Generator**: Download styled `.xlsx` spreadsheets with Master Attendance and Defaulters lists.

6. **Modern Design System**:
   - Responsive, glassmorphism-inspired UI with **Dark Mode / Light Mode** instant toggle.
   - Fluid micro-animations and clean typography (Plus Jakarta Sans).

---

## 📁 Project Architecture

```
c:\CAPSTONE-2003,6002/
├── app.py                     # Flask web server, application routing & API endpoints
├── config.py                  # Environment and system configuration
├── database.py                # SQLAlchemy engine & session management
├── models.py                  # Relational database models (Student, Session, Record, Notification, etc.)
├── requirements.txt           # Python package dependencies
├── services/
│   ├── attendance_service.py  # Attendance business logic, metrics, trends, and aggregations
│   ├── notification_service.py# Email generation, absentee notifications, low-attendance warnings, SMTP client
│   ├── import_export.py       # CSV parser, bulk importer, and openpyxl Excel report builder
│   └── seed_data.py           # Realistic mock university dataset seeder
├── static/
│   ├── css/
│   │   └── style.css          # Modern Vanilla CSS design system (Dark/Light mode, Glassmorphism)
│   └── js/
│       ├── main.js            # UI themes, flash alerts, modal dialogs
│       ├── attendance.js      # Classroom marking grid, live counters, bulk buttons
│       └── charts.js          # Interactive Chart.js graphs
├── templates/
│   ├── base.html              # Layout master template with sidebar & navigation
│   ├── dashboard.html         # Executive overview dashboard
│   ├── attendance/
│   │   ├── mark.html          # Interactive classroom attendance sheet
│   │   ├── history.html       # Searchable session log
│   │   └── view_session.html  # Session detail and edit interface
│   ├── students/
│   │   ├── list.html          # Student directory with search & filters
│   │   ├── profile.html       # Individual student profile & timeline
│   │   └── import_csv.html    # Bulk CSV upload interface
│   ├── courses/
│   │   └── list.html          # Departments & Course catalog
│   ├── reports/
│   │   ├── defaulters.html    # Defaulters (<75%) report & batch email alert dispatcher
│   │   └── analytics.html     # Deep dive visual analytics & Excel exporter
│   └── notifications/
│       ├── logs.html          # Outbox logs & full HTML email preview modal
│       └── settings.html      # SMTP & threshold configuration
└── sample_data/
    └── sample_students.csv    # Ready-to-use CSV template for bulk student import
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- `pip` package manager

### 2. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database (Optional)
To populate the database with realistic sample departments, subjects, students, and 14 days of attendance sessions:
```bash
python services/seed_data.py
```

### 4. Run the Application
Start the Flask development server:
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## ⚙️ SMTP & Email Notification Setup

### Simulation Mode (Default)
By default, the application runs in **Simulation Mode**. All absentee alerts, parent emails, and low-attendance warnings are generated, styled with rich HTML, and logged in the **Notification Hub** (`/notifications`) where you can preview the rendered emails directly in your browser.

### Real SMTP (e.g. Gmail)
To send real outbound emails:
1. Go to **Settings & SMTP** (`/settings`) in the sidebar.
2. Uncheck **Simulation Mode**.
3. Set **SMTP Server Host** to `smtp.gmail.com` and **Port** to `587`.
4. Enter your Gmail address as **Username** and your 16-character **App Password** as **Password**.
5. Click **Save Settings**, then use the **Test Email Dispatch** box to verify delivery.

---

## 📊 Database Schema Summary

- **`Department`**: `id`, `name`, `code`, `created_at`
- **`CourseSubject`**: `id`, `name`, `code`, `department_id`, `semester`, `credits`, `teacher_name`
- **`Student`**: `id`, `roll_no`, `full_name`, `email`, `parent_email`, `phone`, `department_id`, `semester`, `section`, `status`
- **`AttendanceSession`**: `id`, `subject_id`, `date`, `start_time`, `end_time`, `semester`, `section`, `topic_covered`, `created_by`
- **`AttendanceRecord`**: `id`, `session_id`, `student_id`, `status` (`PRESENT`, `ABSENT`, `BYPASS`), `remarks`, `marked_at`
- **`StudentMark`**: `id`, `student_id`, `subject_id`, `mid_sem_marks`, `final_sem_marks`, `updated_at`
- **`NotificationLog`**: `id`, `student_id`, `recipient_email`, `recipient_role`, `notification_type`, `subject`, `body_html`, `status`, `sent_at`
- **`SystemSetting`**: `id`, `key`, `value`, `description`

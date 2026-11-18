import time
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import Attendance, AuditLog, Course, Enrollment, Grade, Role, Student, User
from .schemas import AttendanceInput, CourseCreate, CourseOut, EnrollmentInput, GradeInput, LoginInput, StudentCreate, StudentOut, TokenOut, UserOut


REQUESTS = Counter("student_cloud_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("student_cloud_http_request_duration_seconds", "Request latency", ["method", "path"])


def audit(db: Session, user_id: int | None, action: str, detail: str) -> None:
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))


def update_student_risk(db: Session, student_id: int) -> float:
    student = db.get(Student, student_id)
    enrollments = db.scalars(select(Enrollment).where(Enrollment.student_id == student_id)).all()
    attendance_rows = [row for enrollment in enrollments for row in enrollment.attendance]
    grade_rows = [row for enrollment in enrollments for row in enrollment.grades]
    attendance_rate = sum(1 for row in attendance_rows if row.present) / len(attendance_rows) if attendance_rows else 1
    grade_rate = sum(row.score / row.maximum for row in grade_rows) / len(grade_rows) if grade_rows else 1
    risk = round(max(0, min(100, (1 - attendance_rate) * 60 + (1 - grade_rate) * 40)), 1)
    if student:
        student.risk_score = risk
    return risk


def seed_data() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))):
            return
        admin = User(name="Cloud Administrator", email="admin@studentsphere.edu", password_hash=hash_password("Admin@123"), role=Role.admin)
        teacher = User(name="Dr. Ananya Rao", email="teacher@studentsphere.edu", password_hash=hash_password("Teacher@123"), role=Role.teacher)
        student_user = User(name="Aarav Sharma", email="student@studentsphere.edu", password_hash=hash_password("Student@123"), role=Role.student)
        db.add_all([admin, teacher, student_user])
        db.flush()
        students = [
            Student(user_id=student_user.id, roll_number="CSE-2026-001", name="Aarav Sharma", email=student_user.email, department="Computer Science", semester=8, admission_year=2023),
            Student(roll_number="CSE-2026-002", name="Meera Kapoor", email="meera@studentsphere.edu", department="Computer Science", semester=8, admission_year=2023),
            Student(roll_number="CSE-2026-003", name="Kabir Singh", email="kabir@studentsphere.edu", department="Computer Science", semester=8, admission_year=2023),
            Student(roll_number="ECE-2026-011", name="Ishita Verma", email="ishita@studentsphere.edu", department="Electronics", semester=8, admission_year=2023),
        ]
        courses = [
            Course(code="CS401", title="Cloud Native Computing", credits=4, teacher_id=teacher.id, capacity=60),
            Course(code="CS402", title="Distributed Systems", credits=4, teacher_id=teacher.id, capacity=50),
            Course(code="CS403", title="Applied Machine Learning", credits=3, teacher_id=teacher.id, capacity=45),
        ]
        db.add_all(students + courses)
        db.flush()
        for student in students:
            for course in courses[:2]:
                enrollment = Enrollment(student_id=student.id, course_id=course.id)
                db.add(enrollment)
                db.flush()
                for offset in range(6):
                    present = not (student.id == students[2].id and offset in {1, 3, 5})
                    db.add(Attendance(enrollment_id=enrollment.id, class_date=date.today() - timedelta(days=offset * 3), present=present))
                score = 68 + (student.id * 5) % 24
                db.add(Grade(enrollment_id=enrollment.id, assessment="Mid Semester", score=score, maximum=100))
        db.flush()
        for student in students:
            update_student_risk(db, student.id)
        audit(db, admin.id, "system.seeded", "Demo tenant initialized")
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUESTS.labels(request.method, request.url.path, "500").inc()
        raise
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    LATENCY.labels(request.method, request.url.path).observe(time.perf_counter() - started)
    response.headers["X-Response-Time"] = f"{time.perf_counter() - started:.4f}s"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(_: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "A record with the same unique value already exists"})


@app.get("/")
def root():
    return {"service": settings.app_name, "version": "2.0.0", "docs": "/api/docs"}


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/auth/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    audit(db, user.id, "auth.login", "Successful sign-in")
    db.commit()
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/api/v1/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student_count = db.scalar(select(func.count(Student.id))) or 0
    course_count = db.scalar(select(func.count(Course.id))) or 0
    attendance_count = db.scalar(select(func.count(Attendance.id))) or 0
    present_count = db.scalar(select(func.count(Attendance.id)).where(Attendance.present.is_(True))) or 0
    attendance_rate = round((present_count / attendance_count * 100) if attendance_count else 0, 1)
    at_risk = db.scalar(select(func.count(Student.id)).where(Student.risk_score >= 30)) or 0
    recent = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(6)).all()
    departments = db.execute(select(Student.department, func.count(Student.id)).group_by(Student.department)).all()
    return {
        "viewer": {"name": user.name, "role": user.role.value},
        "kpis": {"students": student_count, "courses": course_count, "attendanceRate": attendance_rate, "atRisk": at_risk},
        "departments": [{"name": name, "students": count} for name, count in departments],
        "activity": [{"action": row.action, "detail": row.detail, "at": row.created_at.isoformat()} for row in recent],
        "cloud": {"api": "healthy", "database": "connected", "metrics": "collecting", "region": "ap-south"},
    }


@app.get("/api/v1/students", response_model=list[StudentOut])
def list_students(search: str | None = Query(default=None, max_length=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Student).order_by(Student.roll_number)
    if user.role == Role.student:
        query = query.where(Student.user_id == user.id)
    if search:
        query = query.where(Student.name.ilike(f"%{search}%"))
    return db.scalars(query).all()


@app.post("/api/v1/students", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)):
    student = Student(**payload.model_dump())
    db.add(student)
    audit(db, user.id, "student.created", f"Created {payload.roll_number}")
    db.commit()
    db.refresh(student)
    return student


@app.get("/api/v1/courses", response_model=list[CourseOut])
def list_courses(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = db.scalars(select(Course).order_by(Course.code)).all()
    return [CourseOut(id=c.id, code=c.code, title=c.title, credits=c.credits, capacity=c.capacity, enrolled=len(c.enrollments)) for c in courses]


@app.post("/api/v1/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, user: User = Depends(require_roles(Role.admin, Role.teacher)), db: Session = Depends(get_db)):
    course = Course(**payload.model_dump(), teacher_id=user.id if user.role == Role.teacher else None)
    db.add(course)
    audit(db, user.id, "course.created", f"Created {payload.code}")
    db.commit()
    db.refresh(course)
    return CourseOut(**payload.model_dump(), id=course.id, enrolled=0)


@app.post("/api/v1/enrollments", status_code=201)
def enroll(payload: EnrollmentInput, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)):
    if not db.get(Student, payload.student_id) or not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Student or course not found")
    enrollment = Enrollment(**payload.model_dump())
    db.add(enrollment)
    audit(db, user.id, "enrollment.created", f"Student {payload.student_id} joined course {payload.course_id}")
    db.commit()
    db.refresh(enrollment)
    return {"id": enrollment.id, "status": enrollment.status}


@app.post("/api/v1/attendance", status_code=201)
def mark_attendance(payload: AttendanceInput, user: User = Depends(require_roles(Role.admin, Role.teacher)), db: Session = Depends(get_db)):
    enrollment = db.get(Enrollment, payload.enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    row = Attendance(**payload.model_dump())
    db.add(row)
    audit(db, user.id, "attendance.marked", f"Enrollment {payload.enrollment_id}: {payload.present}")
    db.flush()
    risk = update_student_risk(db, enrollment.student_id)
    db.commit()
    return {"status": "recorded", "updatedRiskScore": risk}


@app.post("/api/v1/grades", status_code=201)
def add_grade(payload: GradeInput, user: User = Depends(require_roles(Role.admin, Role.teacher)), db: Session = Depends(get_db)):
    if payload.score > payload.maximum:
        raise HTTPException(status_code=422, detail="Score cannot exceed maximum")
    enrollment = db.get(Enrollment, payload.enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.add(Grade(**payload.model_dump()))
    audit(db, user.id, "grade.recorded", f"Enrollment {payload.enrollment_id}: {payload.assessment}")
    db.flush()
    risk = update_student_risk(db, enrollment.student_id)
    db.commit()
    return {"status": "recorded", "updatedRiskScore": risk}


@app.get("/api/v1/analytics/course/{course_id}")
def course_analytics(course_id: int, _: User = Depends(require_roles(Role.admin, Role.teacher)), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    rates = []
    grades = []
    for enrollment in course.enrollments:
        if enrollment.attendance:
            rates.append(sum(row.present for row in enrollment.attendance) / len(enrollment.attendance) * 100)
        grades.extend(row.score / row.maximum * 100 for row in enrollment.grades)
    return {
        "course": course.code,
        "enrolled": len(course.enrollments),
        "capacityUtilization": round(len(course.enrollments) / course.capacity * 100, 1),
        "averageAttendance": round(sum(rates) / len(rates), 1) if rates else 0,
        "averageGrade": round(sum(grades) / len(grades), 1) if grades else 0,
    }


@app.get("/api/v1/insights")
def insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    students = db.scalars(select(Student).order_by(Student.risk_score.desc()).limit(5)).all()
    return {
        "generatedFor": user.role.value,
        "items": [
            {"severity": "high" if row.risk_score >= 40 else "medium" if row.risk_score >= 20 else "low", "title": f"{row.name} • {row.roll_number}", "message": f"Academic risk score is {row.risk_score}%. Review attendance and assessment performance."}
            for row in students
        ],
    }


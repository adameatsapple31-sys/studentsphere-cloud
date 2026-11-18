from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Role


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: Role
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StudentCreate(BaseModel):
    roll_number: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    department: str
    semester: int = Field(ge=1, le=12)
    admission_year: int = Field(ge=2000, le=2100)


class StudentOut(StudentCreate):
    id: int
    risk_score: float
    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    code: str
    title: str
    credits: int = Field(ge=1, le=10)
    capacity: int = Field(default=60, ge=1, le=500)


class CourseOut(CourseCreate):
    id: int
    enrolled: int = 0
    model_config = ConfigDict(from_attributes=True)


class EnrollmentInput(BaseModel):
    student_id: int
    course_id: int


class AttendanceInput(BaseModel):
    enrollment_id: int
    class_date: date
    present: bool


class GradeInput(BaseModel):
    enrollment_id: int
    assessment: str
    score: float = Field(ge=0)
    maximum: float = Field(gt=0)


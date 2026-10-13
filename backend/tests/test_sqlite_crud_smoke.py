"""S1-12：SQLite 内存库 CRUD 冒烟；不连接或清理本机 MySQL。"""
from app.models import Course, User, UserRole


def test_user_and_course_crud_on_sqlite(sqlite_session):
    session = sqlite_session

    user = User(id=1, username="teacher-smoke", password_hash="x" * 60)
    session.add(user)
    session.flush()
    session.add(UserRole(id=1, user_id=user.id, role="teacher"))
    course = Course(
        id=1,
        teacher_id=user.id,
        name="SQLite 冒烟课程",
        invite_code="SMOKE1",
    )
    session.add(course)
    session.commit()

    stored_course = session.get(Course, 1)
    assert stored_course is not None
    assert stored_course.name == "SQLite 冒烟课程"
    assert session.query(UserRole).filter_by(user_id=1, role="teacher").count() == 1

    stored_course.name = "已更新课程名"
    session.commit()
    session.refresh(stored_course)
    assert stored_course.name == "已更新课程名"

    session.delete(stored_course)
    session.commit()
    assert session.get(Course, 1) is None

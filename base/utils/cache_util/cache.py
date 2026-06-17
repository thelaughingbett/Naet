from django.core.cache import cache
from base.models import Student, StudentFeeAccount, Session

""" 
    Timeout guide for your models

    active_session   → 600s (10 min) — changes rarely, only on rollover
    student profile  → 300s (5 min)  — changes occasionally
    fee account      → 120s (2 min)  — balance changes on payment
    enrollments      → 300s (5 min)  — changes at start of semester
    timetable        → 600s (10 min) — rarely changes mid-session
"""


def get_student(user, timeout=300):
    """Cache the student profile for this user"""
    key = f'student:{user.pk}'
    student = cache.get(key)

    if student is None:
        try:
            student = Student.objects.select_related(
                'class_entered__programme__department__school'
            ).get(user=user)
            cache.set(key, student, timeout)
        except Student.DoesNotExist:
            return None

    return student


def get_active_session(timeout=600):
    """Session changes rarely — cache longer"""
    key = 'active_session'
    session = cache.get(key)

    if session is None:
        try:
            session = Session.objects.get(is_active=True)
            cache.set(key, session, timeout)
        except Session.DoesNotExist:
            return None

    return session


def get_fee_account(student, session, timeout=120):
    """Cache fee account per student per session"""
    key = f'fee_account:{student.pk}:{session.pk}'
    account = cache.get(key)

    if account is None:
        try:
            account = StudentFeeAccount.objects.select_related(
                'fee_structure'
            ).get(student=student, session=session)
            cache.set(key, account, timeout)
        except StudentFeeAccount.DoesNotExist:
            return None

    return account


def invalidate_fee_account(student, session):
    """Call this after a payment is made"""
    key = f'fee_account:{student.pk}:{session.pk}'
    cache.delete(key)


def invalidate_student(user):
    """Call this after student profile is updated"""
    key = f'student:{user.pk}'
    cache.delete(key)

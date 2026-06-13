from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.db.models.signals import (
    pre_save,   # fires just BEFORE a model is saved
    post_save,  # fires just AFTER a model is saved
    pre_delete,  # fires just BEFORE a model is deleted
    post_delete,  # fires just AFTER a model is deleted
    post_migrate
)
from django.db import transaction

from base.models import Curriculum, Enrollment, Session, User
from base.utils.signals import send_notification
from base.utils.notifications.handlers import NotificationEngine


class ScopedUser:
    @staticmethod
    def getProfile(instance):
        if hasattr(instance, 'student_profile'):
            return 'Student'

        elif hasattr(instance, 'deptadmin_profile'):
            return 'DeptAdmin'

        elif hasattr(instance, 'lecturer_profile'):
            return 'Lecturer'

        elif hasattr(instance, 'schooladmin_profile'):
            return 'SchoolAdmin'

        elif hasattr(instance, 'instituionadmin_profile'):
            return 'InstitutionAdmin'

        elif hasattr(instance, 'hostelwarden_profile'):
            return 'HosteWarden'

        elif hasattr(instance, 'itstaff_profile'):
            return 'ITSTAFF'

        elif hasattr(instance, 'financestaff'):
            return 'FinanceStaff'


@receiver(post_save, sender='base.Student')
def auto_enroll_core_courses(
    sender,
    instance,
    created,
    **kwargs
):
    if created:
        try:
            current_session = Session.objects.get(is_active=True)
            core_subjects = Curriculum.objects.filter(
                Tclass=instance.class_entered,
                session=current_session,
                course__course_type__in=['C', 'CC']
            )

            Enrollment.objects.bulk_create([
                Enrollment(
                    student=instance,
                    curriculum=curriculum,
                    status='approved'  # core courses auto-approved
                )
                for curriculum in core_subjects
            ],
                ignore_conflicts=True
            )

        except Session.DoesNotExist:
            pass


# To Intergrator  - update the permissions with new models added
@receiver(post_migrate)
def create_roles_and_permissions(
    sender,
    **kwargs
):
    base_ct = ContentType.objects.filter(
        app_label='base',
        model__in=[
            'student',
            'lecturer',
            'course',
            'curriculum',
            'deferment',
            'department',
            'deptadmin',
            'emergencycontact',
            'enrollment',
            'feestructure',
            'studentfeeaccount',
            'hostel',
            'hostelallocation',
            'hostelwarden',
            'overdraft',
            'parentguardian',
            'payment',
            'programme',
            'reporting',
            'result',
            'room',
            'school',
            'schooladmin',
            'session',
            'tclass',
            'timetable',
            'user',
            'deferredstudent',
            'residentstudent',
            'graduatedstudent',
            'itstaff',
            'financestaff',
            'courseevaluation',
            'lecturerevaluation'
        ]
    )

    # --- Student group ---
    student_group, _ = Group.objects.get_or_create(
        name='Student'
    )

    student_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_school',
            'view_department',
            'view_programme',
            'view_session',
            'view_student', 'add_student', 'change_student', 'delete_student',
            'view_studentfeeaccount', 'add_studentfeeaccount', 'change_studentfeeaccount', 'delete_studentfeeaccount',
            'view_reporting', 'add_reporting', 'change_reporting', 'delete_reporting',
            'view_feestructure',
            'view_overdraft', 'change_overdraft', 'add_overdraft',
            'view_studentfeeaccount', 'change_studentfeeaccount', 'add_studentfeeaccount',
            'view_payment', 'change_payment', 'add_payment',
            'view_course',
            'view_curriculum',
            'view_enrollment', 'add_enrollment', 'delete_enrollment', 'change_enrollment',
            'view_deferment', 'add_deferment', 'change_deferment', 'delete_deferment',
            'view_result',
            'view_timetable',
            'view_parentguardian', 'add_parentguardian', 'change_parentguardian', 'delete_parentguardian',
            'view_emergencycontact', 'add_emergencycontact', 'change_emergencycontact', 'delete_emergencycontact',
            'view_hostel',
            'view_room', 'change_room',
            'view_hostelallocation', 'add_hostelallocation', 'change_hostelallocation', 'delete_hostelallocation',
        ]
    )

    # student_group.permissions.set(student_perms)
    student_group.permissions.through.objects.bulk_create(
        [
            student_group.permissions.through(  # create a row in auth_group_permissions
                group=student_group,            # set group_id
                permission=perm                 # set permission_id
            )
            for perm in student_perms           # one row per permission
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- Institution Admin group ---
    institution_admin_group, _ = Group.objects.get_or_create(
        name='InstitutionAdmin'
    )

    institution_admin_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_school', 'add_school', 'change_school', 'delete_school',
            'view_department', 'add_department', 'change_department', 'delete_department',
            'view_programme',
            'view_user', 'add_user', 'change_user', 'delete_user',
            'view_student', 'change_student', 'add_student', 'delete_student',
            'view_lecturer', 'change_lecturer', 'add_lecturer', 'delete_lecturer',
            'view_deptadmin', 'add_deptadmin', 'change_deptadmin', 'delete_deptadmin',
            'view_schooladmin', 'add_schooladmin', 'change_schooladmin', 'delete_schooladmin',
            'view_hostelwarden', 'add_hostelwarden', 'change_hostelwarden', 'delete_hostelwarden',
            'view_itstaff', 'add_itstaff', 'change_itstaff', 'delete_itstaff',
            'view_financestaff', 'add_financestaff', 'change_financestaff', 'delete_financestaff'
        ]
    )

    # institution_admin_group.permissions.set(institution_admin_perms)
    institution_admin_group.permissions.through.objects.bulk_create(
        [
            institution_admin_group.permissions.through(  # create a row in auth_group_permissions
                group=institution_admin_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in institution_admin_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- School Admin group ---
    school_admin_group, _ = Group.objects.get_or_create(
        name='SchoolAdmin'
    )

    school_admin_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_department', 'add_department', 'change_department', 'delete_department',
            'view_programme', 'add_programme', 'change_programme', 'delete_programme',
            'view_tclass', 'add_tclass', 'change_tclass', 'delete_tclass',
            'view_student', 'change_student', 'add_student',
            'view_lecturer', 'change_lecturer', 'add_lecturer', 'delete_lecturer',
            'view_deptadmin', 'add_deptadmin', 'change_deptadmin', 'delete_deptadmin',
            'view_session',
            'view_reporting',
            'view_feestructure', 'add_feestructure', 'change_feestructure', 'delete_feestructure',
            'view_studentfeeaccount',
            'view_overdraft',
            'view_payment',
            'view_course', 'add_course', 'change_course', 'delete_course',
            'view_curriculum', 'add_curriculum', 'change_curriculum', 'delete_curriculum',
            'view_enrollment', 'add_enrollment', 'delete_enrollment', 'change_enrollment',
            'view_deferment', 'add_deferment', 'change_deferment', 'delete_deferment',
            'view_result', 'add_result', 'change_result', 'delete_result',
            'view_timetable', 'add_timetable', 'change_timetable', 'delete_timetable'
        ]
    )
    # school_admin_group.permissions.set(school_admin_perms)
    school_admin_group.permissions.through.objects.bulk_create(
        [
            school_admin_group.permissions.through(  # create a row in auth_group_permissions
                group=school_admin_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in school_admin_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- Dept Admin group ---
    dept_admin_group, _ = Group.objects.get_or_create(
        name='DeptAdmin'
    )

    dept_admin_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_programme', 'add_programme', 'change_programme', 'delete_programme',
            'view_tclass', 'add_tclass', 'change_tclass', 'delete_tclass',
            'view_student', 'change_student', 'add_student',
            'view_lecturer', 'change_lecturer', 'add_lecturer', 'delete_lecturer',
            'view_session',
            'view_reporting',
            'view_feestructure', 'add_feestructure', 'change_feestructure', 'delete_feestructure',
            'view_studentfeeaccount',
            'view_payment',
            'view_course', 'add_course', 'change_course', 'delete_course',
            'view_curriculum', 'add_curriculum', 'change_curriculum', 'delete_curriculum',
            'view_enrollment', 'add_enrollment', 'delete_enrollment', 'change_enrollment',
            'view_deferment', 'add_deferment', 'change_deferment', 'delete_deferment',
            'view_result', 'add_result', 'change_result', 'delete_result',
            'view_timetable', 'add_timetable', 'change_timetable', 'delete_timetable'
        ]
    )

    # dept_admin_group.permissions.set(dept_admin_perms)
    dept_admin_group.permissions.through.objects.bulk_create(
        [
            dept_admin_group.permissions.through(  # create a row in auth_group_permissions
                group=dept_admin_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in dept_admin_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- Lecturer group ---
    lecturer_group, _ = Group.objects.get_or_create(name='Lecturer')

    lecturer_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_student',
            'view_result', 'add_result', 'change_result', 'delete_result',
            'view_enrollment',
            'view_curriculum',
            'view_timetable',
        ]
    )

    # lecturer_group.permissions.set(lecturer_perms)
    lecturer_group.permissions.through.objects.bulk_create(
        [
            lecturer_group.permissions.through(  # create a row in auth_group_permissions
                group=lecturer_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in lecturer_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- Hostel Warden group ---
    hostel_warden_group, _ = Group.objects.get_or_create(
        name="HostelWarden"
    )

    hostel_warden_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_hostel',
            'view_room', 'change_room', 'add_room', 'delete_room',
            'view_hostelallocation', 'add_hostelallocation', 'change_hostelallocation', 'delete_hostelallocation',
            'view_student',  # TODO : change to resident student

        ]
    )

    # hostel_warden_group.permissions.set(hostel_warden_perms)
    hostel_warden_group.permissions.through.objects.bulk_create(
        [
            hostel_warden_group.permissions.through(  # create a row in auth_group_permissions
                group=hostel_warden_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in hostel_warden_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- IT Staff group ---
    it_staff_group, _ = Group.objects.get_or_create(
        name='ITSTAFF'
    )

    it_staff_perms = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_user', 'add_user', 'change_user',
            'view_student', 'change_student', 'add_student',
            'view_lecturer', 'change_lecturer', 'add_lecturer',
            'view_deptadmin', 'add_deptadmin', 'change_deptadmin',
            'view_schooladmin', 'add_schooladmin', 'change_schooladmin',
            'view_hostelwarden', 'add_hostelwarden', 'change_hostelwarden',
            'view_parentguardian', 'add_parentguardian', 'change_parentguardian',
            'view_emergencycontact', 'add_emergencycontact', 'change_emergencycontact'
        ]
    )

    # it_staff_group.permissions.set(it_staff_perms)
    it_staff_group.permissions.through.objects.bulk_create(
        [
            it_staff_group.permissions.through(  # create a row in auth_group_permissions
                group=it_staff_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in it_staff_perms
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )

    # --- finance staff group ---
    finance_staff_group, _ = Group.objects.get_or_create(
        name='FinanceStaff'
    )

    finance_staff_perm = Permission.objects.filter(
        content_type__in=base_ct,
        codename__in=[
            'view_payment', 'add_payment', 'change_payment', 'delete_payment',
            'view_overdraft', 'add-overdraft', 'change_overdraft', 'delete_overdraft',
            'view_feestructure', 'add_feestructure', 'change_feestructure', 'delete_feestructure',
            'view_studentfeeaccount', 'add_studentfeeaccount', 'change_studentfeeaccount', 'delete_studentfeeaccount'
        ]
    )

    # finance_staff_group.permissions.set(finance_staff_perm)
    finance_staff_group.permissions.through.objects.bulk_create(
        [
            finance_staff_group.permissions.through(  # create a row in auth_group_permissions
                group=finance_staff_group,            # set group_id
                permission=perm                 # set permission_id
            )
            # one row per permission
            for perm in finance_staff_perm
        ],
        ignore_conflicts=True  # if row already exists, skip it — no error, no duplicate
    )


@receiver(post_save, sender="base.User")
def assign_user_to_group(sender, instance, created, **kwargs):
    if not created:
        return

    group_name = ScopedUser.getProfile(instance)

    if group_name:
        try:
            group = Group.objects.get(name=group_name)
            instance.groups.add(group)
        except Group.DoesNotExist:
            pass


@receiver(send_notification)
def handle_notification_broadcast(
    sender,
    user,
    template_key,
    channels,
    context,
    **kwargs
):
    """Intercepts custom signals and routes them safely."""

    transaction.on_commit(
        lambda: NotificationEngine.route(user, template_key, channels, context)
    )

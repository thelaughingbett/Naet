from base.models import Student, Enrollment, Lecturer, Deferment, Session, Course, LecturerAssignment, LeaveRequest, StudentRiskScore, Result
from staffConsole.utils.analytics import get_at_risk_score
from staffConsole.views.base import RoleRequiredMixin
from django.views import View
from django.shortcuts import render

from django.db.models import Count, Sum


class DeptAdminDashboardView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_dashboard.html'

    def get(self, request):
        admin = self.get_profile()  # NOTE : Possible problem with adminstrative staff
        session = Session.objects.filter(is_active=True).first()
        dept = admin.department

        students = Student.objects.filter(
            class_entered__programme__department=dept,
            class_entered__graduated=None
            # TODO : make sure that class didnt graduate ✔️
        ).select_related(
            'user',
            'class_entered__programme'
        )

        ug = 0

        for student in students:
            if student.class_entered.programme.level == "Undergraduate":
                ug += 1

        pg = students.count() - ug

        courses = Course.objects.filter(
            department=dept
        )

        elective_count = 0

        for course in courses:
            if course.course_type == "EE":
                elective_count += 1

        faculty = Lecturer.objects.filter(
            department=dept
        ).select_related('user')

        # --- faculty workload ---
        faculty_workload = []

        for lect in faculty[:5]:
            workload = LecturerAssignment.objects.filter(
                lecturer=lect,
                curriculum__session=session,
            ).select_related('curriculum__course')

            row = {
                'lec': lect.name,
                'credits': 0
            }

            credits = 0
            checked = []
            for work in workload:
                if work.curriculum.course in checked:
                    continue
                credits += work.curriculum.course.credits

                checked.append(work.curriculum.course)

            row['credits'] = credits
            faculty_workload.append(row)

        # --- Leave Requests ---
        user_dept = []

        for member in faculty:
            if member == admin:
                continue
            user_dept.append(member.user)

        leave_requests = LeaveRequest.objects.filter(
            applicant__in=user_dept,
            status='pending',
        )[:5]

        # --- Risk Scores ---
        dept_risk_scores = StudentRiskScore.objects.filter(
            student__in=students,
            term=session,
            # TODO :  order by tier ✔️
        ).needing_review().ordered_for_queue()[:5]

        # pending_enrollments = Enrollment.objects.filter(
        #     status='pending',
        #     curriculum__Tclass__programme__department=dept,
        #     curriculum__session=session
        # ).select_related('student__user', 'curriculum__course') if session else []

        pending_deferments = Deferment.objects.filter(
            student__class_entered__programme__department=dept,
            status='requested'
        ).select_related('student__user', 'session_deferred')[:5]

        pending_result_approvals = Result.objects.filter(
            enrollment__curriculum__session=session,
            enrollment__student__in=students,
            state='submitted',
            type__in=['E', 'PR']
        ).select_related('enrollment__student', 'enrollment__curriculum')

        # at_risk = [
        #     {'student': s, 'score': get_at_risk_score(s, session)}
        #     for s in students
        #     if session and get_at_risk_score(s, session) >= 40
        # ]

        # at_risk.sort(key=lambda x: x['score'], reverse=True)

        # NOTE : Add a pending results approval here two ✔️
        context = {
            **self.get_context_data(),
            'session':              session,
            'department':           dept,
            'student_count':        students.count(),
            'course_count': courses.count(),
            # 'pending_enrollments':  pending_enrollments,
            'pending_result_approvals': pending_result_approvals,
            'pending_deferments':   pending_deferments,
            # 'at_risk':              at_risk[:10],
            'lecturer_count':       faculty.count(),
            'faculty_workload': faculty_workload,
            'admin': admin,
            'leave_requests': leave_requests,
            'dept_risk_scores': dept_risk_scores,
            'ug': ug,
            'pg': pg,
            'elective_count': elective_count
        }
        return render(request, self.template_name, context)

from base.models import Student, Enrollment, Result, Deferment, Session
from base.utils.analytics import get_at_risk_score
from staffConsole.views.base import RoleRequiredMixin
from django.views import View
from django.shortcuts import render


class DeptAdminDashboardView(RoleRequiredMixin, View):
    required_role = 'deptadmin'
    template_name = 'staff/dept_admin/dashboard.html'

    def get(self, request):
        admin = self.get_profile()
        session = Session.objects.filter(is_active=True).first()
        dept = admin.department

        students = Student.objects.filter(
            class_entered__programme__department=dept
        ).select_related('user', 'class_entered__programme')

        pending_enrollments = Enrollment.objects.filter(
            status='pending',
            curriculum__Tclass__programme__department=dept,
            curriculum__session=session
        ).select_related('student__user', 'curriculum__course') if session else []

        pending_deferments = Deferment.objects.filter(
            student__class_entered__programme__department=dept,
            status='active'
        ).select_related('student__user', 'session_deferred')

        at_risk = [
            {'student': s, 'score': get_at_risk_score(s, session)}
            for s in students
            if session and get_at_risk_score(s, session) >= 40
        ]
        at_risk.sort(key=lambda x: x['score'], reverse=True)

        context = {
            **self.get_context_data(),
            'session':              session,
            'department':           dept,
            'student_count':        students.count(),
            'pending_enrollments':  pending_enrollments,
            'pending_deferments':   pending_deferments,
            'at_risk':              at_risk[:10],
            'lecturer_count':       dept.lecturer_set.count(),
        }
        return render(request, self.template_name, context)

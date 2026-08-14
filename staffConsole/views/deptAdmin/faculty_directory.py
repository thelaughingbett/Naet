from base.models import Student, Enrollment, Lecturer, Deferment, Session, Course, LecturerAssignment
from staffConsole.utils.analytics import get_at_risk_score
from staffConsole.views.base import RoleRequiredMixin
from django.views import View
from django.shortcuts import render

from django.db.models import Sum


class DeptAdminFAcultyDirectoryView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_faculty_directory.html'

    def get(self, request):
        admin = self.get_profile()
        dept = admin.department

        faculty = Lecturer.objects.filter(
            department=dept
        )
        context = {
            'faculty': faculty
        }
        return render(request, self.template_name, context)

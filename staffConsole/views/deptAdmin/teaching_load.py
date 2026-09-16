from django.views import View
from django.shortcuts import render
import json

from staffConsole.views.base import RoleRequiredMixin
from base.models import Session, Lecturer, LecturerAssignment, Curriculum, Syllabus

from rest_framework.serializers import ModelSerializer


class CurriculumSerializer(ModelSerializer):
    class Meta:
        model = Curriculum
        fields = "__all__"


class DeptAdminTeachingLoadView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_teaching_load_allocation.html'

    def get(self, request):
        admin = self.get_profile()
        session = Session.objects.filter(is_active=True).first()
        dept = admin.department

        faculty = Lecturer.objects.filter(
            department=dept
        ).select_related('user')

        # --- faculty workload ---
        faculty_workload = []

        for lect in faculty:
            workload = LecturerAssignment.objects.filter(
                lecturer=lect,
                curriculum__session=session,
            ).select_related(
                'curriculum__course'
            ).prefetch_related(
                'curriculum__classes'
            )

            row = {
                'lec': lect.name,
                'designation': lect.title,
                'credits': 0,
                'courses': []
            }

            credits = 0
            checked = []
            for work in workload:
                class_names = ", ".join(
                    c.class_name for c in work.curriculum.classes.all()
                )
                course = {
                    'code': work.curriculum.course.course_code,
                    'name': work.curriculum.course.course_name,
                    'class': class_names,
                    'credits': work.curriculum.course.credits,
                    'id': str(work.record_id)
                }
                row['courses'].append(course)
                if work.curriculum.course in checked:
                    continue
                credits += work.curriculum.course.credits
                checked.append(work.curriculum.course)

            row['credits'] = credits
            faculty_workload.append(row)

        context = {
            'faculty_workload': faculty_workload,
        }
        return render(request, self.template_name, context)
